"""Role selection: one application, three jobs — coordinator, worker, client.

The decision is deliberately boring and explainable: score the machine, print the reasons, let the user
override. No role is chosen by asking the user a question they cannot answer.
"""
from __future__ import annotations

from dataclasses import dataclass

from .probe import Hardware


@dataclass
class Decision:
    role: str
    score: float
    reasons: list
    can_coordinator: bool
    can_worker: bool


def _score(hw: Hardware) -> tuple[float, list]:
    reasons = []
    score = 0.0

    score += min(hw.cores_logical, 16) * 1.0
    reasons.append(f'{hw.cores_logical} logical cores → +{min(hw.cores_logical, 16):.0f}')

    memory_points = min(hw.ram_gb, 64) / 4
    score += memory_points
    reasons.append(f'{hw.ram_gb:.0f} GB RAM → +{memory_points:.1f}')

    disk_points = min(hw.disk_free_gb, 2000) / 100
    score += disk_points
    reasons.append(f'{hw.disk_free_gb:.0f} GB free disk → +{disk_points:.1f}')

    if hw.has_gpu:
        vram_points = min(max(hw.gpu_vram_gb, 2.0), 40) * 1.2
        score += vram_points
        reasons.append(f'GPU {hw.gpu_name} ({hw.gpu_vram_gb:g} GB) → +{vram_points:.1f}')

    if hw.network_mbps >= 1000:
        score += 4
        reasons.append('wired 1 GbE or better → +4')
    elif hw.network_mbps >= 100:
        score += 2
        reasons.append(f'{hw.network_mbps:.0f} Mbit/s link → +2')

    if hw.uptime_hours >= 168:
        score += 4
        reasons.append(f'uptime {hw.uptime_hours/24:.1f} days → +4')
    elif hw.uptime_hours >= 24:
        score += 2
        reasons.append(f'uptime {hw.uptime_hours/24:.1f} days → +2')

    if hw.on_battery:
        score -= 6
        reasons.append('on battery → −6')

    return round(score, 1), reasons


def decide(hw: Hardware, requested: str = 'auto') -> Decision:
    score, reasons = _score(hw)

    can_worker = (hw.cores_logical >= 2 and hw.ram_gb >= 4)
    can_coordinator = (hw.cores_logical >= 4 and hw.ram_gb >= 8 and hw.uptime_hours >= 24
                       and hw.network_mbps >= 100)

    if requested in ('coordinator', 'worker', 'client'):
        role = requested
    else:
        if can_coordinator and score >= 20:
            role = 'coordinator'
        elif can_worker:
            role = 'worker'
        else:
            role = 'client'

    return Decision(role=role, score=score, reasons=reasons,
                    can_coordinator=can_coordinator, can_worker=can_worker)


def explain(decision: Decision) -> str:
    head = f'role={decision.role} score={decision.score}'
    return head + '\n  ' + '\n  '.join(decision.reasons)
