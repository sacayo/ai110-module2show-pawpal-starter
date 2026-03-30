# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PawPal+** is a Python/Streamlit pet care planning app. The starter scaffold is intentionally thin — the core scheduling logic and domain classes are meant to be designed and built as part of the project.

## Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the app
streamlit run app.py

# Run tests
pytest

# Run a single test file
pytest tests/test_scheduler.py

# Run a specific test
pytest tests/test_scheduler.py::test_function_name
```

## Architecture

The project follows a **backend logic → UI integration** pattern:

1. **`app.py`** — Streamlit UI shell. Handles all user input and display. Currently has no scheduling logic; the `Generate schedule` button is a placeholder.
2. **Domain classes** (to be built) — `Owner`, `Pet`, `Task`, `Schedule`/`Plan` classes encapsulating the data model.
3. **Scheduler** (to be built) — Core logic that takes owner, pet, and tasks as inputs and produces an ordered daily plan with reasoning.

The intended integration point is the `Generate schedule` button in `app.py` — once the scheduler exists, it should be called there and its output displayed.

## Key Design Requirements

The scheduler must:
- Accept tasks with `title`, `duration_minutes`, and `priority` (low/medium/high)
- Respect owner time constraints and preferences
- Output an ordered plan that explains *why* each task was chosen and when
- Be testable independently of the Streamlit UI (keep scheduling logic in separate modules, not inside `app.py`)

## Testing Approach

Tests go in a `tests/` directory. The most important behaviors to test are scheduling correctness — e.g., high-priority tasks appear before low-priority ones, total duration doesn't exceed available time, all mandatory tasks are included.