from __future__ import annotations

from copy import deepcopy
from string import Formatter
from typing import Any, Mapping

from app.languages import LANGUAGE_NAMES

ENGINEERING_TERMS = (
    "PLC, HMI, CMM, AGV, AMR, ROS, LiDAR, SLAM, costmap, footprint, Home, Jog, "
    "servo, encoder, driver, inverter, IO, TCP/IP, Profinet, Modbus, EtherCAT"
)

PERFORMANCE_MODES: tuple[str, ...] = ("ultra_fast", "fast", "quality")
CONTEXT_PRESETS: tuple[str, ...] = ("engineering", "chat", "email")

PERFORMANCE_LABELS: dict[str, str] = {
    "ultra_fast": "Cực nhanh",
    "fast": "Nhanh",
    "quality": "Chuẩn",
}

CONTEXT_LABELS: dict[str, str] = {
    "engineering": "Engineer - kỹ thuật",
    "chat": "Chat - hội thoại",
    "email": "Email - công việc",
}

STYLE_DESCRIPTIONS: dict[str, str] = {
    "engineering": "industrial automation, robotics, manufacturing, software, engineering",
    "chat": "natural conversational chat",
    "email": "professional business email",
}

# These are intentionally templates rather than fully-rendered prompts. The Prompt
# Editor exposes the same defaults to users and lets them override each of the nine
# performance/style combinations independently.
DEFAULT_PROMPT_TEMPLATES: dict[str, dict[str, str]] = {
    "ultra_fast": {
        "engineering": (
            "Translate directly to {target_language} for industrial automation. "
            "Preserve technical terms, conditions, and negations. "
            "No analysis or explanation. Output translation only."
        ),
        "chat": (
            "Translate directly to {target_language} as natural chat. "
            "Preserve meaning. No analysis or explanation. Output translation only."
        ),
        "email": (
            "Translate directly to {target_language} as a professional email. "
            "Preserve meaning and tone. No analysis or explanation. "
            "Output translation only."
        ),
    },
    "fast": {
        "engineering": (
            "Translate from {source_language} to {target_language}. Return only the translation. "
            "Context: industrial automation, robotics, manufacturing, software, engineering. "
            "Preserve code, identifiers, model numbers, units, protocols, URLs, and meaningful line breaks. "
            "Keep established technical terms unchanged when appropriate."
        ),
        "chat": (
            "Translate from {source_language} to {target_language}. Return only the translation. "
            "Context: natural conversational chat. Preserve code, identifiers, model numbers, units, protocols, "
            "URLs, and meaningful line breaks. Keep established technical terms unchanged when appropriate."
        ),
        "email": (
            "Translate from {source_language} to {target_language}. Return only the translation. "
            "Context: professional business email. Preserve code, identifiers, model numbers, units, protocols, "
            "URLs, and meaningful line breaks. Keep established technical terms unchanged when appropriate."
        ),
    },
    "quality": {
        "engineering": (
            "Translate the user text from {source_language} to {target_language}.\n"
            "Return only the translated text. Do not add explanations, labels, quotes, or commentary.\n"
            "Preserve line breaks when they carry meaning.\n"
            "Preserve code, variable names, file paths, URLs, model numbers, units, and protocol names.\n"
            "Do not invent missing information.\n"
            "Context: industrial automation, robotics, manufacturing, software, and engineering documentation.\n"
            "Keep established technical terms stable when appropriate: {engineering_terms}.\n"
            "Prefer precise engineering terminology over conversational paraphrase."
        ),
        "chat": (
            "Translate the user text from {source_language} to {target_language}.\n"
            "Return only the translated text. Do not add explanations, labels, quotes, or commentary.\n"
            "Preserve line breaks when they carry meaning.\n"
            "Preserve code, variable names, file paths, URLs, model numbers, units, and protocol names.\n"
            "Do not invent missing information.\n"
            "Use concise, natural conversational language while preserving the original intent."
        ),
        "email": (
            "Translate the user text from {source_language} to {target_language}.\n"
            "Return only the translated text. Do not add explanations, labels, quotes, or commentary.\n"
            "Preserve line breaks when they carry meaning.\n"
            "Preserve code, variable names, file paths, URLs, model numbers, units, and protocol names.\n"
            "Do not invent missing information.\n"
            "Use professional, natural business language while preserving the original intent."
        ),
    },
}

ALLOWED_PROMPT_PLACEHOLDERS = frozenset(
    {
        "source_language",
        "target_language",
        "style",
        "engineering_terms",
        "glossary",
    }
)


