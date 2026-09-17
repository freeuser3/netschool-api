import json

from app import config as cfg


def test_load_config_reads_file(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"api_token": "abc"}), encoding="utf-8")
    assert cfg.load_config(str(p))["api_token"] == "abc"


def test_get_api_token_prefers_env(monkeypatch, tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"api_token": "file_token"}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("API_TOKEN", "env_token")
    assert cfg.get_api_token() == "env_token"


def test_get_api_token_falls_back_to_file(monkeypatch, tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"api_token": "file_token"}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("API_TOKEN", raising=False)
    assert cfg.get_api_token() == "file_token"
