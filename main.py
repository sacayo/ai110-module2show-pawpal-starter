"""
Temporary testing ground to verify PawPal+ logic in the terminal.
"""

from datetime import date
from pawpal_system import (
    Owner, OwnerPreferences, Pet, Task,
    WalkSchedule, Feeding, GroomingRecord, MedicationRecord,
    AffectionRecord, Enrichment, Scheduler,
    TimeOfDay, DayOfWeek, Priority, Category, EnrichmentType,
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

    WalkSchedule(mochi, 2.5, 30, DayOfWeek.MONDAY, TimeOfDay.MORNING)
    Feeding(mochi, 200, date.today(), TimeOfDay.EVENING)
    MedicationRecord(mochi, "Heartworm pill", 24)
    AffectionRecord(mochi)
    mochi.add_task(Task("Nail trim", 15, Priority.MEDIUM, Category.GROOMING, frequency="once"))

    # ── Pet 2: Luna the senior cat ────────────────────────────────────────
    luna = Pet("Luna", "Persian", 132, "cat", owner)

    Feeding(luna, 120, date.today(), TimeOfDay.MORNING)
    GroomingRecord(luna, TimeOfDay.MORNING)
    Enrichment(luna, EnrichmentType.PUZZLE, 20, TimeOfDay.EVENING)

    # ── Generate schedules ────────────────────────────────────────────────
    scheduler = Scheduler.for_owner(owner)
    all_plans = scheduler.generate_all_plans()

    print("=" * 60)
    print("  TODAY'S SCHEDULE")
    print("=" * 60)

    for _pet_name, plan in all_plans.items():
        print(f"\n{'─' * 60}")
        print(plan.explanation)
        print(f"{'─' * 60}")
        print(f"  {'Time':<8} {'Task':<30} {'Priority':<10} {'Dur'}")
        print(f"  {'----':<8} {'----':<30} {'--------':<10} {'---'}")
        for item in plan.display_table():
            print(
                f"  {item['start_time']:<8} "
                f"{item['title']:<30} "
                f"{item['priority']:<10} "
                f"{item['duration_minutes']}min"
            )

    print(f"\n{'=' * 60}")
    next_task = scheduler.get_next_task()
    if next_task:
        print(f"  >> What to do first: {next_task.title} ({next_task.priority.value} priority)")
    print("=" * 60)


if __name__ == "__main__":
    main()
