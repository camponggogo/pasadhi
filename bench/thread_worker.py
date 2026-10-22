"""Thread-scaling worker: must run in a fresh process so OPENBLAS_NUM_THREADS takes effect."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', type=int, default=1024)
    args = parser.parse_args()

    rng = np.random.default_rng(3)
    a = rng.standard_normal((args.size, args.size), dtype=np.float32)
    b = rng.standard_normal((args.size, args.size), dtype=np.float32)
    _ = a @ b  # warm up BLAS and page in both matrices

    best = float('inf')
    for _ in range(3):
        started = time.perf_counter()
        _ = a @ b
        best = min(best, time.perf_counter() - started)
    gflops = 2.0 * args.size ** 3 / best / 1e9
    print(json.dumps({'size': args.size, 'gflops': round(gflops, 2)}))


if __name__ == '__main__':
    main()
