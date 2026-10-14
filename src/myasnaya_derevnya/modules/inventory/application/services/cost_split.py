from collections.abc import Sequence
from decimal import ROUND_FLOOR, Decimal

from myasnaya_derevnya.modules.inventory.domain.errors import CostAllocationError


def split_kopecks(total_kopecks: int, weights: Sequence[Decimal]) -> list[int]:
    if not weights:
        return []

    total_weight = sum(weights)
    if total_weight <= 0:
        raise CostAllocationError()

    exact = [Decimal(total_kopecks) * weight / total_weight for weight in weights]
    kopecks = [int(value.to_integral_value(rounding=ROUND_FLOOR)) for value in exact]

    remainder = total_kopecks - sum(kopecks)
    order = sorted(
        range(len(weights)),
        key=lambda index: exact[index] - kopecks[index],
        reverse=True,
    )

    for index in order[:remainder]:
        kopecks[index] += 1

    return kopecks
