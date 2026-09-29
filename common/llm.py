import os
import time
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

from common.data import ROOT

MODEL = "gpt-5.6-luna"
RATE_IN_PER_MTOK = 0.20
RATE_OUT_PER_MTOK = 1.20
MAX_OUTPUT_TOKENS = 2000
RETRY_ATTEMPTS = 5
RETRY_PAUSE_SECONDS = 10


@dataclass(frozen=True)
class Reply:
    text: str
    input_tokens: int
    output_tokens: int

    @property
    def cost(self) -> float:
        return (self.input_tokens * RATE_IN_PER_MTOK
                + self.output_tokens * RATE_OUT_PER_MTOK) / 1_000_000


class LLM:
    def __init__(self, model: str = MODEL):
        load_dotenv(ROOT / ".env")
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set. Copy .env.example to .env.")
        self._client = OpenAI(api_key=key)
        self.model = model
        self.calls: list[Reply] = []

    def chat(self, messages: list[dict], json_mode: bool = False) -> Reply:
        options = {"response_format": {"type": "json_object"}} if json_mode else {}
        response = self._create(messages, options)
        reply = Reply(
            text=response.choices[0].message.content or "",
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )
        self.calls.append(reply)
        return reply

    def ask(self, system: str, user: str, json_mode: bool = False) -> Reply:
        return self.chat([{"role": "system", "content": system},
                          {"role": "user", "content": user}], json_mode=json_mode)

    @property
    def spent(self) -> float:
        return sum(call.cost for call in self.calls)

    def _create(self, messages: list[dict], options: dict):
        for attempt in range(RETRY_ATTEMPTS):
            try:
                return self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_completion_tokens=MAX_OUTPUT_TOKENS,
                    reasoning_effort="none",
                    **options,
                )
            except RateLimitError:
                if attempt == RETRY_ATTEMPTS - 1:
                    raise
                time.sleep(RETRY_PAUSE_SECONDS)
