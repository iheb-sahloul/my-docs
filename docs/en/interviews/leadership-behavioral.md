# Leadership & Behavioral (STAR)

> Technical leadership: feedback, conflict, stakeholders, estimation, team health. Architecture questions live in [System Design](system-design.md). Behavioral ("Tell me about a time…") questions are in the [Behavioral section](#behavioral-star).

## 🟢 Fundamentals

### Leadership

#### Q1. What makes technical feedback and mentorship actually effective, as opposed to just correct?

Effective feedback is specific (points at the actual line/decision, not a general impression),
timely (given close to when the work happened, not batched into a vague quarterly comment),
focused on the work and its impact rather than the person, and — critically for mentorship
specifically — explains the *why* behind the suggestion so the person can generalize it to the
next situation, not just fix this one instance. The distinction from "just correct" matters: a
technically accurate comment delivered in a way that reads as dismissive or purely critical can
be right and still fail at its actual goal, which is helping someone build better judgment over
time, not just getting this one PR fixed.

**Example:**

```text
Correct but unhelpful:  "Don't catch Exception here."
Effective:              "Line 42 catches Exception, so the timeout below is swallowed and the retry
                         never fires (we saw this in last month's incident). Catch IOException
                         instead; rule of thumb: catch only what you can handle at this layer."
```

## 🟡 Senior traps

### Leadership

#### Q2. A junior engineer keeps making the same category of mistake despite repeated code review comments. What's your concrete approach?

**Answer:** First, check whether the feedback so far actually explained the underlying principle
or just corrected the specific instance each time — repeating "fix this" without the reusable
"why" behind it teaches pattern-matching to that one review comment, not the generalizable
judgment that would prevent the *next* instance. Have a direct, private conversation — walk
through two or three real examples together, ask them to articulate the underlying principle in
their own words, and agree on something concrete to try differently going forward. If the pattern
still continues after a genuinely clear, direct conversation, that's a signal to loop in their
manager — but the first move is always a real conversation focused on understanding, not an
escalation.

**Example:**

```text
PR comment pattern (3 PRs in a row): "missing null check on line 42"
                                       "missing null check on line 88"
                                       "missing null check on line 15"
-> each was fixed individually, none explained *why* this class of input can be null here,
   or how to recognize the pattern before writing the code, not just after review flags it.
```

**Why it's a trap:** the instinct under interview pressure is "I'd just keep leaving clear review
comments" — the question is specifically testing whether the candidate recognizes that repeated
correct comments that don't land are a signal the intervention itself needs to change, not repeat.

#### Q3. How do you push back on a technical decision coming from a senior stakeholder or manager that you believe is wrong?

**Answer:** Lead with genuine curiosity about their reasoning before asserting your own — they may
have context you don't (a business constraint, a prior failed attempt, a timeline pressure that
changes the calculus). State your concern concretely and specifically (the actual risk or cost,
ideally with a rough quantification), propose a specific alternative rather than only raising an
objection, and be explicit about what you'd need to see to change your mind. If, after that
conversation, the decision still goes the other way and it's not a correctness-or-safety-critical
issue, the senior-level move is committing fully to the decided direction rather than relitigating
it repeatedly — "disagree and commit," reserved for genuinely non-critical disagreements.

**Example:**

```text
Weak pushback:   "I don't think we should do it this way."
Strong pushback: "This approach adds ~2 weeks of migration risk because it touches the
                  payments schema live. If we instead do X, we lose feature Y for one
                  release but avoid that risk. What would need to be true for the
                  original approach to still be right?"
```

**Why it's a trap:** vague disagreement ("I have concerns") reads as friction without substance —
the trap is stopping at raising an objection instead of pairing it with a concrete cost and a
concrete alternative, which is what actually makes pushback persuasive rather than just noted.

#### Q4. As a tech lead, how do you handle a design review where two senior engineers strongly disagree?

**Answer:** Separate the disagreement from the individuals first — make sure both people feel
genuinely heard, then get both positions written down concretely enough to compare on the same
axes (what does each approach optimize for, what does each cost, under what future scenario would
each turn out to have been the better call). Look for whether this is a decision with a knowable
right answer reachable via more information (a spike, a benchmark) versus a genuine values/
priority trade-off with no objectively correct answer — the first case is resolved by getting the
missing information; the second is a judgment call that ultimately needs an owner to make, once
both sides are fully heard, rather than being left to fester as an unresolved standoff.

**Example:**

```text
Position A: "Event-sourced — full audit trail, but higher complexity, 3 extra weeks."
Position B: "CRUD + audit table — simpler, ships now, harder to replay history later."

Resolvable by a spike? No — it's a genuine priority trade-off (audit depth vs. time-to-ship)
-> tech lead names the priority for this project explicitly, makes the call, explains why.
```

**Why it's a trap:** trying to reach full consensus on a genuine values trade-off can stall a
project indefinitely — the trap is treating "get everyone to agree" as the goal instead of "get
the decision made, explained, and owned," which is what a stalled review actually needs.

#### Q5. How do you scope and estimate a project with genuinely high uncertainty for stakeholders who want a firm date?

**Answer:** Be explicit that a single point estimate for a highly uncertain project is itself a
lie dressed up as precision — instead, communicate a range grounded in the actual sources of
uncertainty (spell out what's unknown: an unfamiliar third-party integration, an unclear
requirement, a dependency on another team's unshipped work). Propose a concrete way to *reduce*
the uncertainty early — a short time-boxed spike on the riskiest unknown before committing to a
full estimate. Break the project into milestones with their own checkpoints, so the stakeholder
gets real signal on whether the project is tracking to the estimate well before the final
deadline.

**Example:**

```text
"3-5 weeks. The 2-week spread is entirely the unfamiliar payment-provider integration —
 we haven't confirmed their sandbox supports partial refunds yet. We'll spike that in
 week 1 and can tighten the estimate to +/- 2 days by end of week 1."
```

**Why it's a trap:** caving to pressure for a fake-precise single date, or refusing to estimate at
all, are both worse than a range with a named cause — the trap is treating "give me a firm date"
as a request that must be answered with a firm date, rather than reframed around what's actually
driving the uncertainty.

## 🔴 Expert / Open

### Leadership & strategy

#### Q6. You inherit a team with low morale and significant technical debt. Describe your approach for the first 90 days as tech lead.

**Answer:** Resist the urge to immediately start big rewrites or sweeping changes before
understanding why things got this way — the first weeks are primarily for listening: 1:1s with
every team member, and reviewing recent incidents/postmortems and the actual state of the codebase
directly rather than relying on secondhand narrative alone. Find one or two concrete, visible wins
achievable within the first month — not the biggest technical debt item, but something that
demonstrably reduces a real daily pain point, building trust that things can actually improve
before asking for patience on the bigger, slower structural work. In parallel, establish a small
number of concrete, lightweight practices that compound over time (a blameless postmortem process,
protected time for technical debt, clearer definition of done), and be explicit and transparent
with the team about the plan and the reasoning behind prioritization decisions. By the end of 90
days, the goal isn't that the technical debt is gone — it's that the team trusts there's a
credible, visible plan being executed.

**Example:**

```text
Weeks 1-2:  1:1s with all 6 engineers + read last 4 postmortems + skim the top 5 hottest files
Week 3:     ship one visible fix for the #1 complaint (flaky CI -> stable in 3 days)
Weeks 4-12: protected 20% time for debt, blameless postmortem template adopted,
            weekly written update on what shipped and why it was prioritized
Day 90:     debt backlog is still long, but every engineer can name what changed and why
```

**Why it's a trap:** the instinct under interview pressure is to open with a bold technical plan
(a rewrite, a new architecture) — the question is testing whether the candidate leads with
listening and a small trust-building win first, since a team with low morale won't buy into a big
plan from someone who hasn't yet earned credibility with them.

#### Q7. How do you decide between building a component yourself and buying (or adopting open source)?

Frame it as **total cost of ownership over the lifetime**, weighed against strategic value. Ask first: is this a **differentiator** — something that gives the product a competitive
advantage — or **commodity** (authentication, payments, email delivery, observability, search)? Commodity capabilities almost always favor buying or adopting: the vendor
has already spent thousands of engineer-years on edge cases, compliance (PCI, SOC 2, GDPR) and security patches, and your engineers' scarce time goes to
what only your company can build. Build when it *is* the differentiator, when no product fits the constraints (latency, data residency, unusual scale), or when vendor lock-in and pricing
at your scale would hurt more than the engineering cost. Include the full cost of each: for **build** — initial development, ongoing maintenance and on-call, security
and upgrade burden, hiring people who understand it, and the opportunity cost of what those people didn't build; for **buy** — license or usage fees that grow with volume (model the
price at 10× traffic), integration effort, **lock-in and exit cost** (data export, API differences), vendor stability, SLAs, and lost flexibility. Reduce the risk of buying by isolating the vendor behind
your own thin interface (an adapter or anti-corruption layer), keeping the data portable, and running a time-boxed proof of concept against your real requirements. Reduce the risk of building by
starting with the smallest version and re-evaluating: a homegrown component that has become a maintenance burden with no differentiating value is a signal to replace it with a product, and a
vendor whose costs or constraints now dominate is a signal to bring it in-house. Write the decision and its assumptions down (an ADR) with a date to revisit it, so the team can tell later whether the reasoning still holds.

