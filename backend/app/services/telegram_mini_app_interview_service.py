from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

INTERVIEW_STORAGE_ROOT = Path("/opt/alpstein-ai/docs/interview")

INTERVIEW_QUESTIONS = [
    "What is the company name?",
    "What does the company sell or provide?",
    "Who are the main customers?",
    "Which communication channels are used now?",
    "What questions do customers ask most often?",
    "Where are leads currently stored?",
    "Which CRM/ERP/software is used?",
    "Which manual processes take the most time?",
    "Where do employees lose leads or forget to answer?",
    "Which parts should AI automate first?",
    "What should AI never do without human approval?",
    "What tone/language should the assistant use?",
    "What information should be collected from customers?",
    "Who should receive notifications when a lead appears?",
    "What would a successful automation result look like?",
]

BUSINESS_ANALYSIS_SECTIONS = [
    "Company overview",
    "Current communication channels",
    "Customer types",
    "Main customer questions",
    "Current workflow",
    "Pain points",
    "Lead handling process",
    "CRM/ERP/software landscape",
    "AI bot opportunities",
    "Recommended automation scenarios",
    "Risks and limitations",
    "Human approval points",
    "Suggested first implementation phase",
    "Suggested future phases",
]

TECHNICAL_SPEC_SECTIONS = [
    "Project name",
    "Alpstein Business ID",
    "Connected channels",
    "Required AI assistant behavior",
    "Required customer data to collect",
    "Lead creation rules",
    "CRM/ERP integration requirements",
    "Notification rules",
    "Bot fallback rules",
    "Human handoff rules",
    "Logging/monitoring requirements",
    "Security requirements",
    "Open questions",
    "Implementation phases",
]


class InterviewAccessError(Exception):
    """Raised when interview storage cannot be scoped safely."""


class InterviewDocumentNotFoundError(Exception):
    """Raised when a requested interview document does not exist."""


@dataclass(frozen=True)
class InterviewSession:
    alpstein_business_id: str
    current_index: int
    question: str | None
    progress_current: int
    progress_total: int
    is_complete: bool
    answers: list[dict[str, Any]]


@dataclass(frozen=True)
class InterviewDocument:
    id: str
    title: str
    document_type: str
    created_at: str
    filename: str
    content: str | None = None


