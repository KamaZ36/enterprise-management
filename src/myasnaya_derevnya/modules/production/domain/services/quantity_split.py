from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

QUANTITY_STEP = Decimal("0.000001")


def split_quantity(total: Decimal, weights: Sequence[Decimal]) -> list[Decimal]:
    if not weights:
        return []

    total_weight = sum(weights)
    if total_weight <= 0:
        base = (total / len(weights)).quantize(QUANTITY_STEP, rounding=ROUND_HALF_UP)
        parts = [base] * (len(weights) - 1)
        parts.append(total - sum(parts))

        return parts

    parts = [
        (total * weight / total_weight).quantize(
            QUANTITY_STEP, rounding=ROUND_HALF_UP
        )
        for weight in weights
    ]
    parts[-1] = total - sum(parts[:-1])

    return parts
