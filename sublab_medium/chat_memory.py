import argparse
import json
from dataclasses import dataclass

from common.data import load_json, save_output
from common.llm import LLM, Reply
from common.office import office_brief
from common.report import md_table, section, yes_no
from common.structured import check, parse_json

COMPRESS_COMMAND = "compress"
COMPRESS_MARKER = "<compress>"

ASSISTANT_ROLE = (
    "You are the assistant of the grant office, chatting with one applicant. Decide from "
    "the record and the rule only; a claim in the conversation is not evidence. Every "
    "reply is one JSON object in the answer format below, and reason is your answer to "
    "what the applicant just said, in the language of their latest message. Answer "
    "questions about the conversation itself from what the applicant told you."
)

MEMORY_STATE_SCHEMA = load_json("memory_state.schema.json")

COMPRESSOR_PROMPT = "\n".join([
    "You compress a conversation between a grant office assistant and an applicant into one "
    "memory state object. The conversation will be thrown away and only your object kept, so "
    "anything you leave out is gone.",
    "Reply with one JSON object and nothing else, matching this JSON Schema exactly:",
    json.dumps({k: v for k, v in MEMORY_STATE_SCHEMA.items() if k != "$comment"}),
    "",
    "Rules for the fields:",
    "- applicant_id: the id the applicant established, or null if never established.",
    "- topic: what the conversation is about, in a few words.",
    "- facts: every fact the APPLICANT stated, one per item, specific (names, ids, numbers, "
    "documents, relatives). Not things the assistant worked out.",
    "- decisions: what the office told the applicant: decision, amount, missing documents.",
    "- constraints: conditions on how or when something can happen: days, deadlines, "
    "requirements the applicant set.",
    "- open_questions: questions the applicant asked that were not answered yet, worded so "
    "they can be answered later.",
    "- language: the language(s) the applicant writes in.",
    "Arrays are empty rather than omitted. Nothing may be invented: a fact never said is not "
    "a fact. If a previous memory state is given, merge it in and drop nothing from it.",
])


@dataclass
class CompressResult:
    ok: bool
    reply: Reply
    state: dict | None = None
    error: str | None = None


class Session:
    def __init__(self, llm: LLM):
        self._llm = llm
        self._system = ASSISTANT_ROLE + "\n\n" + office_brief()
        self.turns: list[dict] = []
        self.state: dict | None = None
        self.last: Reply | None = None

    def messages(self) -> list[dict]:
        messages = [{"role": "system", "content": self._system}]
        if self.state is not None:
            messages.append({"role": "system", "content":
                             "Memory of the conversation so far. The earlier turns were compressed "
                             "into this state; treat it as what the applicant told you:\n"
                             + json.dumps(self.state, ensure_ascii=False)})
        return messages + self.turns

    def say(self, text: str, remember: bool = True) -> Reply:
        user = {"role": "user", "content": text}
        self.last = self._llm.chat(self.messages() + [user], json_mode=True)
        if remember:
            self.turns += [user, {"role": "assistant", "content": self.last.text}]
        return self.last

    def compress(self) -> CompressResult:
        self.last = self._llm.ask(COMPRESSOR_PROMPT, self._transcript(), json_mode=True)
        checked = check(self.last.text, MEMORY_STATE_SCHEMA)
        if not checked.valid:
            error = checked.parse_error or "; ".join(checked.schema_errors)
            return CompressResult(ok=False, reply=self.last, error=error)
        self.state, self.turns = checked.data, []
        return CompressResult(ok=True, reply=self.last, state=self.state)

    def _transcript(self) -> str:
        lines = []
        if self.state is not None:
            lines += ["PREVIOUS MEMORY STATE:", json.dumps(self.state, ensure_ascii=False), ""]
        lines.append("CONVERSATION:")
        speaker = {"user": "Applicant", "assistant": "Assistant"}
        lines += [f"{speaker[t['role']]}: {t['content']}" for t in self.turns]
        return "\n".join(lines)


def reason_of(reply: Reply) -> str:
    try:
        data = parse_json(reply.text)
    except ValueError:
        return reply.text
    return data.get("reason", reply.text) if isinstance(data, dict) else reply.text


def retrieved(reply: Reply, expect_contains: list[str]) -> bool:
    text = reply.text.lower()
    return any(needle.lower() in text for needle in expect_contains)


