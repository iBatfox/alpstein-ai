"""Chain AI configuration, prompt build, gateway, and PromptRun logging (T11.11)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ai_gateway import AiGatewayResult
from app.schemas.ai_reply import AiReplyResult
from app.schemas.assembled_prompt import AssembledPrompt
from app.core.config import settings as app_settings
from app.services.ai_configuration_service import AiConfigurationService
from app.services.ai_gateway_service import AiGatewayService
from app.services.knowledge_retrieval_service import KnowledgeRetrievalService
from app.services.message_service import MessageService
from app.services.conversation_intent_policy import (
    alpstein_product_behavior_enabled_for_business,
)
from app.services.conversation_intent_service import ConversationIntentService
from app.services.greeting_policy_service import GreetingPolicyService
from app.services.langfuse_tracing_service import LangfuseTracingService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.prompt_run_service import PromptRunService


class AiReplyOrchestrationService:
    def __init__(
        self,
        ai_configuration_service: AiConfigurationService | None = None,
        knowledge_retrieval_service: KnowledgeRetrievalService | None = None,
        message_service: MessageService | None = None,
        prompt_builder_service: PromptBuilderService | None = None,
        ai_gateway_service: AiGatewayService | None = None,
        prompt_run_service: PromptRunService | None = None,
        greeting_policy_service: GreetingPolicyService | None = None,
        conversation_intent_service: ConversationIntentService | None = None,
        langfuse_tracing_service: LangfuseTracingService | None = None,
    ) -> None:
        self.ai_configuration_service = (
            ai_configuration_service or AiConfigurationService()
        )
        self.knowledge_retrieval_service = (
            knowledge_retrieval_service or KnowledgeRetrievalService()
        )
        self.message_service = message_service or MessageService()
        self.prompt_builder_service = prompt_builder_service or PromptBuilderService()
        self.ai_gateway_service = ai_gateway_service or AiGatewayService()
        self.prompt_run_service = prompt_run_service or PromptRunService()
        self.greeting_policy_service = greeting_policy_service or GreetingPolicyService()
        self.conversation_intent_service = (
            conversation_intent_service or ConversationIntentService()
        )
        self.langfuse_tracing_service = (
            langfuse_tracing_service or LangfuseTracingService()
        )

    async def generate_reply(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business: object,
        conversation: object,
        message: object,
        customer_message_text: str,
        channel: str,
        template_key: str,
        operator_business_context: str | None = None,
        message_timestamp: datetime | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> AiReplyResult:
        business_id = business.id

        configuration = await self.ai_configuration_service.load_for_message(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            channel=channel,
            template_key=template_key,
        )
        knowledge = await self.knowledge_retrieval_service.retrieve_for_message(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            query_text=customer_message_text,
        )
        history = await self.message_service.load_recent_conversation_history(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            conversation_id=conversation.id,
        )
        greeting_policy = self.greeting_policy_service.resolve(
            history=history,
            current_customer_message=customer_message_text,
            message_timestamp=message_timestamp,
            raw_payload=raw_payload,
        )
        business_external_id = str(getattr(business, "external_id", business_id))
        alpstein_product_behavior_enabled = alpstein_product_behavior_enabled_for_business(
            business_external_id
        )
        conversation_intent = None
        if alpstein_product_behavior_enabled:
            conversation_intent = self.conversation_intent_service.resolve(
                history=history,
                current_customer_message=customer_message_text,
            )
        assembled_prompt = self.prompt_builder_service.build_reply_to_customer(
            configuration=configuration,
            knowledge=knowledge,
            history=history,
            current_customer_message=customer_message_text,
            operator_business_context=operator_business_context,
            greeting_policy=greeting_policy,
            alpstein_product_behavior_enabled=alpstein_product_behavior_enabled,
            conversation_intent=conversation_intent,
        )

        async with self.langfuse_tracing_service.trace_ai_reply(
            business_external_id=str(business_external_id),
            business_id=str(business_id),
            conversation_id=str(conversation.id),
            channel=channel,
            greeting_policy=greeting_policy,
            operator_business_context=operator_business_context,
            customer_message_text=customer_message_text,
            assembled_prompt=assembled_prompt,
        ) as trace_recorder:
            gateway_result = await self.ai_gateway_service.complete(assembled_prompt)
            trace_recorder.record_gateway_result(
                assembled_prompt=assembled_prompt,
                gateway_result=gateway_result,
                model=app_settings.openai_model,
            )

        prompt_run = await self.prompt_run_service.create_prompt_run(
            session,
            tenant_id=tenant_id,
            business=business,
            conversation=conversation,
            message=message,
            prompt_template_id=configuration.platform_template.id,
            prompt_version=configuration.platform_template.version,
            model=gateway_result.model,
            provider=gateway_result.provider,
            input_tokens=gateway_result.input_tokens,
            output_tokens=gateway_result.output_tokens,
            latency_ms=gateway_result.latency_ms,
            result=gateway_result.text if gateway_result.succeeded else None,
            error=gateway_result.error,
            final_prompt=_serialize_assembled_prompt(assembled_prompt),
        )

        return _map_reply_result(gateway_result, prompt_run_id=prompt_run.id)


def _serialize_assembled_prompt(prompt: AssembledPrompt) -> str:
    return "\n\n".join(
        f"=== {section.section_id} ({section.kind}) ===\n{section.content}"
        for section in prompt.sections
    )


def _map_reply_result(
    gateway_result: AiGatewayResult,
    *,
    prompt_run_id: uuid.UUID,
) -> AiReplyResult:
    return AiReplyResult(
        text=gateway_result.text,
        is_success=gateway_result.succeeded,
        prompt_run_id=prompt_run_id,
        model=gateway_result.model,
        provider=gateway_result.provider,
        error=gateway_result.error,
    )
