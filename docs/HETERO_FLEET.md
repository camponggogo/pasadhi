# Heterogeneous fleet: from a 2 GB GTX 1050 to an A100, one scheduler

**Design note · 2026-10-22** · model: `pasadhi/core/hetero.py` · harness: `pasadhi/bench/hetero_model.py`
Card figures are **published specifications**; the scheduler is **simulated**, not run on hardware.

## 1. The inventory

| Class | Cards | VRAM | f32 TFLOP/s | int8 TOPS | GB/s | W |
|---|---:|---:|---:|---:|---:|---:|
| GTX 1050 | 1 000 | 2 GB | 1.86 | 3.7 | 112 | 75 |
| Tesla T4 | 200 | 16 GB | 8.14 | 130 | 320 | 70 |
| RTX 3060 | 200 | 12 GB | 12.74 | 25.5 | 360 | 170 |
| RTX 4090 | 40 | 24 GB | 82.58 | 165 | 1 008 | 450 |
| A100 40GB | 10 | 40 GB | 19.5 | 624 | 1 555 | 250 |
| **Total** | **1 450** | **8.9 TB** | **9.54 PFLOPS** | **47.7 POPS** | — | **143.5 kW** |

Aggregate efficiency: **66.5 GFLOP/s per watt** (f32) or 332 (int8). The ten A100s alone carry **13 % of the
int8 capacity** despite being 0.7 % of the cards — one big card is worth ~170 GTX 1050s for int8 work.

## 2. Which card should a job land on?

Three policies, the same 4 000-job stream (70 % small, 20 % medium, 8 % large, 2 % huge):

| Policy | mixed makespan | no-huge makespan | What happens |
|---|---:|---:|---|
| **best_fit** (smallest card that fits) | 13.19 s | **0.38 s** | small jobs on 1050s, big cards stay free |
| fastest (highest TFLOP/s that fits) | 13.19 s | 0.45 s | everything piles onto the 4090s; 1 200 cards idle |
| worst_fit (largest card that fits) | 18.71 s | 7.31 s | all work queues on the A100s; 19× slower than best_fit |

![fig03](bench/results/fig03_hetero_fleet.png)

**Figure 03.** Left: makespan per policy in both scenarios. Right: who actually did the work when the huge jobs
are removed.

Two findings that matter more than the policy choice:

1. **The tail sets the makespan.** In the mixed stream, 2 % of jobs (35 GB) can only run on the ten A100s, which
   then sit at **92 % utilisation while 1 440 cards idle**. All three policies land within 5 % of each other
   because the tail, not the policy, owns the clock.
2. **Once the tail is removed, policy is worth 19×.** best_fit finishes in 0.38 s against 7.31 s for worst_fit —
   the naive "send it to the biggest card" rule is the most expensive line of code in the system.

## 3. The rule this produces

```
if job.vram > largest_spare_card:      split the job (tile / split-K), do not queue it
elif capacity_of(card) - job.vram > 0:  best_fit among cards that fit
else:                                   queue, and tell the operator which class is saturated
```

Splitting the 35 GB tail is the single highest-value optimisation in the fleet: it converts a 13.19 s makespan
into something closer to the 0.38 s of the no-huge case, without buying a single card. That is the M2.6 milestone.

## 4. Money

Assumptions: 1050 ฿2 500 · T4 ฿9 000 · 3060 ฿9 500 · 4090 ฿45 000 · A100 ฿150 000 (all second-hand), one host per
card at ฿9 000, 36-month life, ฿4.2/kWh, 60 % duty.

| Item | Value |
|---|---:|
| Capital | ฿22.6 M |
| Depreciation + power | ฿1.07 M / month |
| Delivered (60 % duty) | ≈15 000 000 TFLOP / month |
| **Cost per delivered TFLOP** | **฿0.00007** |
| Cloud A100 at list price | ฿0.001 |

The mixed fleet is ~14× cheaper per FLOP than renting, but only if the utilisation problem in §2 is solved —
otherwise the honest number is the 13.19 s makespan and most of that capital is idle.

## 5. Operating a mixed fleet

| Reality | Consequence |
|---|---|
| 5 driver generations, Pascal → Ampere | pin one driver branch per class; never auto-update a working fleet |
| 1 GbE everywhere is not enough for A100s | big cards need 10/25 GbE or they starve; small cards do not |
| 143.5 kW for the cards, ~60 kW more for hosts | this is a server room, not an office corner |
| Mixed failure rates | burn-in every second-hand card; keep 5 % spares per class |
| Wrong policy is invisible | log policy decisions and utilisation per class; a dashboard showing only total FLOPs hides §2 |

## 6. In PASADHI

```python
from pasadhi.core.hetero import MIXED, job_stream, run
result = run('best_fit', job_stream(4000), MIXED, scenario='mixed')
```

- `hetero.choose()` is the policy hook; `run()` is the list scheduler used for the numbers above.
- `plan_bins()` in `core/gpu.py` remains the VRAM packer for independent jobs.
- The scheduler's contract: **a job larger than any spare card is split, never queued**. M2.6 implements it.

## 7. Limits

- The simulation assumes every card is free at t=0, perfect network, and no thermal throttling — real makespans
  will be worse, especially for the 4090s in a small room.
- Card figures are specifications, not measurements; the 70 % efficiency constant is the same for every class,
  which flatters Pascal and penalises Ampere slightly (Tensor Cores are not modelled).
- Job mix (70/20/8/2) is an assumption; a real customer's mix must be measured before quoting a makespan.
