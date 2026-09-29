import json
import re
from dataclasses import dataclass, field

from common.data import DATA, load_json, save_output
from common.llm import LLM
from common.report import md_table, section, yes_no
from common.structured import Checked, check

RUBRIC = load_json("candidate_rubric.json")
CRITERIA = [c["id"] for c in RUBRIC["criteria"]]
WEIGHTS = {c["id"]: c["weight"] for c in RUBRIC["criteria"]}
CLOSE_CALL = 0.05

NULLABLE_STRING = {"type": ["string", "null"]}
NULLABLE_INT = {"type": ["integer", "null"]}
NULLABLE_NUMBER = {"type": ["number", "null"]}
UNPUBLISHED_STATUSES = ["submitted", "under_review", "in_preparation", "in_press", "planned", "other"]


def _object(properties: dict) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def _array_of(item: dict) -> dict:
    return {"type": "array", "items": item}


CV_SCHEMA = _object({
    "candidate_id": {"type": "string"},
    "full_name": NULLABLE_STRING,
    "degree": NULLABLE_STRING,
    "graduation_year": NULLABLE_INT,
    "gpa_original": NULLABLE_NUMBER,
    "gpa_original_scale": NULLABLE_NUMBER,
    "gpa_4_scale": {"type": ["number", "null"], "minimum": 0, "maximum": 4},
    "languages": _array_of({"type": "string"}),
    "published_outputs": _array_of(_object({
        "title_or_topic": {"type": "string"},
        "venue": NULLABLE_STRING,
        "year": NULLABLE_INT,
        "status": {"enum": ["published", "accepted"]},
    })),
    "published_count": {"type": "integer", "minimum": 0},
    "unpublished_outputs": _array_of(_object({
        "title_or_topic": {"type": "string"},
        "status": {"enum": UNPUBLISHED_STATUSES},
    })),
    "experience_periods": _array_of(_object({
        "role": {"type": "string"},
        "start": NULLABLE_STRING,
        "end": NULLABLE_STRING,
        "months": NULLABLE_INT,
        "countable": {"type": "boolean"},
    })),
    "experience_months_total": NULLABLE_INT,
    "evidence": {"type": "object", "additionalProperties": {"type": "string"}},
    "ambiguities": _array_of(_object({
        "field": {"type": "string"},
        "conflict": {"type": "string"},
    })),
})

SCORE_SCHEMA = _object({
    **{c: {"type": "integer", "minimum": 0, "maximum": 5} for c in CRITERIA},
    "notes": _object({c: {"type": "string"} for c in CRITERIA}),
})

EXTRACTION_PROMPT = "\n".join([
    "You turn a scholarship candidate's written story into one structured CV record. The "
    "story may be in English, Kazakh or Russian; write the record in English, but copy "
    "evidence quotes exactly as they appear in the story.",
    "Reply with one JSON object and nothing else, matching this JSON Schema exactly:",
    json.dumps(CV_SCHEMA),
    "",
    "RULES. Follow every one of them:",
    "1. A fact the story does not state is null. Never estimate, never infer. No GPA stated "
    "means gpa_original, gpa_original_scale and gpa_4_scale are all null, whatever the "
    "degree, honours, university or tone of the story suggest.",
    "2. A GPA on another scale is converted to a 4.0 scale linearly: gpa_4_scale = "
    "gpa_original / gpa_original_scale * 4, rounded to two decimals. gpa_original and "
    "gpa_original_scale always record the number and scale the story used. A GPA already on "
    "a 4.0 scale has gpa_original_scale 4.",
    "3. A paper is published only when the story says published or accepted. Submitted, "
    "under review, in preparation, in press, planned or not yet sent are NOT published: put "
    "them in unpublished_outputs and do not count them. Posters and talks that the story "
    "does not call a peer-reviewed publication also go to unpublished_outputs with status "
    "other. published_count is the number of items in published_outputs.",
    "4. Contradictions are not resolved and not averaged. If the story gives two different "
    "values for the same fact, that field is null and the contradiction goes into "
    "ambiguities with the field name and both values. ambiguities holds only such "
    "contradictions: a fact that is simply missing, or stated only relatively (\"last "
    "year\"), is null and is not an ambiguity.",
    "5. Experience counts months, not jobs. Overlapping periods count once. A period with no "
    "dates or month count is recorded with countable false and months null, and adds "
    "nothing. experience_months_total is the countable months, or null if none can be "
    "counted.",
    "6. evidence maps every field you fill from the story (not null, not empty, not "
    "candidate_id) to one short verbatim quote from the story that supports it.",
    '7. candidate_id is the story id you are given, for example "story-01".',
])

