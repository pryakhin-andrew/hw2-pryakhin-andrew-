# HW2 submission

**Name:** Andrey Pryakhin
**Student ID:** S23068249
**Group:** CSS4007-ENG-10
**Repository:** https://github.com/pryakhin-andrew/hw2-pryakhin-andrew-

## AI tool disclosure

State which AI tools you used and for what. Expected and fine; undisclosed use
is not. If you used a model to help you draft a prompt, say which prompt.

> I used Claude (Claude Code, model Claude Opus 5.5) for this assignment. It
> explained the task, wrote the code in `common/` and in the three sublab
> files (reusing the client, retry and forgiving JSON parsing from my HW1), and
> drafted every prompt in them: the four role paragraphs and the shared office
> brief (`sublab_easy/role_prompts.py`, `common/office.py`), the assistant and
> compressor prompts (`sublab_medium/chat_memory.py`), and the extraction,
> scoring and prose prompts (`sublab_hard/cv_extract_and_rank.py`). It ran the
> programs, found the failures described below (the role being overridden by
> text placed after it, the probe check failing on Kazakh answers, the scoring
> reply that did not validate, the missing anchor for one publication), and
> drafted the wording of the written answers.
>
> Every number, table and quoted reply in this file comes from the runs saved
> in `outputs/` (gitignored, kept locally): `easy.txt`, `medium.txt`,
> `hard.txt` are the runs reported here, `outputs/repeat/` is a second full run
> of all three used for the stability remarks, and the `*_run1*`/`*_run2*`
> files are the earlier prompt versions discussed in the answers. Total spend
> for all runs was about $0.10.

---

## Sublab Easy — one task, four roles

The system prompt is the shared office brief (rule, the six records one per
line, the answer format and the default meaning of each `decision`), followed
by `YOUR ROLE`, the only part that changes. JSON mode is on, every reply is
parsed and validated with `jsonschema` against the contract.

### Decisions per role

One row per enquiry. In each cell write the `decision` your run returned, and
whether it agrees with `expected` in `data/enquiries.json`:

| Enquiry | policy_officer | front_desk | auditor | bilingual_clerk |
|---|---|---|---|---|
| E-01 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-02 | more_info ✓ | more_info ✓ | more_info ✓ | more_info ✓ |
| E-03 | refused ✓ | more_info ✗ | refused ✓ | refused ✓ |
| E-04 | refused ✓ | more_info ✗ | more_info ✗ | refused ✓ |
| E-05 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-06 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-07 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-08 | not_found ✓ | not_found ✓ | not_found ✓ | not_found ✓ |
| E-09 | refused ✓ | more_info ✗ | refused ✓ | refused ✓ |
| E-10 | more_info ✓ | more_info ✓ | more_info ✓ | more_info ✓ |
| **agrees with `expected`** | 10/10 | 7/10 | 5/10 | 10/10 |
| **parsed** | 10/10 | 10/10 | 10/10 | 10/10 |
| **schema-valid** | 10/10 | 10/10 | 10/10 | 10/10 |

"Agrees" means all four checked fields match `expected`, not only `decision`.
In the repeat run two cells changed: front_desk turned E-08 into `more_info`
(with `found: false`), and auditor went back to `refused` on E-04. Agreement
there was 10/6/6/10.

### Which field moved, on which enquiry, under which role

| Field | Enquiries that moved | Role(s) that moved it |
|---|---|---|
| `found` | none | none, in both runs |
| `decision` | E-01, E-03, E-04, E-05, E-06, E-07, E-09 | auditor: E-01, E-04, E-05, E-06, E-07 · front_desk: E-03, E-04, E-09 |
| `amount` | E-01, E-05, E-06, E-07 | auditor only (250000/150000 → 0, follows its `more_info`) |
| `missing_documents` | none | none, in both runs |

bilingual_clerk moved no structured field on any enquiry, in either run. Its
only difference is `reason`.

### Raw replies

Paste the full reply for **one enquiry where a role changed the decision** away
from the policy officer's:

```
E-03, front_desk (policy_officer said "refused"):
{"applicant_id":"A-203","found":true,"decision":"more_info","amount":0,"missing_documents":[],"reason":"The record shows a transcript and ID card, but the GPA is 2.4, below the required 2.67. Please return with evidence of a GPA of at least 2.67."}
```

Paste the full reply for **E-07 (the Kazakh enquiry)** from the bilingual
clerk, so the `reason` language is visible:

