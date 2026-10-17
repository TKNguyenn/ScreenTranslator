"""Public Trial settings only; user keys are never bundled here."""
from collections.abc import Mapping
from typing import Any

TRIAL_TYPE = "ai_trial"
TRIAL_BASE_URL = "https://api.vilao.ai/v1"
TRIAL_MODELS = ("gemini-3.8-flash", "gpt-6-luna", "gpt-6-sol")
TRIAL_DAILY_BUDGET_VND = 100
TRIAL_ESTIMATED_COST_VND = {"gpt-6-luna": 1, "gemini-3.8-flash": 3, "gpt-6-sol": 4}
TRIAL_MODEL_NAMES = {"gpt-6-luna": "GPT-6 Luna", "gemini-3.8-flash": "Gemini 3.8 Flash", "gpt-6-sol": "GPT-6 Sol"}


def trial_model_label(model: str) -> str:
    return f"{TRIAL_MODEL_NAMES[model]} — từ {TRIAL_ESTIMATED_COST_VND[model]}đ/lượt"


def is_trial_profile(values: Mapping[str, Any]) -> bool:
    # Custom providers can use the same gateway without Trial restrictions.
    return str(values.get("type", "")).strip().lower() == TRIAL_TYPE


def trial_profile_values(values: Mapping[str, Any]) -> dict[str, Any]:
    model = str(values.get("model", "")).strip() or TRIAL_MODELS[0]
    if model not in TRIAL_MODELS:
        raise ValueError("Trial: hãy chọn một model trong danh sách được hỗ trợ.")
    endpoint = str(values.get("endpoint_mode", "auto")).strip().lower()
    if endpoint not in {"auto", "responses", "chat_completions", "completions"}:
        raise ValueError("Trial: hãy chọn endpoint auto, responses, chat_completions hoặc completions.")
    overrides = values.get("streaming_override", {})
    # Only key, selected model, endpoint mode and streaming are user-owned Trial settings.
    return {
        "type": TRIAL_TYPE,
        "base_url": TRIAL_BASE_URL,
        "api_key": str(values.get("api_key", "")).strip(),
        "models": list(TRIAL_MODELS),
        "model": model,
        "endpoint_mode": endpoint,
        "streaming_override": dict(overrides) if isinstance(overrides, dict) else {},
    }
