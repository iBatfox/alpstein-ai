from dataclasses import fields

import httpx
import pytest

from app.core.config import Settings
from app.schemas.ai_gateway import AiGatewayResult
from app.schemas.assembled_prompt import AssembledPrompt, AssembledPromptSection
from app.services.ai_gateway._openai import (
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    map_assembled_prompt_to_openai_request,
)
from app.services.ai_gateway_service import (
    ERROR_EMPTY_RESPONSE,
    ERROR_MISSING_API_KEY,
    ERROR_PROVIDER_PREFIX,
    ERROR_TIMEOUT,
    AiGatewayService,
)


def _assembled_prompt() -> AssembledPrompt:
    return AssembledPrompt(
        task="reply_to_customer",
        sections=(
            AssembledPromptSection(
                section_id="platform_system",
                label="PLATFORM SYSTEM",
                content="[PLATFORM SYSTEM]\nPlatform safety rules.",
                kind="system",
            ),
            AssembledPromptSection(
                section_id="task_instructions",
                label="TASK INSTRUCTIONS",
                content="[TASK INSTRUCTIONS]\nTASK: reply_to_customer",
                kind="system",
            ),
            AssembledPromptSection(
                section_id="tenant_business_context",
                label="TENANT BUSINESS CONTEXT (reference data)",
                content="[TENANT BUSINESS CONTEXT (reference data)]\ndescription: Barbershop",
                kind="data",
            ),
            AssembledPromptSection(
                section_id="current_customer_message",
                label="CURRENT CUSTOMER MESSAGE (reference data)",
                content="[CURRENT CUSTOMER MESSAGE (reference data)]\nBook a haircut?",
                kind="data",
            ),
        ),
    )


class MockOpenAIChatClient:
    def __init__(
        self,
        *,
        response: OpenAIChatCompletionResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.last_request: OpenAIChatCompletionRequest | None = None

    async def create_chat_completion(
        self,
        request: OpenAIChatCompletionRequest,
    ) -> OpenAIChatCompletionResponse:
        self.last_request = request
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


@pytest.fixture
def gateway_settings() -> Settings:
    return Settings(
        openai_api_key="test-key",
        openai_model="gpt-4o-mini",
        ai_request_timeout_seconds=15.0,
    )


@pytest.mark.anyio
async def test_assembled_prompt_maps_to_openai_request_inside_gateway(
    gateway_settings: Settings,
):
    prompt = _assembled_prompt()
    request = map_assembled_prompt_to_openai_request(
        prompt,
        model=gateway_settings.openai_model,
    )

    assert len(request.messages) == 2
    assert request.messages[0].role == "system"
    assert "Platform safety rules." in request.messages[0].content
    assert "TASK: reply_to_customer" in request.messages[0].content
    assert request.messages[1].role == "user"
    assert "Barbershop" in request.messages[1].content
    assert "Book a haircut?" in request.messages[1].content


@pytest.mark.anyio
async def test_successful_response_returns_normalized_dto(gateway_settings: Settings):
    client = MockOpenAIChatClient(
        response=OpenAIChatCompletionResponse(
            content="Sure, what time works for you?",
            model="gpt-4o-mini",
            input_tokens=120,
            output_tokens=18,
        )
    )
    service = AiGatewayService(app_settings=gateway_settings, client=client)

    result = await service.complete(_assembled_prompt())

    assert isinstance(result, AiGatewayResult)
    assert result.text == "Sure, what time works for you?"
    assert result.model == "gpt-4o-mini"
    assert result.provider == "openai"
    assert result.input_tokens == 120
    assert result.output_tokens == 18
    assert result.latency_ms >= 0
    assert result.error is None
    assert result.succeeded is True
    assert client.last_request is not None
    assert client.last_request.model == "gpt-4o-mini"


@pytest.mark.anyio
async def test_timeout_returns_normalized_error(gateway_settings: Settings):
    client = MockOpenAIChatClient(error=httpx.TimeoutException("timed out"))
    service = AiGatewayService(app_settings=gateway_settings, client=client)

    result = await service.complete(_assembled_prompt())

    assert result.text is None
    assert result.error == ERROR_TIMEOUT
    assert result.provider == "openai"


@pytest.mark.anyio
async def test_empty_response_returns_normalized_error(gateway_settings: Settings):
    client = MockOpenAIChatClient(
        response=OpenAIChatCompletionResponse(
            content="   ",
            model="gpt-4o-mini",
            input_tokens=10,
            output_tokens=0,
        )
    )
    service = AiGatewayService(app_settings=gateway_settings, client=client)

    result = await service.complete(_assembled_prompt())

    assert result.text is None
    assert result.error == ERROR_EMPTY_RESPONSE
    assert result.input_tokens == 10
    assert result.output_tokens == 0


@pytest.mark.anyio
async def test_provider_exception_returns_normalized_error(gateway_settings: Settings):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(503, request=request)
    client = MockOpenAIChatClient(
        error=httpx.HTTPStatusError("service unavailable", request=request, response=response)
    )
    service = AiGatewayService(app_settings=gateway_settings, client=client)

    result = await service.complete(_assembled_prompt())

    assert result.text is None
    assert result.error is not None
    assert result.error.startswith(ERROR_PROVIDER_PREFIX)


@pytest.mark.anyio
async def test_missing_api_key_returns_normalized_error():
    service = AiGatewayService(
        app_settings=Settings(openai_api_key="", openai_model="gpt-4o-mini"),
        client=MockOpenAIChatClient(
            response=OpenAIChatCompletionResponse(
                content="unused",
                model="gpt-4o-mini",
                input_tokens=1,
                output_tokens=1,
            )
        ),
    )

    result = await service.complete(_assembled_prompt())

    assert result.text is None
    assert result.error == ERROR_MISSING_API_KEY


def test_ai_gateway_service_has_no_db_or_session_imports():
    import app.services.ai_gateway_service as module

    source_path = module.__file__
    assert source_path is not None
    source = open(source_path, encoding="utf-8").read().lower()
    assert "sqlalchemy" not in source
    assert "asyncsession" not in source
    assert "app.db" not in source


def test_public_ai_gateway_dto_has_no_provider_specific_types():
    dto_field_types = {field.name: field.type for field in fields(AiGatewayResult)}
    assert set(dto_field_types) == {
        "text",
        "model",
        "provider",
        "input_tokens",
        "output_tokens",
        "latency_ms",
        "error",
    }

    import app.schemas.ai_gateway as schema

    schema_source = open(schema.__file__, encoding="utf-8").read().lower()
    assert "openaichat" not in schema_source
    assert "httpx" not in schema_source


def test_openai_provider_types_stay_in_gateway_internal_module():
    import app.services.ai_gateway._openai as internal
    import app.services.ai_gateway_service as gateway_module

    assert hasattr(internal, "OpenAIChatCompletionRequest")
    gateway_source = open(gateway_module.__file__, encoding="utf-8").read()
    assert "class OpenAIChatCompletionRequest" not in gateway_source
    assert "class OpenAIChatMessage" not in gateway_source