**Example:**

```text
ADR-014: Buy transactional email (SES + thin EmailSender port) rather than build
Context:  commodity capability, 2M mails/month, 1 engineer would own it
Options:  build SMTP pipeline (~3 eng-months + on-call) | buy (~$200/mo, ~$2k/mo at 10x)
Decision: buy; vendor hidden behind EmailSender, templates stored in our repo (exit cost ~1 week)
Revisit:  2027-03 or if monthly cost > $5k
```

#### Q8. How do you run incident command during a major production outage?

**Answer:** Separate the roles so nobody both debugs and coordinates: an **incident commander** who owns decisions and does not touch the keyboard, one or more **responders** who investigate, and a **communicator** who keeps stakeholders informed.

Mitigate first (rollback, feature flag, failover), find the root cause later.

Time-box hypotheses, narrate decisions in one channel, post status updates on a fixed cadence even when there is nothing new, and write the timeline as you go so the postmortem is mostly done when the incident closes.

**Example:**

```text
#inc-2417  IC: Sam   Ops: Lea   Comms: Omar
14:02 IC: SEV1 declared - checkout 5xx at 40%. Lea: look at deploys + DB. Omar: status page in 10 min.
14:09 Lea: deploy 1.84 went out at 13:55, p99 on payments-db tripled.
14:10 IC: decision - roll back 1.84 now; we investigate after mitigation. Objections? None.
14:16 Lea: rollback done, 5xx at 2%. IC: holding SEV1 15 min to confirm.
14:20 Omar -> status page: "Checkout degraded 13:55-14:16, fixed. Next update 14:45 or on change."
```

**Why it's a trap:** candidates describe heroic debugging; the question tests whether you coordinate, mitigate before diagnosing, and communicate on a cadence.

#### Q9. How do you write an RFC or ADR so a team actually decides, rather than debating forever?

**Answer:** State the problem and constraints before the solution, list at least two real alternatives with honest costs (including "do nothing"), give a recommendation, and set a decision deadline and a named decider.

Keep it short (1-2 pages), circulate it for async comments first, and use the meeting only for unresolved points. Record the decision and the reasons it could be revisited, so future readers understand it was a judgment call under known assumptions.

**Example:**

```text
RFC-07: Move session storage from DB to Redis      Decider: Dana   Decide by: Fri 12th
Problem:      session reads are 38% of primary DB load; login p95 = 900 ms at peak
Options:      A) do nothing (add a read replica, ~$900/mo, buys ~6 months)
              B) Redis (new infra, ~2 weeks, p95 target < 150 ms)
              C) signed JWTs (no store, but no server-side revocation)
Recommend:    B. Risk: Redis outage logs everyone out -> mitigated by replica + 30 s grace.
Open points:  session TTL; who is on-call for Redis?
```

**Why it's a trap:** a long document with one option and no decider is a design announcement, not a decision tool.

#### Q10. How do you structure hiring and interviewing so decisions are consistent and fair?

**Answer:** Define the level and the signals you need before interviewing (e.g. debugging, design trade-offs, collaboration), give each interviewer one signal to probe, use the same questions and a written rubric for every candidate, and have interviewers submit written feedback *before* the debrief so the loudest voice doesn't anchor the group.

Evidence ("she identified the race condition unprompted") beats impression ("seems smart"). Treat the candidate experience as part of the job: clear schedule, timely answer.

**Example:**

```text
Rubric - Senior backend, "debugging" signal (1 = no signal, 4 = strong)
 1  needs hints for each step         3  forms hypotheses, narrows with logs/metrics
 2  guesses, changes many things      4  also proposes the prevention (alert, test)
Feedback form: score + 2 concrete observations + "would I be happy to have them on my team? why"
Debrief: read all forms silently (5 min) -> each states score first -> discuss only disagreements
```

**Why it's a trap:** "I go with my gut" is the answer that signals inconsistency and bias.

#### Q11. How do you delegate well, and how do you say no without damaging the relationship?

**Answer:** Delegate the outcome, not the steps: state the goal, the constraints, the decision rights, and the checkpoints, then let the person choose the approach. Match the task to a growth edge but keep a safety net (a mid-way review).

When saying no, acknowledge the goal behind the request, give the trade-off in concrete terms (what slips if we say yes), and offer an alternative or a later date. A no with a reason and an option is a negotiation, not a refusal.

**Example:**

```text
Delegation:  "Own the migration of the billing export to the new queue. Done = zero lost
              invoices in a 1-week shadow run. You decide the rollout; ping me before cutover.
              Checkpoint Thursday: design in 1 page."
Saying no:   "I can't take the dashboard request this sprint without dropping the SSO fix, which
              blocks 3 customers. I can do a basic version next sprint, or start now if
              you tell me which one yields."
```

**Why it's a trap:** "I'd just do it myself" (can't delegate) and "I'd say yes and work nights" (can't say no) are both failure modes the interviewer is probing.

#### Q12. How do you onboard a new engineer so they are productive quickly?

**Answer:** Prepare before day one: laptop, access, a buddy, a written plan. Aim for a small real change in production within the first week (builds confidence and validates the setup), then widen scope progressively. Provide context, not only tasks: architecture overview, who owns what, why key decisions were made. Hold regular 1:1s, collect feedback on onboarding itself, and fix the docs every time a newcomer stumbles.

**Example:**

```text
Day 1   laptop + access ready, meet buddy, run the app locally
Week 1  ship a small ticket to production (typo/log/flag), read 3 key ADRs
Day 30  owns a small feature end to end, has shadowed one on-call shift
Day 60  reviews PRs in one area, first solo on-call with a buddy on standby
Day 90  retro with manager: what was unclear? -> 3 doc fixes merged by the newcomer
```

**Why it's a trap:** "give them the docs and let them read" ignores that the best signal of a healthy team is how fast a newcomer ships something real.

#### Q13. How do you manage up: keeping your manager informed and aligned without surprises?

**Answer:** Agree on priorities and success criteria explicitly, then communicate proactively: bad news early with a proposed plan, progress on a regular cadence, decisions needed with a deadline. Frame things in terms of outcomes and risk, not activity. Ask what your manager is being measured on so your work maps to it. The goal is that your manager is never surprised by something they could have learned from you.

**Example:**

```text
Weekly update (5 lines):
Done:    payments retry shipped, failed charges -18%
Next:    SSO migration (starts Mon)
Risk:    vendor sandbox flaky -> may add 3 days; I'll confirm Wednesday
Need:    decision by Thu: drop legacy CSV export or keep (cost: 4 days)
Help:    intro to the security team for the pen-test slot
```

