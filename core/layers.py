"""Multi-Layer Process: the same work as a single loop, or as a pipelined set of processes.

The point is not "more processes is faster". The point is that a layer which is slow (storage, policy)
should not stop the layer that is fast (the kernel), and that the pipeline can be measured.
"""
from __future__ import annotations

import multiprocessing as mp
import os
import queue
import threading
import time
from dataclasses import dataclass

import numpy as np


def layer_kernel(payload: np.ndarray, weight: np.ndarray) -> np.ndarray:
    """L4: the matrix kernel."""
    return payload @ weight


def layer_normalise(payload: np.ndarray, _weight: np.ndarray) -> np.ndarray:
    """L3: cheap per-item bookkeeping (scale to unit magnitude, as a scheduler would)."""
    scale = np.abs(payload).max() or 1.0
    return payload / scale


def layer_fingerprint(payload: np.ndarray, _weight: np.ndarray) -> np.ndarray:
    """L5: a storage-shaped step — touch every element so memory traffic is real."""
    return np.ascontiguousarray(payload) + 0.0


LAYERS = [layer_kernel, layer_normalise, layer_fingerprint]


@dataclass
class PipelineResult:
    stages: int
    items: int
    seconds: float

    @property
    def throughput(self) -> float:
        return self.items / self.seconds

    @property
    def latency_ms(self) -> float:
        return self.seconds / self.items * 1000


def _worker(index: int, inbox: queue.Queue, outbox: queue.Queue, weight: np.ndarray, functions):
    function = functions[index]
    while True:
        item = inbox.get()
        if item is None:
            outbox.put(None)
            return
        outbox.put(function(item, weight))


def run_sequential(items: int, weight: np.ndarray, payload: np.ndarray, stages: int) -> PipelineResult:
    functions = LAYERS[:stages]
    started = time.perf_counter()
    for _ in range(items):
        value = payload
        for function in functions:
            value = function(value, weight)
    return PipelineResult(stages=stages, items=items, seconds=time.perf_counter() - started)


def run_pipeline(items: int, weight: np.ndarray, payload: np.ndarray, stages: int, depth: int = 4) -> PipelineResult:
    functions = LAYERS[:stages]
    context = mp.get_context('spawn')
    # Every hop is bounded except the last one: nobody drains the sink, and a bounded sink would
    # deadlock the whole pipeline once it fills (the classic pipeline back-pressure trap).
    queues = [context.Queue(maxsize=depth) for _ in range(stages)] + [context.Queue()]
    processes = []
    for index in range(stages):
        process = context.Process(target=_worker, args=(index, queues[index], queues[index + 1], weight, functions))
        process.start()
        processes.append(process)

    started = time.perf_counter()
    stop = threading.Event()

    def drain():
        """A process that finishes still joins its queue feeder thread, so the sink must be read."""
        while not stop.is_set():
            try:
                item = queues[-1].get(timeout=0.1)
            except queue.Empty:
                continue
            if item is None:
                return

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()

    for _ in range(items):
        queues[0].put(payload.copy())
    # One sentinel is enough: every worker forwards it downstream after its own work is done.
    queues[0].put(None)
    for process in processes:
        process.join(timeout=120)
    seconds = time.perf_counter() - started
    stop.set()
    reader.join(timeout=2)
    for process in processes:
        if process.is_alive():
            process.terminate()
    return PipelineResult(stages=stages, items=items, seconds=seconds)


def default_problem(size: int = 256, seed: int = 11):
    rng = np.random.default_rng(seed)
    return rng.standard_normal((size, size), dtype=np.float32), rng.standard_normal((size, size), dtype=np.float32)


def note():
    return f'{os.cpu_count()} logical CPUs visible to the pipeline'
