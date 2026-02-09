# AI Layers Architecture

## Overview

This document describes the AI layers implemented on top of the deterministic Decision Infrastructure core. The AI serves as a **UI/interaction layer**, not the brain:

- ✅ AI compresses questions into deterministic retrieval
- ✅ AI prioritizes deterministic insights for attention
- ✅ AI produces copy-ready narratives from deterministic facts
- ❌ AI never computes financial numbers
- ❌ AI never creates new data
- ❌ AI never predicts/forecasts
- ❌ AI never recommends "do X" actions

---

## Architecture Diagram

```
Client Data → Adapter/Mapping → Canonical Tables → Deterministic Metrics → Deterministic Insights → AI Query & Brief Layer
                                                                                                    ↓
                                                                                           Guardrails & Validation
                                                                                                    ↓
                                                                                            Founder-Facing UI
```

---

## Core Components

### 1. Deterministic Foundation (Already Exists)

- **`src/metrics.py`**: Financial calculation engine (project profitability, utilization, income statement, cashflow, runway)
- **`src/core/insights_engine.py`**: Rule-based insight generation (negative margins, underutilization, cashflow stress)
- **Single source of truth**: All numbers come from deterministic calculations

### 2. AI Layer Components (Newly Added)

#### A. Context Building (`src/core/context_builder.py`)

Builds compact, JSON-serializable context packages for AI queries.

**Key function**: `build_context(intent, metrics_outputs, insights_list, max_rows=5)`

**Rules**:
- Only sends KPIs (scalars), insights, and small table snippets (max 5-10 rows)
- Never sends raw full DataFrames or CSVs
- Returns structured dict: `{kpis, insights, table_snippets, trends}`

#### B. Query Router (`src/core/query_router.py`)

High-level interface for answering user queries deterministically.

**Key function**: `answer_query(user_query, metrics_outputs, insights_list)`

**Process**:
1. Parse intent (project/employee/company/invoices/cashflow)
2. Retrieve compact context
3. Build deterministic answer using template logic
4. Return structured response with facts, insights, and follow-ups

**Returns**:
```python
{
    "answer": "Human-readable response",
    "facts_used": ["Fact 1", "Fact 2", ...],
    "insights_used": ["Insight 1", "Insight 2", ...],
    "followups": ["Question 1", "Question 2", ...],
    "entity": {"type": "project", "id": "P009"}
}
```

#### C. Brief Builder (`src/core/brief_builder.py`)

Generates weekly attention briefs to answer: "What should I look at first?"

**Key function**: `build_attention_brief(metrics_outputs, insights_list, window="latest_month")`

**Ranking Logic (Deterministic)**:
- **Projects**: Absolute negative profit magnitude OR lowest margin %
- **People**: Utilization distance from healthy range (0.6-0.85)
- **Invoices**: Overdue amount/age
- **Cash**: Lowest ending cash or shrinking runway

**Returns**:
```python
{
    "top_critical": [<top 3 critical issues>],
    "top_warnings": [<top 3 warnings>],
    "key_changes": [<detected trends>],
    "summary_stats": {<quick stats>}
}
```

**Shareable Brief Formats**:
- `generate_shareable_brief(brief, format="slack|email|investor")` → Copy-ready text

#### D. AI Guardrails (`src/ai/guardrails.py`)

Validates AI outputs to prevent predictions, new numbers, or prescriptive advice.

**Key functions**:
- `sanitize_context(context_dict)`: Ensures context contains only permitted content
- `validate_llm_output(llm_text, facts_used, strict=True)`: Detects forbidden patterns
- `apply_guardrails(llm_output, deterministic_answer, facts_used)`: Returns safe output or fallback

**Forbidden Language**:
- Prediction: "will likely", "expected to", "forecast", "predict", "probability"
- Prescriptive: "you should", "you must", "i recommend", "advise"
- Future: "going forward", "will be", "will increase"

