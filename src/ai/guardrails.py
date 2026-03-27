"""
AI guardrails.
Validate optional AI outputs so they only explain deterministic facts.
"""

import re
from typing import Dict, List, Optional, Tuple


FORBIDDEN_PHRASES = [
    "will likely",
    "will probably",
    "expected to",
    "expect to",
    "probability",
    "probable",
    "forecast",
    "predict",
    "prediction",
    "in the future",
    "going forward",
    "will be",
    "will have",
    "will increase",
    "will decrease",
    "will improve",
    "will worsen",
    "you should",
    "you must",
    "you need to",
    "i recommend",
    "i suggest",
    "recommend that",
    "suggest that",
    "advise",
    "advised",
    "likely to",
    "unlikely to",
    "high chance",
    "low chance",
    "confidence",
    "confident that",
]


def sanitize_context(context_dict: Dict) -> Dict:
    """Restrict AI context to compact serializable content only."""
    sanitized = {
        "kpis": context_dict.get("kpis", {}),
        "insights": list(context_dict.get("insights", []))[:20],
        "table_snippets": {},
        "trends": context_dict.get("trends", {}),
    }
    for key, value in context_dict.get("table_snippets", {}).items():
        sanitized["table_snippets"][key] = value[:10] if isinstance(value, list) else value
    return sanitized


def validate_llm_output(
    llm_text: str,
    facts_used: List[str],
    strict: bool = True,
) -> Tuple[bool, Optional[str]]:
    """Validate LLM output to detect unsupported claims."""
    forbidden_match = _contains_forbidden_language(llm_text)
    if forbidden_match:
        return False, f"Forbidden language detected: {forbidden_match}"

    if strict:
        new_values = _detect_new_values(llm_text, facts_used)
        if new_values:
            return False, f"New values detected that were not in facts: {new_values[:3]}"

    return True, None


def apply_guardrails(
    llm_output: str,
    deterministic_answer: str,
    facts_used: List[str],
    strict: bool = True,
) -> Tuple[str, bool, Optional[str]]:
    """Apply all guardrails and fall back to deterministic output when blocked."""
    is_valid, error_msg = validate_llm_output(llm_output, facts_used, strict=strict)
    if is_valid:
        return llm_output, False, None
    return deterministic_answer, True, error_msg


def generate_guarded_text(
    llm_output: str,
    deterministic_answer: str,
    facts_used: List[str],
    strict: bool = True,
) -> Dict[str, Optional[str]]:
    """Return a uniform payload for guarded AI text generation."""
    final_output, was_blocked, block_reason = apply_guardrails(
        llm_output,
        deterministic_answer,
        facts_used,
        strict=strict,
    )
    return {
        "final_output": final_output,
        "was_blocked": was_blocked,
        "block_reason": block_reason,
    }


def check_transformers_available() -> bool:
    """Check if transformers library is available."""
    try:
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False


def _contains_forbidden_language(text: str) -> Optional[str]:
    text_lower = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text_lower:
            return phrase
    return None


def _detect_new_values(llm_text: str, facts_used: List[str]) -> List[str]:
    """Detect values introduced by the LLM that are not present in the facts."""
    llm_values = _extract_supported_values(llm_text)
    facts_values = _extract_supported_values(" ".join(facts_used))

    new_values = []
    for value_type, llm_value in llm_values:
        found_match = False
        for fact_type, fact_value in facts_values:
            if value_type != fact_type:
                continue
            if fact_type == "number":
                if abs(llm_value - fact_value) / max(abs(fact_value), 1) < 0.01:
                    found_match = True
                    break
            elif llm_value == fact_value:
                found_match = True
                break
        if not found_match:
            new_values.append(_format_value(value_type, llm_value))

    return new_values


def _extract_supported_values(text: str) -> List[Tuple[str, float]]:
    values: List[Tuple[str, float]] = []

    for match in re.findall(r"(?:EUR|€)\s*([0-9,]+(?:\.[0-9]+)?)", text, flags=re.IGNORECASE):
        values.append(("currency", float(match.replace(",", ""))))

    for match in re.findall(r"([0-9]+(?:\.[0-9]+)?)%", text):
        values.append(("percent", float(match)))

    for match in re.findall(r"([0-9]+(?:\.[0-9]+)?)\s+month", text, flags=re.IGNORECASE):
        values.append(("months", float(match)))

    for match in re.findall(r"\b([0-9]+(?:\.[0-9]+)?)\b", text):
        values.append(("number", float(match)))

    return values


def _format_value(value_type: str, value: float) -> str:
    if value_type == "currency":
        return f"EUR {value:,.0f}"
    if value_type == "percent":
        return f"{value:.1f}%"
    if value_type == "months":
        return f"{value:.1f} months"
    return f"{value:.1f}"
