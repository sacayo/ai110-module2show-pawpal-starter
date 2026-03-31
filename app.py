import pandas as pd
import streamlit as st

from pawpal_system import (
    Owner,
    Pet,
    Task,
    Priority,
    Category,
    TimeOfDay,
    Scheduler,
    by_time_bucket,
    by_status,
    apply_filters,
)

# Row-colouring constants for the schedule dataframe.
# Note: hardcoded hex values are tuned for light mode — a known Streamlit
# limitation since st.dataframe does not support CSS variables.
_PRIORITY_COLORS: dict[str, str] = {
    "high": "#ffdddd",
    "medium": "#fff8dc",
    "low": "#ddffdd",
}
_OVERDUE_COLOR = "#ffe4b5"


def _style_row(row: pd.Series) -> list[str]:
    bg = _PRIORITY_COLORS.get(row.get("priority", ""), "")
    if row.get("overdue", False):
        bg = _OVERDUE_COLOR
    return [f"background-color: {bg}"] * len(row)


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

# On first load create the Owner; on subsequent runs mutate in-place so that
# existing pets and tasks are preserved when only the name or time budget changes.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(
        name=owner_name, available_minutes=int(available_minutes)
    )
else:
    existing = st.session_state.owner
    if existing.name != owner_name or existing.available_minutes != int(available_minutes):
        existing.name = owner_name
        existing.available_minutes = int(available_minutes)
        st.session_state.pop("schedule_result", None)

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
        st.session_state.pop("schedule_result", None)
        st.rerun()

# ── Pet roster ─────────────────────────────────────────────────────────────────
if owner.pets:
    st.write("**Registered pets:**")
    st.dataframe([p.to_dict() for p in owner.pets], use_container_width=True, hide_index=True)
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
        st.session_state.pop("schedule_result", None)
        st.rerun()

    if active_pet.custom_tasks:
        st.write(f"Current tasks for **{active_pet.name}**:")
        st.dataframe(
            [t.to_dict() for t in active_pet.custom_tasks],
            use_container_width=True,
            hide_index=True,
        )
        if st.button("Clear all tasks"):
            active_pet.custom_tasks.clear()
            st.session_state.pop("schedule_result", None)
            st.rerun()
    else:
        st.info(f"No tasks yet for {active_pet.name}.")

    st.divider()

    # ── Schedule generation ────────────────────────────────────────────────────
    st.subheader("Build Schedule")

    # Clicking the button stores results in session state; rendering is
    # separated so filter widgets persist across reruns.
    if st.button("Generate schedule"):
        scheduler = Scheduler.for_owner(owner)
        all_plans, dropped_globally = scheduler.generate_global_plan()
        st.session_state.schedule_result = (all_plans, dropped_globally)

    if "schedule_result" in st.session_state:
        all_plans, dropped_globally = st.session_state.schedule_result

        if st.button("Clear schedule"):
            del st.session_state.schedule_result
            st.rerun()

        # ── Global budget summary ──────────────────────────────────────────────
        total_used = sum(plan.total_minutes for plan in all_plans.values())
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Pets scheduled", len(all_plans))
        mc2.metric(
            "Time used",
            f"{total_used} / {owner.available_minutes} min",
            delta=f"{owner.available_minutes - total_used} min remaining",
        )
        # Use the structured dropped list returned by generate_global_plan()
        # directly — no explanation parsing needed for the count.
        mc3.metric("Tasks dropped", len(dropped_globally))

        # ── Per-pet plan ───────────────────────────────────────────────────────
        for pet_name, plan in all_plans.items():
            st.markdown(f"### {pet_name}")

            if not plan.items:
                st.info(f"No tasks scheduled for {pet_name}.")
                continue

            # Summary banner
            st.success(
                f"{len(plan.items)} task(s) scheduled — {plan.total_minutes} min total."
            )

            # NOTE: per-pet dropped titles and conflict descriptions are parsed
            # from plan.explanation because generate_global_plan() embeds them
            # there but does not return them as structured data.
            # Conflicts cannot be obtained by calling detect_and_resolve_conflicts()
            # again — that method shifts start times and is not idempotent.
            for line in plan.explanation.splitlines():
                if line.startswith("Dropped due to time"):
                    st.warning(f"⏭ {line}")
                elif "WARNING:" in line:
                    st.warning(f"⚠️ {line}")
                elif "[Conflict resolved]" in line:
                    st.info(f"ℹ️ {line.strip()}")

            # ── Filter controls ────────────────────────────────────────────────
            # Widgets are rendered here (outside the button block) so Streamlit
            # preserves their state across reruns.
            with st.expander("Filter tasks", expanded=False):
                fc1, fc2 = st.columns(2)
                with fc1:
                    time_filter = st.selectbox(
                        "Time of day",
                        ["All", "morning", "evening", "night"],
                        key=f"time_{pet_name}",
                    )
                with fc2:
                    status_filter = st.selectbox(
                        "Status",
                        ["All", "pending", "complete", "overdue"],
                        key=f"status_{pet_name}",
                    )

            # Apply composable filters from Scheduler layer
            filtered_items = plan.items
            active_filters = []
            if time_filter != "All":
                active_filters.append(by_time_bucket(TimeOfDay(time_filter)))
            if status_filter != "All":
                active_filters.append(by_status(status_filter))
            if active_filters:
                filtered_items = apply_filters(filtered_items, active_filters)

            if not filtered_items:
                st.info("No tasks match the selected filters.")
            else:
                # Build rows, tagging overdue tasks
                rows = []
                for item in filtered_items:
                    row = item.to_dict()
                    row["overdue"] = item.task.is_overdue()
                    rows.append(row)

                df = pd.DataFrame(rows)
                styled = df.style.apply(_style_row, axis=1)
                st.dataframe(styled, use_container_width=True, hide_index=True)

            # ── Reasoning expander ─────────────────────────────────────────────
            with st.expander("Schedule reasoning"):
                st.text(plan.explanation)
