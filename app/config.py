import json
import os


def load_config(path: str = "config.json") -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_api_token() -> str:
    env_token = os.environ.get("API_TOKEN")
    if env_token:
        return env_token
    return load_config()["api_token"]
