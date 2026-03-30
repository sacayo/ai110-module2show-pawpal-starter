"""
Tests for core PawPal+ behaviors.
Run with: uv run pytest tests/test_pawpal.py -v
"""

from pawpal_system import Owner, Pet, Task, Priority, Category


def make_owner() -> Owner:
    return Owner("Test Owner", available_minutes=120)


def make_pet(owner: Owner) -> Pet:
    return Pet("Buddy", "Labrador", 36, "dog", owner)


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
