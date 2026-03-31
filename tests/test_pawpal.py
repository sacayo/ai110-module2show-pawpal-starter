"""
Tests for core PawPal+ behaviors.
Run with: uv run pytest tests/test_pawpal.py -v
"""

from datetime import date, timedelta, datetime
from unittest.mock import patch

from pawpal_system import (
    Owner, Pet, Task, Priority, Category,
    WalkSchedule, Feeding, GroomingRecord, Scheduler,
    TimeOfDay, DayOfWeek, ScheduledItem,
    by_pet, by_category, by_time_bucket, by_status, apply_filters,
)


def make_owner(minutes: int = 120) -> Owner:
    return Owner("Test Owner", available_minutes=minutes)


def make_pet(owner: Owner, name: str = "Buddy") -> Pet:
    return Pet(name, "Labrador", 36, "dog", owner)


# ── Test 1: Task Completion ───────────────────────────────────────────────────

def test_mark_complete_changes_status():
    """Calling mark_complete() should flip completed to True and record a timestamp."""
    task = Task("Morning walk", 30, Priority.HIGH)

    assert task.completed is False
    assert task.last_completed is None

    task.mark_complete()

    assert task.completed is True
    assert task.last_completed is not None


# ── Test 2: Task Addition ─────────────────────────────────────────────────────

def test_add_task_increases_pet_task_count():
    """Adding a custom task to a Pet should increase its pending task count by 1."""
    owner = make_owner()
    pet = make_pet(owner)

    before = len(pet.get_pending_tasks())

    pet.add_task(Task("Vet appointment", 60, Priority.HIGH, Category.CUSTOM, frequency="once"))

    assert len(pet.get_pending_tasks()) == before + 1


# ── Step 1: Weekly Recurrence Fix ────────────────────────────────────────────

def test_weekly_task_no_scheduled_day_always_due():
    """A weekly task without a scheduled_day should always be due (backward compat)."""
    task = Task("Grooming", 30, Priority.MEDIUM, frequency="weekly")
    assert task.is_due() is True


