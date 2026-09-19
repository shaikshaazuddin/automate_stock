def cost(value, sell, dp_charge=20.0):
    brokerage = min(20.0, 0.001 * value)
    return brokerage + 0.001 * value + (dp_charge if sell else 0)  # + STT 0.1%
