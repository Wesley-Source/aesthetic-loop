#!/usr/bin/env python3
"""wilson.py — IC de Wilson 95% (fórmula fixada no PROTOCOL.md §6).
Uso: python3 benchmark/wilson.py <acertos> <n>   → imprime "p = X% IC95 [a%, b%]"""
import math
import sys


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n <= 0:
        raise ValueError("n deve ser > 0")
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return p, center - half, center + half


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    k, n = int(sys.argv[1]), int(sys.argv[2])
    p, lo, hi = wilson(k, n)
    print(f"p = {p*100:.1f}% IC95 [{lo*100:.1f}%, {hi*100:.1f}%] (n={n})")
    if n < 43:
        print("AVISO: n<43 — estatisticamente indistinguível de acaso (PROTOCOL.md §1).")