**Number Validation**:
- Extracts all currency numbers (e.g., €50,000)
- Compares with `facts_used`
- Blocks output if new numbers detected (with 1% rounding tolerance)

#### E. Local LLM (`src/ai/local_llm.py`)

Uses pre-trained `google/flan-t5-small` for optional text rephrasing only.

**Key functions**:
- `rewrite_answer(summary)`: Rephrases deterministic answer (optional, controlled by toggle)
- `generate_insights_explanation(summary)`: Explains insights in plain English
- `generate_narrative(summary, format)`: Creates copy-ready narratives

**Guardrails**:
- All LLM outputs validated by `guardrails.py`
- If validation fails, deterministic fallback is used
- User sees warning: "AI output blocked (reason). Showing deterministic version."

**Graceful Fallback**:
- If `transformers` library not installed, AI features are disabled
- Deterministic answers still work
- UI shows: "AI phrasing disabled (transformers not installed)"

---

## UI Components

### 1. Ask Your Data (`src/ui/insights_tab.py`)

**Chat-first interface** for querying financial data.

**Features**:
- Chat input with history
- Quick question chips (examples)
- Intent parsing → deterministic answer
- Optional AI phrasing (toggle)
- Sources expander (shows facts + insights used)
- Follow-up suggestions
- Narrative generator (Slack/Email/Investor formats)

**User Flow**:
1. User asks: "Why is P009 unprofitable?"
2. System parses intent → retrieves context → builds deterministic answer
3. If AI phrasing ON → LLM rephrases → guardrails validate
4. Display answer with sources expander
5. Suggest follow-ups

### 2. Weekly Brief (`src/ui/briefs_tab.py`)

**Attention focus page** showing top issues ranked by impact.

**Features**:
- Summary stats (total insights, critical/warning counts)
- Top 3 critical issues (with impact scores)
- Top 3 warnings
- Key changes (revenue/margin trends)
- "Ask about this" buttons (pre-fill chat queries)
- Shareable brief generator (3 formats)

**User Flow**:
1. Page loads → generates brief
2. Shows top issues ranked by impact
3. User clicks "Ask about this" → switches to chat with pre-filled query
4. User clicks "Generate Shareable Brief" → copy-ready text for Slack/Email/Investor

### 3. Projects Page (`src/ui/projects_page.py`)

**Decision-oriented project profitability** (already implemented in previous phase).

**Features**:
- Dropdown project selector
- Verdict card (healthy/at-risk/loss-making)
- Cost allocation breakdown (always shown)
- Drivers and recommended actions
- Optional AI explanation

---

## Data Flow

### Query Answering Flow

```
User Query
    ↓
parse_intent (insights_chat.py)
    ↓
build_context (context_builder.py)
    ↓
retrieve_context (insights_chat.py)
    ↓
build_deterministic_answer (insights_chat.py)
    ↓
[IF AI phrasing ON]
    ↓
rewrite_answer (local_llm.py)
    ↓
validate_llm_output (guardrails.py)
    ↓
[IF validation fails: use deterministic fallback]
    ↓
Display answer + sources + follow-ups
```

### Brief Generation Flow

```
Metrics Outputs + Insights List
    ↓
build_attention_brief (brief_builder.py)
    ↓
Rank by severity + impact score
    ↓
Detect key changes (trends)
    ↓
Display top 3 critical + top 3 warnings
    ↓
[Optional] generate_shareable_brief (brief_builder.py)
    ↓
[Optional] LLM narrative generation (local_llm.py)
    ↓
Copy-ready text
```

---

## Acceptance Tests

### Test 1: Chat Query Works

**Input**: "Why is P009 unprofitable?"

**Expected**:
- Response includes: answer + facts_used + insights_used
- Sources expander shows deterministic facts
- No predictions, no probabilities
- Follow-up suggestions provided

**Status**: ✅ Implemented

### Test 2: Weekly Brief Works

**Input**: Navigate to "Weekly Brief" page

