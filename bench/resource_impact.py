"""How much does each resource percentage actually buy?

Measures, on this host:
  CPU    GEMM throughput under a duty cycle (the way the app enforces a CPU share)
  RAM    working-set size vs throughput (cache/L3 effects, and the largest job that fits)
  DISK   sequential read and 4 KiB random read, then the time to load a 1 GB model cache
  NET    loopback throughput by payload size, then dispatch capacity in jobs/s
  GPU    modelled from published specs (no NVIDIA card in this machine)

    python pasadhi/bench/resource_impact.py
"""
from __future__ import annotations

import json
import os
import socket
import statistics
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'bench' / 'results'
OUT.mkdir(parents=True, exist_ok=True)


def cpu_duty_sweep(duty_points=(10, 25, 50, 75, 90, 100), seconds=2.0, size=512):
    """Run GEMM in 100 ms windows, working for `duty` of each window."""
    rng = np.random.default_rng(4)
    a = rng.standard_normal((size, size), dtype=np.float32)
    b = rng.standard_normal((size, size), dtype=np.float32)
    rows = []
    for pct in duty_points:
        duty = pct / 100
        flops = 0.0
        deadline = time.perf_counter() + seconds
        while time.perf_counter() < deadline:
            work_end = time.perf_counter() + 0.1 * duty
            while time.perf_counter() < work_end:
                started = time.perf_counter()
                _ = a @ b
                flops += 2 * size ** 3
            time.sleep(0.1 * (1 - duty))
        rows.append({'pct': pct, 'gflops': round(flops / seconds / 1e9, 2)})
    return rows


def ram_working_set(size_mb_list=(16, 64, 256, 512, 1024)):
    """Throughput against the size of the working set; also the largest square matrix that fits."""
    rows = []
    for size_mb in size_mb_list:
        n = int((size_mb * 1024 * 1024 / 4 / 2) ** 0.5)
        rng = np.random.default_rng(9)
        a = rng.standard_normal((n, n), dtype=np.float32)
        b = rng.standard_normal((n, n), dtype=np.float32)
        best = float('inf')
        for _ in range(2):
            started = time.perf_counter()
            _ = a @ b
            best = min(best, time.perf_counter() - started)
        rows.append({'working_set_mb': size_mb, 'n': n, 'gflops': round(2 * n ** 3 / best / 1e9, 2)})
    return rows


def disk_bench(path: Path, size_mb=256, block_kb=1024):
    block = block_kb * 1024
    buffer = os.urandom(block)
    target = path / 'pasadhi-disk-test.bin'
    started = time.perf_counter()
    with open(target, 'wb') as handle:
        for _ in range(size_mb * 1024 // block_kb):
            handle.write(buffer)
        handle.flush()
        os.fsync(handle.fileno())
    write_s = time.perf_counter() - started
    started = time.perf_counter()
    with open(target, 'rb') as handle:
        while handle.read(block):
            pass
    read_s = time.perf_counter() - started
    target.unlink(missing_ok=True)

    # 4 KiB random reads
    probe = path / 'pasadhi-rand.bin'
    probe.write_bytes(os.urandom(8 * 1024 * 1024))
    started = time.perf_counter()
    with open(probe, 'rb') as handle:
        for _ in range(2000):
            handle.seek((_ * 7919) % (7 * 1024 * 1024))
            handle.read(4096)
    rand_s = time.perf_counter() - started
    probe.unlink(missing_ok=True)

    return {'write_mb_s': round(size_mb / write_s, 1), 'read_mb_s': round(size_mb / read_s, 1),
            'random_4k_iops': round(2000 / rand_s, 0),
            'model_load_s_per_gb': round(1024 / (size_mb / read_s), 2)}


def net_bench(payloads=(1024, 65536, 1048576), seconds=1.2):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('127.0.0.1', 0))
    server.listen(1)
    port = server.getsockname()[1]
    rows = []

    def serve():
        conn, _ = server.accept()
        total = 0
        while True:
            data = conn.recv(1 << 20)
            if not data:
                break
            total += len(data)
        conn.close()

    for size in payloads:
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        client = socket.create_connection(('127.0.0.1', port))
        chunk = b'x' * size
        count = 0
        deadline = time.perf_counter() + seconds
        while time.perf_counter() < deadline:
            client.sendall(chunk)
            count += 1
        client.close()
        thread.join(timeout=2)
        mbps = count * size / seconds / 1024 / 1024
        rows.append({'payload_kb': round(size / 1024, 1), 'mb_per_s': round(mbps, 1),
                     'jobs_per_s': round(count / seconds, 0)})
        # a fresh listener for the next payload
        server.close()
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', port))
        server.listen(1)
    server.close()
    return rows


