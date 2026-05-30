"""Instagram Graph API client — profile connectivity and manual messaging smoke."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings, settings

INSTAGRAM_GRAPH_ME_URL = "https://graph.instagram.com/me"
INSTAGRAM_GRAPH_API_VERSION = "v24.0"
INSTAGRAM_MESSAGES_URL_TEMPLATE = (
    "https://graph.instagram.com/{api_version}/{ig_user_id}/messages"
)
INSTAGRAM_USER_PROFILE_URL_TEMPLATE = (
    "https://graph.instagram.com/{api_version}/{scoped_user_id}"
)
PROFILE_FIELDS = "id,username,account_type"
USER_PROFILE_FIELDS = "id,username,name,profile_pic"

# Meta Graph API OAuth error code for invalid/expired access tokens.
_META_OAUTH_ERROR_CODE = 190
_META_EXPIRED_TOKEN_SUBCODES = frozenset({463, 467})


@dataclass(frozen=True)
class InstagramProfile:
    id: str
    username: str
    account_type: str


@dataclass(frozen=True)
class InstagramUserProfile:
    id: str
    username: str | None = None
    name: str | None = None
    profile_pic: str | None = None


@dataclass(frozen=True)
class InstagramSendResult:
    recipient_id: str
    message_id: str


class InstagramClientError(Exception):
    """Base error for Instagram Graph connectivity failures."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class InstagramConfigurationError(InstagramClientError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="CONFIGURATION_ERROR")


class InstagramInvalidTokenError(InstagramClientError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="INVALID_TOKEN")


class InstagramExpiredTokenError(InstagramClientError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="EXPIRED_TOKEN")


class InstagramNetworkError(InstagramClientError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="NETWORK_ERROR")


class InstagramApiError(InstagramClientError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="API_ERROR")


class InstagramUserIdMismatchError(InstagramClientError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="USER_ID_MISMATCH")


