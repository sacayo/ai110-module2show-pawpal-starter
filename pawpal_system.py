"""
PawPal+ Logic Layer
All backend classes for the pet care planning system.
"""

from enum import Enum
from datetime import datetime, date, time


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
# Owner & Preferences
# ─────────────────────────────────────────────

class OwnerPreferences:
    def __init__(
        self,
        preferred_walk_time: TimeOfDay = TimeOfDay.MORNING,
        preferred_feed_time: TimeOfDay = TimeOfDay.MORNING,
        priority_order: list[Category] | None = None,
    ):
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
        return {
            "preferred_walk_time": self.preferred_walk_time.value,
            "preferred_feed_time": self.preferred_feed_time.value,
            "priority_order": [c.value for c in self.priority_order],
        }


class Owner:
    def __init__(
        self,
        name: str,
        available_minutes: int,
        preferences: OwnerPreferences | None = None,
    ):
        self.name = name
        self.available_minutes = available_minutes
        self.preferences = preferences or OwnerPreferences()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "available_minutes": self.available_minutes,
            "preferences": self.preferences.to_dict(),
        }


# ─────────────────────────────────────────────
# Pet
# ─────────────────────────────────────────────

class Pet:
    def __init__(self, name: str, breed: str, age_months: int, species: str):
        self.name = name
        self.breed = breed
        self.age_months = age_months
        self.species = species

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "breed": self.breed,
            "age_months": self.age_months,
            "species": self.species,
        }


# ─────────────────────────────────────────────
# Task (universal schedulable unit)
# ─────────────────────────────────────────────

class Task:
    def __init__(
        self,
        title: str,
        duration_minutes: int,
        priority: Priority,
        category: Category = Category.CUSTOM,
        preferred_time: TimeOfDay | None = None,
    ):
        self.title = title
        self.duration_minutes = duration_minutes
        self.priority = priority
        self.category = category
        self.preferred_time = preferred_time

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority.value,
            "category": self.category.value,
            "preferred_time": self.preferred_time.value if self.preferred_time else None,
        }


# ─────────────────────────────────────────────
# Care Records
# ─────────────────────────────────────────────

class WalkSchedule:
    def __init__(
        self,
        distance_km: float,
        duration_minutes: int,
        day_of_week: DayOfWeek,
        time_of_day: TimeOfDay,
    ):
        self.distance_km = distance_km
        self.duration_minutes = duration_minutes
        self.day_of_week = day_of_week
        self.time_of_day = time_of_day
        self.walks_given: int = 0

    def log_walk(self) -> None:
        self.walks_given += 1

    def to_task(self) -> Task:
        return Task(
            title=f"Walk ({self.distance_km}km)",
            duration_minutes=self.duration_minutes,
            priority=Priority.HIGH,
            category=Category.WALK,
            preferred_time=self.time_of_day,
        )


class Feeding:
    def __init__(
        self,
        weight_grams: int,
        feeding_date: date,
        time_of_day: TimeOfDay,
    ):
        self.weight_grams = weight_grams
        self.date = feeding_date
        self.time_of_day = time_of_day
        self.feedings_given: int = 0

    def log_feeding(self) -> None:
        self.feedings_given += 1

    def to_task(self) -> Task:
        return Task(
            title=f"Feeding ({self.weight_grams}g)",
            duration_minutes=10,
            priority=Priority.HIGH,
            category=Category.FEEDING,
            preferred_time=self.time_of_day,
        )


class GroomingRecord:
    def __init__(self, time_of_day: TimeOfDay = TimeOfDay.MORNING):
        self.groom_log: list[tuple[datetime, str]] = []
        self.time_of_day = time_of_day

    def log_groom(self, label: str) -> None:
        self.groom_log.append((datetime.now(), label))

    @property
    def groom_count_this_year(self) -> int:
        current_year = datetime.now().year
        return sum(1 for dt, _ in self.groom_log if dt.year == current_year)

    def to_task(self) -> Task:
        return Task(
            title="Grooming",
            duration_minutes=30,
            priority=Priority.MEDIUM,
            category=Category.GROOMING,
            preferred_time=self.time_of_day,
        )


class MedicationRecord:
    def __init__(self, med_name: str, dosage_interval_hours: int):
        self.med_name = med_name
        self.dosage_interval_hours = dosage_interval_hours
        self.meds_administered: int = 0
        self.last_med_datetime: datetime | None = None

    def administer_med(self) -> None:
        self.meds_administered += 1
        self.last_med_datetime = datetime.now()

    def to_task(self) -> Task:
        return Task(
            title=f"Medication ({self.med_name})",
            duration_minutes=5,
            priority=Priority.HIGH,
            category=Category.MEDICATION,
        )


class AffectionRecord:
    def __init__(self):
        self.affection_counter: int = 0
        self.last_affection_datetime: datetime | None = None

    def give_affection(self) -> None:
        self.affection_counter += 1
        self.last_affection_datetime = datetime.now()

    def to_task(self) -> Task:
        return Task(
            title="Affection / Play",
            duration_minutes=15,
            priority=Priority.LOW,
            category=Category.AFFECTION,
        )


