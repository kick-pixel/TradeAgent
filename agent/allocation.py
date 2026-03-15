"""Budget allocation helpers for auto-invest flows."""

from math import sqrt


def allocate_auto_invest_budget(selected: list[dict], budget_usd: float) -> dict[str, float]:
    """Allocate budget using score and liquidity weighting."""
    if not selected:
        return {}

    if len(selected) == 1:
        return {selected[0]["symbol"]: round(budget_usd, 2)}

    weights: list[float] = []
    for token in selected:
        score = float(token.get("score", 0) or 0)
        liquidity = float(getattr(token.get("analysis"), "liquidity_usd", 0) or 0)
        weight = max(score, 1.0) * max(sqrt(max(liquidity, 1.0)), 1.0)
        weights.append(weight)

    total_weight = sum(weights)
    raw_allocations = [budget_usd * (weight / total_weight) for weight in weights]
    rounded_allocations = [round(amount, 2) for amount in raw_allocations]

    remainder = round(budget_usd - sum(rounded_allocations), 2)
    if remainder != 0:
        max_index = max(range(len(weights)), key=lambda index: weights[index])
        rounded_allocations[max_index] = round(rounded_allocations[max_index] + remainder, 2)

    return {
        token["symbol"]: allocation
        for token, allocation in zip(selected, rounded_allocations, strict=False)
    }
