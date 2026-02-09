# Demo Mode Instructions

## Current Status: DEMO MODE ENABLED ✅

Your app is currently configured to show only 3 pages for the expert demo:
- ✅ Overview Dashboard
- ✅ Projects
- ✅ Insights & Explanations

Hidden pages (code intact, just not visible):
- ⚪ People
- ⚪ Financial Statements
- ⚪ Weekly Brief
- ⚪ Data Quality

---

## How to Revert and Show All Pages

**Option 1: Quick Toggle (Recommended)**

Edit `app.py` at line 33:

```python
# Change this:
DEMO_MODE = True

# To this:
DEMO_MODE = False
```

Save and refresh Streamlit → All pages will be visible again.

---

## What Was Changed

**File Modified**: `app.py` (lines 29-33 and 622-626)

**Change 1**: Added DEMO_MODE flag at the top
```python
# ============================================================
# DEMO MODE: Temporarily hide some pages for expert demo
# To revert and show all pages: Set DEMO_MODE = False
# ============================================================
DEMO_MODE = True
```

**Change 2**: Made navigation conditional
```python
# Demo mode: show only selected pages
if DEMO_MODE:
    available_pages = ["Overview Dashboard", "Projects", "Insights & Explanations"]
else:
    available_pages = ["Overview Dashboard", "Projects", "People", "Financial Statements", "Weekly Brief", "Insights & Explanations", "Data Quality"]
```

**No code was deleted** - all page functions remain intact:
- `page_people()`
- `page_financial_statements()`
- `page_briefs()`
- `page_data_quality()`

---

## Testing Before Demo

1. **Start the app**: `streamlit run app.py`
2. **Verify only 3 pages show** in the sidebar navigation
3. **Test each visible page**:
   - Overview Dashboard → Should work normally
   - Projects → Should work normally
   - Insights & Explanations → Should work normally

---

## After Demo - Reverting

1. Open `app.py`
2. Find line 33: `DEMO_MODE = True`
3. Change to: `DEMO_MODE = False`
4. Save file
5. Refresh Streamlit app
6. All 7 pages will be visible again

---

## Quick Reference

**Show only 3 pages** (for demo): `DEMO_MODE = True`  
**Show all 7 pages** (normal): `DEMO_MODE = False`

That's it! 🚀
