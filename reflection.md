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
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
    -- I test both positive and negative cases of how the algorithm works along with how the data objects works when a user creates a task
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