def test_weekly_task_due_on_correct_day():
    """A weekly task with scheduled_day should be due only on that day."""
    # Today is 2026-03-31, which is a Tuesday (weekday index 1)
    task = Task("Walk", 30, Priority.HIGH, frequency="weekly", scheduled_day=DayOfWeek.TUESDAY)
    with patch("pawpal_system.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 31)  # Tuesday
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        assert task.is_due() is True

    task2 = Task("Walk", 30, Priority.HIGH, frequency="weekly", scheduled_day=DayOfWeek.MONDAY)
    with patch("pawpal_system.date") as mock_date:
        mock_date.today.return_value = date(2026, 3, 31)  # Tuesday, not Monday
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        assert task2.is_due() is False


def test_walk_schedule_creates_weekly_task():
    """WalkSchedule.to_task() should produce a weekly task with the correct scheduled_day."""
    owner = make_owner()
    pet = make_pet(owner)
    ws = WalkSchedule(pet, 2.0, 30, DayOfWeek.FRIDAY, TimeOfDay.MORNING)
    task = ws.to_task()
    assert task.frequency == "weekly"
    assert task.scheduled_day == DayOfWeek.FRIDAY


# ── Step 2: Recurring Task Auto-Generation ───────────────────────────────────

def test_daily_mark_complete_sets_next_due_date():
    """mark_complete() on a daily task should set next_due_date to today + 1 day."""
    task = Task("Feeding", 10, Priority.HIGH, frequency="daily")
    task.mark_complete()
    assert task.next_due_date == date.today() + timedelta(days=1)


def test_weekly_mark_complete_sets_next_due_date():
    """mark_complete() on a weekly task should set next_due_date to today + 7 days."""
    task = Task("Bath", 30, Priority.MEDIUM, frequency="weekly")
    task.mark_complete()
    assert task.next_due_date == date.today() + timedelta(weeks=1)


def test_once_task_mark_complete_no_next_due_date():
    """mark_complete() on a 'once' task should leave next_due_date as None."""
    task = Task("Vet visit", 60, Priority.HIGH, frequency="once")
    task.mark_complete()
    assert task.next_due_date is None


def test_generate_next_occurrence_daily():
    """generate_next_occurrence() for a daily task returns a fresh task due tomorrow."""
    task = Task("Feeding", 10, Priority.HIGH, frequency="daily")
    task.mark_complete()
    next_task = task.generate_next_occurrence()
    assert next_task is not None
    assert next_task.completed is False
    assert next_task.due_date == date.today() + timedelta(days=1)
    assert next_task.title == task.title


def test_generate_next_occurrence_weekly():
    """generate_next_occurrence() for a weekly task returns a task due in 7 days."""
    task = Task("Walk", 30, Priority.HIGH, frequency="weekly", scheduled_day=DayOfWeek.MONDAY)
    task.mark_complete()
    next_task = task.generate_next_occurrence()
    assert next_task is not None
    assert next_task.due_date == date.today() + timedelta(weeks=1)
    assert next_task.scheduled_day == DayOfWeek.MONDAY


def test_once_task_no_next_occurrence():
    """generate_next_occurrence() for a 'once' task should return None."""
    task = Task("Vet visit", 60, Priority.HIGH, frequency="once")
    task.mark_complete()
    assert task.generate_next_occurrence() is None


def test_pet_complete_task_appends_next_occurrence():
    """Pet.complete_task() should append the next occurrence to custom_tasks."""
    owner = make_owner()
    pet = make_pet(owner)
    pet.add_task(Task("Feeding", 10, Priority.HIGH, Category.FEEDING, frequency="daily"))
    custom_before = len(pet.custom_tasks)

    result = pet.complete_task("Feeding")

    assert result is True
    assert len(pet.custom_tasks) == custom_before + 1  # next occurrence added
    next_t = pet.custom_tasks[-1]
    assert next_t.completed is False
    assert next_t.due_date == date.today() + timedelta(days=1)


def test_completed_daily_task_not_due_until_next_due_date():
    """A completed daily task with a future due_date should not appear as due today."""
    task = Task("Feeding", 10, Priority.HIGH, frequency="daily")
    task.mark_complete()
    next_task = task.generate_next_occurrence()
    assert next_task is not None
    # next task's due_date is tomorrow, so it is NOT due today
    assert next_task.is_due() is False


# ── Step 3: Overdue Detection + Priority Boost ───────────────────────────────

def test_is_overdue_daily_completed_yesterday():
    """A daily task last completed yesterday is overdue."""
    task = Task("Feeding", 10, Priority.HIGH, frequency="daily")
    task.last_completed = datetime.combine(date.today() - timedelta(days=1), datetime.min.time())
    assert task.is_overdue() is True


def test_is_overdue_daily_completed_today():
    """A daily task completed today is NOT overdue."""
    task = Task("Feeding", 10, Priority.HIGH, frequency="daily")
    task.mark_complete()
    assert task.is_overdue() is False


def test_is_overdue_past_due_date():
    """A task whose due_date is in the past (and not completed) is overdue."""
    task = Task("Walk", 30, Priority.HIGH, frequency="weekly")
    task.due_date = date.today() - timedelta(days=1)
    assert task.is_overdue() is True


def test_boost_overdue_promotes_low_to_medium():
    """_boost_overdue() should raise LOW priority overdue tasks to MEDIUM."""
    owner = make_owner()
    pet = make_pet(owner)
    scheduler = Scheduler.for_owner(owner)

    task = Task("Cuddle time", 15, Priority.LOW, frequency="daily")
    task.last_completed = datetime.combine(date.today() - timedelta(days=1), datetime.min.time())
    boosted_list = scheduler._boost_overdue([task])
    assert boosted_list[0].priority == Priority.MEDIUM


def test_boost_overdue_promotes_medium_to_high():
    """_boost_overdue() should raise MEDIUM priority overdue tasks to HIGH."""
    owner = make_owner()
    pet = make_pet(owner)
    scheduler = Scheduler.for_owner(owner)

    task = Task("Enrichment", 20, Priority.MEDIUM, frequency="daily")
    task.last_completed = datetime.combine(date.today() - timedelta(days=1), datetime.min.time())
    boosted_list = scheduler._boost_overdue([task])
    assert boosted_list[0].priority == Priority.HIGH


def test_boost_overdue_high_stays_high():
    """_boost_overdue() should not promote a HIGH priority task beyond HIGH."""
    owner = make_owner()
    pet = make_pet(owner)
    scheduler = Scheduler.for_owner(owner)

    task = Task("Medication", 5, Priority.HIGH, frequency="daily")
    task.last_completed = datetime.combine(date.today() - timedelta(days=1), datetime.min.time())
    boosted_list = scheduler._boost_overdue([task])
    assert boosted_list[0].priority == Priority.HIGH


# ── Step 4: Time-Aware Sorting ────────────────────────────────────────────────

def test_sort_by_time_orders_chronologically():
    """sort_by_time() should order ScheduledItems from earliest to latest."""
    from datetime import time
    owner = make_owner()
    pet = make_pet(owner)
    scheduler = Scheduler.for_owner(owner)

    t1 = Task("Late task", 10, Priority.LOW)
    t2 = Task("Early task", 10, Priority.HIGH)
    items = [
        ScheduledItem(t1, time(18, 0), "evening"),
        ScheduledItem(t2, time(6, 0), "morning"),
    ]
    sorted_items = scheduler.sort_by_time(items)
    assert sorted_items[0].task.title == "Early task"
    assert sorted_items[1].task.title == "Late task"


# ── Step 5: Global Time-Budget Fitting ───────────────────────────────────────

def test_global_plan_respects_shared_budget():
    """Total minutes across all pets' plans should not exceed available_minutes."""
    owner = make_owner(minutes=60)
    pet1 = make_pet(owner, "Dog")
    pet2 = make_pet(owner, "Cat")

    pet1.add_task(Task("Walk",    30, Priority.HIGH,   Category.WALK,    frequency="daily"))
    pet1.add_task(Task("Feed",    20, Priority.HIGH,   Category.FEEDING, frequency="daily"))
    pet2.add_task(Task("Groom",   25, Priority.MEDIUM, Category.GROOMING, frequency="daily"))
    pet2.add_task(Task("Cuddle",  15, Priority.LOW,    Category.AFFECTION, frequency="daily"))

    scheduler = Scheduler.for_owner(owner)
    plans, _ = scheduler.generate_global_plan()

    total_used = sum(plan.total_minutes for plan in plans.values())
    assert total_used <= owner.available_minutes


def test_global_plan_includes_both_pets():
    """generate_global_plan() should return a plan entry for each pet."""
    owner = make_owner()
    pet1 = make_pet(owner, "Dog")
    pet2 = make_pet(owner, "Cat")
    pet1.add_task(Task("Walk",  30, Priority.HIGH, Category.WALK,    frequency="daily"))
    pet2.add_task(Task("Feed",  10, Priority.HIGH, Category.FEEDING, frequency="daily"))

    scheduler = Scheduler.for_owner(owner)
    plans, _ = scheduler.generate_global_plan()

    assert "Dog" in plans
    assert "Cat" in plans


def test_generate_all_plans_backward_compat():
    """generate_all_plans() must still return dict[str, DailyPlan]."""
    owner = make_owner()
    pet = make_pet(owner)
    pet.add_task(Task("Walk", 30, Priority.HIGH, frequency="daily"))
    scheduler = Scheduler.for_owner(owner)
    result = scheduler.generate_all_plans()
    assert isinstance(result, dict)
    assert "Buddy" in result


# ── Step 6: Cross-Pet Conflict Detection ─────────────────────────────────────

def test_overlapping_items_get_shifted():
    """detect_and_resolve_conflicts() should shift a later item when two pets overlap."""
    from datetime import time
    from pawpal_system import DailyPlan
    owner = make_owner()
    make_pet(owner)  # register a pet so for_owner() doesn't raise

    t1 = Task("Walk Mochi", 30, Priority.HIGH)
    t2 = Task("Feed Luna",  20, Priority.HIGH)
    item1 = ScheduledItem(t1, time(6, 0), "morning", pet_name="Mochi")
    item2 = ScheduledItem(t2, time(6, 15), "morning", pet_name="Luna")  # overlaps with item1

    plans = {
        "Mochi": DailyPlan(items=[item1], total_minutes=30, explanation=""),
        "Luna":  DailyPlan(items=[item2], total_minutes=20, explanation=""),
    }

    scheduler = Scheduler.for_owner(owner)
    updated_plans, conflicts = scheduler.detect_and_resolve_conflicts(plans)

    luna_start = updated_plans["Luna"].items[0].start_time
    assert luna_start >= time(6, 30)  # shifted to after Mochi's 30-min walk
    assert len(conflicts) == 1


def test_same_pet_overlap_detected_and_shifted():
    """detect_and_resolve_conflicts() should shift and warn when two tasks for the same pet overlap."""
    from datetime import time
    from pawpal_system import DailyPlan
    owner = make_owner()
    make_pet(owner)  # register a pet so for_owner() doesn't raise

    t1 = Task("Feed",  10, Priority.HIGH)
    t2 = Task("Meds",   5, Priority.HIGH)
    # Both start at 06:00 — Feed runs 10 min, so Meds overlaps
    item1 = ScheduledItem(t1, time(6, 0), "morning", pet_name="Mochi")
    item2 = ScheduledItem(t2, time(6, 5), "morning", pet_name="Mochi")

    plans = {"Mochi": DailyPlan(items=[item1, item2], total_minutes=15, explanation="")}

    scheduler = Scheduler.for_owner(owner)
    updated_plans, conflicts = scheduler.detect_and_resolve_conflicts(plans)

    # Second task should be shifted to 06:10 (after 10-min Feed)
    meds_item = updated_plans["Mochi"].items[1]
    assert meds_item.start_time >= time(6, 10)
    # Warning message should be generated
    assert len(conflicts) == 1
    assert "WARNING" in conflicts[0]
    assert "same pet" in conflicts[0]


# ── Step 7: Composable Filtering ─────────────────────────────────────────────

def test_by_pet_filter():
    """by_pet() should return only items for the named pet."""
    from datetime import time
    t = Task("Feed", 10, Priority.HIGH)
    items = [
        ScheduledItem(t, time(6, 0), "", pet_name="Mochi"),
        ScheduledItem(t, time(6, 0), "", pet_name="Luna"),
    ]
    result = apply_filters(items, [by_pet("Mochi")])
    assert len(result) == 1
    assert result[0].pet_name == "Mochi"


def test_by_status_pending():
    """by_status('pending') should exclude completed tasks."""
    from datetime import time
    done = Task("Done task", 10, Priority.HIGH)
    done.mark_complete()
    pending = Task("Pending task", 10, Priority.LOW)
    items = [
        ScheduledItem(done,    time(6, 0), ""),
        ScheduledItem(pending, time(7, 0), ""),
    ]
    result = apply_filters(items, [by_status("pending")])
    assert len(result) == 1
    assert result[0].task.title == "Pending task"


def test_by_status_overdue():
    """by_status('overdue') should return only overdue tasks."""
    from datetime import time
    overdue = Task("Old feeding", 10, Priority.HIGH, frequency="daily")
    overdue.last_completed = datetime.combine(date.today() - timedelta(days=1), datetime.min.time())
    fine = Task("Fresh task", 10, Priority.LOW, frequency="daily")
    items = [
        ScheduledItem(overdue, time(6, 0), ""),
        ScheduledItem(fine,    time(7, 0), ""),
    ]
    result = apply_filters(items, [by_status("overdue")])
    assert len(result) == 1
    assert result[0].task.title == "Old feeding"


def test_combined_filters():
    """Combining by_pet and by_category should return the intersection."""
    from datetime import time
    walk = Task("Walk",  30, Priority.HIGH, Category.WALK)
    feed = Task("Feed",  10, Priority.HIGH, Category.FEEDING)
    items = [
        ScheduledItem(walk, time(6, 0),  "", pet_name="Mochi"),
        ScheduledItem(feed, time(12, 0), "", pet_name="Mochi"),
        ScheduledItem(feed, time(12, 0), "", pet_name="Luna"),
    ]
    result = apply_filters(items, [by_pet("Mochi"), by_category(Category.FEEDING)])
    assert len(result) == 1
    assert result[0].task.title == "Feed"
    assert result[0].pet_name == "Mochi"


# ── Step 8: Priority-Driven Dropping and _fit_to_time ────────────────────────

def test_high_priority_task_survives_tight_budget():
    """When budget is tight, high-priority tasks should stay and low-priority ones be dropped."""
    owner = make_owner(minutes=40)
    pet = make_pet(owner)
    scheduler = Scheduler.for_owner(owner)

    high = Task("Meds",    30, Priority.HIGH,   Category.MEDICATION, frequency="daily")
    low  = Task("Cuddle",  20, Priority.LOW,    Category.AFFECTION,  frequency="daily")

    sorted_tasks = scheduler._sort_by_priority([low, high])
    fitted, dropped = scheduler._fit_to_time(sorted_tasks, owner.available_minutes)

    fitted_titles = [t.title for t in fitted]
    dropped_titles = [t.title for t in dropped]

    assert "Meds"   in fitted_titles
    assert "Cuddle" in dropped_titles


def test_dropped_list_is_populated_when_budget_exceeded():
    """_fit_to_time must return the tasks that did not fit in the dropped list."""
    owner = make_owner(minutes=30)
    pet = make_pet(owner)
    scheduler = Scheduler.for_owner(owner)

    t1 = Task("Walk",  30, Priority.HIGH,   Category.WALK,    frequency="daily")
    t2 = Task("Groom", 20, Priority.MEDIUM, Category.GROOMING, frequency="daily")

    fitted, dropped = scheduler._fit_to_time([t1, t2], owner.available_minutes)
    assert len(dropped) == 1
    assert dropped[0].title == "Groom"


def test_fit_to_time_backfill_readmits_small_task():
    """The two-pass backfill should re-admit a short task dropped in the first pass."""
    owner = make_owner(minutes=35)
    pet = make_pet(owner)
    scheduler = Scheduler.for_owner(owner)

    # sorted order: Walk(30, HIGH), Groom(20, MEDIUM), Feed(5, LOW)
    # First pass: Walk fits (30 used), Groom does not (would be 50), Feed does not (35 total)
    # Backfill: 5 min remaining → Feed (5 min) should be readmitted
    walk  = Task("Walk",  30, Priority.HIGH,   Category.WALK,    frequency="daily")
    groom = Task("Groom", 20, Priority.MEDIUM, Category.GROOMING, frequency="daily")
    feed  = Task("Feed",   5, Priority.LOW,    Category.FEEDING,  frequency="daily")

    fitted, dropped = scheduler._fit_to_time([walk, groom, feed], owner.available_minutes)

    fitted_titles = [t.title for t in fitted]
    assert "Walk" in fitted_titles
    assert "Feed" in fitted_titles   # backfilled into leftover 5 minutes
    assert "Groom" in [t.title for t in dropped]


def test_category_tiebreak_same_priority():
    """Tasks with equal priority should be ordered by owner category preference."""
    owner = make_owner(minutes=120)
    pet = make_pet(owner)
    scheduler = Scheduler.for_owner(owner)

    # Default priority_order: WALK, FEEDING, MEDICATION, GROOMING, ENRICHMENT, AFFECTION
    affection = Task("Cuddle", 15, Priority.MEDIUM, Category.AFFECTION,  frequency="daily")
    walk      = Task("Walk",   30, Priority.MEDIUM, Category.WALK,       frequency="daily")
    feeding   = Task("Feed",   10, Priority.MEDIUM, Category.FEEDING,    frequency="daily")

    sorted_tasks = scheduler._sort_by_priority([affection, walk, feeding])
    titles = [t.title for t in sorted_tasks]

    assert titles.index("Walk")   < titles.index("Feed")
    assert titles.index("Feed")   < titles.index("Cuddle")


def test_generate_global_plan_returns_dropped_tasks():
    """generate_global_plan's second return value should list tasks that exceeded the budget."""
    owner = make_owner(minutes=20)
    pet = make_pet(owner)

    pet.add_task(Task("Walk",  30, Priority.HIGH, Category.WALK,    frequency="daily"))
    pet.add_task(Task("Feed",  10, Priority.HIGH, Category.FEEDING, frequency="daily"))

    scheduler = Scheduler.for_owner(owner)
    plans, dropped = scheduler.generate_global_plan()

    # 20 min budget: Feed(10) fits, Walk(30) cannot fit
    assert isinstance(dropped, list)
    assert any(t.title == "Walk" for t in dropped)


# ── Step 9: Frequency Corner Cases ───────────────────────────────────────────

def test_as_needed_task_is_never_due():
    """A task with frequency='as_needed' should always return False from is_due()."""
    task = Task("Nail trim", 15, Priority.LOW, frequency="as_needed")
    assert task.is_due() is False


def test_once_task_is_due_when_not_completed():
    """A 'once' task that has not been completed should be due."""
    task = Task("Vet visit", 60, Priority.HIGH, frequency="once")
    assert task.is_due() is True


def test_once_task_not_due_after_completion():
    """A 'once' task is no longer due after mark_complete()."""
    task = Task("Vet visit", 60, Priority.HIGH, frequency="once")
    task.mark_complete()
    assert task.is_due() is False


def test_weekly_future_due_date_not_due():
    """A weekly task whose due_date is in the future should not be due today."""
    task = Task("Bath", 30, Priority.MEDIUM, frequency="weekly")
    task.due_date = date.today() + timedelta(days=3)
    assert task.is_due() is False


def test_invalid_frequency_raises():
    """Constructing a Task with an unrecognised frequency string should raise ValueError."""
    try:
        Task("Bad task", 10, Priority.LOW, frequency="hourly")
        assert False, "Expected ValueError"
    except ValueError:
        pass


# ── Step 10: Age Adjustments and get_next_task ────────────────────────────────

def test_adjust_for_pet_caps_walk_for_puppy():
    """Walks for puppies (< 12 months) should be capped at 20 minutes."""
    owner = make_owner()
    puppy = Pet("Pup", "Labrador", 6, "dog", owner)
    scheduler = Scheduler.for_owner(owner)

    task = Task("Walk", 45, Priority.HIGH, Category.WALK, frequency="daily")
    adjusted = scheduler._adjust_for_pet([task], puppy)

    assert adjusted[0].duration_minutes <= 20


def test_adjust_for_pet_caps_walk_for_senior():
    """Walks for senior pets (> 96 months) should be capped at 25 minutes."""
    owner = make_owner()
    senior = Pet("Elder", "Labrador", 100, "dog", owner)
    scheduler = Scheduler.for_owner(owner)

    task = Task("Walk", 60, Priority.MEDIUM, Category.WALK, frequency="daily")
    adjusted = scheduler._adjust_for_pet([task], senior)

    assert adjusted[0].duration_minutes <= 25


def test_adjust_for_pet_promotes_meds_for_senior():
    """Medication tasks for senior pets should be bumped to HIGH priority."""
    owner = make_owner()
    senior = Pet("Elder", "Labrador", 100, "dog", owner)
    scheduler = Scheduler.for_owner(owner)

    task = Task("Meds", 10, Priority.LOW, Category.MEDICATION, frequency="daily")
    adjusted = scheduler._adjust_for_pet([task], senior)

    assert adjusted[0].priority == Priority.HIGH


def test_get_next_task_returns_highest_priority():
    """get_next_task() should return the highest-priority pending due task."""
    owner = make_owner()
    pet = make_pet(owner)
    pet.add_task(Task("Low task",  10, Priority.LOW,  Category.AFFECTION, frequency="daily"))
    pet.add_task(Task("High task", 15, Priority.HIGH, Category.WALK,      frequency="daily"))
    pet.add_task(Task("Med task",  10, Priority.MEDIUM, Category.FEEDING, frequency="daily"))

    scheduler = Scheduler.for_owner(owner)
    next_task = scheduler.get_next_task()

    assert next_task is not None
    assert next_task.title == "High task"


def test_get_next_task_ignores_completed():
    """get_next_task() should skip tasks that are already completed."""
    owner = make_owner()
    pet = make_pet(owner)
    high = Task("Walk",  30, Priority.HIGH, Category.WALK,    frequency="daily")
    low  = Task("Feed",  10, Priority.LOW,  Category.FEEDING, frequency="daily")
    high.mark_complete()
    pet.add_task(high)
    pet.add_task(low)

    scheduler = Scheduler.for_owner(owner)
    next_task = scheduler.get_next_task()

    assert next_task is not None
    assert next_task.title == "Feed"


def test_by_time_bucket_filter():
    """by_time_bucket(MORNING) should return only items scheduled before noon."""
    from datetime import time
    from pawpal_system import by_time_bucket

    morning_item = ScheduledItem(Task("Walk",  30, Priority.HIGH),  time(7, 0),  "")
    evening_item = ScheduledItem(Task("Feed",  10, Priority.HIGH),  time(13, 0), "")
    night_item   = ScheduledItem(Task("Meds",   5, Priority.HIGH),  time(19, 0), "")

    result = apply_filters(
        [morning_item, evening_item, night_item],
        [by_time_bucket(TimeOfDay.MORNING)],
    )
    assert len(result) == 1
    assert result[0].task.title == "Walk"