class Enrichment:
    def __init__(
        self,
        activity_type: EnrichmentType,
        duration_minutes: int,
        time_of_day: TimeOfDay,
    ):
        self.activity_type = activity_type
        self.duration_minutes = duration_minutes
        self.time_of_day = time_of_day

    def to_task(self) -> Task:
        return Task(
            title=f"Enrichment ({self.activity_type.value})",
            duration_minutes=self.duration_minutes,
            priority=Priority.MEDIUM,
            category=Category.ENRICHMENT,
            preferred_time=self.time_of_day,
        )


# ─────────────────────────────────────────────
# Scheduler & Daily Plan
# ─────────────────────────────────────────────

TIME_SLOTS = {
    TimeOfDay.MORNING: time(6, 0),
    TimeOfDay.EVENING: time(12, 0),
    TimeOfDay.NIGHT: time(18, 0),
}


class ScheduledItem:
    def __init__(self, task: Task, start_time: time, reason: str):
        self.task = task
        self.start_time = start_time
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "title": self.task.title,
            "start_time": self.start_time.strftime("%H:%M"),
            "duration_minutes": self.task.duration_minutes,
            "priority": self.task.priority.value,
            "reason": self.reason,
        }


class DailyPlan:
    def __init__(
        self,
        items: list[ScheduledItem],
        total_minutes: int,
        explanation: str,
    ):
        self.items = items
        self.total_minutes = total_minutes
        self.explanation = explanation

    def to_dict(self) -> dict:
        return {
            "items": [item.to_dict() for item in self.items],
            "total_minutes": self.total_minutes,
            "explanation": self.explanation,
        }

    def display_table(self) -> list[dict]:
        return [item.to_dict() for item in self.items]


class Scheduler:
    def __init__(self, owner: Owner, pet: Pet, tasks: list[Task]):
        self.owner = owner
        self.pet = pet
        self.tasks = tasks

    def generate_plan(self) -> DailyPlan:
        sorted_tasks = self._sort_by_priority(self.tasks)
        fitted, dropped = self._fit_to_time(sorted_tasks, self.owner.available_minutes)
        scheduled_items = self._assign_times(fitted)
        explanation = self._build_explanation(fitted, dropped)
        total_minutes = sum(t.duration_minutes for t in fitted)
        return DailyPlan(
            items=scheduled_items,
            total_minutes=total_minutes,
            explanation=explanation,
        )

    def _sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        pref_order = self.owner.preferences.priority_order
        category_rank = {cat: i for i, cat in enumerate(pref_order)}

        def sort_key(task: Task) -> tuple[int, int, str]:
            priority_rank = -task.priority.weight
            cat_rank = category_rank.get(task.category, len(pref_order))
            return (priority_rank, cat_rank, task.title)

        return sorted(tasks, key=sort_key)

    def _fit_to_time(
        self, tasks: list[Task], available: int
    ) -> tuple[list[Task], list[Task]]:
        fitted: list[Task] = []
        dropped: list[Task] = []
        used = 0
        for task in tasks:
            if used + task.duration_minutes <= available:
                fitted.append(task)
                used += task.duration_minutes
            else:
                dropped.append(task)
        return fitted, dropped

    def _assign_times(self, tasks: list[Task]) -> list[ScheduledItem]:
        buckets: dict[TimeOfDay, list[Task]] = {
            TimeOfDay.MORNING: [],
            TimeOfDay.EVENING: [],
            TimeOfDay.NIGHT: [],
        }

        for task in tasks:
            slot = task.preferred_time if task.preferred_time else TimeOfDay.MORNING
            buckets[slot].append(task)

        items: list[ScheduledItem] = []
        for time_of_day in [TimeOfDay.MORNING, TimeOfDay.EVENING, TimeOfDay.NIGHT]:
            current_time = TIME_SLOTS[time_of_day]
            for task in buckets[time_of_day]:
                reason = self._build_item_reason(task, time_of_day)
                items.append(ScheduledItem(task=task, start_time=current_time, reason=reason))
                total_minutes = current_time.hour * 60 + current_time.minute + task.duration_minutes
                current_time = time(total_minutes // 60, total_minutes % 60)

        return items

    def _build_item_reason(self, task: Task, slot: TimeOfDay) -> str:
        parts = [f"{task.priority.value.capitalize()} priority"]
        if task.preferred_time == slot:
            parts.append(f"scheduled in {slot.value} per owner preference")
        else:
            parts.append(f"placed in {slot.value} (default slot)")
        return " — ".join(parts)

    def _build_explanation(
        self, fitted: list[Task], dropped: list[Task]
    ) -> str:
        total = len(fitted) + len(dropped)
        used_min = sum(t.duration_minutes for t in fitted)
        budget = self.owner.available_minutes

        lines = [
            f"Scheduled {len(fitted)} of {total} tasks "
            f"using {used_min} of {budget} available minutes."
        ]

        for task in fitted:
            lines.append(
                f"  • {task.title} ({task.priority.value}, {task.duration_minutes}min)"
            )

        if dropped:
            dropped_names = ", ".join(t.title for t in dropped)
            lines.append(
                f"Dropped due to time constraints: {dropped_names}."
            )

        return "\n".join(lines)
