from __future__ import annotations

import math

import numpy as np


def mape(actual: list[float], predicted: list[float]) -> float:
    """Calculate mean absolute percentage error.

    Returns:
        MAPE as a percentage.
    """
    errors = [
        abs((observed - forecast) / observed)
        for observed, forecast in zip(actual, predicted, strict=True)
        if observed != 0
    ]
    return float(np.mean(errors) * 100) if errors else 0.0


def rmse(actual: list[float], predicted: list[float]) -> float:
    """Calculate root mean squared error.

    Returns:
        RMSE in the same unit as the inputs.
    """
    squared = [
        (observed - forecast) ** 2 for observed, forecast in zip(actual, predicted, strict=True)
    ]
    return math.sqrt(float(np.mean(squared))) if squared else 0.0


def smape(actual: list[float], predicted: list[float]) -> float:
    """Calculate symmetric mean absolute percentage error.

    Returns:
        sMAPE as a percentage.
    """
    errors = []
    for observed, forecast in zip(actual, predicted, strict=True):
        denominator = (abs(observed) + abs(forecast)) / 2
        if denominator > 0:
            errors.append(abs(observed - forecast) / denominator)
    return float(np.mean(errors) * 100) if errors else 0.0
