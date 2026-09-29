from common.data import load_json

DECISIONS = ["granted", "refused", "more_info", "not_found"]
CHECKED_FIELDS = ("found", "decision", "amount", "missing_documents")

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "applicant_id": {"type": ["string", "null"]},
        "found": {"type": "boolean"},
        "decision": {"enum": DECISIONS},
        "amount": {"type": "integer", "minimum": 0},
        "missing_documents": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
    "required": ["applicant_id", "found", "decision", "amount", "missing_documents", "reason"],
    "additionalProperties": False,
}


def _record_line(record: dict) -> str:
    aliases = ", ".join(a for a in record["aliases"] if a != record["name"])
    return (f"{record['id']} | {record['name']} (also written: {aliases}) | {record['city']} | "
            f"GPA {record['gpa']} | income band {record['income_band']} | "
            f"documents on file: {', '.join(record['documents']) or 'none'}")


def office_brief() -> str:
    policy = load_json("policy.json")
    records = load_json("records.json")
    amounts = ", ".join(f"band {band}: {amount}"
                        for band, amount in policy["amount_tenge_by_band"].items())
    return "\n".join([
        f"GRANT RULE ({policy['scheme']}):",
        policy["rule_human"],
        f"- GPA at least {policy['gpa_min']}",
        f"- income band one of {policy['allowed_income_bands']}",
        f"- required documents: {', '.join(policy['required_documents'])}",
        f"- amount in {policy['currency']}: {amounts}",
        "",
        "APPLICANT RECORDS. These are the only applicants on file:",
        *map(_record_line, records),
        "",
        "ANSWER FORMAT. Reply with one JSON object and nothing else, with exactly these keys:",
        '- "applicant_id": the id of the matching record; if no record matches, the id the '
        "message quotes, or null if it quotes none",
        '- "found": true only when a record matches the applicant',
        '- "decision": one of "granted", "refused", "more_info", "not_found"',
        '- "amount": integer in tenge, the grant amount when decision is "granted", otherwise 0',
        '- "missing_documents": required documents the record does not show, [] when none',
        '- "reason": one or two sentences for a human',
        "Meaning of decision: granted = the record satisfies the whole rule, "
        "refused = the record fails the GPA or income band condition, "
        "more_info = a required document is missing from the record, "
        "not_found = no record matches the applicant.",
    ])
