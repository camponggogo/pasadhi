"""PASADHI benchmark harness: kernels, thread scaling, and the multi-layer pipeline.

    python pasadhi/bench/run.py            # full sweep
    python pasadhi/bench/run.py --quick    # one size, fewer repeats
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from pasadhi.core import matrix as mx          # noqa: E402
from pasadhi.core import layers as ly          # noqa: E402

RESULTS = ROOT / 'bench' / 'results'
RESULTS.mkdir(parents=True, exist_ok=True)


def kernel_sweep(sizes, repeats=3):
    rows = []
    for size in sizes:
        a, b = mx.random_pair(size)
        a_q = mx.Quantised.from_float(a, axis=1)
        b_q = mx.Quantised.from_float(b, axis=0)

        f32, ref = mx.timed(lambda: mx.gemm_f32(a, b), repeats)
        blocked, out_blocked = mx.timed(lambda: mx.gemm_blocked(a, b, 128), max(2, repeats - 1))
        int8, out_int8 = mx.timed(lambda: mx.gemm_int8(a_q, b_q), max(2, repeats - 1))

        error_blocked = float(np.abs(out_blocked - ref).max() / (np.abs(ref).max() or 1))
        error_int8 = float(np.abs(out_int8 - ref).mean() / (np.abs(ref).mean() or 1))
        rows.append({
            'size': size,
            'f32_gflops': round(mx.gflops(size, f32), 2),
            'blocked_gflops': round(mx.gflops(size, blocked), 2),
            'int8_gflops': round(mx.gflops(size, int8), 2),
            'blocked_rel_error': round(error_blocked, 6),
            'int8_mean_rel_error': round(error_int8, 4),
        })
        print(f"n={size:>5}  f32 {rows[-1]['f32_gflops']:>6}  blocked {rows[-1]['blocked_gflops']:>6} "
              f" int8 {rows[-1]['int8_gflops']:>6} GFLOPS  (int8 rel err {rows[-1]['int8_mean_rel_error']})")
    return rows


def thread_sweep(size=1024):
    rows = []
    for threads in (1, 2, 4, 8):
        environment = dict(os.environ)
        environment['OPENBLAS_NUM_THREADS'] = str(threads)
        environment['OMP_NUM_THREADS'] = str(threads)
        environment['PYTHONPATH'] = str(ROOT.parent)
        result = subprocess.run(
            [sys.executable, str(ROOT / 'bench' / 'thread_worker.py'), '--size', str(size)],
            capture_output=True, text=True, env=environment, cwd=str(ROOT.parent))
        if result.returncode != 0:
            print('thread worker failed', result.stderr[-300:])
            continue
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        payload['threads'] = threads
        rows.append(payload)
        print(f"threads={threads}  {payload['gflops']} GFLOPS")
    return rows


def pipeline_sweep(items=120, size=256, depth=4):
    weight, payload = ly.default_problem(size)
    rows = []
    for stages in (1, 2, 3):
        sequential = ly.run_sequential(items, weight, payload, stages)
        pipelined = ly.run_pipeline(items, weight, payload, stages, depth)
        rows.append({
            'stages': stages,
            'sequential_rps': round(sequential.throughput, 2),
            'pipeline_rps': round(pipelined.throughput, 2),
            'sequential_ms': round(sequential.latency_ms, 2),
            'pipeline_ms': round(pipelined.latency_ms, 2),
            'speedup': round(pipelined.throughput / sequential.throughput, 2),
        })
        print(f"stages={stages}  sequential {rows[-1]['sequential_rps']:>6} rps  pipeline "
              f"{rows[-1]['pipeline_rps']:>6} rps  speedup {rows[-1]['speedup']}×")
    return rows


def figure(kernels, threads, pipeline):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    INK, MUTED, GRID = '#1a1a1a', '#5a5a5a', '#e3e3e3'
    fig, axes = plt.subplots(1, 3, figsize=(15.2, 4.3), facecolor='white')

    def style(ax, title, xlabel, ylabel):
        ax.set_facecolor('white')
        for spine in ax.spines.values():
            spine.set_color('#999999')
        ax.tick_params(colors=MUTED, labelsize=8.5)
        ax.grid(True, color=GRID, linewidth=0.7)
        ax.set_axisbelow(True)
        ax.set_title(title, color=INK, fontsize=10, pad=9)
        ax.set_xlabel(xlabel, color=MUTED, fontsize=8.5)
        ax.set_ylabel(ylabel, color=MUTED, fontsize=8.5)

    ax = axes[0]
    style(ax, 'GEMM on an i7-8550U (4c/8t)', 'matrix size n', 'GFLOP/s')
    xs = [row['size'] for row in kernels]
    ax.plot(xs, [row['f32_gflops'] for row in kernels], marker='o', color='#1f4e79', label='f32 (BLAS)')
    ax.plot(xs, [row['blocked_gflops'] for row in kernels], marker='s', color='#2e75b6', label='blocked 128')
    ax.plot(xs, [row['int8_gflops'] for row in kernels], marker='^', color='#c55a11', label='int8 quantised')
    ax.set_xscale('log', base=2)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)

    ax = axes[1]
    style(ax, 'Thread scaling (OpenBLAS, n=1024)', 'threads', 'GFLOP/s')
    ax.plot([row['threads'] for row in threads], [row['gflops'] for row in threads],
            marker='o', color='#1f4e79')
    ax.set_xticks([row['threads'] for row in threads])

    ax = axes[2]
    style(ax, 'Multi-Layer Process: pipeline vs single loop', 'layer count', 'items/s')
    width = 0.36
    xs = np.arange(len(pipeline))
    ax.bar(xs - width / 2, [row['sequential_rps'] for row in pipeline], width, color='#7f7f7f', label='single process')
    ax.bar(xs + width / 2, [row['pipeline_rps'] for row in pipeline], width, color='#c55a11', label='pipelined')
    ax.set_xticks(xs)
    ax.set_xticklabels([str(row['stages']) for row in pipeline])
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)

    fig.tight_layout()
    path = RESULTS / 'fig01_pasadhi_kernels.png'
    fig.savefig(path, facecolor='white', dpi=300)
    plt.close(fig)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--skip-threads', action='store_true')
    args = parser.parse_args()

    sizes = [512] if args.quick else [256, 512, 1024]
    kernels = kernel_sweep(sizes, repeats=2 if args.quick else 3)
    threads = [] if args.skip_threads else thread_sweep(1024)
    pipeline = pipeline_sweep(items=60 if args.quick else 120, size=256)

    summary = {
        'host': {
            'cpu': 'Intel Core i7-8550U (4 cores / 8 threads)',
            'numpy': np.__version__,
            'visible_cpus': os.cpu_count(),
        },
        'kernels': kernels,
        'threads': threads,
        'pipeline': pipeline,
    }
    (RESULTS / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    path = figure(kernels, threads or [{'threads': 1, 'gflops': 0}], pipeline)
    print('wrote', RESULTS / 'summary.json')
    print('wrote', path)


if __name__ == '__main__':
    main()
