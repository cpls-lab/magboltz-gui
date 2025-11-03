def linspace_0_1(n: int) -> list[float]:
    "Generate n evenly spaced values between 0 and 1 inclusive."""
    if n <= 1:
        return [0.0]
    step = 1.0 / (n - 1)
    return [i * step for i in range(n)]