**Why it's a trap:** "I just do good work and they see it" leaves the manager blind; the senior move is to make progress and risk visible.

#### Q14. How do you measure whether your team is delivering well, without turning metrics into targets?

**Answer:** Use the four **DORA metrics** as a system-level view: deployment frequency, lead time for changes, change failure rate, and time to restore service. They balance speed against stability, so improving one at the cost of the other shows up.

Read them as trends for the team and the delivery system, never per person, and pair them with qualitative signals: developer experience surveys (the SPACE framework), on-call load, and how often the team hits the commitments it made.

Use them to find bottlenecks ("lead time is 9 days, 6 of them waiting for review"), not to rank people. Once a number becomes a target, people optimize the number (splitting PRs to raise deploy counts), so discuss the story behind it in retros.

**Example:**

```text
Quarter        Deploys/week  Lead time  Change failure  Restore
Q1             3             9 days     22%             5 h
Q2 (actions: review SLA 1 day, feature flags, smaller PRs, canary)
               11            2 days     9%              40 min
```

**Why it's a trap:** comparing teams or individuals on DORA numbers rewards gaming and punishes teams with harder systems; the useful comparison is a team against its own past.

#### Q15. How do you prioritise technical debt against product work?

**Answer:** Make debt visible and costed in business terms, then trade it like any other work.

Keep a short debt register where each item says what it costs today (incidents, slower delivery in that area, onboarding time, security or upgrade risk) and what fixing it would unlock.

Prioritise by **cost of delay × how often the area changes**: debt in code nobody touches can wait; debt in the checkout module the team changes weekly can't.

Combine a standing capacity (often 15–20% per sprint) for small continuous fixes with explicit roadmap items for large ones, presented with a business case.

Fix opportunistically when a feature touches the code ("leave it better"), and set guardrails (lint, ArchUnit, dependency updates) so new debt doesn't accumulate.

**Example:**

```text
Item                         Pain today                         Change freq.  Proposal
Legacy pricing module        3 incidents/qtr, features take 2x  weekly        Q3 roadmap: strangler, 4 weeks
Spring Boot 2 -> 3           EOL, CVEs unpatched                 n/a           Must-do, 2 sprints, date fixed
Old admin UI (jQuery)        ugly, but stable                   twice a year  Leave; revisit if it changes
```

**Why it's a trap:** asking for "a refactoring sprint" without numbers sounds like engineers wanting to polish code, and it loses to any feature; the same work framed as "cut checkout incidents and halve lead time on pricing" usually gets approved.

#### Q16. How do you run a retrospective that leads to change?

**Answer:** Keep it safe and blameless: the facilitator states the goal (improve how we work, not judge people) and makes sure quiet people are heard, for example with silent writing before discussion.

Start with data: what happened in the sprint or incident, metrics, timeline. Group the topics, vote, and spend most of the time on the one or two that matter, digging into causes.

End with **few, concrete actions** with an owner and a date, and start the next retro by reviewing them.

Vary the format occasionally (start/stop/continue, 4Ls, timeline) to avoid routine, and escalate issues the team can't fix itself instead of discussing them every time.

**Example:**

```text
Topic (5 votes): "releases slip because QA starts on day 9"
Cause: stories too big to test before the end of the sprint
Action: split stories so each is testable in ≤ 2 days; Sam owns the refinement checklist; review at next retro
```

**Why it's a trap:** a retro that produces ten vague actions ("communicate better") and never checks them teaches the team that retros don't change anything, and people stop speaking up.

## 🎯 Real-world scenarios

### S1. A design review between two senior engineers stalls a project for weeks with no resolution

- **Symptoms:** Two senior engineers have strongly held, opposing views on a core architectural
  decision, and repeated review meetings fail to converge — the project's timeline is slipping
  while the disagreement continues.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** As the tech lead reviewing this, check whether the disagreement is actually about
  a knowable technical fact (resolvable with a spike/benchmark) or an unstated difference in what
  each person is optimizing for (Q4) — a stalled disagreement often persists specifically because
  neither side has identified that they're arguing from different, unstated priorities.
- **Example:**

  ```text
  Week 1: review meeting -> no resolution, "let's discuss again next week"
  Week 2: same two positions restated, no new information surfaced
  Week 3: project owner asks each engineer to write down what their approach optimizes
          for -> reveals a genuine time-to-ship vs. long-term-flexibility trade-off, not a
          resolvable factual disagreement -> tech lead makes the call the same day
  ```

- **Resolution:** Facilitate a conversation that makes both positions' actual trade-offs explicit
  and comparable, get any resolvable factual question answered directly, and if it's genuinely a
  judgment call with no objectively right answer, make the call explicitly as the decision-owner.
- **Prevention:** Establish a clear decision-making process (who has final say, and under what
  circumstances a time-boxed spike settles a disagreement) before a project starts, so a genuine
  disagreement has a known path to resolution rather than defaulting to indefinite debate.

</details>

### S2. A junior engineer's PRs keep repeating the same category of mistake despite review comments

- **Symptoms:** Code review comments correctly identify the same class of issue across several
  consecutive PRs from the same engineer, each time fixed individually but recurring in the next
  PR.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Per Q2 — the review comments are correcting instances, not building the
  underlying judgment that would prevent the *next* instance; a pattern of recurrence despite
  repeated correct feedback usually means the "why" hasn't actually landed, not that the person
  isn't listening.
- **Example:**

  ```text
  PR #212 review comment: "missing null check here"
  PR #219 review comment: "same issue as #212 — missing null check"
  PR #227 review comment: "third time — let's talk"  <- direct 1:1 held after this, not #212
  ```

- **Resolution:** Have the direct, principle-focused conversation from Q2 rather than another PR
  comment — walk through several real examples together, have them explain the underlying
  principle back in their own words, and agree on a concrete forward practice.
- **Prevention:** For any category of mistake appearing more than twice from the same person,
  switch from PR comments to a direct conversation proactively, rather than waiting for it to
  become an obviously entrenched pattern.

</details>

### S3. Team morale visibly drops after a layoff or reorg, and productivity/trust suffer

- **Symptoms:** Remaining team members show reduced engagement, increased skepticism toward
  leadership communication, and a noticeable slowdown in delivery beyond what headcount reduction
  alone would explain.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Trust erosion after a layoff/reorg is a normal, expected response, not a
  discipline problem — people are processing uncertainty about their own security and grieving
  colleagues/working relationships that changed.
- **Example:**

  ```text
  Before reorg: sprint velocity ~40 pts, Slack activity in #team normal
  2 weeks after: velocity ~22 pts, 1:1s reveal 4/6 remaining engineers are job-searching,
                 standup updates get noticeably shorter and less detailed
  ```

- **Resolution:** Over-communicate, honestly, more than feels necessary — acknowledge what
  happened directly, be transparent about what is and isn't known about the future, and rebuild
  predictability through consistent, smaller commitments kept reliably, rather than one large
  gesture to "fix" morale.
- **Prevention:** This is largely not preventable at the individual-manager level once a
  layoff/reorg decision is made above them, but a manager's own consistent, honest communication
  pattern *before* any such event is what determines how much residual trust there is to rebuild
  from.

</details>

### S4. A stakeholder demands an unrealistic deadline for a complex feature

- **Symptoms:** A stakeholder states a hard deadline for a feature the engineering team assesses
  as requiring meaningfully more time than that, with the deadline apparently non-negotiable from
  the stakeholder's framing.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Before assuming the deadline itself is the immovable constraint, clarify what's
  actually driving it (a real external commitment versus an internally chosen target that's more
  flexible than it sounds) and separately clarify whether the *scope* is truly fixed.
- **Example:**

  ```text
  Stakeholder: "This needs to ship by the 30th, no exceptions — it's tied to a partner launch."
  Follow-up: "Is the 30th the partner's hard date, or our internal target for it?"
  Answer: "...it's actually our target, the partner's real cutoff is 6 weeks later."
  -> the "non-negotiable" deadline had 6 weeks of hidden slack once actually asked about.
  ```

