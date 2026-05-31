#!/usr/bin/env python3
"""Backfill ERPNext Communication rows from Alpstein PostgreSQL messages.

Default mode is dry-run. The script is intentionally host-run for the current
Docker topology: PostgreSQL is read via `docker exec ... psql`; ERPNext is
written through the same token-authenticated REST API used by n8n.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import requests

DEFAULT_POSTGRES_CONTAINER = "f54f1116670d_alpstein_postgres"
DEFAULT_POSTGRES_USER = "alpstein"
DEFAULT_POSTGRES_DB = "alpstein_ai"
DEFAULT_ERPNEXT_BASE_URL = "https://crm.alpstein-ai.ch"
DEFAULT_ERPNEXT_AUTH_ENV = "/etc/alpstein/erpnext-n8n-api.env"
DEFAULT_N8N_DB = "/var/lib/docker/volumes/alpstein_n8n_data/_data/database.sqlite"
WORKFLOW_ID = "aYrRmAGKhP4TJbG9"


@dataclass(frozen=True)
class LeadRef:
    name: str
    channel: str
    business_id: str
    chat_id: str | None
    external_user_id: str | None
    instagram_username: str | None
    instagram_display_name: str | None


@dataclass(frozen=True)
class Candidate:
    lead_name: str
    sender_type: str
    external_message_id: str
    legacy_external_message_id: str | None
    business_id: str
    channel: str
    conversation_id: str
    communication_date: str
    content: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="create/update ERPNext rows")
    parser.add_argument("--business-id", default="alpstein_ai_demo_001")
    parser.add_argument("--limit", type=int, default=0, help="limit PostgreSQL messages")
    parser.add_argument("--postgres-container", default=DEFAULT_POSTGRES_CONTAINER)
    parser.add_argument("--postgres-user", default=DEFAULT_POSTGRES_USER)
    parser.add_argument("--postgres-db", default=DEFAULT_POSTGRES_DB)
    parser.add_argument("--erpnext-base-url", default=os.getenv("ERPNEXT_BASE_URL", DEFAULT_ERPNEXT_BASE_URL))
    parser.add_argument("--erpnext-auth-env", default=DEFAULT_ERPNEXT_AUTH_ENV)
    parser.add_argument("--n8n-db", default=DEFAULT_N8N_DB)
    parser.add_argument("--skip-profile-backfill", action="store_true")
    return parser.parse_args()


def load_env_file(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    if not Path(path).exists():
        return values
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def erpnext_session(args: argparse.Namespace) -> requests.Session:
    auth_env = load_env_file(args.erpnext_auth_env)
    api_key = os.getenv("ERPNEXT_API_KEY") or auth_env.get("ERPNEXT_API_KEY")
    api_secret = os.getenv("ERPNEXT_API_SECRET") or auth_env.get("ERPNEXT_API_SECRET")
    if not api_key or not api_secret:
        raise RuntimeError("ERPNEXT_API_KEY / ERPNEXT_API_SECRET are required")
    session = requests.Session()
    session.headers.update({"Authorization": f"token {api_key}:{api_secret}"})
    return session


def erpnext_url(args: argparse.Namespace, path: str) -> str:
    return args.erpnext_base_url.rstrip("/") + path


def erpnext_get_list(
    session: requests.Session,
    args: argparse.Namespace,
    doctype: str,
    *,
    filters: list[Any],
    fields: list[str],
    limit: int = 1000,
) -> list[dict[str, Any]]:
    response = session.get(
        erpnext_url(args, f"/api/resource/{doctype}"),
        params={
            "filters": json.dumps(filters),
            "fields": json.dumps(fields),
            "limit_page_length": str(limit),
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("data", [])


def erpnext_insert(
    session: requests.Session,
    args: argparse.Namespace,
    doctype: str,
    body: dict[str, Any],
) -> str:
    response = session.post(
        erpnext_url(args, f"/api/resource/{doctype}"),
        json=body,
        timeout=30,
    )
    response.raise_for_status()
    name = response.json().get("data", {}).get("name")
    if not name:
        raise RuntimeError(f"ERPNext {doctype} response missing name")
    return str(name)


def erpnext_update(
    session: requests.Session,
    args: argparse.Namespace,
    doctype: str,
    name: str,
    body: dict[str, Any],
) -> None:
    response = session.put(
        erpnext_url(args, f"/api/resource/{doctype}/{name}"),
        json=body,
        timeout=30,
    )
    response.raise_for_status()


def load_messages(args: argparse.Namespace) -> list[dict[str, Any]]:
    limit_sql = f" limit {int(args.limit)}" if args.limit else ""
    sql = f"""
