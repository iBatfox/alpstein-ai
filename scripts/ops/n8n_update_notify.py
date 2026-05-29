#!/usr/bin/env python3
"""Notify owner when a new official n8n release is available (ops-only, no auto-update)."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import Any

GITHUB_LATEST_URL = "https://api.github.com/repos/n8n-io/n8n/releases/latest"
DEFAULT_STATE_PATH = Path("/var/lib/alpstein-ops/n8n-update-notify/state.json")
DEFAULT_CONTAINER = "alpstein_n8n_compose"
SEMVER_RE = re.compile(r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+(?P<text>.+)$")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
FALLBACK_BULLET = "See full release notes on GitHub."
MAX_BULLET_LEN = 120
STATE_SCHEMA_VERSION = 1

LOGGER = logging.getLogger("n8n_update_notify")


class ImpactLevel(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @property
    def label(self) -> str:
        return {ImpactLevel.LOW: "Low", ImpactLevel.MEDIUM: "Medium", ImpactLevel.HIGH: "High"}[
            self
        ]

    @property
    def emoji(self) -> str:
        return {ImpactLevel.LOW: "🟢", ImpactLevel.MEDIUM: "🟡", ImpactLevel.HIGH: "🔴"}[self]


@dataclass(frozen=True, order=True)
class SemVer:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class ReleaseInfo:
    version: SemVer
    published_at: str
    body: str
    html_url: str


@dataclass
class NotifyState:
    schema_version: int = STATE_SCHEMA_VERSION
    last_checked_at: str | None = None
    last_checked_version: str | None = None
    last_notified_version: str | None = None
    last_notified_at: str | None = None
    last_installed_version: str | None = None
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "last_checked_at": self.last_checked_at,
            "last_checked_version": self.last_checked_version,
            "last_notified_version": self.last_notified_version,
            "last_notified_at": self.last_notified_at,
            "last_installed_version": self.last_installed_version,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotifyState:
        return cls(
            schema_version=int(data.get("schema_version", STATE_SCHEMA_VERSION)),
            last_checked_at=data.get("last_checked_at"),
            last_checked_version=data.get("last_checked_version"),
            last_notified_version=data.get("last_notified_version"),
            last_notified_at=data.get("last_notified_at"),
            last_installed_version=data.get("last_installed_version"),
            last_error=data.get("last_error"),
        )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_semver(raw: str) -> SemVer | None:
    if not raw:
        return None
    cleaned = raw.strip()
    for prefix in ("n8n@", "n8nio/n8n:", "n8n:", "v"):
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix) :]
    if ":" in cleaned:
        cleaned = cleaned.rsplit(":", 1)[-1]
    match = SEMVER_RE.search(cleaned)
    if not match:
        return None
    return SemVer(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
    )


def parse_image_tag(image_ref: str) -> SemVer | None:
    return normalize_semver(image_ref)


def should_notify(
    installed: SemVer,
    latest: SemVer,
    last_notified_version: str | None,
    *,
    force_notify: bool = False,
) -> bool:
    if latest <= installed:
        return False
    if force_notify:
        return True
    if last_notified_version == str(latest):
        return False
    return True


def bump_impact(level: ImpactLevel) -> ImpactLevel:
    if level == ImpactLevel.HIGH:
        return ImpactLevel.HIGH
    return ImpactLevel(level + 1)


def classify_impact(installed: SemVer, latest: SemVer, release_body: str) -> ImpactLevel:
    if latest.major > installed.major:
        level = ImpactLevel.HIGH
    elif latest.minor > installed.minor:
        level = ImpactLevel.MEDIUM
    else:
        level = ImpactLevel.LOW

    body_lower = release_body.lower()
    if any(
        keyword in body_lower
        for keyword in ("breaking", "security", "security fix", "vulnerability")
    ):
        level = bump_impact(level)
    return level


def _strip_markdown_links(text: str) -> str:
    return LINK_RE.sub(r"\1", text).strip()


def extract_release_bullets(body: str, *, max_items: int = 4) -> list[str]:
    if not body:
        return [FALLBACK_BULLET] * max_items

    bullets: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--"):
            continue
        match = LIST_ITEM_RE.match(stripped)
        if match:
            candidate = _strip_markdown_links(match.group("text"))
        elif len(stripped) <= 200 and not stripped.startswith("#"):
            candidate = _strip_markdown_links(stripped)
        else:
            continue
        if not candidate:
            continue
        if len(candidate) > MAX_BULLET_LEN:
            candidate = candidate[: MAX_BULLET_LEN - 3].rstrip() + "..."
        bullets.append(candidate)
        if len(bullets) >= max_items:
            break

    while len(bullets) < max_items:
        bullets.append(FALLBACK_BULLET)
    return bullets[:max_items]


def format_telegram_message(
    latest: SemVer,
    bullets: list[str],
    impact: ImpactLevel,
) -> str:
    lines = [
        "🚀 n8n Update Available",
        "",
        "Version:",
        str(latest),
        "",
        "Changes:",
        "",
    ]
    for index, bullet in enumerate(bullets, start=1):
        lines.append(f"{index}. {bullet}")
    lines.extend(
        [
            "",
            "Impact Level:",
            f"{impact.emoji} {impact.label}",
            "",
            "Action:",
            "No update performed.",
            "",
            "Decision Required:",
            "Review and approve update if needed.",
        ]
    )
    return "\n".join(lines)


def fresh_state() -> NotifyState:
    return NotifyState()


def load_state(path: Path) -> tuple[NotifyState, bool]:
    """Load state; return (state, was_reset_after_corruption)."""
    if not path.exists():
        return fresh_state(), False

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("state root must be object")
        return NotifyState.from_dict(data), False
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        backup = path.with_suffix(path.suffix + f".bak.{utc_now_iso().replace(':', '-')}")
        try:
            path.rename(backup)
            LOGGER.warning("STATE_INVALID: backed up corrupt state to %s (%s)", backup, exc)
        except OSError as rename_exc:
            LOGGER.warning("STATE_INVALID: could not backup state: %s", rename_exc)
        return fresh_state(), True


def save_state_atomic(path: Path, state: NotifyState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def http_get_json(url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request_headers = {"Accept": "application/vnd.github+json", "User-Agent": "alpstein-n8n-update-notify"}
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(url, headers=request_headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = response.read().decode("utf-8")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("expected JSON object from GitHub")
    return data


def fetch_latest_release(*, github_token: str | None = None) -> ReleaseInfo:
    headers: dict[str, str] = {}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    data = http_get_json(GITHUB_LATEST_URL, headers=headers)
    tag_name = str(data.get("tag_name") or "")
    version = normalize_semver(tag_name)
    if version is None:
        raise ValueError(f"GITHUB_PARSE_ERROR: invalid tag_name {tag_name!r}")

    published_at = str(data.get("published_at") or "")
    body = str(data.get("body") or "")
    html_url = str(data.get("html_url") or "")
    return ReleaseInfo(version=version, published_at=published_at, body=body, html_url=html_url)


def read_installed_version(container: str) -> SemVer:
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.Config.Image}}", container],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError(f"CONTAINER_NOT_FOUND: {container}") from exc

    image_ref = result.stdout.strip()
    version = parse_image_tag(image_ref)
    if version is None:
        raise ValueError(f"VERSION_PARSE_ERROR: could not parse image tag {image_ref!r}")
    return version


def telegram_configured() -> tuple[str, str] | None:
    token = os.environ.get("N8N_UPDATE_NOTIFY_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("N8N_UPDATE_NOTIFY_TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return None
    return token, chat_id


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"TELEGRAM_SEND_FAILED: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("TELEGRAM_SEND_FAILED: network error") from exc

    if not payload.get("ok"):
        raise RuntimeError("TELEGRAM_SEND_FAILED: API returned ok=false")


def run_check(
    *,
    state_path: Path,
    container: str,
    dry_run: bool = False,
    force_notify: bool = False,
) -> int:
    state, _ = load_state(state_path)
    state.last_error = None

    try:
        release = fetch_latest_release(github_token=os.environ.get("GITHUB_TOKEN"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        state.last_error = "GITHUB_UNAVAILABLE"
        LOGGER.error("GITHUB_UNAVAILABLE: %s", exc)
        if not dry_run:
            save_state_atomic(state_path, state)
        return 1
    except (ValueError, json.JSONDecodeError) as exc:
        state.last_error = "GITHUB_PARSE_ERROR"
        LOGGER.error("GITHUB_PARSE_ERROR: %s", exc)
        if not dry_run:
            save_state_atomic(state_path, state)
        return 1

    try:
        installed = read_installed_version(container)
    except (RuntimeError, ValueError) as exc:
        state.last_error = str(exc).split(":", 1)[0]
        LOGGER.error("%s", exc)
        if not dry_run:
            save_state_atomic(state_path, state)
        return 1

    latest = release.version
    state.last_checked_at = utc_now_iso()
    state.last_checked_version = str(latest)
    state.last_installed_version = str(installed)

    notify = should_notify(
        installed,
        latest,
        state.last_notified_version,
        force_notify=force_notify,
    )

    LOGGER.info(
        "installed=%s latest=%s last_notified=%s should_notify=%s",
        installed,
        latest,
        state.last_notified_version,
        notify,
    )

    bullets = extract_release_bullets(release.body)
    impact = classify_impact(installed, latest, release.body)
    message = format_telegram_message(latest, bullets, impact)

    if not notify:
        if not dry_run:
            save_state_atomic(state_path, state)
        return 0

    if dry_run:
        print(message)
        print("")
        print(f"[dry-run] would_notify=true installed={installed} latest={latest}")
        save_state_atomic(state_path, state)
        return 0

    config = telegram_configured()
    if config is None:
        LOGGER.warning("TELEGRAM_NOT_CONFIGURED: missing bot token or chat id; skipping send")
        save_state_atomic(state_path, state)
        return 0

    token, chat_id = config
    try:
        send_telegram_message(token, chat_id, message)
    except RuntimeError as exc:
        state.last_error = str(exc).split(":", 1)[0]
        LOGGER.error("%s", exc)
        save_state_atomic(state_path, state)
        return 1

    state.last_notified_version = str(latest)
    state.last_notified_at = utc_now_iso()
    save_state_atomic(state_path, state)
    LOGGER.info("notification sent for n8n %s", latest)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Notify owner when a new official n8n release is available.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print Telegram message; do not send or update last_notified_*.",
    )
    parser.add_argument(
        "--force-notify",
        action="store_true",
        help="Send even if this release was already notified (still requires latest > installed).",
    )
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path(os.environ.get("N8N_UPDATE_NOTIFY_STATE_PATH", str(DEFAULT_STATE_PATH))),
        help="Path to JSON state file.",
    )
    parser.add_argument(
        "--container",
        default=os.environ.get("N8N_UPDATE_NOTIFY_CONTAINER", DEFAULT_CONTAINER),
        help="Docker container name for installed n8n image tag.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    args = build_parser().parse_args(argv)
    return run_check(
        state_path=args.state_path,
        container=args.container,
        dry_run=args.dry_run,
        force_notify=args.force_notify,
    )


if __name__ == "__main__":
    sys.exit(main())
