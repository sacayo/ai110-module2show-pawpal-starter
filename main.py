"""
Temporary testing ground to verify PawPal+ logic in the terminal.
"""

from datetime import date
from pawpal_system import (
    Owner, OwnerPreferences, Pet, Task,
    WalkSchedule, Feeding, GroomingRecord, MedicationRecord,
    AffectionRecord, Enrichment, Scheduler,
    TimeOfDay, DayOfWeek, Priority, Category, EnrichmentType,
    by_pet, by_category, by_time_bucket, by_status, apply_filters,
)


def print_plan_table(plan, title=""):
    if title:
        print(f"\n  {title}")
    print(f"  {'Time':<8} {'Task':<30} {'Priority':<10} {'Dur'}")
    print(f"  {'----':<8} {'----':<30} {'--------':<10} {'---'}")
    for item in plan.display_table():
        print(
            f"  {item['start_time']:<8} "
            f"{item['title']:<30} "
            f"{item['priority']:<10} "
            f"{item['duration_minutes']}min"
        )


def main():
    # ── Owner ─────────────────────────────────────────────────────────────
    prefs = OwnerPreferences(
        preferred_walk_time=TimeOfDay.MORNING,
        preferred_feed_time=TimeOfDay.EVENING,
    )
    owner = Owner("Jordan", available_minutes=120, preferences=prefs)

    # ── Pet 1: Mochi the dog ──────────────────────────────────────────────
    mochi = Pet("Mochi", "Shiba Inu", 24, "dog", owner)

    WalkSchedule(mochi, 2.5, 30, DayOfWeek.TUESDAY, TimeOfDay.MORNING)
    Feeding(mochi, 200, date.today(), TimeOfDay.EVENING)
    MedicationRecord(mochi, "Heartworm pill", 24)
    AffectionRecord(mochi)
    mochi.add_task(Task("Nail trim", 15, Priority.MEDIUM, Category.GROOMING, frequency="once"))

    # ── Pet 2: Luna the senior cat ────────────────────────────────────────
    luna = Pet("Luna", "Persian", 132, "cat", owner)

    Feeding(luna, 120, date.today(), TimeOfDay.MORNING)
    GroomingRecord(luna, TimeOfDay.MORNING)
    Enrichment(luna, EnrichmentType.PUZZLE, 20, TimeOfDay.EVENING)

    # ── Generate global schedule (shared 120-min budget) ──────────────────
    scheduler = Scheduler.for_owner(owner)
    all_plans = scheduler.generate_all_plans()

    print("=" * 60)
    print("  TODAY'S SCHEDULE  (shared 120-min budget)")
    print("=" * 60)

    for _pet_name, plan in all_plans.items():
        print(f"\n{'─' * 60}")
        print(plan.explanation)
        print(f"{'─' * 60}")
        print_plan_table(plan)

    # ── What to do first ─────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    next_task = scheduler.get_next_task()
    if next_task:
        print(f"  >> What to do first: {next_task.title} ({next_task.priority.value} priority)")
    print("=" * 60)

    # ── Composable filter demos ───────────────────────────────────────────
    all_items = [item for plan in all_plans.values() for item in plan.items]

    print(f"\n{'─' * 60}")
    print("  FILTER: Morning tasks only")
    print(f"{'─' * 60}")
    morning = apply_filters(all_items, [by_time_bucket(TimeOfDay.MORNING)])
    for item in morning:
        d = item.to_dict()
        print(f"  {d['start_time']}  {d['title']:<30} [{item.pet_name}]")

    print(f"\n{'─' * 60}")
    print("  FILTER: Mochi's tasks")
    print(f"{'─' * 60}")
    mochi_items = apply_filters(all_items, [by_pet("Mochi")])
    for item in mochi_items:
        d = item.to_dict()
        print(f"  {d['start_time']}  {d['title']:<30} ({d['priority']})")

    print(f"\n{'─' * 60}")
    print("  FILTER: Luna — morning feeding")
    print(f"{'─' * 60}")
    luna_morning_feed = apply_filters(
        all_items,
        [by_pet("Luna"), by_category(Category.FEEDING), by_time_bucket(TimeOfDay.MORNING)],
    )
    if luna_morning_feed:
        for item in luna_morning_feed:
            d = item.to_dict()
            print(f"  {d['start_time']}  {d['title']}")
    else:
        print("  (none found)")

    print(f"\n{'─' * 60}")
    print("  FILTER: Pending tasks only (not yet completed)")
    print(f"{'─' * 60}")
    pending_items = apply_filters(all_items, [by_status("pending")])
    for item in pending_items:
        d = item.to_dict()
        print(f"  {d['start_time']}  {d['title']:<30} [{item.pet_name}]")

    # ── Recurring task demo ───────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print("  DEMO: Mark Mochi feeding complete → auto-generates next occurrence")
    print(f"{'─' * 60}")
    mochi.complete_task("Feeding (200g)")
    # Next occurrence is queued in custom_tasks with due_date = tomorrow
    next_feeding = next(
        (t for t in mochi.custom_tasks if "Feeding" in t.title and t.due_date is not None), None
    )
    if next_feeding:
        print(f"  Next feeding scheduled for: {next_feeding.due_date} (today + 1 day via timedelta)")
    else:
        print("  No next occurrence generated (task not found or not daily).")

    print(f"\n{'=' * 60}\n")


if __name__ == "__main__":
    main()