select coalesce(json_agg(row_to_json(q)), '[]'::json)
from (
  select
    m.id::text as id,
    m.created_at::text as created_at,
    m.channel,
    m.sender_type,
    m.direction,
    nullif(m.external_message_id, '') as external_message_id,
    m.conversation_id::text as conversation_id,
    c.external_conversation_id,
    cu.external_customer_id,
    b.external_id as business_external_id,
    m.message_text
  from messages m
  join conversations c on c.id = m.conversation_id
  join customers cu on cu.id = c.customer_id
  join businesses b on b.id = m.business_id
  where m.channel in ('telegram', 'instagram')
    and b.external_id = '{args.business_id}'
  order by m.created_at asc, m.id asc
  {limit_sql}
) q;
"""
    result = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            args.postgres_container,
            "psql",
            "-U",
            args.postgres_user,
            "-d",
            args.postgres_db,
            "-t",
            "-A",
            "-c",
            sql,
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout.strip() or "[]")


def load_leads(session: requests.Session, args: argparse.Namespace) -> list[LeadRef]:
    rows = erpnext_get_list(
        session,
        args,
        "Lead",
        filters=[["alpstein_business_id", "=", args.business_id]],
        fields=[
            "name",
            "alpstein_channel",
            "alpstein_business_id",
            "alpstein_chat_id",
            "alpstein_external_user_id",
            "instagram_username",
            "instagram_display_name",
        ],
        limit=1000,
    )
    return [
        LeadRef(
            name=row["name"],
            channel=row.get("alpstein_channel"),
            business_id=row.get("alpstein_business_id"),
            chat_id=row.get("alpstein_chat_id"),
            external_user_id=row.get("alpstein_external_user_id"),
            instagram_username=row.get("instagram_username"),
            instagram_display_name=row.get("instagram_display_name"),
        )
        for row in rows
    ]


def load_existing_communication_keys(
    session: requests.Session,
    args: argparse.Namespace,
) -> set[tuple[str, str]]:
    rows = erpnext_get_list(
        session,
        args,
        "Communication",
        filters=[["alpstein_business_id", "=", args.business_id]],
        fields=["name", "alpstein_external_message_id", "alpstein_business_id"],
        limit=5000,
    )
    return {
        (row["alpstein_external_message_id"], row["alpstein_business_id"])
        for row in rows
        if row.get("alpstein_external_message_id") and row.get("alpstein_business_id")
    }


def build_lead_indexes(leads: list[LeadRef]) -> tuple[dict[tuple[str, str, str], LeadRef], dict[tuple[str, str, str], LeadRef]]:
    by_chat: dict[tuple[str, str, str], LeadRef] = {}
    by_external: dict[tuple[str, str, str], LeadRef] = {}
    for lead in leads:
        if lead.chat_id:
            by_chat[(lead.channel, lead.business_id, lead.chat_id)] = lead
        if lead.external_user_id:
            by_external[(lead.channel, lead.business_id, lead.external_user_id)] = lead
    return by_chat, by_external


def channel_chat_id(row: dict[str, Any]) -> str | None:
    if row["channel"] == "instagram":
        return row.get("external_conversation_id") or (
            f"ig:{row['external_customer_id']}" if row.get("external_customer_id") else None
        )
    if row["channel"] == "telegram":
        return row.get("external_customer_id")
    return None


def communication_medium(channel: str) -> str:
    return {
        "instagram": "Instagram",
        "telegram": "Telegram",
    }.get(channel, channel)


def build_candidates(messages: list[dict[str, Any]], leads: list[LeadRef]) -> tuple[list[Candidate], dict[str, int]]:
    by_chat, by_external = build_lead_indexes(leads)
    last_inbound_external: dict[str, str] = {}
    candidates: list[Candidate] = []
    skipped = {"no_lead": 0, "unsupported_sender": 0, "missing_external_id": 0}

    for row in messages:
        channel = row["channel"]
        business_id = row["business_external_id"]
        chat_id = channel_chat_id(row)
        lead = None
        if chat_id:
            lead = by_chat.get((channel, business_id, chat_id))
        if lead is None and row.get("external_customer_id"):
            lead = by_external.get((channel, business_id, row["external_customer_id"]))
        if lead is None:
            skipped["no_lead"] += 1
            continue

        conversation_id = row["conversation_id"]
        sender_type = row["sender_type"]
        external_message_id = row.get("external_message_id")
        legacy_external_message_id = None

        if sender_type == "customer" and row["direction"] == "incoming":
            if not external_message_id:
                skipped["missing_external_id"] += 1
                continue
            last_inbound_external[conversation_id] = external_message_id
        elif sender_type == "ai" and row["direction"] == "outgoing":
            legacy_external_message_id = f"alpstein:message:{row['id']}"
            external_message_id = (
                external_message_id
                or (
                    f"alpstein:ai:{last_inbound_external[conversation_id]}"
                    if conversation_id in last_inbound_external
                    else legacy_external_message_id
                )
            )
        else:
            skipped["unsupported_sender"] += 1
            continue

        candidates.append(
            Candidate(
                lead_name=lead.name,
                sender_type=sender_type,
                external_message_id=external_message_id,
                legacy_external_message_id=legacy_external_message_id,
                business_id=business_id,
                channel=channel,
                conversation_id=conversation_id,
                communication_date=row["created_at"].split(".")[0],
                content=row["message_text"],
            )
        )

    return candidates, skipped


def communication_body(candidate: Candidate) -> dict[str, Any]:
    inbound = candidate.sender_type == "customer"
    medium = communication_medium(candidate.channel)
    return {
        "reference_doctype": "Lead",
        "reference_name": candidate.lead_name,
        "communication_type": "Communication",
        "communication_medium": medium,
        "sent_or_received": "Received" if inbound else "Sent",
        "content": candidate.content,
        "text_content": candidate.content,
        "subject": f"{'Inbound' if inbound else 'AI'} {medium} {'message' if inbound else 'reply'}",
        "communication_date": candidate.communication_date,
        "alpstein_external_message_id": candidate.external_message_id,
        "alpstein_channel": candidate.channel,
        "alpstein_business_id": candidate.business_id,
        "alpstein_direction": "incoming" if inbound else "outgoing",
        "alpstein_sender_type": candidate.sender_type,
        "alpstein_conversation_id": candidate.conversation_id,
    }


def parse_flatted(value: str) -> Any:
    table = json.loads(value)
    memo: dict[int, Any] = {}

    def revive_index(index: int) -> Any:
        if index in memo:
            return memo[index]
        raw = table[index]
        if isinstance(raw, str):
            memo[index] = raw
            return raw
        if isinstance(raw, list):
            out: list[Any] = []
            memo[index] = out
            out.extend(revive(item) for item in raw)
            return out
        if isinstance(raw, dict):
            out: dict[str, Any] = {}
            memo[index] = out
            for key, item in raw.items():
                out[key] = revive(item)
            return out
        memo[index] = raw
        return raw

    def revive(raw: Any) -> Any:
        if isinstance(raw, str) and raw.isdigit() and int(raw) < len(table):
            return revive_index(int(raw))
        return raw

    return revive_index(0)


def load_instagram_profiles_from_n8n(path: str) -> dict[str, dict[str, str]]:
    db_path = Path(path)
    if not db_path.exists():
        return {}
    profiles: dict[str, dict[str, str]] = {}
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        select d.data
        from execution_entity e
        join execution_data d on d.executionId = e.id
        where e.workflowId = ?
          and d.data like '%instagram_context%'
        order by e.id desc
        """,
        (WORKFLOW_ID,),
    )
    for row in rows:
        try:
            payload = parse_flatted(row["data"])
            run_data = payload.get("resultData", {}).get("runData", {})
            normalized_runs = run_data.get("Normalize Instagram Incoming", [])
            for run in normalized_runs:
                for output in run.get("data", {}).get("main", []):
                    for item in output or []:
                        ctx = item.get("json", {}).get("instagram_context", {})
                        user_id = ctx.get("instagram_user_id")
                        username = ctx.get("instagram_username")
                        display_name = ctx.get("instagram_display_name")
                        if user_id and (username or display_name):
                            profiles.setdefault(str(user_id), {})
                            if username:
                                profiles[str(user_id)]["instagram_username"] = str(username)
                            if display_name:
                                profiles[str(user_id)]["instagram_display_name"] = str(display_name)
        except Exception:
            continue
    connection.close()
    return profiles