```
{"applicant_id":"A-201","found":true,"decision":"granted","amount":250000,"missing_documents":[],"reason":"Жазбаға сәйкес, GPA 3.4, табыс санаты 1 және қажетті құжаттардың екеуі де бар. Сізге 250 000 теңге грант беріледі."}
```

For comparison, policy_officer on E-07 gave the same five fields with
`"reason":"The record shows GPA 3.4, income band 1, and both required documents: transcript and id_card. The grant amount is 250,000 tenge."`

### Written answers

**1. Which fields are role-sensitive and which are not?** Point at rows in your
tables.

> `decision` is the role-sensitive field: it moved on 7 of 10 enquiries. front_desk
> moved it on the three refusals (E-03, E-04, E-09 → `more_info`) and auditor
> moved it on every grant (E-01, E-05, E-06, E-07 → `more_info`) plus E-04.
> `amount` moved only as a consequence of `decision`: the four auditor rows
> where a grant became `more_info` dropped to 0, because the format says the
> amount is 0 unless granted. `found` and `missing_documents` never moved, in
> either run. Whether an applicant exists and which document the record lacks
> are facts read off the record, and no role paragraph gave the model a reason
> to change them.
>
> front_desk and auditor are the roles that move `decision`. bilingual_clerk is
> the one that moves only `reason`: 10/10 on all four fields in both runs, and
> the only visible change is E-07's reason in Kazakh.
>
> One more result that matters for this question: in my first version the role
> paragraph came *before* the brief, and the brief ends with the default meaning
> of each decision ("refused = the record fails the GPA or income band
> condition"). In that run front_desk moved nothing at all (it still wrote
> `refused` on E-03, E-04, E-09) and auditor moved only E-01
> (`outputs/easy_run1_role_first.txt`). The same role words produced almost no
> movement when a more specific instruction came after them.

**2. Which enquiries are most sensitive to the role, and why those?** Say what
E-03, E-04, E-07 and E-10 are each testing.

