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
