from src.ai.guardrails import apply_guardrails, sanitize_context, validate_llm_output


def test_validate_llm_output_blocks_forbidden_language_and_new_numbers():
    facts_used = ["Revenue: \u20ac18,000", "Gross profit: \u20ac2,000"]

    bad_text = "The project will likely improve, with revenue of \u20ac99,999."
    is_valid, error = validate_llm_output(bad_text, facts_used, strict=True)
    assert not is_valid
    assert "Forbidden language detected" in error

    bad_number_text = "The project generated \u20ac99,999 in revenue."
    is_valid, error = validate_llm_output(bad_number_text, facts_used, strict=True)
    assert not is_valid
    assert "New values detected" in error


def test_apply_guardrails_falls_back_to_deterministic_answer():
    facts_used = ["Revenue: \u20ac18,000", "Gross profit: \u20ac2,000"]
    fallback = "Deterministic answer."
    safe_text, was_blocked, reason = apply_guardrails(
        "You should definitely improve this, it will likely worsen.",
        fallback,
        facts_used,
        strict=True,
    )

    assert was_blocked is True
    assert safe_text == fallback
    assert reason is not None


def test_sanitize_context_trims_large_payloads():
    context = {
        "kpis": {"revenue": 100},
        "insights": [{"i": idx} for idx in range(25)],
        "table_snippets": {"rows": [{"i": idx} for idx in range(12)]},
        "trends": {"series": [1, 2, 3]},
    }

    sanitized = sanitize_context(context)
    assert len(sanitized["insights"]) == 20
    assert len(sanitized["table_snippets"]["rows"]) == 10
    assert sanitized["kpis"] == {"revenue": 100}
    assert sanitized["trends"] == {"series": [1, 2, 3]}
