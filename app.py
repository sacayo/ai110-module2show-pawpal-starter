import streamlit as st

from pawpal_system import (
    Owner,
    Pet,
    Task,
    Priority,
    Category,
    TimeOfDay,
    Scheduler,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

# ── Lookup maps ────────────────────────────────────────────────────────────────
priority_map = {"low": Priority.LOW, "medium": Priority.MEDIUM, "high": Priority.HIGH}
category_map = {c.value: c for c in Category}
time_map = {t.value: t for t in TimeOfDay}

# ── Owner ──────────────────────────────────────────────────────────────────────
st.subheader("Owner")
col1, col2 = st.columns(2)
with col1:
    owner_name = st.text_input("Owner name", value="Jordan")
with col2:
    available_minutes = st.number_input(
        "Available minutes today", min_value=1, max_value=1440, value=120
    )

# Persist Owner in session state; recreate only when form values change.
owner_changed = (
    "owner" not in st.session_state
    or st.session_state.owner.name != owner_name
    or st.session_state.owner.available_minutes != int(available_minutes)
)
if owner_changed:
    st.session_state.owner = Owner(
        name=owner_name, available_minutes=int(available_minutes)
    )

owner: Owner = st.session_state.owner

# ── Add a Pet ──────────────────────────────────────────────────────────────────
st.subheader("Pets")

with st.form("add_pet_form", clear_on_submit=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        new_pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        new_species = st.selectbox("Species", ["dog", "cat", "other"])
    with col3:
        new_breed = st.text_input("Breed", value="Mixed")
    with col4:
        new_age = st.number_input("Age (months)", min_value=1, max_value=300, value=24)
    submitted = st.form_submit_button("Add pet")

if submitted:
    # Prevent duplicate names
    if owner.get_pet_by_name(new_pet_name):
        st.warning(f"A pet named '{new_pet_name}' already exists for this owner.")
    else:
        # Pet.__init__ auto-calls owner.add_pet(self), registering it immediately.
        Pet(
            name=new_pet_name,
            breed=new_breed,
            age_months=int(new_age),
            species=new_species,
            owner=owner,
        )
        st.rerun()

# ── Pet roster ─────────────────────────────────────────────────────────────────
if owner.pets:
    st.write("**Registered pets:**")
    st.table([p.to_dict() for p in owner.pets])
else:
    st.info("No pets yet. Add one above.")

# ── Active pet selector ────────────────────────────────────────────────────────
if owner.pets:
    pet_names = [p.name for p in owner.pets]

    # Default active pet to the first one if not set or if it no longer exists.
    if (
        "active_pet_name" not in st.session_state
        or st.session_state.active_pet_name not in pet_names
    ):
        st.session_state.active_pet_name = pet_names[0]

    st.session_state.active_pet_name = st.selectbox(
        "Manage tasks for",
        pet_names,
        index=pet_names.index(st.session_state.active_pet_name),
    )

    active_pet: Pet = owner.get_pet_by_name(st.session_state.active_pet_name)

    # ── Task inputs ────────────────────────────────────────────────────────────
    st.subheader(f"Tasks — {active_pet.name}")

    with st.form("add_task_form", clear_on_submit=True):
        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
        with col2:
            duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        with col3:
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        with col4:
            category = st.selectbox("Category", [c.value for c in Category], index=0)
        with col5:
            preferred_time = st.selectbox(
                "Time of day", ["(none)"] + [t.value for t in TimeOfDay]
            )
        task_submitted = st.form_submit_button("Add task")

    if task_submitted:
        task = Task(
            title=task_title,
            duration_minutes=int(duration),
            priority=priority_map[priority],
            category=category_map[category],
            preferred_time=time_map[preferred_time] if preferred_time != "(none)" else None,
            frequency="daily",
        )
        active_pet.add_task(task)
        st.rerun()

    if active_pet.custom_tasks:
        st.write(f"Current tasks for **{active_pet.name}**:")
        st.table([t.to_dict() for t in active_pet.custom_tasks])
        if st.button("Clear all tasks"):
            active_pet.custom_tasks.clear()
            st.rerun()
    else:
        st.info(f"No tasks yet for {active_pet.name}.")

    st.divider()

    # ── Schedule generation ────────────────────────────────────────────────────
    st.subheader("Build Schedule")

    if st.button("Generate schedule"):
        scheduler = Scheduler.for_owner(owner)
        all_plans = scheduler.generate_all_plans()

        for pet_name, plan in all_plans.items():
            if not plan.items:
                st.info(f"No tasks scheduled for {pet_name}.")
                continue
            st.markdown(f"### {pet_name}")
            st.success(f"{len(plan.items)} tasks — {plan.total_minutes} minutes total.")
            st.text(plan.explanation)
            st.table(plan.display_table())
