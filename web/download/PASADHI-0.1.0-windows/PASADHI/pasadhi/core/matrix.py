"""Matrix kernels for old CPUs: portable float32, blocked, and int8-quantised GEMM.

Every kernel returns a numpy array; the harness measures them, the scheduler composes them.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np


def gemm_f32(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Reference path: BLAS (OpenBLAS / MKL) already does blocking and threading."""
    return a @ b


def gemm_blocked(a: np.ndarray, b: np.ndarray, block: int = 128) -> np.ndarray:
    """Explicit tiling on top of BLAS. Useful when a matrix exceeds the last-level cache.

    The inner call is still BLAS, but the working set per call is block-sized, so an ageing L3
    (8 MB on this class of CPU) is not thrashed by a 2 048-wide stream.
    """
    n, k = a.shape
    _, m = b.shape
    out = np.zeros((n, m), dtype=np.float32)
    for i in range(0, n, block):
        i_end = min(i + block, n)
        for j in range(0, m, block):
            j_end = min(j + block, m)
            for p in range(0, k, block):
                p_end = min(p + block, k)
                out[i:i_end, j:j_end] += a[i:i_end, p:p_end] @ b[p:p_end, j:j_end]
    return out


@dataclass
class Quantised:
    """Symmetric int8 matrix with one scale per row (a) and per column (b)."""

    values: np.ndarray
    scale: np.ndarray

    @classmethod
    def from_float(cls, matrix: np.ndarray, axis: int = 1) -> 'Quantised':
        scale = np.abs(matrix).max(axis=axis, keepdims=True) / 127.0
        scale = np.where(scale == 0, 1.0, scale).astype(np.float32)
        values = np.clip(np.round(matrix / scale), -127, 127).astype(np.int8)
        return cls(values=values, scale=scale)


def gemm_int8(a_q: Quantised, b_q: Quantised, block: int = 256) -> np.ndarray:
    """int8 × int8 → int32 accumulation, then de-quantise.

    Integer multiply-accumulate is where old AVX2 hardware still competes: four times the
    elements per cache line and no floating-point dependency chains.
    """
    n, k = a_q.values.shape
    _, m = b_q.values.shape
    out = np.zeros((n, m), dtype=np.float32)
    for i in range(0, n, block):
        i_end = min(i + block, n)
        for j in range(0, m, block):
            j_end = min(j + block, m)
            acc = np.zeros((i_end - i, j_end - j), dtype=np.int32)
            for p in range(0, k, block):
                p_end = min(p + block, k)
                acc += a_q.values[i:i_end, p:p_end].astype(np.int32) @ b_q.values[p:p_end, j:j_end].astype(np.int32)
            out[i:i_end, j:j_end] = acc.astype(np.float32) * a_q.scale[i:i_end] * b_q.scale[:, j:j_end]
    return out


def gemm_naive(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Deliberately slow reference. Only used at tiny sizes to keep the harness honest."""
    n, k = a.shape
    _, m = b.shape
    out = np.zeros((n, m), dtype=np.float32)
    for i in range(n):
        for p in range(k):
            out[i, :] += a[i, p] * b[p, :]
    return out


def gflops(size: int, seconds: float) -> float:
    return 2.0 * size ** 3 / seconds / 1e9


def timed(fn, repeats: int = 3):
    """Return (best_seconds, result) — best of n, because the host is shared and noisy."""
    best = float('inf')
    value = None
    for _ in range(repeats):
        started = time.perf_counter()
        value = fn()
        best = min(best, time.perf_counter() - started)
    return best, value


def random_pair(size: int, seed: int = 7):
    rng = np.random.default_rng(seed)
    return rng.standard_normal((size, size), dtype=np.float32), rng.standard_normal((size, size), dtype=np.float32)