- **Resolution:** Present the actual trade-off explicitly — "here's what fits by that date, here's
  what would need to move to a follow-up, here's the risk if we compress it instead" — and let the
  stakeholder make an informed decision, using Q5's estimation-under-uncertainty approach if the
  scope itself is still unclear.
- **Prevention:** Build a working relationship with recurring stakeholders where scope and
  timeline trade-offs are a normal, expected part of the conversation from the start of any
  project, rather than the first such conversation happening under deadline pressure.

</details>

### S5. Two team members are in ongoing conflict over code ownership or technical approach

- **Symptoms:** Repeated friction in reviews or planning between two specific team members,
  escalating beyond normal technical disagreement into a personal or territorial dynamic that's
  starting to affect the wider team's dynamics.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Distinguish a genuine, resolvable technical disagreement (Q4's territory) from a
  relationship/communication breakdown that happens to be expressed through technical
  disagreements — the second needs a different intervention than more technical discussion.
- **Example:**

  ```text
  Reviewer A (1:1): "I keep getting blocked because B rewrites my PRs in review instead of
                      commenting."
  Reviewer B (1:1): "A's code doesn't follow the patterns we agreed on, so I just fix it
                      myself to keep things moving."
  -> both are reacting to a missing shared review norm, not to each other personally.
  ```

- **Resolution:** Have separate 1:1 conversations with each person first, then, if appropriate, a
  facilitated joint conversation focused on working relationship and communication norms going
  forward, not relitigating the specific technical disagreements that triggered it.
- **Prevention:** Address friction early, at the first sign of a pattern rather than after it's
  visibly affecting the broader team — a private, low-stakes conversation early is far easier than
  a larger mediation after weeks of accumulated friction.

</details>

### S6. A production incident traces back to an architectural decision you personally made

- **Symptoms:** A postmortem investigation identifies the root cause as a specific design choice
  you advocated for and made, not an unrelated bug or an outside factor.
- **Diagnosis/reflection:** This is a moment where how you handle it matters as much as the
  technical fix — minimizing your own role, or conversely over-apologizing in a way that derails
  the postmortem's actual purpose, are both less useful than a clear, factual account of the
  decision and what's different now that makes the outcome visible.
- **Example:**

  ```text
  Postmortem timeline entry, written by the decision-maker themselves:
  "2026-02-11: I chose async replication for the orders DB to hit the launch date,
   accepting the RPO trade-off documented in ADR-014. That trade-off is what caused
   today's data loss on failover. The information available in Feb didn't include our
   current write volume."
  ```

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Resolution:** Own the decision plainly without deflecting blame elsewhere, focus the
  discussion on the blameless postmortem's actual goal (what systemic factor allowed this outcome,
  and what changes reduce the chance of a similar mistake from anyone in the future), and follow
  through visibly on the agreed action items.
- **Prevention:** A team that's watched their tech lead handle their own mistake this way builds
  far more trust in the blameless postmortem process than one that's only seen it applied to
  others — this specific moment is disproportionately influential in whether the team actually
  believes the process is blameless in practice.

</details>

### S7. An on-call rotation drowns in non-actionable pages, and the team stops trusting alerts enough to react quickly to a real one

- **Symptoms:** The on-call rotation receives dozens of pages a week, the large majority of which
  resolve themselves or require no action; engineers report muting or delaying pages, and a
  genuinely critical incident recently went unacknowledged for 20+ minutes because it looked like
  routine noise.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Pull the last month of pages and categorize each as actionable (required a human
  response) vs. non-actionable (self-resolved, flapping, or symptomatic of a known, already-tracked
  issue) — a high non-actionable ratio is the direct cause of the desensitization, not a discipline
  problem with whoever's on call.
- **Example:**

  ```text
  Last 30 days: 214 pages fired
    - 6   required actual human intervention
    - 91  self-resolved within 2 minutes (flapping health check, no action needed)
    - 117 duplicate/downstream alerts for one root-cause incident, firing separately
  -> signal-to-noise ratio ~2.8%, and the one incident that mattered was buried in it
  ```

- **Resolution:** Re-tune alert thresholds against actual actionability, add alert deduplication/
  grouping so one root cause fires one page instead of many, and delete or downgrade-to-
  non-paging any alert that hasn't required action in the review window.
- **Prevention:** Review paging alerts against actual actionability on a recurring cadence, and
  treat "did this page require a human to actually do something" as the bar for keeping it as a
  page at all, rather than a ticket or a dashboard metric.

*See also:* [Full Stack S22](fullstack-devops-k8s.md) for the technical side: SLO-based, symptom-first alerts.

</details>

### S8. A team member consistently responds defensively to code review feedback, regardless of how it's delivered

- **Symptoms:** Reasonable, well-phrased review feedback is repeatedly met with pushback,
  justification, or visible frustration from one specific team member, even when the feedback is
  factually correct and delivered constructively by multiple different reviewers.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Consistent defensiveness across multiple reviewers and multiple delivery styles
  suggests the issue isn't really about how feedback is phrased — it's more likely about how the
  person experiences feedback generally.
- **Example:**

  ```text
  Reviewer A: "consider extracting this into a helper" -> pushback + justification thread
  Reviewer B: "nit: this could be simplified" -> same pattern, different reviewer, same person
  Reviewer C (different team, first time reviewing this person): same pattern again
  -> consistent across reviewers and phrasing rules out "it's how it's being said."
  ```

- **Resolution:** Have a direct, private, curious (not accusatory) conversation specifically about
  the pattern itself, separate from any specific PR, and separately, make sure the team's review
  culture itself isn't inadvertently contributing.
- **Prevention:** Establish clear, shared review norms and expectations across the team early, so
  an individual's reaction to feedback is more likely to be about the specific content than an
  ambiguous or inconsistently-applied standard.

</details>

### S9. A cross-team dependency repeatedly blocks your team's delivery

- **Symptoms:** Your team's roadmap keeps slipping because a required piece of work from another
  team isn't ready when needed, recurring across multiple projects rather than a one-off
  scheduling miss.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** A recurring pattern suggests a structural issue — priorities aren't actually
  aligned between the teams, or there's no clear process for negotiating and committing to
  cross-team work items with any real accountability.
- **Example:**

  ```text
  Project Alpha: slipped 3 weeks waiting on Team Y's export API
  Project Beta (2 months later): slipped 2 weeks waiting on the same Team Y, different API
  -> a recurring pattern with the same team, not a one-off scheduling miss
  ```

- **Resolution:** Escalate to make the dependency and its business impact visible at a level where
  both teams' priorities can actually be reconciled, bringing concrete, quantified impact rather
  than a vague "we're blocked" complaint.
- **Prevention:** For known, recurring cross-team dependencies, establish an explicit
  prioritization/commitment process before the next project needs it, rather than informal asks
  that have no real mechanism for being honored under competing priorities.

</details>

### S10. Sunsetting a legacy system that many teams still depend on proves far harder than expected

- **Symptoms:** A planned deprecation of an old system stalls repeatedly — teams keep having "just
  one more" dependency that isn't ready to migrate, and the sunset date keeps slipping.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The plan likely underestimated the actual scope of dependents and/or didn't give
  dependent teams sufficient incentive or support to actually prioritize their migration work over
  their own roadmap pressures.
- **Example:**

  ```text
  known dependents at planning time: 4 services
  actual dependents discovered mid-migration: 11 services, including one found only
  because it started throwing errors the week the legacy write path was deprecated
  ```

- **Resolution:** Do a genuinely thorough dependency audit before committing to a hard date,
  provide concrete migration support (tooling, documentation, direct engineering help for the
  highest-friction migrations), and consider a staged sunset that surfaces forgotten dependents
  earlier and less catastrophically.
