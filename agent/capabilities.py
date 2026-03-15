"""Capability catalog for the Solana meme agent."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    """A user-facing capability supported by the agent."""

    name: str
    summary: str
    examples: list[str]
    guidance: str


_CAPABILITIES: tuple[Capability, ...] = (
    Capability(
        name="scan",
        summary="Find trending Solana meme coins and surface candidates worth checking.",
        examples=[
            "scan hot Solana memes",
            "find trending Solana meme coins",
        ],
        guidance="Use this when the user wants discovery, market scan, or new opportunities.",
    ),
    Capability(
        name="analyze",
        summary="Run a meme token risk and market analysis before any trade.",
        examples=[
            "analyze this token 7xKX...",
            "should I buy this Solana meme token?",
        ],
        guidance="Use this when the user asks about risk, liquidity, security, or trade quality.",
    ),
    Capability(
        name="buy",
        summary="Prepare and execute a buy after analysis and explicit confirmation.",
        examples=[
            "buy BONK with 0.05 SOL",
            "put 0.1 SOL into this token",
        ],
        guidance="Use this only after analysis and always require explicit confirmation before execution.",
    ),
    Capability(
        name="sell",
        summary="Close an existing position after showing the current sale context.",
        examples=[
            "sell position abc123",
            "close my BONK position",
        ],
        guidance="Use this when the user wants to exit a holding or lock in profit/loss.",
    ),
    Capability(
        name="portfolio",
        summary="Show wallet, portfolio status, open positions, and recent trade history.",
        examples=[
            "show my portfolio status",
            "what positions do I still hold?",
        ],
        guidance="Use this when the user asks about status, balance, positions, or history.",
    ),
    Capability(
        name="auto invest",
        summary="Scan opportunities and propose a small Solana meme allocation plan.",
        examples=[
            "auto invest 0.01 SOL",
            "auto invest 10 USDT into top opportunities",
            "build me a small meme allocation plan",
        ],
        guidance="Use this when the user wants a guided basket or automated candidate selection.",
    ),
)


def get_capabilities() -> list[Capability]:
    """Return the supported user-facing capability catalog."""
    return list(_CAPABILITIES)


def get_capability_examples(limit: int | None = None) -> list[str]:
    """Return example utterances across all supported capabilities."""
    examples: list[str] = []
    max_examples = max(len(capability.examples) for capability in _CAPABILITIES)

    for example_index in range(max_examples):
        for capability in _CAPABILITIES:
            if example_index < len(capability.examples):
                examples.append(capability.examples[example_index])

    return examples if limit is None else examples[:limit]


def build_capability_help() -> str:
    """Build natural-language guidance for supported capabilities."""
    lines = [
        "Talk to me in natural language. I can guide you through these Solana meme workflows:",
    ]
    for capability in _CAPABILITIES:
        lines.append(f"- {capability.name}: {capability.summary}")

    lines.append("")
    lines.append("Example requests:")
    for example in get_capability_examples(limit=6):
        lines.append(f"- {example}")
    return "\n".join(lines)


def build_capability_prompt() -> str:
    """Build capability context for the system prompt."""
    lines = ["## Supported capabilities"]
    for capability in _CAPABILITIES:
        lines.append(f"- {capability.name}: {capability.summary}")
        lines.append(f"  Guidance: {capability.guidance}")
        lines.append(f"  Example requests: {', '.join(capability.examples)}")
    return "\n".join(lines)
