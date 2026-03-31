# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
    - the UML diagram provides a full system flow detailing owner, pet, pet activities, datetime objects, and schedule objects for tracking pet activities.
- What classes did you include, and what responsibilities did you assign to each?
    - I included 17 classes:
        -- TimeOfDay: keep track of time of last activity type
        -- DayOfWeek: keep track of day of last activity type
        -- Priority: priority flag of activity
        -- Category: category of activity
        -- Enrichment: object for enrichment
        -- EnrichmentType: type of enrichment activity(puzzle, toys, training, social)
        -- OwnerPreference: preferred walking and feeding time for petp
        -- Owner: data profile of owner
        -- Pet: data profile of pet 
        -- Task: task object
        -- WalkSchedule: distance, duration, time of day, day of week, counter of walks given
        -- Feeding: weight of food, date, time of day, counter of feeding
        -- GroomingRecord: groom log
        -- MedicationRecord: medication log(med name, last med datetime, dosage)
        -- AffectionRecord: affection counter, last affection given
        -- SceduledItem: handles overall pending items
        -- DailyPlan: daily pending items provided by scheduled item
        -- Scheduler: scheduling object

**b. Design changes**

- Did your design change during implementation?
    yes, there were a few relationship that failed to be converted into code. for instance, 
        - owner <-> was not linked in code
        - pet <-> was not linked in code
        - medication scheduling ignored dose interval
        - pet data was unused by scheduler
- If yes, describe at least one change and why you made it.
    here are the list of fixes.
        fix 1: owner <-> pet relationship
        -- Add pets: list[Pet] to Owner. Add owner: Owner parameter back to Pet.__init__. When a Pet is created with an owner, it
            auto-registers itself into owner.pets. Update to_dict() on both.
        fix 2: pet <-> care record relationship
        -- Add attributes to Pet:
            - walk_schedules: list[WalkSchedule]
            - feedings: list[Feeding]
            - grooming: GroomingRecord | None
            - medication: MedicationRecord | None
            - affection: AffectionRecord | None
            - enrichments: list[Enrichment]
        fix 3: medictation dse interval
            -- Add an is_dose_due() method that checks if last_med_datetime is None (never dosed) or if enough hours have elapsed
            since the last dose. Update to_task() to return None when no dose is due, and update the return type to Task | None.
            Callers must handle the None case.
        fix 4: scheduler doesn't use pet data
        -- self.pet is stored but never read. A senior dog and a kitten get identical plans.
            - If pet.age_months < 12 (puppy/kitten): increase walk frequency importance, reduce walk duration
            - If pet.age_months > 96 (senior, ~8+ years): reduce walk duration, increase medication priority
            - Include pet name and species in the explanation string
 Why: Without this, there's no way to ask "which pets does this owner have?" — the core domain relationship is missing.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
    -- there is a total minutes the owner can spend and only keeps tasks whose combined duration fit this budget
    -- time of day buckets is used for perferred time

- How did you decide which constraints mattered most?
    -- I queried the AI assistant to help me reason about the most impactful tradeoffs

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
    -- the scheduler sorts by priority and takes into consideration of priority order (with category tie-breaks from owner preference), and anything that doesn't fit in a owner's available times is dropped.
- Why is that tradeoff reasonable for this scenario?
    -- the tradeoff make sense because the app is meant to help owner prioritize daily task for pet managment. Use a priority order is essiental, although the way the app dropped other item is not optimized.
---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
    -- Used AI for UML design brainstorming — generating the initial 17-class schema and reasoning through which relationships were needed (owner → pet, pet → care records, etc.)
    -- Used AI for debugging — the four design-to-code gaps identified in section 1b (missing owner–pet link, pet–care record link, medication dose interval, and scheduler ignoring pet data) were all surfaced through AI-assisted diagnosis
    -- Used AI for refactoring — the `_adjust_for_pet` method (age-aware walk caps and medication priority escalation) and the two-pass `_fit_to_time` algorithm were shaped through back-and-forth with AI
- What kinds of prompts or questions were most helpful?
    -- Diagnosis questions were most useful: "why does a senior dog and a kitten get the same daily plan?" and "what domain relationships am I missing between these classes?" — open-ended, problem-first questions rather than "write this for me" requests

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
    -- The AI's first draft of `_fit_to_time` was a simple single-pass greedy algorithm — take tasks in priority order until the budget runs out. I rejected that because it would drop all remaining tasks even when a small lower-priority task could still fit in the leftover time. The two-pass approach (priority pass, then backfill with smaller dropped tasks) was the result of that push-back.
- How did you evaluate or verify what the AI suggested?
    -- Verified by writing a concrete test: add tasks whose combined duration slightly exceeds the budget but where a small low-priority task fits in the remaining gap — confirmed the backfill pass rescues it rather than dropping it entirely.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
    -- I test both positive and negative cases of how the algorithm works along with how the data objects works when a user creates a task
- Why were these tests important?
    -- Positive cases (task correctly scheduled, high-priority tasks first, correct next_due_date) confirmed the happy path. Negative cases (task dropped when budget exceeded, `as_needed` frequency never auto-scheduled, `once` task not rescheduled after completion) confirmed the guard rails. Without both directions you can't distinguish "this always returns true" from "this actually works."

**b. Confidence**

- How confident are you that your scheduler works correctly?
    -- High confidence in the core sorting/fitting pipeline because `_sort_by_priority`, `_fit_to_time`, `_boost_overdue`, and `_adjust_for_pet` each have dedicated unit tests covering both the happy path and boundary behavior.
- What edge cases would you test next if you had more time?
    -- `available_minutes = 0` (should produce an empty plan, not a crash)
    -- Two pets whose tasks both prefer MORNING and together exceed the morning time window (silent time overflow at bucket boundary)
    -- Medication task where `is_dose_due()` returns False — verify the scheduler omits it entirely
    -- Owner with no pets registered — `generate_global_plan()` should return an empty dict cleanly

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
    -- Most satisfied with the domain model depth: the 17-class design with real bidirectional relationships (`owner.pets`, `pet.walk_schedules`, `pet.medication`, etc.) and the `_boost_overdue` mechanism that dynamically elevates neglected tasks. Those two features together make the scheduler feel like it is actually reasoning about a pet's individual situation, not just sorting a static list.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
    -- The time-slot assignment in `_assign_times` clamps overflow to `BUCKET_END_MINUTES` but doesn't shift tasks to the next time bucket — a heavy morning schedule silently compresses tasks rather than moving them to evening.
    -- Owner preferences only fill `preferred_time` for WALK and FEEDING categories; GROOMING, ENRICHMENT, and MEDICATION all default to MORNING even if the owner would prefer otherwise.
    -- The greedy drop approach in `_fit_to_time` is not globally optimal — a dynamic-programming or bin-packing approach could fit more total care minutes within the same budget.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
    -- AI is most valuable as a diagnostic partner, not a code generator. The highest-value interactions were prompts that asked "what is wrong or missing" — surfacing the four design gaps — not prompts that asked "write this class for me." Knowing how to ask the right diagnosis question is a more durable skill than knowing how to prompt for output.
