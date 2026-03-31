# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Smarter Scheduling

The scheduler in `pawpal_system.py` goes well beyond a simple priority sort:

- **Multi-pet, shared budget.** `Scheduler.for_owner(owner)` collects due tasks across all registered pets and fits them into one `owner.available_minutes` budget, then returns an individual `DailyPlan` — with a plain-text explanation — for each pet.
- **Priority ordering with owner preferences and overdue boosts.** Tasks are sorted first by `Priority` (HIGH/MEDIUM/LOW), then by the owner's preferred category order (e.g. walks before feedings before grooming). Overdue tasks are automatically promoted one priority level so they are not silently skipped again.
- **Age-aware adjustments.** Walk durations are capped for puppies/kittens (under 12 months) and seniors (over 96 months), and medication is escalated to HIGH priority for senior pets. The generated explanation notes which rules applied.
- **Owner preference defaults.** When a task has no explicit `preferred_time`, the scheduler fills in the owner's default walk or feed time-of-day from `OwnerPreferences`, ensuring tasks land in the right part of the day without extra configuration.
- **Time buckets and clock times.** Fitted tasks are grouped into morning / evening / night buckets and assigned concrete start times within each bucket. Every `ScheduledItem` includes an end time and a short human-readable reason explaining its slot placement.
- **Cross-pet conflict resolution.** After building per-pet timelines, `detect_and_resolve_conflicts` scans for overlapping intervals across pets, shifts later items forward, and appends a note to the affected plan's explanation. Composable filter helpers (`by_pet`, `by_category`, `by_time_bucket`, `by_status`) and `get_next_task` ("what should I do right now?") round out the API.

## Features

- **Priority-driven task ordering** — Tasks are sorted by `Priority` (HIGH/MEDIUM/LOW) numeric weights, then by the owner's custom category preference order (walks → feedings → medication → grooming → enrichment → affection), then alphabetically as a tiebreaker. (`Scheduler._sort_by_priority`)
- **Two-pass greedy time-budget fitting** — A first pass fills tasks in priority order until the owner's `available_minutes` budget is exhausted; a second backfill pass slots in any smaller dropped tasks that still fit in the remainder. (`Scheduler._fit_to_time`)
- **Daily and weekly recurrence** — Each task carries a `frequency` (`daily`, `weekly`, `once`, `as_needed`). `is_due()` checks today's weekday against `scheduled_day` for weekly tasks. Completing a task records `next_due_date`; `generate_next_occurrence()` creates a fresh instance for the next cycle.
- **Overdue detection and automatic priority boost** — `is_overdue()` flags tasks whose `due_date` has passed without completion. `_boost_overdue` automatically promotes overdue tasks one priority level (LOW→MEDIUM, MEDIUM→HIGH) so they are never silently skipped again.
- **Age-aware task adjustments** — Walk durations are capped at 20 min for puppies/kittens (under 12 months) and 25 min for seniors (over 96 months). Medication is automatically escalated to HIGH priority for senior pets. (`Scheduler._adjust_for_pet`)
- **Time-bucket assignment with concrete clock times** — Fitted tasks are grouped into morning (starts 06:00), evening (starts 12:00), and night (starts 18:00) buckets. Consecutive tasks within a bucket receive sequential start/end times, clamped to prevent midnight overflow. (`Scheduler._assign_times`)
- **Chronological sorting of scheduled items** — `sort_by_time()` orders all `ScheduledItem`s by their assigned HH:MM start time, producing a clean chronological agenda.
- **Owner preference defaults** — When a task has no explicit `preferred_time`, `_apply_owner_preferences` fills it in from `OwnerPreferences` (preferred walk time, preferred feed time), ensuring tasks land in the right part of the day without extra configuration.
- **Multi-pet shared-budget planning** — `Scheduler.for_owner(owner)` collects due tasks from all registered pets into one pool, fits them against a single shared time budget, then returns a per-pet `DailyPlan` with a plain-text explanation. (`generate_global_plan`)
- **Cross-pet conflict detection and resolution** — `detect_and_resolve_conflicts` scans merged per-pet timelines for overlapping intervals, shifts the later item's start time forward to clear the overlap, and appends a human-readable warning to the affected plan's explanation.
- **Composable filter predicates** — Standalone helpers `by_pet`, `by_category`, `by_time_bucket`, and `by_status` (pending/complete/overdue) can be combined via `apply_filters` to slice any list of `ScheduledItem`s.
- **Interval-based medication due check** — `MedicationRecord.is_dose_due()` compares the current time against `last_med_datetime + dosage_interval_hours`; a task is only generated and scheduled when a dose is actually due.
- **"What's next" query** — `Scheduler.get_next_task()` returns the single highest-priority pending due task across all tasks, answering "what should I do right now?"

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Testing PawPal+

The test suite lives in `tests/test_pawpal.py` and contains **45 tests** across 12 categories. Run the full suite with:

```bash
pytest tests/test_pawpal.py -v
# or, if using uv:
uv run pytest tests/test_pawpal.py -v
```

| Step | Category | Tests | What it covers |
|------|----------|-------|----------------|
| 1 | Task Completion | 1 | `mark_complete()` flips status and records a timestamp |
| 2 | Task Addition | 1 | `Pet.add_task()` increases the pending task count |
| 3 | Weekly Recurrence Fix | 3 | `scheduled_day` gating; backward-compat "always due"; `WalkSchedule.to_task()` |
| 4 | Recurring Task Auto-Generation | 5 | `next_due_date` after completion; `generate_next_occurrence`; `Pet.complete_task` list mutation; next occurrence suppressed until future `due_date` |
| 5 | Overdue Detection + Priority Boost | 6 | `is_overdue()` for daily/past-due tasks; `_boost_overdue` LOW→MEDIUM→HIGH; HIGH stays HIGH |
| 6 | Time-Aware Sorting | 1 | `sort_by_time()` returns items in chronological order |
| 7 | Global Time-Budget Fitting | 3 | Shared budget ceiling across pets; both pets appear in output; `generate_all_plans` return shape |
| 8 | Cross-Pet Conflict Detection | 2 | Cross-pet and same-pet overlap detection, shift, and warning messages |
| 9 | Composable Filtering | 4 | `by_pet`, `by_status` (pending/overdue), `by_category`, combined filter intersection |
| 10 | Priority-Driven Dropping & `_fit_to_time` | 5 | High-priority task survives tight budget; explicit dropped list; two-pass backfill; category tie-break; `generate_global_plan` dropped return value |
| 11 | Frequency Corner Cases | 5 | `as_needed` never due; `once` due before and not-due after completion; weekly future `due_date` suppressed; invalid frequency raises `ValueError` |
| 12 | Age Adjustments & `get_next_task` | 6 | Puppy/senior walk duration caps; senior medication priority escalation; `get_next_task` returns highest priority and skips completed tasks; `by_time_bucket` filter |

Together these categories validate the core scheduling contract: **correct priority-driven ordering**, **recurring task lifecycle** (create → complete → regenerate → suppress), **cross-pet conflict resolution**, and **boundary/edge-case behavior** for frequencies, budgets, and age rules.

## Demo

<a href="/course_images/ai110/Screenshot 2026-03-31 at 10.36.26 AM.png" target="_blank"><img src='/course_images/ai110/Screenshot 2026-03-31 at 10.36.26 AM.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>.