"""Unit tests for scripts/ops/n8n_update_notify.py"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

OPS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(OPS_DIR))

import n8n_update_notify as notify  # noqa: E402


def v(major: int, minor: int, patch: int) -> notify.SemVer:
    return notify.SemVer(major, minor, patch)


def test_normalize_semver_strips_prefixes():
    assert str(notify.normalize_semver("n8n@1.95.3")) == "1.95.3"
    assert str(notify.normalize_semver("v2.22.5")) == "2.22.5"
    assert str(notify.parse_image_tag("docker.n8n.io/n8nio/n8n:2.22.5")) == "2.22.5"
    assert notify.normalize_semver("not-a-version") is None


def test_should_notify_requires_newer_latest():
    installed = v(2, 22, 5)
    latest = v(2, 23, 0)
    assert notify.should_notify(installed, latest, None) is True
    assert notify.should_notify(installed, latest, "2.23.0") is False
    assert notify.should_notify(installed, v(2, 22, 5), None) is False
    assert notify.should_notify(installed, v(2, 22, 4), None) is False


def test_force_notify_bypasses_dedup_only():
    installed = v(1, 0, 0)
    latest = v(1, 1, 0)
    assert notify.should_notify(installed, latest, "1.1.0", force_notify=True) is True
    assert notify.should_notify(installed, installed, "1.0.0", force_notify=True) is False


def test_classify_impact_semver_and_security_bump():
    installed = v(1, 2, 3)
    assert notify.classify_impact(installed, v(1, 2, 4), "") == notify.ImpactLevel.LOW
    assert notify.classify_impact(installed, v(1, 3, 0), "") == notify.ImpactLevel.MEDIUM
    assert notify.classify_impact(installed, v(2, 0, 0), "") == notify.ImpactLevel.HIGH
    assert (
        notify.classify_impact(installed, v(1, 2, 4), "security fix for webhook")
        == notify.ImpactLevel.MEDIUM
    )


def test_extract_release_bullets():
    body = """
<!-- comment -->

## Highlights