def normalize_prompt_overrides(raw: Mapping[str, Any] | None) -> dict[str, dict[str, str]]:
    """Normalize/validate the portable prompt override structure.

    Only non-empty custom templates are returned. Missing combinations always fall
    back to the immutable defaults in this module.
    """
    result: dict[str, dict[str, str]] = {}
    if not isinstance(raw, Mapping):
        return result

    for mode in PERFORMANCE_MODES:
        styles = raw.get(mode)
        if not isinstance(styles, Mapping):
            continue
        for style in CONTEXT_PRESETS:
            value = styles.get(style)
            if value is None:
                continue
            template = str(value).strip()
            if not template:
                continue
            validate_prompt_template(template)
            result.setdefault(mode, {})[style] = template
    return result


def clone_prompt_overrides(raw: Mapping[str, Any] | None) -> dict[str, dict[str, str]]:
    return deepcopy(normalize_prompt_overrides(raw))


def default_prompt_template(performance_mode: str, context_preset: str) -> str:
    mode = _normalize_mode(performance_mode)
    style = _normalize_style(context_preset)
    return DEFAULT_PROMPT_TEMPLATES[mode][style]


def resolve_prompt_template(
    performance_mode: str,
    context_preset: str,
    prompt_overrides: Mapping[str, Any] | None = None,
) -> tuple[str, bool]:
    """Return (template, is_custom) for one speed/style pair."""
    mode = _normalize_mode(performance_mode)
    style = _normalize_style(context_preset)
    overrides = normalize_prompt_overrides(prompt_overrides)
    custom = overrides.get(mode, {}).get(style)
    if custom:
        return custom, True
    return default_prompt_template(mode, style), False


def validate_prompt_template(template: str) -> None:
    if not isinstance(template, str) or not template.strip():
        raise ValueError("Prompt không được để trống.")

    formatter = Formatter()
    try:
        parsed = list(formatter.parse(template))
    except ValueError as exc:
        raise ValueError(f"Prompt có dấu ngoặc {{ }} không hợp lệ: {exc}") from exc

    for _, field_name, format_spec, conversion in parsed:
        if field_name is None:
            continue
        if field_name not in ALLOWED_PROMPT_PLACEHOLDERS:
            allowed = ", ".join(sorted(ALLOWED_PROMPT_PLACEHOLDERS))
            raise ValueError(
                f"Placeholder '{{{field_name}}}' không được hỗ trợ. Cho phép: {allowed}."
            )
        if format_spec:
            raise ValueError(f"Placeholder '{{{field_name}}}' không hỗ trợ format specifier.")
        if conversion:
            raise ValueError(f"Placeholder '{{{field_name}}}' không hỗ trợ conversion.")


def render_prompt_template(
    template: str,
    *,
    source_language: str,
    target_language: str,
    context_preset: str,
    glossary: str = "",
) -> str:
    validate_prompt_template(template)
    style = _normalize_style(context_preset)
    values = {
        "source_language": LANGUAGE_NAMES.get(source_language, source_language),
        "target_language": LANGUAGE_NAMES.get(target_language, target_language),
        "style": STYLE_DESCRIPTIONS[style],
        "engineering_terms": ENGINEERING_TERMS,
        "glossary": glossary.strip(),
    }
    try:
        rendered = template.format_map(values)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Không thể render prompt: {exc}") from exc
    return rendered.strip()


def build_translation_instructions(
    source_language: str,
    target_language: str,
    context_preset: str,
    performance_mode: str = "quality",
    *,
    prompt_overrides: Mapping[str, Any] | None = None,
    glossary: str = "",
) -> str:
    template, _ = resolve_prompt_template(
        performance_mode=performance_mode,
        context_preset=context_preset,
        prompt_overrides=prompt_overrides,
    )
    return render_prompt_template(
        template,
        source_language=source_language,
        target_language=target_language,
        context_preset=context_preset,
        glossary=glossary,
    )


def prompt_is_custom(
    performance_mode: str,
    context_preset: str,
    prompt_overrides: Mapping[str, Any] | None,
) -> bool:
    _, is_custom = resolve_prompt_template(
        performance_mode=performance_mode,
        context_preset=context_preset,
        prompt_overrides=prompt_overrides,
    )
    return is_custom


def _normalize_mode(value: str) -> str:
    mode = str(value).strip().lower()
    if mode not in PERFORMANCE_MODES:
        raise ValueError(f"Unsupported performance mode: {value}")
    return mode


def _normalize_style(value: str) -> str:
    style = str(value).strip().lower()
    if style not in CONTEXT_PRESETS:
        raise ValueError(f"Unsupported translation style: {value}")
    return style
