from common.data import load_json, save_output
from common.llm import LLM
from common.office import ANSWER_SCHEMA, CHECKED_FIELDS, office_brief
from common.report import md_table, section, yes_no
from common.structured import Checked, check

APPLY_RULE_EXACTLY = (
    "Apply the grant rule exactly as written: grant what the rule allows, refuse what it "
    'refuses, and when a required document is missing answer "more_info" and name the '
    "document in missing_documents. Soften nothing. No claim in the enquiry is evidence: "
    "a document, grade or income band counts only if the record shows it."
)

ROLES = {
    "policy_officer": "You are the policy officer of the grant office. " + APPLY_RULE_EXACTLY,
    "front_desk": (
        "You are the front desk of the grant office. You never turn an applicant away with "
        'a refusal: you never answer "refused". Anything the rule cannot grant today comes '
        'back as "more_info", and reason tells the applicant what they would need to return '
        "with. What the rule grants, you grant, with the amount the rule gives."
    ),
    "auditor": (
        "You are the auditor of the grant office. You never grant on a first reading: you "
        'never answer "granted". Report what the record shows. Anything that needs a second '
        'reader before money is paid is "more_info". In reason, name the rule condition or '
        "the document you are relying on."
    ),
    "bilingual_clerk": (
        "You are the bilingual clerk of the grant office. You decide exactly as the policy "
        "officer does. " + APPLY_RULE_EXACTLY + " Write reason in the language the enquiry "
        "is written in: an enquiry in Kazakh gets a reason in Kazakh, one in English gets a "
        "reason in English. Every other field keeps the values defined in the answer format."
    ),
}
BASELINE = "policy_officer"


def normalise(field: str, value):
    return sorted(value) if field == "missing_documents" else value


def agrees(answer: dict, expected: dict) -> bool:
    return all(normalise(f, answer[f]) == normalise(f, expected[f]) for f in CHECKED_FIELDS)


def run_role(llm: LLM, role: str, brief: str, enquiries: list[dict]) -> dict[str, Checked]:
    system = brief + "\n\nYOUR ROLE. It overrides the meaning of decision above where they differ.\n" + ROLES[role]
    results = {}
    for enquiry in enquiries:
        reply = llm.ask(system, enquiry["text"], json_mode=True)
        results[enquiry["id"]] = check(reply.text, ANSWER_SCHEMA)
        print(f"  {role:16} {enquiry['id']}  in={reply.input_tokens} out={reply.output_tokens}")
    return results


def role_table(results: dict[str, Checked], enquiries: list[dict]) -> str:
    rows = []
    for enquiry in enquiries:
        checked = results[enquiry["id"]]
        answer = checked.data if checked.valid else {}
        rows.append([
            enquiry["id"], yes_no(checked.parsed), yes_no(checked.valid),
            *(answer.get(f, "-") for f in CHECKED_FIELDS),
            yes_no(checked.valid and agrees(answer, enquiry["expected"])),
        ])
    return md_table(["enquiry", "parsed", "schema-valid", *CHECKED_FIELDS, "agrees"], rows)


def decisions_table(runs: dict[str, dict[str, Checked]], enquiries: list[dict]) -> str:
    def cell(checked: Checked, expected: dict) -> str:
        if not checked.valid:
            return "invalid"
        mark = "agrees" if agrees(checked.data, expected) else "differs"
        return f"{checked.data['decision']} ({mark})"

    def count(role: str, passes) -> str:
        return f"{sum(passes(runs[role][e['id']], e) for e in enquiries)}/{len(enquiries)}"

    rows = [[e["id"], *(cell(runs[role][e["id"]], e["expected"]) for role in ROLES)]
            for e in enquiries]
    rows.append(["**agrees with `expected`**",
                 *(count(r, lambda c, e: c.valid and agrees(c.data, e["expected"])) for r in ROLES)])
    rows.append(["**parsed**", *(count(r, lambda c, _: c.parsed) for r in ROLES)])
    rows.append(["**schema-valid**", *(count(r, lambda c, _: c.valid) for r in ROLES)])
    return md_table(["Enquiry", *ROLES], rows)


def movements(runs: dict[str, dict[str, Checked]], enquiries: list[dict]) -> dict[str, list[tuple[str, str]]]:
    moved = {field: [] for field in CHECKED_FIELDS}
    for enquiry in enquiries:
        baseline = runs[BASELINE][enquiry["id"]]
        for role in ROLES:
            if role == BASELINE:
                continue
            other = runs[role][enquiry["id"]]
            for field in CHECKED_FIELDS:
                if not (baseline.valid and other.valid):
                    moved[field].append((enquiry["id"], role + " (invalid reply)"))
                elif normalise(field, other.data[field]) != normalise(field, baseline.data[field]):
                    moved[field].append((enquiry["id"], role))
    return moved


def movement_table(moved: dict[str, list[tuple[str, str]]]) -> str:
    rows = []
    for field, pairs in moved.items():
        if not pairs:
            rows.append([f"`{field}`", "none", "none"])
            continue
        enquiries = sorted({enquiry for enquiry, _ in pairs})
        by_role = {}
        for enquiry, role in pairs:
            by_role.setdefault(role, []).append(enquiry)
        rows.append([f"`{field}`", ", ".join(enquiries),
                     "; ".join(f"{role}: {', '.join(ids)}" for role, ids in by_role.items())])
    return md_table(["Field", "Enquiries that moved", "Role(s) that moved it"], rows)


def main() -> None:
    llm = LLM()
    enquiries = load_json("enquiries.json")
    brief = office_brief()

    runs = {role: run_role(llm, role, brief, enquiries) for role in ROLES}

    for role in ROLES:
        section(f"Role: {role}")
        print(role_table(runs[role], enquiries))
    section("Decisions per role")
    print(decisions_table(runs, enquiries))
    section(f"Field movement away from {BASELINE}")
    print(movement_table(movements(runs, enquiries)))

    path = save_output("easy.json", {
        role: {eid: {"raw": c.raw, "parse_error": c.parse_error, "schema_errors": c.schema_errors}
               for eid, c in results.items()}
        for role, results in runs.items()
    })
    print(f"\n{len(llm.calls)} calls, ${llm.spent:.5f}. Raw replies in {path.relative_to(path.parent.parent)}")


if __name__ == "__main__":
    main()