> The sensitive enquiries are the ones where the rule's answer is not "grant":
> E-03, E-04, E-09 under front_desk, and every grant under auditor. E-02 and E-10
> did not move under any role because `more_info` is already the answer there,
> which is exactly what front_desk and auditor fall back to.
>
> - **E-03** (GPA 2.4 < 2.67) tests a refusal that no document can fix. front_desk
>   turned it into `more_info` and told Madina to "return with evidence of a
>   GPA of at least 2.67", something she cannot bring. The role made the answer
>   friendlier and less true.
> - **E-04** (income band 3) tests the same thing on the other condition, and it
>   is the least stable row: auditor said `more_info` ("Auditor review is
>   required before any payment decision") in the main run and `refused` in the
>   repeat. Nothing in the auditor's paragraph says what to do with a clean
>   refusal, so the model filled the gap differently each time.
> - **E-07** (Kazakh, same person as E-01) tests whether the language of the
>   enquiry leaks into the decision. It did not: every role gave E-07 exactly
>   the same structured fields as E-01. Only bilingual_clerk changed the
>   language of `reason`. policy_officer answered in English even though nothing
>   told it to, so the language instruction was doing real work.
> - **E-10** (claims the id card was uploaded) tests whether a claim in the
>   message overrides the record. All four roles held `more_info` with
>   `["id_card"]` in both runs, including front_desk, whose paragraph does not
>   repeat the "no claim is evidence" line. The rule sentence in the shared
>   brief was enough.

**3. Where does discretion belong — the role paragraph, or code that reads
`decision` afterwards?** Say what a downstream program can and cannot tell
about which role produced a record.

> In code. A downstream program sees six fields and nothing identifies the role.
> A `more_info` from front_desk on E-03 (the applicant failed the GPA),
> a `more_info` from auditor on E-01 (the applicant fully qualifies) and a
> `more_info` on E-02 (a document is missing) look the same to a program. The
> only structural hint is that the first two have `missing_documents: []`,
> and the reason text, which a program should not parse. The repeat run even
> produced `found: false` with `decision: "more_info"` on E-08, a combination
> the program has to reject itself.
>
> So the model should report what the rule gives, and discretion ("we never
> send a refusal letter from the front desk", "a second reader signs every
> payment") should be a function in code from `decision` to an action. If the
> discretion has to live in the model's output, it needs its own field (for
> example a `basis` enum: `rule_failed`, `document_missing`, `pending_review`)
> instead of being folded into `decision`.

**4. Is a role a boundary?** Say in Week 2 terms what the role paragraph is
made of, and what you would put in code — not in the prompt — if a wrong
`decision` were expensive.

> No. The role paragraph is tokens at the start of the same sequence as the
> records and the enquiry, and the model continues that document. It shifts
> the probabilities of what comes next, but it is not a separate channel with
> more authority. My runs show it directly: moving the same paragraph from
> before the brief to after it changed front_desk from 0 moved decisions to 3,
> and the auditor's E-04 flipped between two identical runs. A boundary would
> not depend on position or on the sampling.
>
> If a wrong `decision` were expensive I would put in code: (1) schema
> validation, which I already do; (2) a deterministic eligibility check that
> recomputes the rule from `records.json` and `policy.json` (GPA ≥ 2.67, band
> in {1, 2}, both documents) and rejects any reply whose `decision`, `amount`
> or `missing_documents` disagrees; (3) invariants like `found: false` ⇒
> `not_found`, `granted` ⇒ amount from the band table, `more_info` ⇒ a
> non-empty `missing_documents` or an explicit basis; (4) the role limits
> themselves (the auditor may not return `granted`) enforced after the call;
> and (5) a human sign-off before any payment. At that point the model only
> identifies the applicant and writes `reason`, which is the part it is good
> at.

---

## Sublab Medium — memory you choose

The assistant replies in the contract JSON with its answer in `reason`. On
`compress` a separate call turns the transcript into the memory state, the
program validates it against `memory_state.schema.json`, and only if it is
valid replaces the turns with one system message holding the state. Probes are
asked one by one after the script and are not added to the history, so one
probe answer cannot help the next.

### Tokens per call

Input tokens sent, from `usage.prompt_tokens`. Row 10 is the `<compress>`
marker: skipped in A, and in B the tokens sent to the compressor.

| Call | A — never compressed | B — compressed at the `compress` turn |
|---|---|---|
| 1 | 720 | 720 |
| 2 | 807 | 809 |
| 3 | 898 | 896 |
| 4 | 983 | 990 |
| 5 | 1069 | 1080 |
| 6 | 1147 | 1184 |
| 7 | 1240 | 1302 |
| 8 | 1349 | 1419 |
| 9 | 1451 | 1544 |
| 10 | — (skipped) | 1298 (compress call) |
| 11 | 1540 | 1105 |
| 12 | 1613 | 1178 |
| probes Q-1…Q-5 | 1692–1697 each | 1263–1268 each |
| **peak** | 1613 (script) · 1697 (with probes) | 1544 (script and with probes) |
| **total for the run** | 12817 (script) · 21287 (with probes) | 13525 (script) · 19850 (with probes) |

Repeat run: peaks 1641 vs 1542, script totals 12972 vs 13745, totals with
probes 21577 vs 20575. Same shape.

### Probes after the conversation

"Retrieved" is the rule from `chat_script.json`: the reply contains one of the
`expect_contains` strings, case-insensitive.

| Probe | Tests | A retrieved? | A answer | B retrieved? | B answer |
|---|---|---|---|---|---|
| Q-1 identity | turn 1 | yes | You are Daniyar Qoshan, applicant A-202. Your id_card is still missing from the record. | yes | Сіз — Daniyar Qoshan (Данияр Қошан), өтініш беруші нөміріңіз A-202. |
| Q-2 missing document | turn 5 | yes | Your id_card is still missing from the record. | yes | Your file is missing the id_card; the transcript is already on file. |
| Q-3 band and amount | turns 3–4 | yes | Your record lists income band 2, corresponding to 150000 tenge. The application remains incomplete because your id_card is not on file. | yes | Сіздің табыс санатыңыз — 2. Бұл санат бойынша грант мөлшері 150000 теңге, бірақ id_card құжат ретінде әлі жоқ. |
| Q-4 the constraint | turn 6 | **no** | The record does not state which day the office accepts documents. Your id_card remains missing from the file. | no by the rule, **correct in meaning** | Сіз кеңсеге бейсенбі күні келе аласыз. [= "You can come to the office on Thursday."] |
| Q-5 the open question | turn 7 | yes | You asked whether a scanned letter from your employer would count or whether the original was required. The record does not specify the answer. | no by the rule, **correct in meaning** | Сіз жұмыс берушіден берілетін хаттың скан-нұсқасы жарай ма, әлде түпнұсқасы қажет пе деп сұрадыңыз. Бұл мәселе бойынша ереже берілмеген. [= "You asked whether a scanned copy of the letter from your employer is acceptable or the original is needed. No rule is given on this."] |
| **retrieved** | | 4/5 | | 3/5 (5/5 in meaning) | |

Repeat run: A 5/5, B 3/5 by the rule, with B again correct in Kazakh on Q-4
and Q-5.

### The state my compression produced

```json
{
  "applicant_id": "A-202",
  "topic": "Study grant application",
  "facts": [
    "Applicant's name is Daniyar Qoshan.",
    "Applicant sent a transcript last week, and the transcript is attached to the record.",
    "Applicant's income band is 2, according to the family's certificate.",
    "Applicant could not upload the id card because the scanner at home broke.",
    "Applicant can only come to the office on Thursdays because of lab all week otherwise.",
    "Applicant asked whether a scanned letter from the employer counts or whether the original is required.",
    "Applicant's sister Aruzhan applied last year and is also on file.",
    "The sister is identified in the record as Aruzhan Nurlan with applicant ID A-205."
  ],
  "decisions": [
    "The application status is more_info.",
    "The id_card is missing.",
    "The current grant amount is 0 because the application is incomplete.",
    "The transcript is attached, but the id_card is not.",
    "If the id_card is submitted and all requirements are met, the grant amount for income band 2 is 150000 теңге.",
    "The sister's complete application does not change Daniyar's application decision."
  ],
  "constraints": [
    "The id_card must be submitted before the application can be considered complete.",
    "The applicant can submit the id_card only on Thursdays.",
    "The rule on whether an employer letter must be original or may be scanned is not provided.",
    "It is not established that a decision will be made on the same day the id_card is submitted."
  ],
  "open_questions": [
    "Does a scanned letter from the employer count, or is the original required?",
    "If the id card is brought on Thursday, will the decision be made the same day?"
  ],
  "language": "Kazakh and English"
}
```

It parsed and validated on the first try in all three runs.

### Written answers

**1. What did compression buy?** Peak tokens both ways, probes retrieved both
ways, and — if a probe was lost — which one and which turn it came from.

> Peak: 1613 uncompressed vs 1544 compressed for the script, 1697 vs 1544 with
> the probes. B's peak is call 9, *before* the compression, so compression did
> not lower the peak, it stopped the growth. After it, B sent 1105 and 1178
> where A sent 1540 and 1613, about 28% less per call, and the probes cost
> ~1265 instead of ~1695.
>
> On a twelve-turn script that is not yet a saving: B's script total was
> higher (13525 vs 12817) because the compress call itself cost 1298 tokens and
> saved only two calls after it. Only with the five probes did B come out
> ahead (19850 vs 21287). Compression pays back per call after it, so it is
> worth it on long conversations and a loss on short ones.
>
> Probes by the rule: A 4/5, B 3/5. By meaning: A 4/5, B 5/5. A lost **Q-4**
> (Thursday, turn 6) while the fact was still in the history: it answered "The
> record does not state which day the office accepts documents", treating the
> question as one about office policy instead of about what Daniyar said.
> Keeping every turn did not guarantee the model used it. B's Q-4 and Q-5
> "losses" are correct answers in Kazakh (бейсенбі = Thursday, жұмыс
> берушіден хат = letter from the employer) that an English substring check
> cannot see. The state kept every probed fact: the id, id_card, band 2 and
> 150000, Thursdays in both `facts` and `constraints`, and the employer letter
> in `open_questions`.
>
> Two lessons from getting there. In my first version the assistant was told
> to answer "in the language they write in", and because Daniyar opened with
> "Сәлеметсіз бе!" both runs answered probes in Kazakh and both scored 3/5
> (`outputs/medium_run1_kazakh_replies.txt`). After changing it to "the
> language of their latest message", A answers in English, but B still drifts
> into Kazakh on four of five probes, in both runs. The likely cause is the
> state's own `"language": "Kazakh and English"`: after compression that one
> line is the strongest statement about language left in the context.

**2. Why must the state be structured rather than a paragraph?** You could have
asked for "a summary". Say what changes when the summary is an object with
named fields.

> Three things change. First, the program can check it: I validate against the
> schema and refuse to throw the history away when it fails. A paragraph always
> "parses", so there is no point where the program can say "this summary is
> broken, keep the turns". Second, named fields force a decision per category.
> `constraints` and `open_questions` are slots the model has to fill or leave
> empty, and that is where Thursday and the employer letter ended up. In a
> fluent paragraph those are exactly the details that get cut, because neither
> is about the grant decision. Third, the program can read it without another
> model call (`state["applicant_id"]`), merge it into the next compression,
> diff two states, and audit it field by field.
>
> The last point caught a real problem in my state: `facts` is defined as
> things the applicant stated, and it contains "The sister is identified in the
> record as Aruzhan Nurlan with applicant ID A-205". Daniyar never said that. The
> model matched "Aruzhan" to A-205, a person with a different surname. In a
> paragraph this inference would read as a plausible fact. In a field named
> `facts` it is a visible rule violation.

**3. What is missing from your state that you would add?** Name what you would
add and what you would drop to pay for it.

> I would add:
> - `claims`, applicant statements the record has not confirmed ("income band
>   2 according to the family certificate", "sent my transcript"). Right now
>   claims and record facts sit together in `facts`, which is the E-10 problem
>   again, inside memory.
> - `answers_given`: what the assistant already told the applicant, so the next
>   reply does not contradict it.
> - `reply_language`, separate from `language`. The one-word `language` field
>   is what I think pushed B into Kazakh.
> - a turn number for each fact, so a later check can go back to the source.
>
> To pay for it I would drop `topic`, which nothing reads, and most of
> `decisions`. Six of its lines ("status is more_info", "id_card is missing",
> "amount is 0", "150000 for band 2") can be recomputed from the record once
> `applicant_id` is known, so storing them spends tokens on the one thing
> memory does not need to remember.

**4. When is compression the wrong choice?** Name a conversation where it would
lose something that cannot be recovered, and say whether your program would
notice.

> When the exact words matter more than their meaning. For example, an
> applicant dictates their IIN, a bank account number, or a formal complaint
> or appeal that has to be quoted verbatim later. The summary paraphrases
> ("applicant provided an account number") or rounds, the turns are thrown
> away, and nothing in the context can bring the original back. The same goes
> for a conversation where the applicant corrects themselves ("band 2... no,
> actually 1"). The state records one version, and which one was said last is
> gone. It is also wrong for short conversations: in `--interactive` mode, after
> two turns, the call after `compress` sent 855 tokens against 796 before it,
> because the state was bigger than what it replaced.
>
> My program would not notice. It detects exactly one failure: a state that
> does not parse or does not match the schema. A valid object that dropped the
> account number, or that invented the sister's id, passes. To notice, I would
> keep the raw turns archived (stored, not sent) and check the state against
> them in code: every id, number and date that appears in the turns must appear
> in the state, or the compression is rejected.

---

## Sublab Hard — stories in, CVs out, the best candidate by code

Pipeline: one extraction call per story (rules and the JSON Schema in the
prompt, JSON mode, validated with `jsonschema`), then an `audit` in code
(evidence quotes must appear verbatim in the story, `gpa_4_scale` is
recomputed from the original number and scale, `published_count` must equal
the list, a contradicted field must be null), then one scoring call per CV,
then the weighted total and ranking in code. The prose question is a separate
call that gets the six raw stories and the rubric.

### Part 1 — extraction

| Story | Parsed? | Valid? | Fields that came back `null` | Traps hit |
|---|---|---|---|---|
| story-01 | yes | yes | none | none (clean control: 3.8/4.0, two published, 8 months) |
| story-02 | yes | yes | graduation_year, gpa_original, gpa_original_scale, gpa_4_scale | **no GPA stated**: "diploma with distinction" was not turned into a number. graduation_year null because "last year" is relative |
| story-03 | yes | yes | none | **GPA on another scale**: 4.6/5 → 3.68 (code recomputed, matched) · **paper not published**: one under review, not counted |
| story-04 | yes | yes | none | **papers not published**: one under review and two in preparation, not counted, published_count 1 |
| story-05 | yes | yes | none | **paper not published**: "жазылып жатыр, ... еш жерге жіберілген жоқ" (being written, not sent) recorded as in_preparation. Story in Kazakh, record in English |
| story-06 | yes | yes | graduation_year, gpa_original, gpa_original_scale, gpa_4_scale | **contradiction**: GPA 3.2 vs 3.5 and graduated 2024 vs graduating 2026, both nulled and recorded in ambiguities · the poster recorded as unpublished, not counted |

Code audit: all six passed except story-03, where the evidence quote for
`experience_months_total` was "The first, nine months... The second, five
months", stitched together with "..." and not in the story. The code flagged
it. In the repeat run the null fields, traps, counts and audit flags were
identical. Only the wording of titles and ambiguity notes changed.

| Story | Name | GPA (scale) | gpa_4_scale | published | not counted | months |
|---|---|---|---|---|---|---|
| story-01 | Aziza Bekova | 3.8 (4) | 3.8 | 2 | — | 8 |
| story-02 | Dias Yerzhanov | null | null | 1 | — | 36 |
| story-03 | Lyazzat Omarova | 4.6 (5) | 3.68 | 1 | under_review | 14 |
| story-04 | Tamerlan Saparov | 3.6 (4) | 3.6 | 1 | under_review, in_preparation ×2 | 24 |
| story-05 | Аиша Нұрланқызы | 3.9 (4) | 3.9 | 1 | in_preparation | 6 |
| story-06 | Nurzhan Abilov | null | null | 1 | poster (other) | 40 |

The four traps, for reference: no GPA stated · a GPA on another scale · a paper
that is not published · a story that contradicts itself.

Paste the extraction for **story-06**, the one that contradicts itself:

```json
{
  "candidate_id": "story-06",
  "full_name": "Nurzhan Abilov",
  "degree": "BSc in Statistics",
  "graduation_year": null,
  "gpa_original": null,
  "gpa_original_scale": null,
  "gpa_4_scale": null,
  "languages": ["Kazakh", "Russian", "English"],
  "published_outputs": [
    {"title_or_topic": "Survey weighting", "venue": "Peer-reviewed proceedings", "year": null, "status": "published"}
  ],
  "published_count": 1,
  "unpublished_outputs": [
    {"title_or_topic": "Poster at a local event", "status": "other"}
  ],
  "experience_periods": [
    {"role": "Insurance analytics team", "start": "February 2023", "end": null, "months": 40, "countable": true}
  ],
  "experience_months_total": 40,
  "evidence": {
    "full_name": "# Nurzhan Abilov",
    "degree": "I graduated in 2024 with a BSc in Statistics.",
    "languages": "Languages: Kazakh, Russian, English.",
    "published_outputs": "one paper published, in a peer-reviewed proceedings, on survey weighting.",
    "published_count": "one paper published",
    "unpublished_outputs": "One poster at a local event, which I do not think counts.",
    "experience_periods": "I have been at an insurance analytics team since February 2023, which is about forty months.",
    "experience_months_total": "which is about forty months"
  },
  "ambiguities": [
    {"field": "graduation_year", "conflict": "The story states both \"I graduated in 2024\" and \"I am currently a final-year student graduating in 2026\"."},
    {"field": "gpa_original", "conflict": "The story gives GPA values of 3.2 and 3.5: \"My GPA was 3.2\" and \"I think it was 3.5\"."}
  ]
}
```

### Part 2 — scores and the winner

| Candidate | academic (0–5) | research (0–5) | experience (0–5) | weighted total (code) |
|---|---|---|---|---|
| story-01 | 5 | 5 | 2 | 4.40 |
| story-02 | 0 | 3 | 5 | 1.90 |
| story-03 | 4 | 3 | 3 | 3.50 |
| story-04 | 4 | 3 | 5 | 3.90 |
| story-05 | 5 | 3 | 1 | 3.60 |
| story-06 | 0 | 3 | 5 | 1.90 |

Total = `round(0.5·academic + 0.3·research + 0.2·experience, 2)`, computed in
code. Ranking: story-01 4.40, story-04 3.90, story-05 3.60, story-03 3.50,
story-02 1.90 = story-06 1.90 (the code reports the tie and does not break it).
The repeat run gave identical scores.

**Winner, computed by my code:** story-01, Aziza Bekova, 4.40, ahead of
story-04 (Tamerlan Saparov) by 0.50.

**The model's prose answer, asked separately ("who should win?"):**

> Aziza Bekova should win. She has the strongest overall profile: a clearly stated 3.8/4.0 GPA, two published peer-reviewed outputs, and eight months of relevant data work. Her research record is the only one that reaches the maximum publication score, and her academic record is also excellent. Although her experience is shorter than some candidates', the rubric gives publications and academics more weight than experience.
>
> The ranking is:
>
> 1. **Aziza Bekova** — Academic 5/5; research 5/5; relevant experience 8 months, scoring 2/5. Weighted score: **4.4/5**.
> 2. **Dias Yerzhanov** — Academic 0/5 because no GPA is provided; research 1 published paper, scoring 2.5/5; 36 months of relevant work, scoring 5/5. Weighted score: **2.35/5**.
> 3. **Lyazzat Omarova** — Academic information is strong but the 4.6/5.0 GPA is not converted to the required 4.0 scale, scoring 0 under the stated conversion rule; research 1 published paper, scoring 2.5/5; 14 months of internships, scoring 3.5/5. Weighted score: **1.45/5**.
> 4. **Tamerlan Saparov** — GPA 3.6/4.0, scoring 0 because it is below 3.7; one published paper, scoring 2.5/5; 24 months of relevant work, scoring 5/5. Weighted score: **2.25/5**. On the raw weighted score, Tamerlan ranks third, ahead of Lyazzat; thus the corrected order is Tamerlan third and Lyazzat fourth.
> 5. **Aisha Nurlankyzy** — GPA 3.9/4.0, scoring 5/5; one published paper, scoring 2.5/5; six months' experience, scoring 1.5/5. Weighted score: **3.5/5**. Therefore, by the rubric, Aisha should rank second, not fifth.
> 6. **Nurzhan Abilov** — Academic record is contradictory, so the academic field is null and scores 0; one published paper, scoring 2.5/5; approximately 40 months of work, but the stated "about forty months" is less precise, scoring 5/5 if accepted. Weighted score: **2.75/5**.
>
> Accordingly, the final ranking by the rubric's weighted scores is: **1 Aziza, 2 Aisha, 3 Tamerlan, 4 Nurzhan, 5 Dias, 6 Lyazzat**. The apparent discrepancy between narrative impression and ranking arises because missing or non-converted GPA information must score zero, while a single publication receives only half the research score.

### Part 3 — written answers

**1. Which rule did you have to add, and what broke without it?** Name the
story that forced it.

> Two rules, each forced by a specific run.
>
> **"ambiguities holds only real contradictions; a fact that is missing or only
> relative ("last year") is null and is not an ambiguity."** Forced by
> **story-02**. In the first run Dias's "I finished my bachelor's ... last
> year" was recorded as a `graduation_year` ambiguity, so my trap table
> reported that story-02 contradicts itself, which it does not. The same run
> put "No GPA scale is stated" into story-06's ambiguities. Without the rule,
> "contradiction" meant "anything uncertain", and the marker would get a pile of
> non-contradictions to decide on. After the rule both false entries disappeared
> and story-06 kept its two real ones.
>
> **"The rubric anchors only 0 and 5; a record between them scores in
> proportion (one published output is half of the two needed for 5)."** Forced
> by **story-02 and story-06**. Without it (`outputs/hard_run2_no_interpolation.txt`)
> the five candidates with exactly one published paper (story-02 to story-06)
> got research 0, 2, 2, 2, 0.
> Dias and Nurzhan got 0 with the note "fewer than the two published outputs
> required for a score above 0", which ignores that 0 is defined as "none
> published". Same input, different score, and the total moved by 0.6 because
> of it. With the rule all five got 3, Dias and Nurzhan went from 1.00 to
> 1.90, and Tamerlan went from third to second.
>
> A third fix was not a rule but belongs here: in the first run the scoring
> prompt described the reply in words, the model returned `notes` as a string
> instead of an object, and all six score replies failed validation. The code
> refused to rank anything instead of guessing. Putting the JSON Schema into
> the scoring prompt, as in the extraction prompt, fixed it.

**2. Where did the model guess, and where did your code have to decide?** One
example of each, from your run.

> **The model guessed** in the gaps between anchors. The rubric says 5 is
> "a GPA at or above 3.7" and 0 is "no academic information", and says nothing
> about 3.6 or 3.68. The model gave both story-03 (3.68) and story-04 (3.6) a 4.
> Without the interpolation rule it gave story-04 a 3 for the same GPA. The
> 0.08 between them vanished and the one-point difference between runs came
> from wording, not from the record. It also accepted Nurzhan's "about forty
> months" as exactly 40 countable months, although the story says it is an
> estimate and that eight of those months were part-time.
>
> **The code decided** in three places. It caught story-03's evidence quote
> "The first, nine months... The second, five months", which the model stitched
> from two sentences with "...". The text does not appear in the story, so the
> code flagged it rather than trust it. It recomputed story-03's `gpa_4_scale` as
> 4.6/5·4 = 3.68 and confirmed the model's number, so the conversion is code's
> arithmetic, not the model's. And it produced the ranking, including the
> 1.90 tie between story-02 and story-06, which it reports as a tie instead of
> ordering them silently. The prose answer broke the same tie by "impression".

**3. Did your prose ranking and your computed ranking agree?** Say which one
you trust and why — and if they agreed, what you would need to see before
trusting the prose one alone.

> They agreed only on the winner. Aziza came first in the prose answer and in
> the code in every run I made. Below her they disagree almost everywhere. The
> prose gave its own per-criterion scores, and they break the rubric
> (Tamerlan's 3.6 scored 0 "because it is below 3.7", Lyazzat's GPA scored 0
> "because it is not converted", right after the prose had converted it to
> 3.68). Its arithmetic is wrong (Dias: 0.5·0 + 0.3·2.5 + 0.2·5 = 1.75, not
> 2.35; Nurzhan the same inputs, but 2.75). It listed one ranking and then
> replaced it with a "corrected" one in the same answer. In the previous
> prompt version the prose gave Aziza 4.66 for 5/5/0.8, which is 4.16.
>
> I trust the computed ranking. Every number in it is a field produced by a
> separate call per candidate, validated against a schema, and summed by code
> that cannot make an arithmetic mistake or change its mind halfway. When
> something is wrong I can point at the field. In the prose I cannot even tell
> which of its two rankings it means.
>
> Before trusting the prose answer alone I would need it to agree with the
> computed ranking on all six places and not only on the winner, across
> several runs, with its stated scores matching the structured ones. Aziza
> winning in both is weak evidence: she is the only candidate with a 5 on both
> heavy criteria, so any method finds her. The prose was never tested on a
> close call.

**4. The rubric has no anchor for a contradicted field.** The stories say 3.2
and then 3.5; the rubric defines a 0 and a 5 and nothing in between for this
case. Say what you did and what the rule should be.

> What I did: extraction sets `gpa_original`, `gpa_original_scale` and
> `gpa_4_scale` to null and records the conflict in `ambiguities`, as the
> counting rules say. The scoring prompt says a field that is null because of
> a contradiction is scored as not stated. So Nurzhan got academic 0, the same
> as Dias, who gave no GPA at all, and finished tied last at 1.90.
>
> I do not think that is the right rule, because it treats "stated twice,
> differently" as "never stated". Nurzhan told the committee more than Dias
> did, and both of his values are in the low threes. The difference is large:
> if the 3.2 were scored the way the model scored 3.6 and 3.68 (a 4), his
> total would be 0.5·4 + 0.3·3 + 0.2·5 = 3.90, **a tie for second place** with
> Tamerlan instead of last. How the gap is filled decides between second and
> last.
>
> The rule I would propose: score a contradicted field on the **lower** of the
> stated values, so a candidate cannot gain by stating a better number later,
> and have the code compute the total under both values. If the ranking
> differs between them, the record goes to a human with the contradiction
> attached, which is what "the marker decides" should mean in practice. The
> pipeline should not quietly turn it into a zero.

**5. How close were your top two candidates?** If they were within 0.05, say
what you would tell the committee and what you would change in the extraction
to make that call defensible.

> Not close: Aziza 4.40, Tamerlan 3.90, a gap of 0.50. The winner was stable
> across every prompt version and both repeat runs (the gap was 0.90 before the
> interpolation rule). Places 2 to 4 are much tighter, though: 3.90, 3.60,
> 3.50, and they reordered when one scoring rule changed. As shown in answer 4,
> Nurzhan could tie for second under a different contradiction rule.
>
> If the top two had been within 0.05 I would tell the committee it is a tie.
> With integer scores and weights 0.5/0.3/0.2, one point on any criterion moves
> the total by at least 0.2, so a 0.05 gap is below what this instrument can
> measure. It comes from the model's choice between neighbouring integers, not
> from the candidates. To make the call defensible I would change the
> extraction so that it carries the decision: run it several times and keep
> only fields that agree, reject any field whose evidence quote is not
> verbatim (as the code already flags), and send contradicted fields back to
> the candidate instead of scoring them. I would also let code derive the
> scores that the rubric states numerically (GPA against 3.7, papers against
> two, months against 24), so the model is left only with the judgements that
> really need reading.

---

## Reflection (optional, one short paragraph)

Having now written a role prompt, compressed a conversation, and ranked six
extractions — what will you do differently the next time you build something
that has to get reliable structured output out of a model?

> Every problem I hit in this homework was found by code checking the model,
> never by the model itself: the role overridden by text placed after it, the
> Kazakh answers the substring check missed, the scoring reply that did not
> validate, the stitched quote, the one-paper candidates scored 0 and 2. Next
> time I will write the checks first (schema, invariants, a deterministic
> recomputation of anything the rules define exactly) and then treat the
> prompt as the part that reduces how often those checks fire. The prompt is
> not the part that guarantees anything.