- **Prevention:** For any future system expected to have broad internal adoption, build in
  deprecation/migration tooling and dependency tracking from early in its life, not as an
  afterthought once sunsetting becomes necessary years later.

</details>

### S11. As an interviewer, you need to evaluate a candidate's system design answer fairly

- **Symptoms:** A candidate produces a design with a reasonable-looking diagram, but you need to
  assess whether it actually reflects strong system design judgment versus memorized, template
  answers that don't demonstrate real understanding.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The strongest signal isn't whether they drew the "right" diagram — it's whether
  they asked clarifying questions before designing ([System Design Q1](system-design.md)), whether they can articulate the actual
  trade-off behind each significant decision, and whether they can go deep on at least one
  component when pushed.
- **Example:**

  ```text
  Candidate proposes fan-out-on-write for the whole feed design, no mention of celebrity
  accounts. Interviewer: "This account has 50M followers — walk me through what happens
  when they post."
  Strong candidate: adapts live, proposes the fan-out-on-read special case ([System Design Q42](system-design.md)).
  Weak candidate: repeats the original design unchanged, doesn't register the new constraint.
  ```

- **Resolution:** Push on trade-offs specifically ("why this and not X") rather than accepting a
  stated design at face value, and introduce a changed constraint mid-interview to see whether
  they can adapt their design and reasoning live.
- **Prevention:** Calibrate interviewer expectations and rubrics around trade-off reasoning and
  adaptability specifically, not diagram completeness or matching a specific "correct" reference
  architecture.

</details>

### S12. Product wants features only; engineering says the tech debt is slowing everyone down — and leadership won't fund cleanup

