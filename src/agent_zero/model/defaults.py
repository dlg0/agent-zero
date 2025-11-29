"""Default prices and demand levels for the toy model.

These values are used to initialise the world state when the
assumptions do not specify explicit numbers.
"""

# Baseline commodity prices (arbitrary units)
DEFAULT_PRICES = {
    "electricity": 50.0,
    "hydrogen": 3.0,
    "carbon": 0.0,
}

# Baseline commodity demand (arbitrary units)
DEFAULT_DEMAND = {
    "electricity": 100.0,
    "hydrogen": 10.0,
}