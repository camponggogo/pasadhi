"""Heterogeneous fleet: one scheduler, cards from a 2 GB GTX 1050 to an 80 GB A100.

The interesting question is not "how many FLOPs do we own" but "which card should this job land on".
Three policies are implemented and measured against the same job mix:

    best_fit   smallest card whose VRAM fits — preserves the big cards for the jobs that need them
    fastest    highest throughput that fits — drains the queue quickly, burns the big cards
    worst_fit  largest card that fits — the naive policy, kept as the baseline
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Card:
    name: str
    vram_gb: float
    tflops_f32: float
    tops_int8: float
    bandwidth_gbps: float
    watts: float


GTX1050 = Card('GTX 1050 2GB', 2.0, 1.862, 3.72, 112.0, 75.0)
T4 = Card('Tesla T4 16GB', 16.0, 8.141, 130.0, 320.0, 70.0)
RTX3060 = Card('RTX 3060 12GB', 12.74, 12.74, 25.5, 360.0, 170.0)
RTX4090 = Card('RTX 4090 24GB', 24.0, 82.58, 165.0, 1008.0, 450.0)
A100 = Card('A100 40GB', 40.0, 19.5, 624.0, 1555.0, 250.0)

# A realistic mixed inventory for an organisation that bought whatever was cheap over five years.
MIXED = {GTX1050: 1000, T4: 200, RTX3060: 200, RTX4090: 40, A100: 10}


@dataclass
class Job:
    vram_gb: float
    flops: float
    index: int = 0


@dataclass
class Slot:
    card: Card
    busy_until: float = 0.0
    busy_total: float = 0.0
    jobs: int = 0


@dataclass
class Result:
    policy: str
    scenario: str
    makespan: float
    mean_wait: float
    throughput_tflops: float
    rejected: int
    utilisation: dict = field(default_factory=dict)
    per_class_jobs: dict = field(default_factory=dict)
    class_finish: dict = field(default_factory=dict)


def inventory(mix: dict[Card, int]) -> list[Slot]:
    slots = []
    for card, count in mix.items():
        slots.extend(Slot(card=card) for _ in range(count))
    return slots


def job_stream(count: int, seed: int = 5, scenario: str = 'mixed') -> list[Job]:
    """70 % small, 20 % medium, 8 % large, 2 % huge — measured against the 2 GB card's reality.

    scenario='no_huge' drops the 35 GB jobs, which is what most organisations actually run.
    """
    rng = random.Random(seed)
    jobs = []
    for index in range(count):
        roll = rng.random()
        if roll < 0.70:
            jobs.append(Job(vram_gb=0.4, flops=2e9, index=index))
        elif roll < 0.90:
            jobs.append(Job(vram_gb=6.0, flops=2e11, index=index))
        elif roll < 0.98 or scenario == 'no_huge':
            jobs.append(Job(vram_gb=18.0, flops=2e12, index=index))
        else:
            jobs.append(Job(vram_gb=35.0, flops=2e13, index=index))
    return jobs


def fits(slot: Slot, job: Job) -> bool:
    return job.vram_gb <= slot.card.vram_gb * 0.9


def choose(policy: str, candidates: list[Slot]) -> Slot:
    if policy == 'best_fit':
        return min(candidates, key=lambda slot: (slot.card.vram_gb, slot.busy_until))
    if policy == 'fastest':
        return max(candidates, key=lambda slot: (slot.card.tflops_f32, -slot.busy_until))
    if policy == 'worst_fit':
        return max(candidates, key=lambda slot: (slot.card.vram_gb, -slot.busy_until))
    raise ValueError(policy)


def run(policy: str, jobs: list[Job], mix: dict[Card, int], efficiency: float = 0.7,
        scenario: str = 'mixed') -> Result:
    slots = inventory(mix)
    waits, rejected = [], 0
    total_flops = 0.0
    class_finish = {}

    for job in jobs:
        candidates = [slot for slot in slots if fits(slot, job)]
        if not candidates:
            rejected += 1
            continue
        slot = choose(policy, candidates)
        start = slot.busy_until
        duration = job.flops / (slot.card.tflops_f32 * 1e12 * efficiency)
        waits.append(start)
        slot.busy_until = start + duration
        slot.busy_total += duration
        slot.jobs += 1
        total_flops += job.flops
        key = f'{job.vram_gb:g}GB'
        class_finish[key] = max(class_finish.get(key, 0.0), slot.busy_until)

    makespan = max((slot.busy_until for slot in slots), default=0.0) or 1e-9
    utilisation = {}
    per_class = {}
    for slot in slots:
        name = slot.card.name
        utilisation.setdefault(name, [0.0, 0])
        utilisation[name][0] += slot.busy_total
        utilisation[name][1] += 1
        per_class[name] = per_class.get(name, 0) + slot.jobs
    utilisation = {name: round(busy / (count * makespan), 4) for name, (busy, count) in utilisation.items()}

    return Result(
        policy=policy,
        scenario=scenario,
        makespan=round(makespan, 2),
        mean_wait=round(sum(waits) / max(1, len(waits)), 2),
        throughput_tflops=round(total_flops / makespan / 1e12, 1),
        rejected=rejected,
        utilisation=utilisation,
        per_class_jobs=per_class,
        class_finish={key: round(value, 2) for key, value in class_finish.items()},
    )


def aggregate(mix: dict[Card, int], dtype: str = 'f32') -> dict:
    if dtype == 'f32':
        peak = sum(card.tflops_f32 * count for card, count in mix.items())
    else:
        peak = sum(card.tops_int8 * count for card, count in mix.items())
    power = sum(card.watts * count for card, count in mix.items()) / 1000
    vram = sum(card.vram_gb * count for card, count in mix.items())
    return {
        'dtype': dtype,
        'peak_pflops': round(peak / 1000, 2) if dtype == 'f32' else round(peak / 1000, 1),
        'power_kw': round(power, 1),
        'vram_tb': round(vram / 1024, 1),
        'cards': sum(mix.values()),
        'gflops_per_watt': round(peak * 1000 / (power * 1000), 1),
    }
