"""Unit tests for Instagram Graph profile client (mocked HTTP)."""

from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import Settings
from app.services.instagram_client import (
    InstagramApiError,
    InstagramConfigurationError,
    INSTAGRAM_GRAPH_API_VERSION,
    InstagramExpiredTokenError,
    InstagramGraphClient,
    InstagramInvalidTokenError,
    InstagramNetworkError,
    InstagramUserIdMismatchError,
)


@pytest.fixture
def ig_settings() -> Settings:
    return Settings(
        instagram_access_token="test-token",
        instagram_user_id="12345",
    )


def test_get_profile_success(ig_settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "graph.instagram.com"
        assert request.url.path == "/me"
        assert request.url.params["access_token"] == "test-token"
        return httpx.Response(
            200,
            json={
                "id": "12345",
                "username": "alpstein_test",
                "account_type": "BUSINESS",
            },
        )

    transport = httpx.MockTransport(handler)
    client = InstagramGraphClient(
        app_settings=ig_settings,
        http_client=httpx.Client(transport=transport),
    )
    profile = client.get_profile()
    assert profile.id == "12345"
    assert profile.username == "alpstein_test"
    assert profile.account_type == "BUSINESS"


def test_get_profile_missing_token() -> None:
    cfg = Settings(instagram_access_token="", instagram_user_id="12345")
    client = InstagramGraphClient(app_settings=cfg)
    with pytest.raises(InstagramConfigurationError) as exc_info:
        client.get_profile()
    assert exc_info.value.code == "CONFIGURATION_ERROR"


def test_get_profile_invalid_token(ig_settings: Settings) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "Invalid OAuth access token.",
                    "type": "OAuthException",
                    "code": 190,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    client = InstagramGraphClient(
        app_settings=ig_settings,
        http_client=httpx.Client(transport=transport),
    )
    with pytest.raises(InstagramInvalidTokenError):
        client.get_profile()


def test_get_profile_expired_token(ig_settings: Settings) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "Error validating access token: Session has expired.",
                    "type": "OAuthException",
                    "code": 190,
                    "error_subcode": 463,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    client = InstagramGraphClient(
        app_settings=ig_settings,
        http_client=httpx.Client(transport=transport),
    )
    with pytest.raises(InstagramExpiredTokenError):
        client.get_profile()


def test_get_profile_network_error(ig_settings: Settings) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    transport = httpx.MockTransport(handler)
    client = InstagramGraphClient(
        app_settings=ig_settings,
        http_client=httpx.Client(transport=transport),
    )
    with pytest.raises(InstagramNetworkError):
        client.get_profile()


def test_get_profile_user_id_mismatch(ig_settings: Settings) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "99999",
                "username": "other",
                "account_type": "PERSONAL",
            },
        )

    transport = httpx.MockTransport(handler)
    client = InstagramGraphClient(
        app_settings=ig_settings,
        http_client=httpx.Client(transport=transport),
    )
    with pytest.raises(InstagramUserIdMismatchError):
        client.get_profile()


def test_get_profile_api_error_missing_fields(ig_settings: Settings) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "12345"})

    transport = httpx.MockTransport(handler)
    client = InstagramGraphClient(
        app_settings=ig_settings,
        http_client=httpx.Client(transport=transport),
    )
    with pytest.raises(InstagramApiError):
        client.get_profile()


def test_get_user_profile_success(ig_settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.host == "graph.instagram.com"
        assert request.url.path == f"/{INSTAGRAM_GRAPH_API_VERSION}/17841400000000001"
        assert request.url.params["fields"] == "id,username,name,profile_pic"
        assert request.url.params["access_token"] == "test-token"
        return httpx.Response(
            200,
            json={
                "id": "17841400000000001",
                "username": "ibatfox",
                "name": "Ivan Bataiev-Lykhvar",
                "profile_pic": "https://example.test/profile.jpg",
            },
        )

    transport = httpx.MockTransport(handler)
    client = InstagramGraphClient(
        app_settings=ig_settings,
        http_client=httpx.Client(transport=transport),
    )

    profile = client.get_user_profile(" 17841400000000001 ")

    assert profile.id == "17841400000000001"
    assert profile.username == "ibatfox"
    assert profile.name == "Ivan Bataiev-Lykhvar"
    assert profile.profile_pic == "https://example.test/profile.jpg"


def test_get_user_profile_api_error(ig_settings: Settings) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "(#10) Application does not have permission",
                    "type": "OAuthException",
                    "code": 10,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    client = InstagramGraphClient(
        app_settings=ig_settings,
        http_client=httpx.Client(transport=transport),
    )

    with pytest.raises(InstagramApiError) as exc_info:
        client.get_user_profile("17841400000000001")

    assert "permission" in str(exc_info.value)


def test_send_text_message_success(ig_settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.host == "graph.instagram.com"
        assert request.url.path == f"/{INSTAGRAM_GRAPH_API_VERSION}/12345/messages"
        assert request.headers["authorization"] == "Bearer test-token"
        assert request.url.query == b""
        assert json.loads(request.content) == {
            "recipient": {"id": "17841400000000000"},
            "message": {"text": "Manual test"},
        }
        return httpx.Response(
            200,
            json={
                "recipient_id": "17841400000000000",
                "message_id": "mid.sent.001",
            },
        )

    transport = httpx.MockTransport(handler)
    client = InstagramGraphClient(
        app_settings=ig_settings,
        http_client=httpx.Client(transport=transport),
    )

    result = client.send_text_message(
        recipient_id=" 17841400000000000 ",
        text=" Manual test ",
    )

    assert result.recipient_id == "17841400000000000"
    assert result.message_id == "mid.sent.001"


def test_send_text_message_missing_token() -> None:
    cfg = Settings(instagram_access_token="", instagram_user_id="12345")
    client = InstagramGraphClient(app_settings=cfg)

    with pytest.raises(InstagramConfigurationError) as exc_info:
        client.send_text_message("17841400000000000", "Manual test")

    assert exc_info.value.code == "CONFIGURATION_ERROR"


def test_send_text_message_requires_recipient_and_text(ig_settings: Settings) -> None:
    client = InstagramGraphClient(app_settings=ig_settings)

    with pytest.raises(InstagramConfigurationError):
        client.send_text_message("", "Manual test")
    with pytest.raises(InstagramConfigurationError):
        client.send_text_message("17841400000000000", " ")


def test_send_text_message_api_error(ig_settings: Settings) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "Unsupported post request.",
                    "type": "GraphMethodException",
                    "code": 100,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    client = InstagramGraphClient(
        app_settings=ig_settings,
        http_client=httpx.Client(transport=transport),
    )

    with pytest.raises(InstagramApiError):
        client.send_text_message("17841400000000000", "Manual test")