**Expected**:
- Shows top 3 critical + top 3 warning
- Issues ranked by impact score
- "Ask about this" buttons pre-fill chat queries
- Shareable brief generator works (Slack/Email/Investor)

**Status**: ✅ Implemented

### Test 3: Narrative Generator Works

**Input**: Click "Generate Email Memo" in Insights page

**Expected**:
- Produces copy-ready summary for chosen entity
- Only uses deterministic facts
- Includes disclaimer: "Generated from computed data; no predictions"

**Status**: ✅ Implemented

### Test 4: Guardrails Work

**Test Case 1**: LLM tries to use "will likely" phrase
- **Expected**: Output blocked, deterministic fallback shown
- **Warning**: "AI output blocked (Forbidden language detected: will likely). Showing deterministic version."

**Test Case 2**: LLM introduces new number (€99,999) not in facts
- **Expected**: Output blocked, deterministic fallback shown
- **Warning**: "AI output blocked (New numbers detected: €99,999). Showing deterministic version."

**Status**: ✅ Implemented

### Test 5: No Breaking Changes to Deterministic Engine

**Test**: Existing pages (Overview, Projects, People, Financial Statements) still work

**Expected**:
- All existing functionality unchanged
- Metrics calculations unmodified
- No regressions

**Status**: ✅ Verified (minimal changes to existing code)

---

## Configuration

### AI Features Toggle

AI features can be disabled if `transformers` library is not installed:

```python
from src.ai.guardrails import check_transformers_available

if check_transformers_available():
    # Enable AI phrasing toggle
    use_ai_phrasing = st.checkbox("Use AI phrasing (optional)")
else:
    # Disable AI features, use deterministic only
    st.caption("AI phrasing disabled (transformers not installed)")
```

### Guardrails Strictness

```python
from src.ai.guardrails import apply_guardrails

# Strict mode: checks forbidden language AND new numbers
final_output, was_blocked, reason = apply_guardrails(
    llm_output, 
    deterministic_answer, 
    facts_used, 
    strict=True
)

# Lenient mode: checks only forbidden language
final_output, was_blocked, reason = apply_guardrails(
    llm_output, 
    deterministic_answer, 
    facts_used, 
    strict=False
)
```

---

## File Structure

```
Decision-Infrastructure/
├── src/
│   ├── core/
│   │   ├── insights_engine.py          # Rule-based insights (existing)
│   │   ├── insights_chat.py            # Chat logic (existing)
│   │   ├── context_builder.py          # NEW: Compact context packages
│   │   ├── query_router.py             # NEW: Query answering interface
│   │   └── brief_builder.py            # NEW: Weekly attention briefs
│   ├── ai/
│   │   ├── local_llm.py                # LLM integration (updated)
│   │   ├── summary_builder.py          # Compact summaries (existing)
│   │   └── guardrails.py               # NEW: AI output validation
│   ├── ui/
│   │   ├── insights_tab.py             # Chat UI (updated with guardrails + narratives)
│   │   ├── briefs_tab.py               # NEW: Weekly brief UI
│   │   └── projects_page.py            # Projects page (existing)
│   ├── metrics.py                      # Deterministic calculations (unchanged)
│   └── data_loader.py                  # Data loading (unchanged)
├── app.py                              # Main Streamlit app (updated navigation)
└── AI_LAYERS_ARCHITECTURE.md          # This document
```

---

## Usage Examples

### Example 1: Ask a Question

```python
from src.core.query_router import answer_query

response = answer_query(
    user_query="Why is P009 unprofitable?",
    metrics_outputs=metrics_outputs,
    insights_list=insights_list
)

print(response["answer"])
# Output: "Project P009 Analysis: This project is unprofitable with -266.6% margin..."

print(response["facts_used"])
# Output: ["Revenue: €18,000", "Gross profit: -€47,985", ...]
```

### Example 2: Generate Weekly Brief