- First important change
* Second item with [link](https://example.com)
1. Third numbered item

Some long paragraph that should be ignored because it is not a list and is intentionally longer than two hundred characters so the extractor skips it and continues scanning for proper list items in the release notes body content area.

- Fourth change
"""
    bullets = notify.extract_release_bullets(body)
    assert len(bullets) == 4
    assert bullets[0] == "First important change"
    assert "link" in bullets[1]
    assert bullets[2] == "Third numbered item"
    assert bullets[3] == "Fourth change"


def test_format_telegram_message_shape():
    text = notify.format_telegram_message(
        v(2, 23, 0),
        ["a", "b", "c", "d"],
        notify.ImpactLevel.MEDIUM,
    )
    assert "🚀 n8n Update Available" in text
    assert "Version:\n2.23.0" in text
    assert "1. a" in text
    assert "🟡 Medium" in text
    assert "No update performed." in text


def test_save_and_load_state_roundtrip(tmp_path: Path):
    path = tmp_path / "state.json"
    state = notify.NotifyState(last_checked_version="1.0.0")
    notify.save_state_atomic(path, state)
    loaded, reset = notify.load_state(path)
    assert reset is False
    assert loaded.last_checked_version == "1.0.0"


def test_corrupt_state_backed_up_and_reset(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_text("{not-json", encoding="utf-8")
    loaded, reset = notify.load_state(path)
    assert reset is True
    assert loaded.last_checked_version is None
    backups = list(tmp_path.glob("state.json.bak.*"))
    assert len(backups) == 1
    assert not path.exists()


def test_dry_run_does_not_send_telegram_or_set_notified(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("N8N_UPDATE_NOTIFY_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("N8N_UPDATE_NOTIFY_TELEGRAM_CHAT_ID", "123")

    release = notify.ReleaseInfo(
        version=v(9, 0, 0),
        published_at="2026-05-29T00:00:00Z",
        body="- change one",
        html_url="https://github.com/n8n-io/n8n/releases/tag/n8n@9.0.0",
    )

    with (
        patch.object(notify, "fetch_latest_release", return_value=release),
        patch.object(notify, "read_installed_version", return_value=v(1, 0, 0)),
        patch.object(notify, "send_telegram_message") as send_mock,
    ):
        code = notify.run_check(
            state_path=tmp_path / "state.json",
            container="alpstein_n8n_compose",
            dry_run=True,
        )

    assert code == 0
    send_mock.assert_not_called()
    state, _ = notify.load_state(tmp_path / "state.json")
    assert state.last_checked_version == "9.0.0"
    assert state.last_notified_version is None


def test_force_notify_sends_when_dedup_would_block(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("N8N_UPDATE_NOTIFY_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("N8N_UPDATE_NOTIFY_TELEGRAM_CHAT_ID", "123")

    state_path = tmp_path / "state.json"
    notify.save_state_atomic(
        state_path,
        notify.NotifyState(last_notified_version="2.0.0"),
    )

    release = notify.ReleaseInfo(
        version=v(2, 0, 0),
        published_at="2026-05-29T00:00:00Z",
        body="- security fix",
        html_url="https://example.com",
    )

    with (
        patch.object(notify, "fetch_latest_release", return_value=release),
        patch.object(notify, "read_installed_version", return_value=v(1, 0, 0)),
        patch.object(notify, "send_telegram_message") as send_mock,
    ):
        code = notify.run_check(
            state_path=state_path,
            container="alpstein_n8n_compose",
            force_notify=True,
        )

    assert code == 0
    send_mock.assert_called_once()
    state, _ = notify.load_state(state_path)
    assert state.last_notified_version == "2.0.0"


def test_missing_telegram_config_exits_zero_without_send(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("N8N_UPDATE_NOTIFY_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("N8N_UPDATE_NOTIFY_TELEGRAM_CHAT_ID", raising=False)

    release = notify.ReleaseInfo(
        version=v(3, 0, 0),
        published_at="2026-05-29T00:00:00Z",
        body="- change",
        html_url="https://example.com",
    )

    with (
        patch.object(notify, "fetch_latest_release", return_value=release),
        patch.object(notify, "read_installed_version", return_value=v(1, 0, 0)),
        patch.object(notify, "send_telegram_message") as send_mock,
    ):
        code = notify.run_check(state_path=tmp_path / "state.json", container="test")

    assert code == 0
    send_mock.assert_not_called()
    state, _ = notify.load_state(tmp_path / "state.json")
    assert state.last_notified_version is None
    assert state.last_checked_version == "3.0.0"


def test_github_failure_exits_nonzero_without_advancing_notified(tmp_path: Path):
    import urllib.error

    state_path = tmp_path / "state.json"
    notify.save_state_atomic(
        state_path,
        notify.NotifyState(last_notified_version="1.0.0"),
    )

    with patch.object(
        notify,
        "fetch_latest_release",
        side_effect=urllib.error.URLError("network down"),
    ):
        code = notify.run_check(state_path=state_path, container="test")

    assert code == 1
    state, _ = notify.load_state(state_path)
    assert state.last_notified_version == "1.0.0"


def test_telegram_failure_does_not_advance_notified(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("N8N_UPDATE_NOTIFY_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("N8N_UPDATE_NOTIFY_TELEGRAM_CHAT_ID", "123")

    state_path = tmp_path / "state.json"
    release = notify.ReleaseInfo(
        version=v(4, 0, 0),
        published_at="2026-05-29T00:00:00Z",
        body="- item",
        html_url="https://example.com",
    )

    with (
        patch.object(notify, "fetch_latest_release", return_value=release),
        patch.object(notify, "read_installed_version", return_value=v(1, 0, 0)),
        patch.object(
            notify,
            "send_telegram_message",
            side_effect=RuntimeError("TELEGRAM_SEND_FAILED: HTTP 500"),
        ),
    ):
        code = notify.run_check(state_path=state_path, container="test")

    assert code == 1
    state, _ = notify.load_state(state_path)
    assert state.last_notified_version is None


REPO_ROOT = OPS_DIR.parent.parent
SYSTEMD_DIR = REPO_ROOT / "docs" / "ops" / "systemd"


def test_systemd_units_present_and_notify_only():
    service = (SYSTEMD_DIR / "alpstein-n8n-update-notify.service").read_text()
    timer = (SYSTEMD_DIR / "alpstein-n8n-update-notify.timer").read_text()
    assert "Type=oneshot" in service
    assert "n8n_update_notify.py" in service
    assert "/etc/alpstein/n8n-update-notify.env" in service
    assert "OnCalendar=daily" in timer
    assert "RandomizedDelaySec=30min" in timer
    assert "Persistent=true" in timer
    forbidden = ("compose pull", "compose up", "compose down", "docker pull", "docker restart")
    combined = (service + timer).lower()
    for phrase in forbidden:
        assert phrase not in combined
