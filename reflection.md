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
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

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