```python
from src.core.brief_builder import build_attention_brief, generate_shareable_brief

brief = build_attention_brief(metrics_outputs, insights_list)

print(brief["top_critical"][0]["message"])
# Output: "Project P009 has negative gross margin (-266.6%)"

slack_update = generate_shareable_brief(brief, format="slack")
print(slack_update)
# Output: "📊 Weekly Brief\n🔴 3 critical issues | 🟡 5 warnings\n..."
```

### Example 3: Apply Guardrails

```python
from src.ai.guardrails import apply_guardrails

llm_output = "This project will likely fail with a 90% probability..."
deterministic_answer = "This project has a negative margin of -266.6%."
facts_used = ["Revenue: €18,000", "Margin: -266.6%"]

final_output, was_blocked, reason = apply_guardrails(
    llm_output, 
    deterministic_answer, 
    facts_used
)

print(was_blocked)  # True
print(reason)       # "Forbidden language detected: will likely"
print(final_output) # "This project has a negative margin of -266.6%."
```

---

## Best Practices

### For Developers

1. **Always use deterministic core**: Never bypass metrics.py or insights_engine.py
2. **Context packages must be small**: Max 5-10 rows per table, scalars only for KPIs
3. **Test guardrails**: Add new forbidden phrases to `guardrails.py` as needed
4. **Graceful degradation**: AI features should always have deterministic fallbacks
5. **Source citations**: Every AI answer must show "Sources (deterministic)" expander

### For Users

1. **Understand AI's role**: AI is an interpreter, not a decision-maker
2. **Check sources**: Always expand "Sources (deterministic)" to verify facts
3. **Disable AI if uncertain**: Toggle off "Use AI phrasing" for pure deterministic mode
4. **Report violations**: If AI output seems predictive, report it (should trigger guardrails)
5. **Use Weekly Brief first**: Start with ranked top issues before diving into chat

---

## Future Enhancements (Not Implemented Yet)

### Onboarding Mapping Copilot (Phase 2)

- Help founders map their CSV columns to canonical schema
- Suggest mappings based on column names
- Validate mappings against rules
- **Important**: This is a future feature, not yet implemented

### Advanced Context Retrieval (Optional)

- Semantic search over insights (if needed)
- Time-window filtering (last 7 days, last 30 days)
- Entity grouping (all projects for a client)

---

## Debugging

### Enable Verbose Guardrails Logging

```python
# In src/ai/guardrails.py, add print statements:

def validate_llm_output(llm_text, facts_used, strict=True):
    print(f"[Guardrails] Validating LLM output: {llm_text[:100]}...")
    
    forbidden_check = _contains_forbidden_language(llm_text)
    if forbidden_check[0]:
        print(f"[Guardrails] BLOCKED: Forbidden language '{forbidden_check[1]}'")
        return (False, f"Forbidden language detected: {forbidden_check[1]}")
    
    # ... rest of validation
```

### Test Guardrails Directly

```python
from src.ai.guardrails import validate_llm_output

llm_text = "This project will likely improve next quarter."
facts_used = ["Revenue: €18,000"]

is_valid, error = validate_llm_output(llm_text, facts_used)
print(f"Valid: {is_valid}, Error: {error}")
# Output: Valid: False, Error: Forbidden language detected: will likely
```

---

## Summary

This AI layer implementation achieves the following goals:

✅ **A) Conversational Query Layer**: Chat-first UI with deterministic answers + optional AI phrasing
✅ **B) Weekly Attention Brief**: Ranked top issues with impact scores + shareable formats
✅ **C) Narrative Generator**: Copy-ready summaries for Slack/Email/Investor
✅ **Strong Guardrails**: Forbidden language + new number detection
✅ **Source Citations**: Every answer shows "Sources (deterministic)"
✅ **No Breaking Changes**: Existing deterministic engine unchanged
✅ **Graceful Degradation**: Works without transformers library

The system maintains a clear separation: **deterministic core = brain, AI = interpreter/UI layer**.