def main() -> int:
    args = parse_args()
    session = erpnext_session(args)

    messages = load_messages(args)
    leads = load_leads(session, args)
    existing = load_existing_communication_keys(session, args)
    candidates, skipped = build_candidates(messages, leads)

    missing: list[Candidate] = []
    planned_keys: set[tuple[str, str]] = set()
    primary_seen_counts: dict[tuple[str, str], int] = {}
    per_lead: dict[str, dict[str, int]] = {}
    for candidate in candidates:
        primary_key = (candidate.external_message_id, candidate.business_id)
        primary_seen_counts[primary_key] = primary_seen_counts.get(primary_key, 0) + 1
        legacy_key = (
            (candidate.legacy_external_message_id, candidate.business_id)
            if candidate.legacy_external_message_id
            else None
        )

        if primary_key in existing or primary_key in planned_keys:
            if (
                candidate.sender_type == "ai"
                and candidate.legacy_external_message_id
                and primary_seen_counts[primary_key] > 1
                and legacy_key not in existing
                and legacy_key not in planned_keys
            ):
                candidate = replace(
                    candidate,
                    external_message_id=candidate.legacy_external_message_id,
                    legacy_external_message_id=None,
                )
                primary_key = (candidate.external_message_id, candidate.business_id)
            else:
                continue

        if legacy_key and legacy_key in existing:
            continue

        planned_keys.add(primary_key)
        missing.append(candidate)
        bucket = per_lead.setdefault(candidate.lead_name, {"customer": 0, "ai": 0})
        bucket[candidate.sender_type] += 1

    created: list[dict[str, str]] = []
    if args.apply:
        for candidate in missing:
            name = erpnext_insert(session, args, "Communication", communication_body(candidate))
            existing.add((candidate.external_message_id, candidate.business_id))
            created.append(
                {
                    "name": name,
                    "lead": candidate.lead_name,
                    "sender_type": candidate.sender_type,
                    "external_message_id": candidate.external_message_id,
                }
            )

    profile_updates: list[dict[str, Any]] = []
    if not args.skip_profile_backfill:
        profiles = load_instagram_profiles_from_n8n(args.n8n_db)
        for lead in leads:
            if lead.channel != "instagram" or not lead.external_user_id:
                continue
            profile = profiles.get(lead.external_user_id)
            if not profile:
                continue
            update: dict[str, str] = {}
            if not lead.instagram_username and profile.get("instagram_username"):
                update["instagram_username"] = profile["instagram_username"]
            if not lead.instagram_display_name and profile.get("instagram_display_name"):
                update["instagram_display_name"] = profile["instagram_display_name"]
            if not update:
                continue
            profile_updates.append({"lead": lead.name, **update})
            if args.apply:
                erpnext_update(session, args, "Lead", lead.name, update)

    summary = {
        "mode": "apply" if args.apply else "dry_run",
        "messages_scanned": len(messages),
        "candidate_communications": len(candidates),
        "existing_keys": len(existing),
        "missing_total": len(missing),
        "missing_inbound": sum(1 for row in missing if row.sender_type == "customer"),
        "missing_outbound_ai": sum(1 for row in missing if row.sender_type == "ai"),
        "skipped": skipped,
        "per_lead_missing": per_lead,
        "created": created,
        "profile_updates": profile_updates,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(1) from exc
