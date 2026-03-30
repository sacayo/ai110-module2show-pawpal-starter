"""
PawPal+ Logic Layer
All backend classes for the pet care planning system.
"""

from __future__ import annotations

from enum import Enum
from datetime import datetime, date, time, timedelta


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class TimeOfDay(Enum):
    MORNING = "morning"
    EVENING = "evening"
    NIGHT = "night"


class DayOfWeek(Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class Priority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def weight(self) -> int:
        """Return numeric weight for sorting: HIGH=3, MEDIUM=2, LOW=1."""
        return {"high": 3, "medium": 2, "low": 1}[self.value]


class Category(Enum):
    WALK = "walk"
    FEEDING = "feeding"
    GROOMING = "grooming"
    MEDICATION = "medication"
    AFFECTION = "affection"
    ENRICHMENT = "enrichment"
    CUSTOM = "custom"


class EnrichmentType(Enum):
    PUZZLE = "puzzle"
    TOY = "toy"
    TRAINING = "training"
    SOCIAL = "social"


# ─────────────────────────────────────────────
# Task
# ─────────────────────────────────────────────

class Task:
    """
    Represents a single pet care activity.

    Attributes:
        title            Human-readable name of the activity.
        duration_minutes How long the activity takes.
        priority         HIGH / MEDIUM / LOW — drives scheduling order.
        category         Which care type this belongs to.
        preferred_time   Optional time-of-day hint for the scheduler.
        frequency        How often this recurs: "daily", "weekly", "once", "as_needed".
        completed        Whether this task has been completed today.
        last_completed   Timestamp of the most recent completion.
    """

    VALID_FREQUENCIES = {"daily", "weekly", "once", "as_needed"}

    def __init__(
        self,
        title: str,
        duration_minutes: int,
        priority: Priority,
        category: Category = Category.CUSTOM,
        preferred_time: TimeOfDay | None = None,
        frequency: str = "daily",
    ):
        """Initialize a task, validating frequency against allowed values."""
        if frequency not in self.VALID_FREQUENCIES:
            raise ValueError(f"frequency must be one of {self.VALID_FREQUENCIES}")
        self.title = title
        self.duration_minutes = duration_minutes
        self.priority = priority
        self.category = category
        self.preferred_time = preferred_time
        self.frequency = frequency
        self.completed: bool = False
        self.last_completed: datetime | None = None

    def mark_complete(self) -> None:
        """Mark this task as done and record when it was completed."""
        self.completed = True
        self.last_completed = datetime.now()

    def reset(self) -> None:
        """Clear completion status — called at the start of a new day."""
        self.completed = False

    def is_due(self, current_day: DayOfWeek | None = None) -> bool:
        """
        Return True if this task should appear on today's schedule.

        - "daily"     → always due.
        - "weekly"    → due only when current_day matches the task's preferred_time day
                        (falls back to always due if current_day not provided).
        - "once"      → due only if not yet completed.
        - "as_needed" → never auto-scheduled; owner triggers manually.
        """
        if self.frequency == "daily":
            return True
        if self.frequency == "weekly":
            # Without a day argument, include it (scheduler can filter later)
            return True
        if self.frequency == "once":
            return not self.completed
        if self.frequency == "as_needed":
            return False
        return True

    def to_dict(self) -> dict:
        """Serialize the task to a plain dictionary including completion state."""
        return {
            "title": self.title,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority.value,
            "category": self.category.value,
            "preferred_time": self.preferred_time.value if self.preferred_time else None,
            "frequency": self.frequency,
            "completed": self.completed,
            "last_completed": self.last_completed.isoformat() if self.last_completed else None,
        }


# ─────────────────────────────────────────────
# Owner & Preferences
# ─────────────────────────────────────────────

class OwnerPreferences:
    def __init__(
        self,
        preferred_walk_time: TimeOfDay = TimeOfDay.MORNING,
        preferred_feed_time: TimeOfDay = TimeOfDay.MORNING,
        priority_order: list[Category] | None = None,
    ):
        """Initialize owner scheduling preferences with sensible defaults."""
        self.preferred_walk_time = preferred_walk_time
        self.preferred_feed_time = preferred_feed_time
        self.priority_order = priority_order or [
            Category.WALK,
            Category.FEEDING,
            Category.MEDICATION,
            Category.GROOMING,
            Category.ENRICHMENT,
            Category.AFFECTION,
        ]

    def to_dict(self) -> dict:
        """Serialize preferences to a plain dictionary."""
        return {
            "preferred_walk_time": self.preferred_walk_time.value,
            "preferred_feed_time": self.preferred_feed_time.value,
            "priority_order": [c.value for c in self.priority_order],
        }


class Owner:
    """
    Manages multiple pets and provides unified access to all their tasks.

    Responsibilities:
        - Holds a list of all owned pets.
        - Exposes cross-pet task queries (all tasks, pending tasks).
        - Stores scheduling preferences (available time, time-of-day preferences).
    """

    def __init__(
        self,
        name: str,
        available_minutes: int,
        preferences: OwnerPreferences | None = None,
    ):
        """Initialize an owner with a name, time budget, and optional preferences."""
        self.name = name
        self.available_minutes = available_minutes
        self.preferences = preferences or OwnerPreferences()
        self.pets: list[Pet] = []

    # ── Pet management ────────────────────────────────────────────────────────

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner, preventing duplicates."""
        if pet not in self.pets:
            self.pets.append(pet)

    def get_pet_by_name(self, name: str) -> Pet | None:
        """Return the first pet whose name matches (case-insensitive)."""
        for pet in self.pets:
            if pet.name.lower() == name.lower():
                return pet
        return None

    # ── Cross-pet task queries ────────────────────────────────────────────────

    def get_all_tasks(self) -> list[Task]:
        """Return every due task from every pet, as a flat list."""
        tasks: list[Task] = []
        for pet in self.pets:
            tasks.extend(pet.collect_tasks())
        return tasks

    def get_all_pending_tasks(self) -> list[Task]:
        """Return all due, not-yet-completed tasks across every pet."""
        return [t for t in self.get_all_tasks() if not t.completed]

    def to_dict(self) -> dict:
        """Serialize owner info including per-pet task counts."""
        return {
            "name": self.name,
            "available_minutes": self.available_minutes,
            "preferences": self.preferences.to_dict(),
            "pets": [
                {
                    "name": p.name,
                    "pending_tasks": len(p.get_pending_tasks()),
                    "completed_tasks": len(p.get_completed_tasks()),
                }
                for p in self.pets
            ],
        }


# ─────────────────────────────────────────────
# Pet
# ─────────────────────────────────────────────

class Pet:
    """
    Stores pet details and owns all care records and tasks.

    Responsibilities:
        - Holds structured care records (walks, feedings, grooming, etc.).
        - Accepts custom one-off tasks not tied to any care record.
        - Provides task management: add, remove, complete, and query by status.
    """

    def __init__(
        self,
        name: str,
        breed: str,
        age_months: int,
        species: str,
        owner: Owner,
    ):
        """Initialize a pet and auto-register it with its owner."""
        self.name = name
        self.breed = breed
        self.age_months = age_months
        self.species = species
        self.owner = owner
        # Auto-register with owner
        owner.add_pet(self)

        # Structured care records
        self.walk_schedules: list[WalkSchedule] = []
        self.feedings: list[Feeding] = []
        self.grooming: GroomingRecord | None = None
        self.medication: MedicationRecord | None = None
        self.affection: AffectionRecord | None = None
        self.enrichments: list[Enrichment] = []

        # Custom / one-off tasks not backed by a care record
        self.custom_tasks: list[Task] = []

    # ── Task management ───────────────────────────────────────────────────────

    def add_task(self, task: Task) -> None:
        """Add a custom task directly to this pet."""
        self.custom_tasks.append(task)

    def remove_task(self, title: str) -> bool:
        """
        Remove the first custom task whose title matches.
        Returns True if a task was found and removed.
        """
        for i, task in enumerate(self.custom_tasks):
            if task.title.lower() == title.lower():
                self.custom_tasks.pop(i)
                return True
        return False

    def complete_task(self, title: str) -> bool:
        """
        Mark the first task (care record or custom) with this title as complete.
        Returns True if found.
        """
        for task in self.collect_tasks(filter_due=False):
            if task.title.lower() == title.lower():
                task.mark_complete()
                return True
        return False

    def get_pending_tasks(self) -> list[Task]:
        """Return all due tasks that are not yet completed."""
        return [t for t in self.collect_tasks() if not t.completed]

    def get_completed_tasks(self) -> list[Task]:
        """Return all tasks marked complete today."""
        return [t for t in self.collect_tasks(filter_due=False) if t.completed]

    def collect_tasks(self, filter_due: bool = True) -> list[Task]:
        """
        Gather all Tasks from every care record and custom task list.

        Args:
            filter_due: If True (default), only return tasks where is_due() is True.
        """
        tasks: list[Task] = []

        for walk in self.walk_schedules:
            tasks.append(walk.to_task())
        for feeding in self.feedings:
            tasks.append(feeding.to_task())
        if self.grooming:
            tasks.append(self.grooming.to_task())
        if self.medication:
            med_task = self.medication.to_task()
            if med_task:
                tasks.append(med_task)
        if self.affection:
            tasks.append(self.affection.to_task())
        for enrichment in self.enrichments:
            tasks.append(enrichment.to_task())
        tasks.extend(self.custom_tasks)

        if filter_due:
            tasks = [t for t in tasks if t.is_due()]
        return tasks

    def to_dict(self) -> dict:
        """Serialize pet details to a plain dictionary."""
        return {
            "name": self.name,
            "breed": self.breed,
            "age_months": self.age_months,
            "species": self.species,
            "owner": self.owner.name,
        }


# ─────────────────────────────────────────────
# Care Records
# ─────────────────────────────────────────────

class WalkSchedule:
    def __init__(
        self,
        pet: Pet,
        distance_km: float,
        duration_minutes: int,
        day_of_week: DayOfWeek,
        time_of_day: TimeOfDay,
    ):
        """Create a walk schedule and register it with the pet."""
        self.distance_km = distance_km
        self.duration_minutes = duration_minutes
        self.day_of_week = day_of_week
        self.time_of_day = time_of_day
        self.walks_given: int = 0
        pet.walk_schedules.append(self)

    def log_walk(self) -> None:
        """Record that one walk was completed, incrementing the counter."""
        self.walks_given += 1

    def to_task(self) -> Task:
        """Convert this walk schedule into a schedulable Task."""
        return Task(
            title=f"Walk ({self.distance_km}km)",
            duration_minutes=self.duration_minutes,
            priority=Priority.HIGH,
            category=Category.WALK,
            preferred_time=self.time_of_day,
            frequency="daily",
        )


class Feeding:
    def __init__(
        self,
        pet: Pet,
        weight_grams: int,
        feeding_date: date,
        time_of_day: TimeOfDay,
    ):
        """Create a feeding record and register it with the pet."""
        self.weight_grams = weight_grams
        self.date = feeding_date
        self.time_of_day = time_of_day
        self.feedings_given: int = 0
        pet.feedings.append(self)

    def log_feeding(self) -> None:
        """Record that one feeding was completed, incrementing the counter."""
        self.feedings_given += 1

    def to_task(self) -> Task:
        """Convert this feeding record into a schedulable Task."""
        return Task(
            title=f"Feeding ({self.weight_grams}g)",
            duration_minutes=10,
            priority=Priority.HIGH,
            category=Category.FEEDING,
            preferred_time=self.time_of_day,
            frequency="daily",
        )


class GroomingRecord:
    def __init__(self, pet: Pet, time_of_day: TimeOfDay = TimeOfDay.MORNING):
        """Create a grooming tracker and register it with the pet."""
        self.groom_log: list[tuple[datetime, str]] = []
        self.time_of_day = time_of_day
        pet.grooming = self

    def log_groom(self, label: str) -> None:
        """Append a timestamped grooming session with the given label."""
        self.groom_log.append((datetime.now(), label))

    @property
    def groom_count_this_year(self) -> int:
        """Return the number of grooming sessions logged in the current calendar year."""
        current_year = datetime.now().year
        return sum(1 for dt, _ in self.groom_log if dt.year == current_year)

    def to_task(self) -> Task:
        """Convert this grooming record into a schedulable weekly Task."""
        return Task(
            title="Grooming",
            duration_minutes=30,
            priority=Priority.MEDIUM,
            category=Category.GROOMING,
            preferred_time=self.time_of_day,
            frequency="weekly",
        )


class MedicationRecord:
    def __init__(self, pet: Pet, med_name: str, dosage_interval_hours: int):
        """Create a medication tracker and register it with the pet."""
        self.med_name = med_name
        self.dosage_interval_hours = dosage_interval_hours
        self.meds_administered: int = 0
        self.last_med_datetime: datetime | None = None
        pet.medication = self

    def administer_med(self) -> None:
        """Record that a dose was given and update the last-administered timestamp."""
        self.meds_administered += 1
        self.last_med_datetime = datetime.now()

    def is_dose_due(self) -> bool:
        """Returns True if a dose has never been given or the interval has elapsed."""
        if self.last_med_datetime is None:
            return True
        return datetime.now() - self.last_med_datetime >= timedelta(hours=self.dosage_interval_hours)

    def to_task(self) -> Task | None:
        """Returns None when no dose is currently due."""
        if not self.is_dose_due():
            return None
        return Task(
            title=f"Medication ({self.med_name})",
            duration_minutes=5,
            priority=Priority.HIGH,
            category=Category.MEDICATION,
            frequency="daily",
        )


class AffectionRecord:
    def __init__(self, pet: Pet):
        """Create an affection tracker and register it with the pet."""
        self.affection_counter: int = 0
        self.last_affection_datetime: datetime | None = None
        pet.affection = self

    def give_affection(self) -> None:
        """Increment the affection counter and record the current timestamp."""
        self.affection_counter += 1
        self.last_affection_datetime = datetime.now()

    def to_task(self) -> Task:
        """Convert this affection record into a schedulable Task."""
        return Task(
            title="Affection / Play",
            duration_minutes=15,
            priority=Priority.LOW,
            category=Category.AFFECTION,
            frequency="daily",
        )


class Enrichment:
    def __init__(
        self,
        pet: Pet,
        activity_type: EnrichmentType,
        duration_minutes: int,
        time_of_day: TimeOfDay,
    ):
        """Create an enrichment activity and register it with the pet."""
        self.activity_type = activity_type
        self.duration_minutes = duration_minutes
        self.time_of_day = time_of_day
        pet.enrichments.append(self)

    def to_task(self) -> Task:
        """Convert this enrichment activity into a schedulable Task."""
        return Task(
            title=f"Enrichment ({self.activity_type.value})",
            duration_minutes=self.duration_minutes,
            priority=Priority.MEDIUM,
            category=Category.ENRICHMENT,
            preferred_time=self.time_of_day,
            frequency="daily",
        )


# ─────────────────────────────────────────────
# Scheduler & Daily Plan
# ─────────────────────────────────────────────

TIME_SLOTS = {
    TimeOfDay.MORNING: time(6, 0),
    TimeOfDay.EVENING: time(12, 0),
    TimeOfDay.NIGHT: time(18, 0),
}

BUCKET_END_MINUTES = {
    TimeOfDay.MORNING: 12 * 60,
    TimeOfDay.EVENING: 18 * 60,
    TimeOfDay.NIGHT: 23 * 60 + 59,
}


class ScheduledItem:
    def __init__(self, task: Task, start_time: time, reason: str):
        """Wrap a Task with its assigned start time and scheduling reason."""
        self.task = task
        self.start_time = start_time
        self.reason = reason

    def to_dict(self) -> dict:
        """Serialize this scheduled item to a plain dictionary for display."""
        return {
            "title": self.task.title,
            "start_time": self.start_time.strftime("%H:%M"),
            "duration_minutes": self.task.duration_minutes,
            "priority": self.task.priority.value,
            "completed": self.task.completed,
            "reason": self.reason,
        }


class DailyPlan:
    def __init__(
        self,
        items: list[ScheduledItem],
        total_minutes: int,
        explanation: str,
    ):
        """Store the ordered list of scheduled items and the scheduler's explanation."""
        self.items = items
        self.total_minutes = total_minutes
        self.explanation = explanation

    def to_dict(self) -> dict:
        """Serialize the full plan to a nested dictionary."""
        return {
            "items": [item.to_dict() for item in self.items],
            "total_minutes": self.total_minutes,
            "explanation": self.explanation,
        }

    def display_table(self) -> list[dict]:
        """Return items as a flat list of dicts, suitable for st.table()."""
        return [item.to_dict() for item in self.items]


class Scheduler:
    """
    The scheduling brain. Retrieves, organizes, and manages tasks across pets.

    Can be constructed two ways:
        Scheduler(owner, pet, tasks)     — single-pet mode (backward compatible)
        Scheduler.for_owner(owner)       — multi-pet mode, auto-collects all tasks
    """

    def __init__(self, owner: Owner, pet: Pet, tasks: list[Task]):
        """Initialize the scheduler with an owner, a primary pet, and a flat task list."""
        self.owner = owner
        self.pet = pet
        self.tasks = tasks
        self.all_pets: list[Pet] = [pet]

    @classmethod
    def for_owner(cls, owner: Owner) -> Scheduler:
        """
        Factory: build a Scheduler that covers all of the owner's pets.
        Tasks are collected from every pet automatically.
        """
        if not owner.pets:
            raise ValueError(f"Owner '{owner.name}' has no pets registered.")
        all_tasks = owner.get_all_tasks()
        scheduler = cls(owner=owner, pet=owner.pets[0], tasks=all_tasks)
        scheduler.all_pets = list(owner.pets)
        return scheduler

    # ── Multi-pet interface ───────────────────────────────────────────────────

    def generate_all_plans(self) -> dict[str, DailyPlan]:
        """Generate one DailyPlan per pet, keyed by pet name."""
        return {pet.name: self.generate_plan_for_pet(pet) for pet in self.all_pets}

    def get_next_task(self) -> Task | None:
        """
        Return the single highest-priority pending task across all pets.
        Useful for "what should I do right now?"
        """
        pending = [t for t in self.tasks if not t.completed and t.is_due()]
        if not pending:
            return None
        return max(pending, key=lambda t: t.priority.weight)

    def complete_task(self, pet_name: str, task_title: str) -> bool:
        """
        Mark a task complete by pet name and task title.
        Returns True if the task was found and marked.
        """
        pet = self.owner.get_pet_by_name(pet_name)
        if pet is None:
            return False
        return pet.complete_task(task_title)

    def reset_all_tasks(self) -> None:
        """Reset completion status on all tasks — call at the start of a new day."""
        for task in self.tasks:
            task.reset()

    # ── Per-pet planning ──────────────────────────────────────────────────────

    def generate_plan(self) -> DailyPlan:
        """Generate a plan for the primary pet (backward-compatible entry point)."""
        return self.generate_plan_for_pet(self.pet)

    def generate_plan_for_pet(self, pet: Pet) -> DailyPlan:
        """Generate a DailyPlan scoped to one pet's pending tasks."""
        pet_tasks = [t for t in pet.collect_tasks() if not t.completed]
        adjusted = self._adjust_for_pet(pet_tasks, pet)
        preffed = self._apply_owner_preferences(adjusted)
        sorted_tasks = self._sort_by_priority(preffed)
        fitted, dropped = self._fit_to_time(sorted_tasks, self.owner.available_minutes)
        scheduled_items = self._assign_times(fitted)
        explanation = self._build_explanation(fitted, dropped, pet)
        total_minutes = sum(t.duration_minutes for t in fitted)
        return DailyPlan(items=scheduled_items, total_minutes=total_minutes, explanation=explanation)

    # ── Pet-aware adjustments ─────────────────────────────────────────────────

    def _adjust_for_pet(self, tasks: list[Task], pet: Pet) -> list[Task]:
        """Adjust task durations/priorities based on this specific pet's age."""
        age = pet.age_months
        adjusted = []
        for task in tasks:
            if task.category == Category.WALK:
                cap = 20 if age < 12 else 25 if age > 96 else None
                if cap:
                    task = Task(task.title, min(task.duration_minutes, cap),
                                task.priority, task.category, task.preferred_time, task.frequency)
            elif task.category == Category.MEDICATION and age > 96:
                task = Task(task.title, task.duration_minutes, Priority.HIGH,
                            task.category, task.preferred_time, task.frequency)
            adjusted.append(task)
        return adjusted

    # ── Owner preference application ──────────────────────────────────────────

    def _apply_owner_preferences(self, tasks: list[Task]) -> list[Task]:
        """Fill preferred_time from owner preferences for tasks that have none."""
        prefs = self.owner.preferences
        result = []
        for task in tasks:
            if task.preferred_time is None:
                preferred = (
                    prefs.preferred_walk_time if task.category == Category.WALK
                    else prefs.preferred_feed_time if task.category == Category.FEEDING
                    else None
                )
                if preferred:
                    task = Task(task.title, task.duration_minutes, task.priority,
                                task.category, preferred, task.frequency)
            result.append(task)
        return result

    # ── Scheduling core ───────────────────────────────────────────────────────

    def _sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Sort tasks by priority weight then owner category preference, then title."""
        pref_order = self.owner.preferences.priority_order
        category_rank = {cat: i for i, cat in enumerate(pref_order)}
        return sorted(
            tasks,
            key=lambda t: (-t.priority.weight, category_rank.get(t.category, len(pref_order)), t.title),
        )

    def _fit_to_time(
        self, tasks: list[Task], available: int
    ) -> tuple[list[Task], list[Task]]:
        """Two-pass greedy fit: priority-ordered pass, then backfill with smaller dropped tasks."""
        fitted, dropped, used = [], [], 0
        for task in tasks:
            if used + task.duration_minutes <= available:
                fitted.append(task)
                used += task.duration_minutes
            else:
                dropped.append(task)

        remaining = available - used
        still_dropped = []
        for task in dropped:
            if task.duration_minutes <= remaining:
                fitted.append(task)
                remaining -= task.duration_minutes
            else:
                still_dropped.append(task)

        return fitted, still_dropped

    def _assign_times(self, tasks: list[Task]) -> list[ScheduledItem]:
        """Assign clock times to tasks, clamped to prevent midnight overflow."""
        buckets: dict[TimeOfDay, list[Task]] = {
            TimeOfDay.MORNING: [],
            TimeOfDay.EVENING: [],
            TimeOfDay.NIGHT: [],
        }
        for task in tasks:
            slot = task.preferred_time or TimeOfDay.MORNING
            buckets[slot].append(task)

        items: list[ScheduledItem] = []
        for time_of_day in [TimeOfDay.MORNING, TimeOfDay.EVENING, TimeOfDay.NIGHT]:
            current_minutes = TIME_SLOTS[time_of_day].hour * 60 + TIME_SLOTS[time_of_day].minute
            end_boundary = BUCKET_END_MINUTES[time_of_day]
            for task in buckets[time_of_day]:
                current_minutes = min(current_minutes, 23 * 60 + 59)
                start = time(current_minutes // 60, current_minutes % 60)
                items.append(ScheduledItem(task, start, self._build_item_reason(task, time_of_day)))
                next_minutes = current_minutes + task.duration_minutes
                current_minutes = min(next_minutes, end_boundary)
        return items

    def _build_item_reason(self, task: Task, slot: TimeOfDay) -> str:
        """Build a human-readable reason string for why a task landed in a given slot."""
        placement = (
            f"scheduled in {slot.value} per owner preference"
            if task.preferred_time == slot
            else f"placed in {slot.value} (default slot)"
        )
        return f"{task.priority.value.capitalize()} priority — {placement}"

    def _build_explanation(
        self, fitted: list[Task], dropped: list[Task], pet: Pet
    ) -> str:
        """Compose the full plain-text explanation shown at the top of each daily plan."""
        used_min = sum(t.duration_minutes for t in fitted)
        total = len(fitted) + len(dropped)
        budget = self.owner.available_minutes

        age_note = (
            f" ({pet.name} is a puppy/kitten — walk durations capped at 20 min.)" if pet.age_months < 12
            else f" ({pet.name} is a senior — walks capped at 25 min, meds prioritized.)" if pet.age_months > 96
            else ""
        )

        lines = [
            f"Plan for {pet.name} ({pet.species}, {pet.age_months} months) — owner: {self.owner.name}.{age_note}",
            f"Scheduled {len(fitted)} of {total} tasks using {used_min} of {budget} available minutes.",
        ]
        for task in fitted:
            status = "✓" if task.completed else "○"
            lines.append(f"  {status} {task.title} ({task.priority.value}, {task.duration_minutes}min, {task.frequency})")
        if dropped:
            lines.append(f"Dropped due to time constraints: {', '.join(t.title for t in dropped)}.")
        if not fitted:
            lines.append("Nothing to schedule — all tasks are complete or no tasks are due.")
        return "\n".join(lines)