class InstagramGraphClient:
    """Instagram Graph client for credential validation and manual smoke sends."""

    def __init__(
        self,
        *,
        app_settings: Settings | None = None,
        http_client: httpx.Client | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._settings = app_settings or settings
        self._http_client = http_client
        self._timeout_seconds = timeout_seconds

    def get_profile(self) -> InstagramProfile:
        access_token = self._settings.instagram_access_token.strip()
        expected_user_id = self._settings.instagram_user_id.strip()

        if not access_token:
            raise InstagramConfigurationError(
                "INSTAGRAM_ACCESS_TOKEN is not configured",
            )
        if not expected_user_id:
            raise InstagramConfigurationError(
                "INSTAGRAM_USER_ID is not configured",
            )

        timeout = self._timeout_seconds
        if timeout is None:
            timeout = float(self._settings.ai_request_timeout_seconds)

        params = {
            "fields": PROFILE_FIELDS,
            "access_token": access_token,
        }

        try:
            if self._http_client is not None:
                response = self._http_client.get(
                    INSTAGRAM_GRAPH_ME_URL,
                    params=params,
                )
            else:
                with httpx.Client(timeout=httpx.Timeout(timeout)) as client:
                    response = client.get(INSTAGRAM_GRAPH_ME_URL, params=params)
        except httpx.TimeoutException as exc:
            raise InstagramNetworkError(
                f"Instagram Graph API request timed out: {exc}",
            ) from exc
        except httpx.RequestError as exc:
            raise InstagramNetworkError(
                f"Instagram Graph API network error: {exc}",
            ) from exc

        return _parse_profile_response(
            response,
            expected_user_id=expected_user_id,
        )

    def send_text_message(self, recipient_id: str, text: str) -> InstagramSendResult:
        access_token = self._settings.instagram_access_token.strip()
        ig_user_id = self._settings.instagram_user_id.strip()
        clean_recipient_id = recipient_id.strip()
        clean_text = text.strip()

        if not access_token:
            raise InstagramConfigurationError(
                "INSTAGRAM_ACCESS_TOKEN is not configured",
            )
        if not ig_user_id:
            raise InstagramConfigurationError(
                "INSTAGRAM_USER_ID is not configured",
            )
        if not clean_recipient_id:
            raise InstagramConfigurationError("recipient_id is required")
        if not clean_text:
            raise InstagramConfigurationError("text is required")

        timeout = self._timeout_seconds
        if timeout is None:
            timeout = float(self._settings.ai_request_timeout_seconds)

        url = INSTAGRAM_MESSAGES_URL_TEMPLATE.format(
            api_version=INSTAGRAM_GRAPH_API_VERSION,
            ig_user_id=ig_user_id,
        )
        payload = {
            "recipient": {"id": clean_recipient_id},
            "message": {"text": clean_text},
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            if self._http_client is not None:
                response = self._http_client.post(
                    url,
                    json=payload,
                    headers=headers,
                )
            else:
                with httpx.Client(timeout=httpx.Timeout(timeout)) as client:
                    response = client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise InstagramNetworkError(
                f"Instagram Messaging API request timed out: {exc}",
            ) from exc
        except httpx.RequestError as exc:
            raise InstagramNetworkError(
                f"Instagram Messaging API network error: {exc}",
            ) from exc

        return _parse_send_response(response)

    def get_user_profile(self, scoped_user_id: str) -> InstagramUserProfile:
        access_token = self._settings.instagram_access_token.strip()
        clean_user_id = scoped_user_id.strip()

        if not access_token:
            raise InstagramConfigurationError(
                "INSTAGRAM_ACCESS_TOKEN is not configured",
            )
        if not clean_user_id:
            raise InstagramConfigurationError("scoped_user_id is required")

        timeout = self._timeout_seconds
        if timeout is None:
            timeout = float(self._settings.ai_request_timeout_seconds)

        url = INSTAGRAM_USER_PROFILE_URL_TEMPLATE.format(
            api_version=INSTAGRAM_GRAPH_API_VERSION,
            scoped_user_id=clean_user_id,
        )
        params = {
            "fields": USER_PROFILE_FIELDS,
            "access_token": access_token,
        }

        try:
            if self._http_client is not None:
                response = self._http_client.get(url, params=params)
            else:
                with httpx.Client(timeout=httpx.Timeout(timeout)) as client:
                    response = client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise InstagramNetworkError(
                f"Instagram User Profile API request timed out: {exc}",
            ) from exc
        except httpx.RequestError as exc:
            raise InstagramNetworkError(
                f"Instagram User Profile API network error: {exc}",
            ) from exc

        return _parse_user_profile_response(
            response,
            expected_user_id=clean_user_id,
        )


def get_profile(*, app_settings: Settings | None = None) -> InstagramProfile:
    """Fetch the authenticated Instagram account profile via Graph API /me."""
    return InstagramGraphClient(app_settings=app_settings).get_profile()


def send_text_message(
    recipient_id: str,
    text: str,
    *,
    app_settings: Settings | None = None,
) -> InstagramSendResult:
    """Send a manual Instagram text message to a webhook sender id."""
    return InstagramGraphClient(app_settings=app_settings).send_text_message(
        recipient_id,
        text,
    )


def get_user_profile(
    scoped_user_id: str,
    *,
    app_settings: Settings | None = None,
) -> InstagramUserProfile:
    """Fetch an Instagram messaging sender profile by Instagram-scoped user id."""
    return InstagramGraphClient(app_settings=app_settings).get_user_profile(
        scoped_user_id,
    )


def _parse_profile_response(
    response: httpx.Response,
    *,
    expected_user_id: str,
) -> InstagramProfile:
    try:
        payload: dict[str, Any] = response.json()
    except ValueError as exc:
        raise InstagramApiError(
            f"Instagram Graph API returned non-JSON response (HTTP {response.status_code})",
        ) from exc

    if response.is_error or "error" in payload:
        raise _classify_graph_error(payload.get("error", payload))

    profile_id = str(payload.get("id", "")).strip()
    username = str(payload.get("username", "")).strip()
    account_type = str(payload.get("account_type", "")).strip()

    if not profile_id or not username:
        raise InstagramApiError(
            "Instagram Graph API response is missing required profile fields",
        )

    if profile_id != expected_user_id:
        raise InstagramUserIdMismatchError(
            "INSTAGRAM_USER_ID does not match the account returned by Graph API /me",
        )

    return InstagramProfile(
        id=profile_id,
        username=username,
        account_type=account_type or "unknown",
    )


def _parse_send_response(response: httpx.Response) -> InstagramSendResult:
    try:
        payload: dict[str, Any] = response.json()
    except ValueError as exc:
        raise InstagramApiError(
            "Instagram Messaging API returned non-JSON response "
            f"(HTTP {response.status_code})",
        ) from exc

    if response.is_error or "error" in payload:
        raise _classify_graph_error(payload.get("error", payload))

    recipient_id = str(payload.get("recipient_id", "")).strip()
    message_id = str(payload.get("message_id", "")).strip()
    if not recipient_id or not message_id:
        raise InstagramApiError(
            "Instagram Messaging API response is missing required send fields",
        )

    return InstagramSendResult(recipient_id=recipient_id, message_id=message_id)


def _parse_user_profile_response(
    response: httpx.Response,
    *,
    expected_user_id: str,
) -> InstagramUserProfile:
    try:
        payload: dict[str, Any] = response.json()
    except ValueError as exc:
        raise InstagramApiError(
            "Instagram User Profile API returned non-JSON response "
            f"(HTTP {response.status_code})",
        ) from exc

    if response.is_error or "error" in payload:
        raise _classify_graph_error(payload.get("error", payload))

    profile_id = str(payload.get("id", "")).strip()
    if not profile_id:
        raise InstagramApiError(
            "Instagram User Profile API response is missing id",
        )
    if profile_id != expected_user_id:
        raise InstagramUserIdMismatchError(
            "Instagram User Profile API returned a different sender id",
        )

    username = _optional_string(payload.get("username"))
    name = _optional_string(payload.get("name"))
    profile_pic = _optional_string(payload.get("profile_pic"))

    return InstagramUserProfile(
        id=profile_id,
        username=username,
        name=name,
        profile_pic=profile_pic,
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _classify_graph_error(error: Any) -> InstagramClientError:
    if not isinstance(error, dict):
        return InstagramApiError("Instagram Graph API returned an error")

    message = str(error.get("message") or "Instagram Graph API error")
    code = error.get("code")
    subcode = error.get("error_subcode")
    lowered = message.lower()

    if code == _META_OAUTH_ERROR_CODE or "access token" in lowered:
        if subcode in _META_EXPIRED_TOKEN_SUBCODES or "expired" in lowered:
            return InstagramExpiredTokenError(message)
        return InstagramInvalidTokenError(message)

    if "session has been invalidated" in lowered:
        return InstagramExpiredTokenError(message)

    return InstagramApiError(message)