- **Symptoms:** Lead time per feature has doubled in a year, incidents recur in the same legacy module, and the best engineers grumble about "the
  billing code". Every request for a "refactoring sprint" is turned down as an unquantified cost with no customer value.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The problem is usually **communication and prioritization**, not a lack of goodwill: debt is described in engineering terms ("it's messy") that
  the business cannot weigh against features. Gather evidence: how much of each sprint goes to rework and bug fixes in that module, cycle time and change-failure rate before and
  after, incident count and cost attributable to it, onboarding time, and the features it has *blocked or delayed*. Identify which debt has interest (in the path of upcoming roadmap
  work) versus debt that is ugly but stable and can be left alone (Q6's 90-day approach).
- **Example:**

  ```text
  Billing module, last 2 quarters:
    31% of bug tickets, 4 of 6 Sev-2 incidents, median PR lead time 9 days (vs 2 days elsewhere)
    Q3 roadmap: 3 of 5 planned features touch it  ->  estimated 6 weeks of extra work if untouched
  ```

- **Resolution:** Present it as a business case: cost of delay and risk versus a bounded investment ("3 weeks now saves ~6 weeks in Q3 and removes the main
  source of Sev-2s"). Propose an incremental approach that keeps shipping — refactor *as part of* the roadmap features that touch the area, protect a fixed capacity
  share (10–20%) for debt with agreed metrics, or a strangler approach — rather than a big-bang "stop features for a quarter". Agree on success measures and review them.
- **Prevention:** Track debt explicitly (a visible register with impact and cost of delay), make quality metrics part of regular product reviews, apply the "boy scout" rule
  in day-to-day work, and keep engineering leaders and product in a standing conversation about capacity allocation rather than a crisis-time negotiation.

</details>

### S13. An engineer's output and quality have dropped over several months, and the team notices

- **Symptoms:** A previously reliable engineer now misses commitments, PRs are late and low-effort, they are quieter in meetings, and colleagues quietly start
  routing around them. No one has raised it directly.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Don't assume "performance problem" — first find out **what changed**: the person's work (a mismatch of role or skill, unclear expectations, an
  unwanted project), the environment (a reorg, a new manager, unclear priorities, a toxic dynamic, blocked by other teams) or their life (health, burnout, family). Have a
  private, curious one-to-one (before any formal process) asking open questions and looking at facts: specific examples of missed expectations, how they got there, whether goals were clear, whether
  the workload is realistic. Compare against the expectations the person was actually given, not an unstated bar.
- **Example:**

  ```text
  1:1 opening: "I've noticed the last three deliverables slipped and you seem less engaged than usual.
                I want to understand what's going on and how I can help - what's your view?"
  -> reveals: moved to a legacy project against their wishes + no clear ownership since the reorg
  ```

- **Resolution:** Depending on the cause: clarify expectations and ownership in writing, remove blockers, adjust the work or give support (time off, reduced load
  if it is a personal situation, coaching or pairing for a skill gap), and agree on **specific, measurable goals with a check-in cadence** (e.g. weekly for 4–6 weeks). Document the conversations. If
  there is no improvement despite clear expectations and real support, involve HR/the manager and move to a formal improvement plan — with dignity, and with honest communication about the possible outcomes. Verify
  progress against the agreed goals, not impressions.
- **Prevention:** Regular 1:1s and early, specific feedback so problems surface in weeks, not quarters; explicit expectations per level; watch for burnout signals; and address the issue directly instead of letting
  the team compensate silently, which erodes the trust of everyone else.

</details>

## 🗣️ Behavioral (STAR)

> Behavioral questions ("Tell me about a time when…") test judgment, ownership and communication through *past* behavior. Every model answer below is structured with the **STAR** method. Technical-leadership scenarios live in [Leadership](leadership-behavioral.md).

### ⭐ The STAR method

| Letter | Part | Share of the answer | What to say |
|--------|------|---------------------|-------------|
| **S** | Situation | ~10% | Context in 1–2 sentences: team, system, stakes. |
| **T** | Task | ~10% | *Your* responsibility or goal — what you were accountable for. |
| **A** | Action | ~60% | What **you** did, step by step, and why. Use "I", not "we". |
| **R** | Result | ~20% | Measurable outcome + what you learned / would do differently. |

```text
S: "Our checkout API p95 hit 2.4 s during the Black Friday ramp-up."
T: "As the service owner I had 3 days to get it under 800 ms without a rewrite."
A: "I profiled with async-profiler, found an N+1 in the order mapper, added a fetch join,
    a Redis cache for the price list, and a load test in CI to prevent regressions."
R: "p95 went to 420 ms, zero incidents on the day, and the load test caught two later regressions."
```

**Rules of thumb**

- Prepare a **story bank** of 6–8 real stories (see the [cheat-sheet](#cheat-sheet)); each one can answer several questions.
- **Quantify** results (latency, cost, incidents, time saved, team size).
- Keep it to **2 minutes**; let the interviewer dig in.
- Failures are fine — a story with no learning is not.
- Never invent: follow-up questions will expose it.

### 🟢 Fundamentals

#### Self-presentation

#### B1. Tell me about yourself.

**Why they ask:** to see if you can summarize your career into a coherent, relevant narrative.

- **S** — Present: "I'm a senior full-stack engineer with 8 years of experience, mostly Java/Spring Boot backends and React frontends on Kubernetes."
- **T** — Past focus: what you were responsible for in your last role (e.g. owning the payments platform for 5 squads).
- **A** — Key milestones: 2–3 achievements that match the job (migration to event-driven architecture, mentoring, on-call reduction).
- **R** — Future: why this role is the logical next step.

**Pitfall:** reciting your CV chronologically for 5 minutes. Use *present → past → future* and stay under 90 seconds.

#### B2. Tell me about an achievement you are particularly proud of.

**Why they ask:** what you value, and the scale of impact you operate at.

- **S** — Legacy monolith, nightly batch taking 7 h and regularly failing, blocking the finance team's morning reports.
- **T** — I volunteered to make the batch reliable and under 1 h.
- **A** — I split it into idempotent chunks, moved the heavy aggregations to PostgreSQL window functions, parallelized with virtual threads, and added metrics and an alert on lag.
- **R** — Runtime dropped from 7 h to 38 min, failures went from ~3/month to 0 over 6 months, and the pattern was reused by two other teams.

**Pitfall:** picking an achievement with no measurable result, or saying "we" throughout so your own part is invisible.

#### B3. What are your greatest strengths and weaknesses?

**Why they ask:** self-awareness and whether you actively improve.

- **S** — Strength: I break ambiguous problems into shippable increments. Weakness: I used to take on too much myself instead of delegating.
- **T** — Demonstrate the strength with a case; show a weakness that was *real* but *addressed*.
- **A** — Strength example: turned a vague "make search faster" into 3 measurable steps, delivered the first in a week. Weakness: I now write down what I can delegate each sprint, pair with the owner, and review outcomes rather than code line by line.
- **R** — Search latency −60% in 3 sprints; two teammates now own components I used to maintain alone.

**Pitfall:** "I'm a perfectionist" or a weakness that disqualifies you for the role.

#### B4. Why do you want to work here?

**Why they ask:** motivation, research, and fit.

- **S** — What you found: product, engineering blog, tech stack, scale problems.
- **T** — Connect it to what you want to grow into.
- **A** — Name 2 specific things (e.g. "your move to multi-region Kafka" and "your engineering ladder") and tie them to past experience.
- **R** — Say what you would bring in the first 6 months.

**Pitfall:** generic praise ("great company") or only talking about salary/remote.

#### B5. Why do you want to work in healthcare (or for a company like Doctolib)?

**Why they ask:** motivation that survives hard days, and whether you understand the domain's stakes (patient data, availability, trust).

- **S** — Your story starts with a concrete, personal link to the mission (a relative who waited weeks for an appointment, a project where your software had real users who depended on it).
- **T** — Explain why *this* kind of problem, not just "a good company".
- **A** — Connect your experience to the work: reliability matters more when a failure means a missed consultation, privacy is a design constraint (GDPR, health-data hosting), and scale is real (millions of appointments). Mention what you researched: the product, the engineering blog, the stack.
- **R** — Close with what you want to contribute and learn, e.g. "I want my work to measurably reduce the time people wait for care."

**Pitfall:** generic answers ("great culture", "innovative") or flattery that could apply to any company. Another trap is ignoring the constraints: showing enthusiasm without acknowledging compliance and data sensitivity sounds naive.

*See also:* [Security Q19](security.md) for what protecting health data means technically, and [Behavioral B4](leadership-behavioral.md) for the generic version of this question.

### 🟡 Senior traps

#### Failure and feedback

#### B6. Tell me about a time you made a significant mistake.

**Why they ask:** accountability, honesty, and whether you turn mistakes into systems improvements.

- **S** — I shipped a Flyway migration adding a `NOT NULL` column with a default on a 200M-row table; it locked writes for 9 minutes in production.
- **T** — As the author, I owned the incident: restore service, then make sure it could not happen again.
- **A** — I rolled back, communicated status every 10 minutes, wrote a blameless postmortem, and introduced a migration checklist (online-safe patterns, `CONCURRENTLY`, batch backfills) plus a CI job running migrations on a prod-sized snapshot.
- **R** — Outage ended in 9 min; no migration-related incident in the following 12 months, and the CI check caught 3 unsafe migrations from others.

**Pitfall:** a fake failure ("I worked too hard") or blaming others/tools. Own it in the first sentence.

#### B7. Tell me about a time you received tough feedback. How did you react?

**Why they ask:** coachability and ego.

- **S** — My tech lead told me my PRs were too large and hard to review, slowing the team.
- **T** — Change my way of working without losing delivery speed.
- **A** — I asked for concrete examples, then adopted stacked PRs under 400 lines, added a PR description template (context, risk, test plan), and asked the reviewer for a follow-up after a month.
- **R** — Average review time dropped from 2 days to 5 hours; the lead later asked me to share the approach with the team.

**Pitfall:** getting defensive, or choosing "feedback" that is really a compliment in disguise.

#### Conflict and influence

#### B8. Describe a conflict with a colleague and how you resolved it.

**Why they ask:** emotional intelligence; do you escalate, avoid, or resolve?

- **S** — A backend peer and I disagreed on API versioning: they wanted breaking changes in `v1`, I needed stability for the mobile app.
- **T** — Reach a decision quickly without damaging the relationship.
- **A** — I proposed a 30-min call, first restated their constraints (delivery pressure), then showed data on mobile adoption (35% of users on old versions). We agreed on additive changes plus a deprecation window, and wrote it as an ADR.
- **R** — No forced app update, the feature shipped on time, and we reused the ADR template for later API decisions.

**Pitfall:** a story where you were simply right and the other person wrong. Show empathy and a compromise based on data.

#### B9. Tell me about a time you disagreed with your manager.

**Why they ask:** do you speak up respectfully, and do you commit once the decision is made?

- **S** — My manager wanted to ship a feature without load testing to hit a client demo date.
- **T** — Raise the risk without blocking the business goal.
- **A** — I estimated the failure cost (demo at 10× the usual traffic), proposed a 1-day reduced load test on the critical path only, and offered to cut a non-essential screen to pay for it.
- **R** — Test revealed a connection-pool limit that would have crashed the demo; fixed in 2 hours. My manager now asks for the same "minimum viable test" on deadlines.

**Pitfall:** "disagree and commit" without showing the disagreement, or the opposite: refusing to commit afterward.

*Method:* [Leadership Q3](leadership-behavioral.md) covers how to push back on a senior stakeholder; this question asks for the story.

#### B10. Tell me about a time you worked under tight deadline or pressure.

**Why they ask:** prioritization and composure.

- **S** — A regulatory change required a new KYC flow live in 3 weeks; the estimate was 6.
- **T** — As tech lead, deliver the compliant minimum on time.
- **A** — I split scope into *must* (legal) and *nice*, got sign-off from product, feature-flagged the rest, set daily 15-min syncs, and cut review latency by pairing on risky parts.
- **R** — Shipped in 19 days with 0 critical bugs; deferred features followed in the next sprint.

**Pitfall:** heroics (all-nighters) as the main action. Seniors reduce scope and risk instead.

#### B11. Tell me about a time you had to work with an unclear or changing requirement.

**Why they ask:** comfort with ambiguity.

- **S** — Product asked for "a better reporting dashboard" with no definition of "better".
- **T** — Turn ambiguity into a clear, testable scope.
- **A** — I interviewed 5 users, prototyped 2 layouts in a day, agreed on 3 success metrics (time to find a report, export usage, support tickets), and shipped an MVP behind a flag.
- **R** — Support tickets on reports −40%; two of the "must-have" requests turned out unnecessary, saving ~3 weeks.

**Pitfall:** waiting for perfect requirements, or building a lot before validating.

### 🔴 Expert / Open

#### B12. Tell me about a time you influenced a decision without having authority.

**Why they ask:** staff-level impact across teams.

- **S** — Four teams used four different logging formats, making cross-service tracing painful during incidents.
- **T** — Standardize without being anyone's manager.
- **A** — I measured the pain (MTTR of last 5 incidents), wrote a short RFC with a working prototype (OpenTelemetry + a shared Spring starter), presented to each team's lead, and offered to do the migration PR for the first two teams.
- **R** — 4/4 teams adopted it within a quarter; MTTR on cross-service incidents dropped from ~70 to ~25 min.

**Pitfall:** "I convinced them" with no mechanism. Show data, a prototype, and lowered adoption cost.

*Method:* [Leadership Q3](leadership-behavioral.md) covers influence without authority; this question asks for the story.

#### B13. Tell me about a time you drove a major technical change.

**Why they ask:** vision, risk management and execution at scale.

- **S** — A monolith deployed once a month, with 1 release in 4 rolled back.
- **T** — Lead the move to independent deployable services and CI/CD with a small team.
- **A** — Chose the strangler pattern, extracted the highest-churn module first, introduced contract tests and canary releases, ran weekly demos for stakeholders, and documented decisions as ADRs.
- **R** — Deploy frequency from monthly to daily for the extracted service, rollback rate from 25% to <5%, and the roadmap was adopted for 3 more modules.

**Pitfall:** a big-bang rewrite story; interviewers look for incremental, reversible steps.

#### B14. Tell me about a time you improved code quality in your team.

**Why they ask:** whether you raise the bar through influence and habits rather than lectures or heroics.

- **S** — Our service had flaky tests, 40-minute reviews and a recurring class of regressions around date handling.
- **T** — Improve quality measurably without freezing feature work or blaming anyone.
- **A** — I measured first (flaky-test rate, escaped bugs, review time), proposed two small changes the team agreed on (a PR template with a test checklist, a shared date utility with tests), automated what could be (static analysis and a formatter in CI so reviews focus on design), quarantined flaky tests with an owner and a deadline, and held a monthly 30-minute "bug review" to learn from escapes.
- **R** — Flaky tests fell from 12% to under 2%, median review time dropped to 15 minutes, and date-related regressions stopped for two quarters. The practices outlived my involvement.

**Pitfall:** a solo crusade ("I rewrote it all") or a vague answer without numbers. Quality improvements that the team did not adopt are not an achievement.

*See also:* [Testing Q18](testing.md) for quality gates in the pipeline, and [Behavioral B20](leadership-behavioral.md) on quality versus speed.

#### B15. Tell me about a time you mentored or helped a struggling teammate.

**Why they ask:** multiplier effect and patience.

- **S** — A junior engineer missed estimates by 2× for two sprints and lost confidence.
- **T** — Help them become autonomous without taking over their tasks.
- **A** — I paired twice a week, taught them to split tasks to ≤1 day, introduced a daily checkpoint, and gave feedback on *how* they investigated rather than fixing the code myself.
- **R** — Their estimates were within 20% after 6 weeks and they handled their first on-call alone in month 3.

**Pitfall:** describing yourself as the hero who fixed everything. The result must be *their* growth.

*Method:* [Leadership Q1](leadership-behavioral.md) and [Leadership S2](leadership-behavioral.md) cover effective mentoring; this question asks for the story.

#### B16. Tell me about a decision you made with incomplete information.

**Why they ask:** judgment under uncertainty and reversibility.

- **S** — We had to pick a message broker in 2 weeks, with unclear throughput forecasts.
- **T** — Decide without over-investing or locking the company in.
- **A** — I classified the decision as *reversible with a cost*, ran a 3-day spike on Kafka vs RabbitMQ with a realistic load profile, hid the broker behind an interface, and wrote an ADR with explicit review triggers.
- **R** — Chose Kafka; 8 months later volume was 5× the forecast and no change was needed. The ADR trigger was never hit.

**Pitfall:** pretending you were certain. Show how you reduced uncertainty and limited the blast radius.

#### B17. Tell me about a time you made sure your work delivered real value to users.

**Why they ask:** whether you care about outcomes, not just shipped tickets.

- **S** — We were asked to build a self-service export for clinic admins; the spec described a full reporting module.
- **T** — Deliver what users actually needed, early, and prove it worked.
- **A** — I talked to three admins before building and found 90% of the need was one monthly CSV. We shipped that in a week behind a feature flag, instrumented usage (exports per week, failures, time to complete), and iterated from the data instead of the original spec.
- **R** — Support tickets on the topic fell by 60%, adoption reached 70% of clinics in a month, and we skipped two months of reporting work nobody would have used.

**Pitfall:** describing delivery ("we shipped on time") without any evidence of impact. Say how you measured value, and what you chose *not* to build.

*See also:* [Full Stack Q8](fullstack-devops-k8s.md) on measuring what users experience.

#### B18. Tell me about a production incident you investigated.

**Why they ask:** calm, method and learning under pressure, plus honesty about your own part.

- **S** — Latency alerts fired on the booking API at 14:10 and error rates climbed to 8%.
- **T** — Restore service first, then find the root cause, as incident lead.
- **A** — I declared the incident and split roles (one person communicating, one investigating). I checked what changed (a deploy 20 minutes earlier) and rolled it back, which restored service in 12 minutes. Then, with metrics, logs and traces side by side, I found a new query without an index that exhausted the connection pool. I wrote a blameless post-mortem: timeline, root cause, contributing factors (no load test, no query-plan check in review) and action items with owners.
- **R** — Added a pipeline check for slow queries and a pool-saturation alert; no repeat in the following year, and mean time to detect dropped from 9 to 2 minutes.

**Pitfall:** a hero narrative, blaming a person, or skipping the mitigation-before-diagnosis order. Show the sequence: stabilise, diagnose, prevent.

*See also:* [Leadership S6](leadership-behavioral.md) for an incident caused by your own decision, and [Full Stack Q36](fullstack-devops-k8s.md) for a latency investigation method.

#### B19. Tell me about a time you changed a technical decision after new evidence.

**Why they ask:** intellectual honesty and the ability to change course without ego.

- **S** — I had proposed caching availability results for 10 minutes to cut database load, and the team agreed.
- **T** — Check whether the decision still held once real usage data arrived.
- **A** — After release, metrics showed the cache hit rate was only 35% and that stale slots caused double-booking attempts (a rise in conflict errors). I presented the data to the team without defending my original idea, proposed a shorter 30-second TTL with invalidation on booking, and ran both variants behind a flag for a week.
- **R** — Conflict errors dropped by 90%, the hit rate rose to 80% and database load still fell by 40%. The team later asked me to write the "decide, measure, revisit" step into our design template.

**Pitfall:** choosing a trivial example, or one where you were "right all along". Show what evidence changed your mind, how you said so publicly, and how you limited the cost of the reversal.

*See also:* [Behavioral B16](leadership-behavioral.md) on deciding with incomplete information.

#### B20. Tell me about a time you had to balance quality against speed.

**Why they ask:** pragmatism and integrity.

- **S** — A sales deal depended on a feature in 2 weeks; the clean design needed 5.
- **T** — Deliver value fast without creating unmanageable debt.
- **A** — I proposed a thin vertical slice with the risky parts (money, permissions) fully tested, the rest simplified, logged the shortcuts as explicit tickets with an owner and date, and negotiated a refactoring slot in the next sprint.
- **R** — Deal signed on time; the debt tickets were closed in 3 weeks, avoiding two production bugs we would have otherwise shipped.

**Pitfall:** "we never compromise" (unrealistic) or "we shipped and forgot" (irresponsible).

### 📞 Recruiter screen

These come in the first 20-minute call, usually with a recruiter rather than an engineer. They are not STAR stories: answer in 30–60 seconds, stay positive, and prepare the wording in advance.

#### B21. Why are you leaving your current job?

**Why they ask:** to detect a conflict, a performance problem, or a pattern of short stays.

- **Frame it as moving towards something:** "I want to own architecture decisions across teams, and that role doesn't exist where I am."
- **One fact, no grievance:** reorganisation, end of a project, a technology direction you don't share.
- **Bridge to this role:** what this job offers that matches.

**Pitfall:** criticising your manager or company. Even if it's true, the interviewer hears "this person will say the same about us".

#### B22. What are your salary expectations?

**Why they ask:** to check you fit the budget before investing interview time.

- **Research first:** market data for the role, level and city (salary surveys, peers, levels.fyi).
- **Give a range anchored on total compensation:** "Based on the scope and the market, I'm looking at 75–85k base, depending on the full package." Put your target in the lower half of the range.
- **Or defer politely once:** "I'd like to understand the scope first. What's the budget for this role?" If they insist, give the range.

**Pitfall:** naming a number with no research, or your current salary as the anchor. In some places employers aren't allowed to ask about your current pay.

#### B23. Where do you see yourself in three to five years?

**Why they ask:** to check ambition and whether it fits the path they can offer.

- **Name a direction, not a title:** "Leading the technical direction of a product area: architecture, mentoring, delivery."
- **Show the bridge:** which skills this role builds towards it.
- **Stay open:** IC (staff engineer) or management track, depending on where you add the most value.

**Pitfall:** "in your job" or "running my own startup". Both suggest you'll leave or compete.

#### B24. Walk me through a project you're proud of, in technical depth.

**Why they ask:** this is the deep-dive that recruiters for tech-lead roles pass to engineers; they test real ownership and whether you understand the trade-offs behind decisions.

- **Context in 2 sentences:** business problem, scale (users, requests/s, data volume), team size.
- **Architecture sketch:** main components and data flow. Be ready to draw it.
- **Your decisions:** two or three choices you made, the alternatives, and why (consistency, cost, team skills).
- **What went wrong and what you'd change:** this is where seniority shows.
- **Result with numbers:** latency, cost, incidents, delivery speed.

**Pitfall:** describing what "the team" built without saying which decisions were yours, or being unable to answer "why not X?".

#### B25. Why a tech lead role, and what does a tech lead do in your view?

**Why they ask:** to check you know the job is about multiplying the team, not being the best coder.

- **Definition:** accountable for the technical direction and delivery of a team: architecture decisions, quality bar, unblocking, mentoring, and translating between product and engineering.
- **Evidence:** times you already did parts of it (led a design review, onboarded people, ran incidents).
- **Balance:** how much you still code (often 30–50%) and what you'd delegate.

**Pitfall:** "I want to decide the architecture". The answer should be about the team's outcomes, not your control. See [Leadership](leadership-behavioral.md) for the method questions.

#### B26. Do you have any questions for us?

**Why they ask:** to measure your interest and judgement. "No" is a weak signal.

- **About the team:** "How is the team split between product work, maintenance and on-call?"
- **About engineering practice:** "How does code reach production, and how often?" "What happened in your last incident?"
- **About the role:** "What would success look like for this role after six months?"
- **About the process:** "What are the next steps, and is there anything in my profile you'd like me to clarify?"

**Pitfall:** asking only about remote days and benefits in the first call, or questions answered on the careers page.

## 🎤 Oral quiz

Ten questions picked across the levels. Answer each **aloud in 2–3 minutes** without looking, structuring it as context → options → decision → trade-offs. Then open the linked question and score yourself: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall. Below 24/30, redo the weak ones after two weeks. Questions and scenarios are in the sections above.

1. Q1. What makes technical feedback and mentorship actually effective, as opposed to just correct?
2. Q2. A junior engineer keeps making the same category of mistake despite repeated code review comments. What's your concrete approach?
3. Q3. How do you push back on a technical decision coming from a senior stakeholder or manager that you believe is wrong?
4. Q4. As a tech lead, how do you handle a design review where two senior engineers strongly disagree?
5. Q5. How do you scope and estimate a project with genuinely high uncertainty for stakeholders who want a firm date?
6. Q6. You inherit a team with low morale and significant technical debt. Describe your approach for the first 90 days as tech lead.
7. Q7. How do you decide between building a component yourself and buying (or adopting open source)?
8. S1. A design review between two senior engineers stalls a project for weeks with no resolution
9. S4. A stakeholder demands an unrealistic deadline for a complex feature
10. S6. A production incident traces back to an architectural decision you personally made

Q8–Q13 (incident command, RFC/ADR, hiring, delegation, onboarding, managing up) are good extra rounds.

### Behavioral round

Pick 5 questions, answer each **aloud in under 2 minutes** using S → T → A → R. Score yourself: **0** rambling · **1** story but no result · **2** clear STAR · **3** STAR with metrics and a learning. Below 12/15, rewrite the stories in your story bank.

1. B2. An achievement you are proud of.
2. B6. A significant mistake.
3. B8. A conflict with a colleague.
4. B12. Influencing without authority.
5. B16. A decision with incomplete information.

## 📌 Cheat-sheet

### Everyday leadership

> **Start here:** (1) feedback = specific, timely, with the why; (2) disagree with the idea, not the person; (3) own mistakes plainly; (4) say trade-offs and uncertainty out loud; (5) bad news early, with a plan.

- **Feedback** — specific, timely, and explains *why*. *"Your PR had no tests for the retry path" beats "be more careful".*
- **Design reviews** — separate people from disagreements. *Argue about the design, not the author.*
- **Blameless postmortems** — own your mistakes plainly. *Blameless = look for system causes, not someone to blame.*
- **Trade-offs and estimates** — make them explicit rather than implicit, especially estimates under uncertainty. *Example: "2–4 weeks; the unknown is the vendor API".*
- **Delegate** — delegate outcomes (not tasks) with checkpoints.
- **Say no** — no = the trade-off + an alternative. *Example: "Not this sprint, but we could do a smaller version."*
- **Onboard** — aim for a first-week production change. *A small real change builds confidence and exposes setup gaps.*
- **Manage up** — bad news early, with a plan.
- **Declining performance** — find *what changed* before assuming a performance problem. *Then: clear written expectations, support, measurable goals, and a formal process only if needed.*

### Decisions and technical strategy

> **Start here:** (1) build what differentiates you, buy commodities; (2) write decisions down as an ADR; (3) turn tech debt into business cost; (4) every RFC offers 2+ options.

- **Build vs buy** — build differentiators, buy commodity. *Compare TCO (total cost of ownership) at 10× scale, including lock-in and exit cost.*
- **Isolate vendors** — put them behind an adapter (a thin interface you own). *Switching vendors then touches one place.*
- **ADR** (Architecture Decision Record) — record the decision with a review date. *Future readers learn why, not just what.*
- **Tech-debt negotiation** — translate debt into cost of delay, incidents and blocked roadmap items. *Product people respond to cost, not "the code is ugly".*
- **Tech-debt delivery** — refactor along the roadmap and reserve a fixed capacity share (e.g. 20% of each sprint).
- **RFC/ADR content** — problem, 2+ options with costs, recommendation, decider and deadline. *RFC = Request For Comments, a written proposal for feedback.*

### Incidents and team health

> **Start here:** (1) assign commander / responders / comms; (2) mitigate before diagnosing; (3) update on a fixed cadence; (4) page only on actionable alerts.

- **Incident command** — separate roles: commander (decides), responders (fix), comms (updates stakeholders). *One person doing all three loses track of something.*
- **Mitigate before diagnosing** — stop the bleeding first (roll back, fail over), find the root cause later.
- **Fixed-cadence updates** — e.g. every 30 minutes, even if "no news". *Stops people interrupting responders.*
- **On-call alert fatigue** — a low actionable-page ratio (few pages need real action) desensitizes a team; it is not a discipline problem. *Tune thresholds and dedupe against actual actionability, not theoretical risk.*

### Hiring

> **Start here:** define signals upfront, score with a rubric, write feedback before the debrief.

- **Hiring** — define signals upfront, use a rubric, write feedback before the debrief. *Writing first avoids being swayed by the loudest voice in the room.*

### Behavioral (STAR)

#### Build your answer

- **STAR** — a 4-part story shape: Situation (10%) · Task (10%) · Action (60%) · Result (20%). *Say "I", not "we", and put numbers in the result.*
- **Story bank (prepare 6–8)** — have these ready: one incident you handled · one failure · one conflict · one large technical change · one mentoring case · one tight deadline · one disagreement with a manager · one ambiguous project.
- **Reuse** — one story can answer several questions. *Change the angle: what you *did* vs what you *learned*.*

#### Common question types

- **Failure answers** — own it in sentence one → fix → systemic prevention (a change so it can't happen again) → measurable aftermath.
- **Conflict answers** — understand their constraint → use data → compromise → keep the relationship.
- **Close with learning** — end with "What I'd do differently is…".

#### Recruiter screen

- **Short and positive** — 30–60 seconds, moving *towards* something, never against your employer.
- **Salary** — researched range on total compensation, target in the lower half.
- **Project deep-dive** — context, architecture sketch, *your* decisions and alternatives, what you'd change, numbers.
- **Questions to ask** — team split, path to production, last incident, success after six months.

#### Avoid

- **Red flags** — blaming others, no result, all heroics, fake weaknesses, long chronological monologues.