SCORING_PROMPT = "\n".join([
    "You score one scholarship candidate's CV record against a rubric. Score only from the "
    "record; do not reward anything the record does not contain.",
    "",
    "RUBRIC (each criterion 0 to 5, integers only):",
    *(f"- {c['id']} ({c['label']}): 5 = {c['what_5_means']}; 0 = {c['what_0_means']}."
      for c in RUBRIC["criteria"]),
    "COUNTING RULES:",
    *(f"- {name}: {rule}" for name, rule in RUBRIC["counting_rules"].items()),
    "- The rubric anchors only 0 and 5. A record between the two anchors gets a score "
    "between them in proportion to how far it gets toward the 5 anchor: one published "
    "output is half of the two needed for 5, twelve months is half of the twenty-four "
    "needed for 5. Only a record that meets the 0 description exactly scores 0.",
    "- A field that is null because the story contradicts itself is scored as not stated, "
    "and the note says so.",
    "",
    "Reply with one JSON object and nothing else, matching this JSON Schema exactly:",
    json.dumps(SCORE_SCHEMA),
    f"Each of {', '.join(CRITERIA)} is an integer 0-5, and notes has one sentence per "
    "criterion saying why. Do not compute a total, a weighted score or a ranking.",
])

PROSE_PROMPT = "\n".join([
    "You are advising a scholarship committee with one funded place and six candidates.",
    "RUBRIC:",
    *(f"- {c['label']} (weight {c['weight']}): 5 = {c['what_5_means']}; 0 = {c['what_0_means']}."
      for c in RUBRIC["criteria"]),
    *(f"- {name}: {rule}" for name, rule in RUBRIC["counting_rules"].items()),
    "",
    "Read the six stories and say in prose which candidate should win and why, then rank "
    "all six. A few short paragraphs.",
])


@dataclass
class Candidate:
    story_id: str
    story: str
    extraction: Checked
    issues: list[str] = field(default_factory=list)
    scores: Checked | None = None

    @property
    def cv(self) -> dict | None:
        return self.extraction.data if self.extraction.valid else None

    @property
    def total(self) -> float | None:
        if self.scores is None or not self.scores.valid:
            return None
        return round(sum(WEIGHTS[c] * self.scores.data[c] for c in CRITERIA), 2)


def load_stories() -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8")
            for p in sorted((DATA / "candidates").glob("story-*.md"))}


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def audit(cv: dict, story: str) -> tuple[dict, list[str]]:
    """Checks the code owns: quotes exist, arithmetic is right, contradicted fields are null."""
    cv, issues = json.loads(json.dumps(cv)), []

    squashed = _squash(story)
    for name, quote in cv["evidence"].items():
        if _squash(quote) not in squashed:
            issues.append(f"evidence for {name} is not a verbatim quote")

    if cv["gpa_original"] is not None and cv["gpa_original_scale"]:
        converted = round(cv["gpa_original"] / cv["gpa_original_scale"] * 4, 2)
        if cv["gpa_4_scale"] != converted:
            issues.append(f"gpa_4_scale {cv['gpa_4_scale']} recomputed as {converted}")
            cv["gpa_4_scale"] = converted

    if cv["published_count"] != len(cv["published_outputs"]):
        issues.append(f"published_count {cv['published_count']} recomputed as "
                      f"{len(cv['published_outputs'])}")
        cv["published_count"] = len(cv["published_outputs"])

    for ambiguity in cv["ambiguities"]:
        if cv.get(ambiguity["field"]) is not None:
            issues.append(f"{ambiguity['field']} is contradicted but not null")

    return cv, issues


def null_fields(cv: dict) -> list[str]:
    return [name for name, value in cv.items() if value is None]


def traps_hit(cv: dict) -> list[str]:
    contradicted = {a["field"] for a in cv["ambiguities"]}
    traps = []
    if cv["gpa_original"] is None and not any("gpa" in f for f in contradicted):
        traps.append("no GPA stated")
    if cv["gpa_original_scale"] not in (None, 4):
        traps.append(f"GPA on a {cv['gpa_original_scale']:g}-point scale")
    if cv["unpublished_outputs"]:
        statuses = sorted({o["status"] for o in cv["unpublished_outputs"]})
        traps.append(f"unpublished output ({', '.join(statuses)})")
    if contradicted:
        traps.append(f"contradiction ({', '.join(sorted(contradicted))})")
    return traps


def extract(llm: LLM, story_id: str, story: str) -> Candidate:
    reply = llm.ask(EXTRACTION_PROMPT, f"Story id: {story_id}\n\n{story}", json_mode=True)
    candidate = Candidate(story_id, story, check(reply.text, CV_SCHEMA))
    if candidate.extraction.valid:
        candidate.extraction.data, candidate.issues = audit(candidate.extraction.data, story)
    print(f"  extracted {story_id}  in={reply.input_tokens} out={reply.output_tokens}")
    return candidate


