
"""Day 017: simulate one-step LLM token sampling with toy logits."""

from collections import Counter
from collections.abc import Sequence
import argparse

import numpy as np


def softmax(logits: Sequence[float], temperature: float = 1.0) -> np.ndarray:
    """Turn model scores into a distribution of probabilities."""
    if not np.isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature must be a finite number greater than 0")

    scores = np.asarray(logits, dtype=float)
    if scores.ndim != 1 or scores.size == 0 or not np.all(np.isfinite(scores)):
        raise ValueError("logits must be a non-empty 1D list of finite numbers")

    scaled = scores / temperature
    shifted = scaled - np.max(scaled)  # Prevent exponential overflow.
    exps = np.exp(shifted)
    return exps / exps.sum()


def top_p_filter(probabilities: Sequence[float], top_p: float = 1.0) -> np.ndarray:
    """Keep the smallest top-ranked set whose cumulative probability reaches top_p."""
    if not np.isfinite(top_p) or not 0 < top_p <= 1:
        raise ValueError("top_p must be in (0, 1]")

    probs = np.asarray(probabilities, dtype=float)
    if (
        probs.ndim != 1
        or probs.size == 0
        or not np.all(np.isfinite(probs))
        or np.any(probs < 0)
        or probs.sum() <= 0
    ):
        raise ValueError("probabilities must be non-negative and sum to > 0")

    probs = probs / probs.sum()
    order = np.argsort(probs)[::-1]
    keep_count = np.searchsorted(np.cumsum(probs[order]), top_p) + 1

    filtered = np.zeros_like(probs)
    filtered[order[:keep_count]] = probs[order[:keep_count]]
    return filtered / filtered.sum()


def sample_token(
    tokens: Sequence[str],
    logits: Sequence[float],
    temperature: float = 1.0,
    top_p: float = 1.0,
    rng: np.random.Generator | None = None,
) -> str:
    """Randomly select one token using temperature and top-p probabilities."""
    if len(tokens) != len(logits):
        raise ValueError("tokens and logits must be the same length")

    probs = top_p_filter(softmax(logits, temperature), top_p)
    generator = rng if rng is not None else np.random.default_rng()
    index = generator.choice(len(tokens), p=probs)
    return tokens[int(index)]


def plot_distributions(tokens: Sequence[str], logits: Sequence[float]) -> None:
    """Visualize how temperature changes probabilities."""
    import matplotlib.pyplot as plt

    x = np.arange(len(tokens))
    width = 0.25

    for i, temperature in enumerate((0.5, 1.0, 2.0)):
        probs = softmax(logits, temperature)
        plt.bar(
            x + (i - 1) * width,
            probs,
            width,
            label=f"T={temperature}",
        )

    plt.xticks(x, tokens)
    plt.ylim(0, 1)
    plt.ylabel("Next-token probability")
    plt.title("Temperature changes the next-token distribution")
    plt.legend()
    plt.tight_layout()
    plt.show()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()

    tokens = ["radiation", "medicine", "water"]
    logits = [2.0, 1.0, 0.0]  # Toy scores, not actual LLM outputs.

    for temperature in (0.5, 1.0, 2.0):
        probs = softmax(logits, temperature)
        rng = np.random.default_rng(42)

        counts = Counter(
            sample_token(tokens, logits, temperature, rng=rng)
            for _ in range(1000)
        )

        print(f"\nTemperature: {temperature}")
        print("Probabilities:", dict(zip(tokens, np.round(probs, 3))))
        print("Sample counts (1000 selections):", dict(counts))

    if args.plot:
        plot_distributions(tokens, logits)


if __name__ == "__main__":
    main()
