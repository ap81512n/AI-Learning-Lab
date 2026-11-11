
import logging
import os
from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

from openai import APIError, OpenAI

logger = logging.getLogger(__name__)
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    estimated_cost_usd: float | None


class ModelCallError(Exception):
    """Safe application error for model failures."""


class ModelAdapter(Protocol):
    def generate(
        self, *, instructions: str, prompt: str
    ) -> LLMResult: ...


class OpenAIModelAdapter:
    def __init__(
        self,
        *,
        model: str,
        input_rate: float,
        output_rate: float,
        client=None,
    ):
        if input_rate < 0 or output_rate < 0:
            raise ValueError("Token rates cannot be negative")

        self.model = model
        self.input_rate = input_rate
        self.output_rate = output_rate
        self.client = (
            client if client is not None
            else OpenAI(timeout=20.0, max_retries=2)
        )

    def generate(
        self, *, instructions: str, prompt: str
    ) -> LLMResult:
        start = perf_counter()

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=prompt,
            )
        except APIError as exc:
            # Do not log prompts, keys or raw provider errors.
            logger.warning(
                "LLM request failed: %s",
                type(exc).__name__,
            )
            raise ModelCallError(
                "Model provider is temporarily unavailable"
            ) from None

        latency_ms = round((perf_counter() - start) * 1000)

        usage = response.usage
        input_tokens = usage.input_tokens if usage else 0
        output_tokens = usage.output_tokens if usage else 0

        cost = None
        if usage is not None:
            cost = round(
                (
                    input_tokens * self.input_rate
                    + output_tokens * self.output_rate
                ) / 1_000_000,
                8,
            )

        logger.info(
            "model=%s input_tokens=%d output_tokens=%d "
            "latency_ms=%d estimated_cost_usd=%s",
            response.model,
            input_tokens,
            output_tokens,
            latency_ms,
            cost,
        )

        return LLMResult(
            text=response.output_text,
            model=response.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            estimated_cost_usd=cost,
            
        )


def build_model_adapter() -> OpenAIModelAdapter:
    return OpenAIModelAdapter(
        model=os.environ["OPENAI_MODEL"],
        input_rate=float(
            os.environ["LLM_INPUT_USD_PER_1M"]
        ),
        output_rate=float(
            os.environ["LLM_OUTPUT_USD_PER_1M"]
        ),
    )