class TelegramMiniAppInterviewService:
    def __init__(self, storage_root: Path = INTERVIEW_STORAGE_ROOT) -> None:
        self.storage_root = storage_root

    def create_or_get_session(self, *, alpstein_business_id: str | None) -> InterviewSession:
        session = self._load_session(alpstein_business_id)
        return self._session_response(session)

    def save_answer(
        self,
        *,
        alpstein_business_id: str | None,
        answer: str,
    ) -> InterviewSession:
        clean_answer = answer.strip()
        if not clean_answer:
            raise ValueError("Answer is required")

        session = self._load_session(alpstein_business_id)
        current_index = int(session.get("current_index", 0))
        if current_index >= len(INTERVIEW_QUESTIONS):
            return self._session_response(session)

        answers = list(session.get("answers", []))
        item = {
            "question_index": current_index,
            "question": INTERVIEW_QUESTIONS[current_index],
            "answer": clean_answer,
            "answered_at": _now_iso(),
        }
        if current_index < len(answers):
            answers[current_index] = item
        else:
            answers.append(item)

        session["answers"] = answers
        session["current_index"] = min(current_index + 1, len(INTERVIEW_QUESTIONS))
        session["updated_at"] = _now_iso()
        self._write_session(alpstein_business_id, session)
        return self._session_response(session)

    def generate_documents(
        self,
        *,
        alpstein_business_id: str | None,
        company_name: str,
        integrations: list[Any],
    ) -> list[InterviewDocument]:
        session = self._load_session(alpstein_business_id)
        now = datetime.now(UTC)
        date_prefix = now.date().isoformat()
        business_dir = self._business_dir(alpstein_business_id)
        answers = list(session.get("answers", []))

        documents = [
            (
                "business_analysis",
                "Business Analysis",
                f"{date_prefix}-business-analysis.md",
                self._business_analysis_markdown(
                    alpstein_business_id=alpstein_business_id or "",
                    company_name=company_name,
                    answers=answers,
                    integrations=integrations,
                    created_at=now.isoformat(timespec="seconds"),
                ),
            ),
            (
                "technical_specification",
                "Technical Specification",
                f"{date_prefix}-technical-spec.md",
                self._technical_spec_markdown(
                    alpstein_business_id=alpstein_business_id or "",
                    company_name=company_name,
                    answers=answers,
                    integrations=integrations,
                    created_at=now.isoformat(timespec="seconds"),
                ),
            ),
        ]

        saved: list[InterviewDocument] = []
        for document_type, title, filename, content in documents:
            path = self._safe_document_path(business_dir, filename)
            path.write_text(content, encoding="utf-8")
            saved.append(
                InterviewDocument(
                    id=path.stem,
                    title=title,
                    document_type=document_type,
                    created_at=now.isoformat(timespec="seconds"),
                    filename=path.name,
                )
            )
        return saved

    def list_documents(self, *, alpstein_business_id: str | None) -> list[InterviewDocument]:
        business_dir = self._business_dir(alpstein_business_id)
        documents: list[InterviewDocument] = []
        for path in sorted(business_dir.glob("*.md"), key=lambda item: item.name, reverse=True):
            document_type, title = _document_type_and_title(path.name)
            documents.append(
                InterviewDocument(
                    id=path.stem,
                    title=title,
                    document_type=document_type,
                    created_at=datetime.fromtimestamp(path.stat().st_mtime).isoformat(
                        timespec="seconds"
                    ),
                    filename=path.name,
                )
            )
        return documents

    def get_document(
        self,
        *,
        alpstein_business_id: str | None,
        document_id: str,
    ) -> InterviewDocument:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,119}", document_id):
            raise InterviewDocumentNotFoundError()

        business_dir = self._business_dir(alpstein_business_id)
        matches = sorted(business_dir.glob(f"{document_id}.md"))
        if not matches:
            raise InterviewDocumentNotFoundError()
        path = self._safe_document_path(business_dir, matches[0].name)
        if not path.exists() or not path.is_file():
            raise InterviewDocumentNotFoundError()
        document_type, title = _document_type_and_title(path.name)
        return InterviewDocument(
            id=path.stem,
            title=title,
            document_type=document_type,
            created_at=datetime.fromtimestamp(path.stat().st_mtime).isoformat(
                timespec="seconds"
            ),
            filename=path.name,
            content=path.read_text(encoding="utf-8"),
        )

    def _load_session(self, alpstein_business_id: str | None) -> dict[str, Any]:
        path = self._session_path(alpstein_business_id)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        session = {
            "id": str(uuid.uuid4()),
            "alpstein_business_id": alpstein_business_id,
            "current_index": 0,
            "answers": [],
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        self._write_session(alpstein_business_id, session)
        return session

    def _write_session(
        self,
        alpstein_business_id: str | None,
        session: dict[str, Any],
    ) -> None:
        path = self._session_path(alpstein_business_id)
        path.write_text(
            json.dumps(session, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _session_response(self, session: dict[str, Any]) -> InterviewSession:
        current_index = int(session.get("current_index", 0))
        is_complete = current_index >= len(INTERVIEW_QUESTIONS)
        return InterviewSession(
            alpstein_business_id=str(session.get("alpstein_business_id") or ""),
            current_index=current_index,
            question=None if is_complete else INTERVIEW_QUESTIONS[current_index],
            progress_current=min(current_index + 1, len(INTERVIEW_QUESTIONS)),
            progress_total=len(INTERVIEW_QUESTIONS),
            is_complete=is_complete,
            answers=list(session.get("answers", [])),
        )

    def _session_path(self, alpstein_business_id: str | None) -> Path:
        return self._business_dir(alpstein_business_id) / "session.json"

    def _business_dir(self, alpstein_business_id: str | None) -> Path:
        safe_business_id = _safe_business_id(alpstein_business_id)
        root = self.storage_root.resolve()
        business_dir = (root / safe_business_id).resolve()
        if root not in business_dir.parents and business_dir != root:
            raise InterviewAccessError("Invalid interview storage path")
        business_dir.mkdir(parents=True, exist_ok=True)
        return business_dir

    def _safe_document_path(self, business_dir: Path, filename: str) -> Path:
        if "/" in filename or "\\" in filename or not filename.endswith(".md"):
            raise InterviewAccessError("Invalid interview document path")
        path = (business_dir / filename).resolve()
        if business_dir.resolve() not in path.parents:
            raise InterviewAccessError("Invalid interview document path")
        return path

    def _business_analysis_markdown(
        self,
        *,
        alpstein_business_id: str,
        company_name: str,
        answers: list[dict[str, Any]],
        integrations: list[Any],
        created_at: str,
    ) -> str:
        answer_map = _answer_map(answers)
        lines = [
            "# Business Automation Analysis",
            "",
            f"Generated at: {created_at}",
            f"Company: {company_name}",
            f"Alpstein Business ID: {alpstein_business_id}",
            "",
        ]
        section_content = {
            "Company overview": _answer(answer_map, 0, company_name),
            "Current communication channels": _answer(answer_map, 3, _integration_summary(integrations)),
            "Customer types": _answer(answer_map, 2, "To be confirmed."),
            "Main customer questions": _answer(answer_map, 4, "To be confirmed."),
            "Current workflow": _answer(answer_map, 5, "To be confirmed."),
            "Pain points": "; ".join(
                [
                    _answer(answer_map, 7, "Manual process pain points to be confirmed."),
                    _answer(answer_map, 8, "Lead loss points to be confirmed."),
                ]
            ),
            "Lead handling process": _answer(answer_map, 5, "To be confirmed."),
            "CRM/ERP/software landscape": _answer(answer_map, 6, "To be confirmed."),
            "AI bot opportunities": _answer(answer_map, 9, "To be confirmed."),
            "Recommended automation scenarios": _answer(answer_map, 9, "Start with connected customer channels."),
            "Risks and limitations": _answer(answer_map, 10, "Human approval boundaries must be confirmed."),
            "Human approval points": _answer(answer_map, 10, "To be confirmed."),
            "Suggested first implementation phase": "Stabilize AI responses for connected channels and lead capture.",
            "Suggested future phases": "Add deeper CRM/ERP sync, reporting, and additional channels after review.",
        }
        for section in BUSINESS_ANALYSIS_SECTIONS:
            lines.extend([f"## {section}", "", section_content[section], ""])
        return "\n".join(lines)

    def _technical_spec_markdown(
        self,
        *,
        alpstein_business_id: str,
        company_name: str,
        answers: list[dict[str, Any]],
        integrations: list[Any],
        created_at: str,
    ) -> str:
        answer_map = _answer_map(answers)
        lines = [
            "# Technical Specification Draft",
            "",
            f"Generated at: {created_at}",
            "",
        ]
        section_content = {
            "Project name": f"{company_name} AI automation",
            "Alpstein Business ID": alpstein_business_id,
            "Connected channels": _integration_summary(integrations),
            "Required AI assistant behavior": _answer(answer_map, 11, "Tone and behavior to be confirmed."),
            "Required customer data to collect": _answer(answer_map, 12, "To be confirmed."),
            "Lead creation rules": _answer(answer_map, 5, "Create leads when customer intent is qualified."),
            "CRM/ERP integration requirements": _answer(answer_map, 6, "To be confirmed."),
            "Notification rules": _answer(answer_map, 13, "To be confirmed."),
            "Bot fallback rules": "If confidence is low or policy blocks action, ask clarifying questions or hand off.",
            "Human handoff rules": _answer(answer_map, 10, "Human approval required for sensitive actions."),
            "Logging/monitoring requirements": "Log channel, message flow, lead events, delivery state, and errors.",
            "Security requirements": "Telegram Mini App access must use signed initData and allowlist business scope.",
            "Open questions": _missing_answer_summary(answer_map),
            "Implementation phases": _answer(answer_map, 14, "Phase 1: connected channel assistant review."),
        }
        for section in TECHNICAL_SPEC_SECTIONS:
            lines.extend([f"## {section}", "", section_content[section], ""])
        return "\n".join(lines)


def _safe_business_id(value: str | None) -> str:
    clean = (value or "").strip().lower()
    if not clean:
        raise InterviewAccessError("Alpstein Business ID is required")
    safe = re.sub(r"[^a-z0-9_-]+", "-", clean).strip("-")
    if not safe or safe in {".", ".."}:
        raise InterviewAccessError("Alpstein Business ID is invalid")
    return safe[:80]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _document_type_and_title(filename: str) -> tuple[str, str]:
    if "technical-spec" in filename:
        return "technical_specification", "Technical Specification"
    return "business_analysis", "Business Analysis"


def _answer_map(answers: list[dict[str, Any]]) -> dict[int, str]:
    return {
        int(item["question_index"]): str(item.get("answer", "")).strip()
        for item in answers
        if "question_index" in item
    }


def _answer(answer_map: dict[int, str], index: int, fallback: str) -> str:
    return answer_map.get(index) or fallback


def _integration_summary(integrations: list[Any]) -> str:
    if not integrations:
        return "No connected channels are registered yet."
    rows = []
    for item in integrations:
        rows.append(
            "- "
            + " / ".join(
                value
                for value in [
                    getattr(item, "display_name", None),
                    getattr(item, "channel_type", None),
                    getattr(item, "status", None),
                ]
                if value
            )
        )
    return "\n".join(rows)


def _missing_answer_summary(answer_map: dict[int, str]) -> str:
    missing = [
        question
        for index, question in enumerate(INTERVIEW_QUESTIONS)
        if not answer_map.get(index)
    ]
    if not missing:
        return "No open questions from the interview."
    return "\n".join(f"- {question}" for question in missing)
