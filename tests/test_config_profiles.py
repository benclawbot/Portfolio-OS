import json

import pytest

from portfolio_os.config import load_runtime_config


def test_named_profile_inherits_and_overrides_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "workspace": "/default",
                "logging": {"level": "info", "json": False},
                "github": {"owner": "benclawbot"},
                "profiles": {
                    "ci": {
                        "workspace": "/ci",
                        "logging": {"json": True},
                        "analysis": {"fail_on_plugin_error": True},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_runtime_config(path, "ci")

    assert str(config.workspace) == "/ci"
    assert config.profile == "ci"
    assert config.logging.level == "INFO"
    assert config.logging.json is True
    assert config.github.owner == "benclawbot"
    assert config.analysis.fail_on_plugin_error is True


def test_profile_can_be_selected_from_environment(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"profiles": {"local": {"workspace": "/local"}}}), encoding="utf-8")
    monkeypatch.setenv("PORTFOLIO_OS_PROFILE", "local")

    assert str(load_runtime_config(path).workspace) == "/local"


def test_unknown_profile_fails_clearly(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"profiles": {}}), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown runtime configuration profile"):
        load_runtime_config(path, "missing")