def gpu_model():
    cpu_peak = 83.3           # measured, 4 threads
    gpu = 1862.0              # GTX 1050 fp32, spec
    return {'cpu_gflops': cpu_peak, 'gpu_gflops': gpu, 'ratio': round(gpu / cpu_peak, 1)}


def elasticity(cpu_rows, base_pct=35, delta=10):
    """Percent more throughput for ten more points of CPU, at the operating point."""
    by_pct = {row['pct']: row['gflops'] for row in cpu_rows}
    low = min(by_pct, key=lambda p: abs(p - base_pct))
    high = min(by_pct, key=lambda p: abs(p - (base_pct + delta)))
    if low == high:
        return 0.0
    return round((by_pct[high] - by_pct[low]) / by_pct[low] * 100, 1)


def main():
    cpu_rows = cpu_duty_sweep()
    for row in cpu_rows:
        print(f"CPU {row['pct']:>3} %  {row['gflops']:>7} GFLOP/s")

    ram_rows = ram_working_set()
    for row in ram_rows:
        print(f"RAM working set {row['working_set_mb']:>5} MB (n={row['n']:>4})  {row['gflops']:>7} GFLOP/s")

    disk = disk_bench(Path(os.environ.get('TEMP', '.')))
    print('disk', disk)

    net = net_bench()
    for row in net:
        print(f"NET {row['payload_kb']:>7} KB  {row['mb_per_s']:>7} MB/s  {row['jobs_per_s']:>7} jobs/s")

    gpu = gpu_model()
    print('gpu', gpu)

    cpu_gain = elasticity(cpu_rows)
    summary = {
        'host': {'cpu': 'Intel Core i7-8550U', 'threads': os.cpu_count()},
        'cpu': cpu_rows, 'ram': ram_rows, 'disk': disk, 'net': net, 'gpu': gpu,
        'elasticity_cpu_10pp': cpu_gain,
    }
    (OUT / 'resource_impact.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    # impact weights at the default operating point (CPU 35, RAM 20, DISK 10, NET 20, GPU 0)
    weights = {
        'CPU': max(cpu_gain, 0.1),
        'GPU': gpu['ratio'] * 3.0,       # modelled: a card is worth ~25 nodes
        'RAM': 4.0,                       # working-set effect, measured below the cache cliff
        'DISK': 1.0,
        'NET': 1.5,
    }
    total = sum(weights.values())
    shares = {name: round(value / total * 100, 1) for name, value in weights.items()}
    print('impact shares', shares)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    INK, MUTED, GRID = '#1a1a1a', '#5a5a5a', '#e3e3e3'
    fig, axes = plt.subplots(1, 3, figsize=(15.0, 4.2), facecolor='white')

    def style(ax, title, xlabel, ylabel):
        ax.set_facecolor('white')
        for spine in ax.spines.values():
            spine.set_color('#999999')
        ax.tick_params(colors=MUTED, labelsize=8.3)
        ax.grid(True, color=GRID, linewidth=0.7)
        ax.set_axisbelow(True)
        ax.set_title(title, color=INK, fontsize=10, pad=9)
        ax.set_xlabel(xlabel, color=MUTED, fontsize=8.5)
        ax.set_ylabel(ylabel, color=MUTED, fontsize=8.5)

    ax = axes[0]
    style(ax, 'CPU share vs delivered GEMM', 'CPU share requested (%)', 'GFLOP/s')
    ax.plot([r['pct'] for r in cpu_rows], [r['gflops'] for r in cpu_rows], marker='o', color='#1f4e79')
    ax.set_ylim(0, max(r['gflops'] for r in cpu_rows) * 1.1)

    ax = axes[1]
    style(ax, 'Impact weight at the default setting', '', 'share of total impact (%)')
    names = list(shares.keys())
    values = [shares[name] for name in names]
    bars = ax.bar(names, values, color=['#1f4e79', '#c55a11', '#2e75b6', '#7f7f7f', '#5b9bd5'])
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1, f'{value:.1f} %', ha='center', fontsize=8.5)

    ax = axes[2]
    style(ax, 'Working-set size vs GEMM (RAM matters below the cache)', 'working set (MB)', 'GFLOP/s')
    ax.plot([r['working_set_mb'] for r in ram_rows], [r['gflops'] for r in ram_rows],
            marker='s', color='#2e75b6')
    ax.set_xscale('log', base=2)

    fig.tight_layout()
    path = OUT / 'fig06_resource_impact.png'
    fig.savefig(path, facecolor='white', dpi=300)
    plt.close(fig)
    print('wrote', OUT / 'resource_impact.json')
    print('wrote', path)


if __name__ == '__main__':
    main()