def score(llm: LLM, candidate: Candidate) -> None:
    record = {k: v for k, v in candidate.cv.items() if k != "evidence"}
    reply = llm.ask(SCORING_PROMPT, json.dumps(record, ensure_ascii=False), json_mode=True)
    candidate.scores = check(reply.text, SCORE_SCHEMA)
    print(f"  scored    {candidate.story_id}  in={reply.input_tokens} out={reply.output_tokens}")


def ask_prose(llm: LLM, candidates: list[Candidate]) -> str:
    stories = "\n\n".join(f"=== {c.story_id} ===\n{c.story}" for c in candidates)
    return llm.ask(PROSE_PROMPT, stories).text


def extraction_table(candidates: list[Candidate]) -> str:
    rows = []
    for c in candidates:
        cv = c.cv
        rows.append([
            c.story_id, yes_no(c.extraction.parsed), yes_no(c.extraction.valid),
            ", ".join(null_fields(cv)) or "none" if cv else "-",
            "; ".join(traps_hit(cv)) or "none" if cv else "-",
            "; ".join(c.issues) or "none",
        ])
    return md_table(["Story", "Parsed?", "Valid?", "Fields that came back `null`",
                     "Traps hit", "Fixed or flagged by code"], rows)


def cv_summary_table(candidates: list[Candidate]) -> str:
    rows = [[c.story_id, c.cv["full_name"], c.cv["gpa_original"], c.cv["gpa_original_scale"],
             c.cv["gpa_4_scale"], c.cv["published_count"],
             ", ".join(o["status"] for o in c.cv["unpublished_outputs"]) or "-",
             c.cv["experience_months_total"]]
            for c in candidates if c.cv]
    return md_table(["Story", "Name", "GPA", "scale", "gpa_4_scale", "published",
                     "not counted", "months"], rows)


def score_table(candidates: list[Candidate]) -> str:
    rows = []
    for c in candidates:
        scores = c.scores.data if c.scores and c.scores.valid else {}
        rows.append([c.story_id, *(scores.get(k, "-") for k in CRITERIA),
                     "-" if c.total is None else f"{c.total:.2f}"])
    return md_table(["Candidate", *(f"{k} (0-5)" for k in CRITERIA), "weighted total (code)"], rows)


def ranking(candidates: list[Candidate]) -> list[Candidate]:
    return sorted((c for c in candidates if c.total is not None),
                  key=lambda c: c.total, reverse=True)


def main() -> None:
    llm = LLM()
    candidates = [extract(llm, sid, story) for sid, story in load_stories().items()]
    for candidate in candidates:
        if candidate.cv:
            score(llm, candidate)
    prose = ask_prose(llm, candidates)

    section("Part 1 - extraction")
    print(extraction_table(candidates))
    print()
    print(cv_summary_table(candidates))
    for c in candidates:
        for stage, checked in (("extraction", c.extraction), ("scoring", c.scores)):
            if checked is not None and not checked.valid:
                print(f"\n{c.story_id} {stage} failed: {checked.parse_error or checked.schema_errors}")
    story_06 = next(c for c in candidates if c.story_id == "story-06")
    section("Extraction for story-06")
    print(json.dumps(story_06.cv or story_06.extraction.raw, ensure_ascii=False, indent=2))

    section("Part 2 - scores")
    print(score_table(candidates))
    ranked = ranking(candidates)
    print("\nComputed ranking: " + ", ".join(f"{c.story_id} {c.total:.2f}" for c in ranked))
    if ranked:
        winner = ranked[0]
        print(f"Winner, computed by code: {winner.story_id} ({winner.cv['full_name']}), {winner.total:.2f}")
    if len(ranked) > 1:
        margin = round(ranked[0].total - ranked[1].total, 2)
        tied = [c.story_id for c in ranked if c.total == ranked[0].total]
        print(f"Margin over second: {margin:.2f}" + (" - CLOSE CALL" if margin <= CLOSE_CALL else ""))
        if len(tied) > 1:
            print("Tied for first: " + ", ".join(tied))
    print("\nScore notes:")
    for c in candidates:
        if c.scores and c.scores.valid:
            for k in CRITERIA:
                print(f"  {c.story_id} {k}: {c.scores.data['notes'][k]}")

    section("The model's prose answer")
    print(prose)

    save_output("hard.json", {
        "candidates": [{"story_id": c.story_id, "cv": c.cv, "raw": c.extraction.raw,
                        "schema_errors": c.extraction.schema_errors, "issues": c.issues,
                        "scores": c.scores.data if c.scores else None, "total": c.total}
                       for c in candidates],
        "ranking": [c.story_id for c in ranked],
        "prose": prose,
    })
    print(f"\n{len(llm.calls)} calls, ${llm.spent:.5f}")


if __name__ == "__main__":
    main()