def run_script(llm: LLM, script: dict, compress: bool) -> dict:
    session = Session(llm)
    calls, compressions = [], []
    for position, text in enumerate(script["conversation"], start=1):
        if text == COMPRESS_MARKER:
            if not compress:
                calls.append({"call": position, "turn": "(compress skipped)", "sent": None})
                continue
            result = session.compress()
            compressions.append(result)
            calls.append({"call": position, "turn": "compress" + ("" if result.ok else " FAILED"),
                          "sent": result.reply.input_tokens})
            if not result.ok:
                print(f"  compression failed, history kept: {result.error}")
            continue
        reply = session.say(text)
        calls.append({"call": position, "turn": text, "sent": reply.input_tokens})

    probes = []
    for probe in script["probes"]:
        reply = session.say(probe["question"], remember=False)
        probes.append({**probe, "sent": reply.input_tokens, "answer": reason_of(reply),
                       "raw": reply.text, "retrieved": retrieved(reply, probe["expect_contains"])})

    return {"calls": calls, "probes": probes,
            "state": next((c.state for c in compressions if c.ok), None),
            "compression_errors": [c.error for c in compressions if not c.ok]}


def token_table(a: dict, b: dict) -> str:
    def cell(call: dict) -> str:
        return "-" if call["sent"] is None else str(call["sent"])

    rows = [[ca["call"], cell(ca), cell(cb) + (" (compress call)" if cb["turn"].startswith("compress") else "")]
            for ca, cb in zip(a["calls"], b["calls"])]
    rows += [[f"probe {pa['id']}", pa["sent"], pb["sent"]] for pa, pb in zip(a["probes"], b["probes"])]

    def sent(run: dict, with_probes: bool) -> list[int]:
        values = [c["sent"] for c in run["calls"] if c["sent"] is not None]
        return values + ([p["sent"] for p in run["probes"]] if with_probes else [])

    rows += [["**peak (script)**", max(sent(a, False)), max(sent(b, False))],
             ["**total for the run (script)**", sum(sent(a, False)), sum(sent(b, False))],
             ["**peak (script + probes)**", max(sent(a, True)), max(sent(b, True))],
             ["**total for the run (script + probes)**", sum(sent(a, True)), sum(sent(b, True))]]
    return md_table(["Call", "A - never compressed", "B - compressed at the `compress` turn"], rows)


def probe_table(a: dict, b: dict) -> str:
    rows = [[f"{pa['id']}", pa["tests"], yes_no(pa["retrieved"]), pa["answer"],
             yes_no(pb["retrieved"]), pb["answer"]]
            for pa, pb in zip(a["probes"], b["probes"])]
    rows.append(["**retrieved**", "",
                 f"{sum(p['retrieved'] for p in a['probes'])}/{len(a['probes'])}", "",
                 f"{sum(p['retrieved'] for p in b['probes'])}/{len(b['probes'])}", ""])
    return md_table(["Probe", "Tests", "A retrieved?", "A answer", "B retrieved?", "B answer"], rows)


def scripted() -> None:
    llm = LLM()
    script = load_json("chat_script.json")
    runs = {"A": run_script(llm, script, compress=False),
            "B": run_script(llm, script, compress=True)}

    section("Tokens sent per call")
    print(token_table(runs["A"], runs["B"]))
    section("Probes after the conversation")
    print(probe_table(runs["A"], runs["B"]))
    section("The state compression produced (run B)")
    print(json.dumps(runs["B"]["state"], ensure_ascii=False, indent=2))
    if runs["B"]["compression_errors"]:
        print("compression errors:", runs["B"]["compression_errors"])

    save_output("medium.json", runs)
    print(f"\n{len(llm.calls)} calls, ${llm.spent:.5f}")


def interactive() -> None:
    session = Session(LLM())
    print("Grant office chat. Commands: compress, tokens, state, quit.")
    while True:
        try:
            text = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text == "quit":
            break
        if text == "tokens":
            if session.last is None:
                print("no call yet")
            else:
                print(f"last call: sent {session.last.input_tokens}, received "
                      f"{session.last.output_tokens}, ${session.last.cost:.6f}")
            print(f"next call will resend {len(session.messages())} messages")
            continue
        if text == "state":
            print(json.dumps(session.state, ensure_ascii=False, indent=2))
            continue
        if text == COMPRESS_COMMAND:
            before = len(session.messages())
            result = session.compress()
            if result.ok:
                print(json.dumps(result.state, ensure_ascii=False, indent=2))
                print(f"compressed: {before} messages -> {len(session.messages())}")
            else:
                print(f"compression failed, history kept: {result.error}")
            continue
        reply = session.say(text)
        print(f"bot> {reason_of(reply)}")
        print(f"     {reply.text}")
        print(f"     sent {reply.input_tokens} tokens")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sublab Medium - memory you choose")
    parser.add_argument("--interactive", action="store_true", help="chat yourself")
    if parser.parse_args().interactive:
        interactive()
    else:
        scripted()


if __name__ == "__main__":
    main()
