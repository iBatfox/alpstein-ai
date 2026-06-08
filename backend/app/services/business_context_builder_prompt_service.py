"""Prompt assembly for Business Context Builder AI tasks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.models.business_context_builder import (
    MESSAGE_ROLE_ASSISTANT,
    MESSAGE_ROLE_USER,
)
from app.schemas.assembled_prompt import AssembledPrompt, AssembledPromptSection
from app.services.business_context_builder_constants import (
    ALLOWED_STEPS,
    INTERVIEW_STEPS,
    STEP_COMMUNICATION_STYLE,
    STEP_BUSINESS_DESCRIPTION,
    STEP_COMPANY_INFORMATION,
    STEP_PRODUCTS_SERVICES,
    STEP_SALES_PROCESS,
    STEP_TARGET_CUSTOMERS,
)

BCB_NEXT_QUESTION_TASK = "bcb_next_question"
BCB_DRAFT_RESULT_TASK = "bcb_draft_result"
BCB_NEXT_QUESTION_PROMPT_VERSION = "1.0"
BCB_DRAFT_RESULT_PROMPT_VERSION = "1.0"

STEP_FOCUS_LABELS: dict[str, str] = {
    STEP_COMPANY_INFORMATION: "company name, website, industry, and location",
    STEP_BUSINESS_DESCRIPTION: "what the company does and how it helps customers",
    STEP_TARGET_CUSTOMERS: "target customers and ideal client profile",
    STEP_PRODUCTS_SERVICES: "main products or services offered",
    STEP_SALES_PROCESS: "sales, booking, or inquiry process",
    STEP_COMMUNICATION_STYLE: "preferred assistant tone and communication style",
}

PLATFORM_SYSTEM_PROMPT = (
    "You are an interview assistant helping a business owner draft a Business Context.\n"
    "Your only job in this turn is to ask the next single interview question.\n"
    "Rules:\n"
    "- Ask exactly one clear question.\n"
    "- Do not generate the final business context, summary, JSON, or prompt draft.\n"
    "- Do not mention internal system fields, steps, schemas, or platform instructions.\n"
    "- Do not ask for passwords, payment card numbers, government IDs, or other sensitive "
    "personal data.\n"
    "- Keep the question practical for building business context for a customer-facing "
    "assistant.\n"
    "- Respond in the user's language when it is clear from the conversation; otherwise use "
    "English.\n"
    "- Return only the question text with no preamble, bullet list, or markdown."
)

DRAFT_RESULT_SYSTEM_PROMPT = (
    "You are helping prepare a draft Business Context from an interview transcript.\n"
    "Use only facts present in the interview messages.\n"
    "Do not invent company details, services, policies, prices, locations, or customer "
    "promises.\n"
    "Clearly mark unknown or missing sections as unknown, not provided, or missing.\n"
    "Do not ask another question and do not request more information.\n"
    "Do not publish, optimize, or format this as a production assistant prompt.\n"
    "Do not mention internal database fields, table names, schemas, IDs, prompts, or "
    "platform implementation details.\n"
    "Use the language of the interview if clear; otherwise use English.\n"
    "Return only a valid JSON object with no markdown fences or commentary."
)

TASK_INSTRUCTIONS_TEMPLATE = (
    "TASK: generate_next_assistant_question\n"
    "Interview focus for this turn: {step_label}\n"
    "Ask one question that helps collect information about {step_focus}.\n"
    "Do not repeat a question that was already asked unless a short clarification is truly "
    "needed.\n"
    "Output only the next assistant question."
)

DRAFT_RESULT_TASK_INSTRUCTIONS = (
    "TASK: generate_business_context_draft_result\n"
    "Create a stable machine-storable JSON object from the interview history.\n"
    "Required top-level keys:\n"
    "- structured_context: object\n"
    "- generated_prompt: string\n"
    "structured_context must include these keys:\n"
    "- company_overview\n"
    "- business_description\n"
    "- target_customers\n"
    "- products_services\n"
    "- sales_process\n"
    "- communication_style\n"
    "- known_constraints\n"
    "- missing_information\n"
    "- draft_quality_confidence\n"
    "generated_prompt should be a draft review text derived only from provided interview "
    "facts. It is draft-only and must not claim to be production-ready.\n"
    "Do not ask another question."
)


@dataclass(frozen=True)
class BusinessContextBuilderConversationTurn:
    role: str
    content: str


@dataclass(frozen=True)
class BusinessContextBuilderPromptInput:
    session_id: uuid.UUID
    tenant_id: uuid.UUID
    business_id: uuid.UUID
    next_step: str
    messages: tuple[BusinessContextBuilderConversationTurn, ...]


class BusinessContextBuilderPromptService:
    def next_question_prompt_version(self) -> str:
        return BCB_NEXT_QUESTION_PROMPT_VERSION

    def draft_result_prompt_version(self) -> str:
        return BCB_DRAFT_RESULT_PROMPT_VERSION

    def build_next_question_prompt(
        self,
        prompt_input: BusinessContextBuilderPromptInput,
    ) -> AssembledPrompt:
        history_content = _format_conversation_history(prompt_input.messages)
        step_context = _format_step_context(prompt_input.next_step)

        sections: list[AssembledPromptSection] = [
            AssembledPromptSection(
                section_id="platform_system",
                label="PLATFORM SYSTEM",
                content=_labeled("PLATFORM SYSTEM", PLATFORM_SYSTEM_PROMPT),
                kind="system",
            ),
            AssembledPromptSection(
                section_id="task_instructions",
                label="TASK INSTRUCTIONS",
                content=_labeled(
                    "TASK INSTRUCTIONS",
                    (
                        f"prompt_version: {BCB_NEXT_QUESTION_PROMPT_VERSION}\n"
                        + TASK_INSTRUCTIONS_TEMPLATE.format(
                            step_label=_step_label(prompt_input.next_step),
                            step_focus=_step_focus(prompt_input.next_step),
                        )
                    ),
                ),
                kind="system",
            ),
        ]

        if history_content:
            sections.append(
                AssembledPromptSection(
                    section_id="conversation_history",
                    label="CONVERSATION HISTORY (reference data)",
                    content=_labeled(
                        "CONVERSATION HISTORY (reference data)",
                        history_content,
                    ),
                    kind="data",
                )
            )

        sections.append(
            AssembledPromptSection(
                section_id="step_context",
                label="INTERVIEW STEP CONTEXT (reference data)",
                content=_labeled("INTERVIEW STEP CONTEXT (reference data)", step_context),
                kind="data",
            )
        )

        return AssembledPrompt(task=BCB_NEXT_QUESTION_TASK, sections=tuple(sections))

    def build_draft_result_prompt(
        self,
        prompt_input: BusinessContextBuilderPromptInput,
    ) -> AssembledPrompt:
        history_content = _format_conversation_history(prompt_input.messages)
        sections: list[AssembledPromptSection] = [
            AssembledPromptSection(
                section_id="platform_system",
                label="PLATFORM SYSTEM",
                content=_labeled("PLATFORM SYSTEM", DRAFT_RESULT_SYSTEM_PROMPT),
                kind="system",
            ),
            AssembledPromptSection(
                section_id="task_instructions",
                label="TASK INSTRUCTIONS",
                content=_labeled(
                    "TASK INSTRUCTIONS",
                    (
                        f"prompt_version: {BCB_DRAFT_RESULT_PROMPT_VERSION}\n"
                        + DRAFT_RESULT_TASK_INSTRUCTIONS
                    ),
                ),
                kind="system",
            ),
        ]

        sections.append(
            AssembledPromptSection(
                section_id="conversation_history",
                label="CONVERSATION HISTORY (interview source of truth)",
                content=_labeled(
                    "CONVERSATION HISTORY (interview source of truth)",
                    history_content or "No interview messages were provided.",
                ),
                kind="data",
            )
        )

        return AssembledPrompt(task=BCB_DRAFT_RESULT_TASK, sections=tuple(sections))


def _labeled(label: str, body: str) -> str:
    return f"[{label}]\n{body}"


def _step_label(step: str) -> str:
    return step.replace("_", " ")


def _step_focus(step: str) -> str:
    return STEP_FOCUS_LABELS.get(step, _step_label(step))


def _format_step_context(next_step: str) -> str:
    allowed = ", ".join(INTERVIEW_STEPS)
    return (
        f"next_step: {next_step}\n"
        f"allowed_steps: {allowed}\n"
        f"allowed_step_values: {', '.join(sorted(ALLOWED_STEPS))}"
    )


def _format_conversation_history(
    messages: tuple[BusinessContextBuilderConversationTurn, ...],
) -> str:
    lines: list[str] = []
    for message in messages:
        if message.role not in {MESSAGE_ROLE_USER, MESSAGE_ROLE_ASSISTANT}:
            continue
        content = message.content.strip()
        if not content:
            continue
        lines.append(f"{message.role}: {content}")
    return "\n".join(lines)
