import os
from openai import OpenAI


def get_client():
    api_key = os.environ.get("OPENCODE_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://opencode.ai/zen/v1")
    if base_url.endswith("/chat/completions"):
        base_url = base_url[:-len("/chat/completions")]
    return OpenAI(api_key=api_key, base_url=base_url)


def get_model():
    return os.environ.get("OPENAI_MODEL", "big-pickle")
