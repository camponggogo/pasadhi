# GPU layer: 1 000 × GTX 1050 2 GB

**Design note · 2026-10-22** · model: `pasadhi/core/gpu.py` · harness: `pasadhi/bench/gpu_model.py`
**Every GTX 1050 number below is derived from published specifications, not measured on this host** — the
development machine has no NVIDIA card. The CPU comparison points are measured.

## 1. The card

| Spec | GTX 1050 2 GB (GP107, SM_61) |
|---|---|
| CUDA cores / clock | 640 / 1 354–1 455 MHz |
| FP32 | 1.86 TFLOPS |
| INT8 (DP4A) | ~3.72 TOPS |
| Memory | 2 GB GDDR5, 112 GB/s |
| Bus / power | PCIe 3.0 x16 / 75 W (no auxiliary power) |
| Tensor cores | none (Pascal) |

Two facts follow immediately: **2 GB is the constraint that shapes everything**, and the card is
**power-inefficient** by modern standards — 25 GFLOPS/W against ~78 for an A100.

## 2. Two modes that behave nothing alike

| Mode | What the network carries | 1 000 cards, f32 | 1 000 cards, int8 |
|---|---|---:|---:|
| **Independent** — every card owns its job | results only | **1.30 PFLOPS** | **2.60 POPS** |
| Sharded GEMM · 1 GbE | both operands, every step | 0.16 PFLOPS (8.5 % efficiency) | 0.29 POPS (15.6 %) |
| Sharded GEMM · 10 GbE | both operands, every step | 0.89 PFLOPS (48 %) | 2.41 POPS (64.9 %) |

![fig02](bench/results/fig02_gpu_fleet.png)

**Figure 02.** Left: the share of a card's compute that survives the link, by matrix size. Right: aggregate
throughput for 1 000 cards under each mode.

The left panel is the whole argument: at n = 4 096 on 1 GbE, **91.5 % of the card's time is spent waiting for
data**. The crossover (compute time = transfer time) is at n ≈ 177 000 for f32 on 1 GbE — a matrix of 117 GB,
which cannot exist on a 2 GB card. On 10 GbE the crossover falls to n ≈ 17 700; with int8 to n ≈ 8 900.

## 3. What fits in 2 GB

| Budget | Largest square matrix | Practical meaning |
|---|---:|---|
| f32, two operands | 15 543 | a 15k × 15k GEMM fits, barely |
| int8, two operands | 31 086 | int8 doubles the ceiling |
| LLM weights, int8 | ~1.5–1.8 B params | Qwen2.5-1.5B int8 ≈ 1.5 GB → KV cache nearly nothing left |
| LLM weights, 4-bit | ~2.8–3.2 B params | leaves ~0.3 GB for KV; 7B does not fit, in any precision |

So the honest framing: **this fleet runs many small models and many small matrices, not one big one.**

## 4. Cost, and the uncomfortable comparison

Capital: 1 000 × (฿2 500 used card + ฿9 000 host) = ฿11.5 M, depreciated over 36 months.
Power: 75 kW at the wall for the cards alone (hosts add ~40 kW), ฿4.2/kWh.

| Path | THB per delivered TFLOP |
|---|---:|
| PASADHI CPU node (measured, priced at 70 % margin) | 0.0157 |
| **PASADHI GPU fleet (1 000 × 1050, cost basis)** | **0.0003** |
| PASADHI GPU fleet at 70 % margin | 0.0010 |
| Cloud A100 (list price, Oct 2026) | 0.0010 |

**The GPU fleet lands on the same price per FLOP as renting an A100** — it does not beat the cloud, it matches it,
and only while the cards are nearly free and the labour is unpaid. That is still useful: it matches cloud price
with **residency, no egress and a 36-month asset**. But it is not a margin business on compute alone; the margin
is in the software and the support contract.

## 5. The 1 000-machine reality check

| Item | Number | Consequence |
|---|---:|---|
| Cards + hosts at the wall | 115 kW | a small server room, not an office corner |
| Switch ports | 1 000 | 21 × 48-port switches, or 10 GbE uplinks if sharding matters |
| Physical space | ~1 000 SFF PCs ≈ 18–22 racks | floor space and cooling become the project |
| Spares | 5 % (50 cards, 50 hosts) | ฿575 k of dead stock |
| Maintenance | 2 FTE for 1 000 boxes | ฿1.2 M/year, more than the electricity |
| Driver support | Pascal is on legacy drivers | pin the driver, mirror the installer, no auto-update |

**The arithmetic of scale kills the romance:** at 1 000 machines the operating cost is dominated by people, not
silicon. A 50-machine fleet is an office project; a 1 000-machine fleet is a data-centre project with second-hand
hardware.

## 6. How it plugs into PASADHI

```
pasadhi run job.toml --device gpu|cpu|mixed --vram-budget 1.8
```

- `core/gpu.py` exposes `Device`, `plan_bins()` (first-fit-decreasing over VRAM) and `fleet()` for both modes.
- The scheduler treats a 2 GB card as a **bin**: a job larger than 1.8 GB is split, a job smaller is packed with
  others. Mixed mode sends VRAM-heavy tiles to cards and cache-friendly tiles to CPU nodes.
- Placement prefers local PCIe (16 GB/s) over any network; cross-host sharding is allowed only when the tile's
  arithmetic intensity clears the crossover in §2.
- Failure: a card that disappears mid-tile is re-queued; the tile id is the retry key (same contract as M3).

## 7. What we would build first

1. **CUDA-free day one.** Start with `nvidia-ml-py` for discovery and a DP4A path through `cupy`/`numba`; do not
   write a custom kernel until the scheduler is proven.
2. **Prove independent mode on 10 cards** — that is where 90 % of the value is, and it needs no network work.
3. **Only then** attempt sharded GEMM, and only on 10 GbE or better.
4. **Pin drivers and publish the matrix** of card × driver × CUDA version that is known to work.

## 8. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| 2 GB VRAM | most modern models do not fit | sell it for small models, image tiles and signal work — not for 7B chat |
| Pascal EOL | drivers freeze, CUDA features stop | pin the stack; treat the fleet as an appliance |
| 1 GbE | sharded GEMM is 8.5 % efficient | independent mode by default; 10 GbE is a prerequisite for sharding |
| Heat/noise | office rejection | 75 W cards are quiet; 1 000 of them are not — host them in a room |
| Second-hand supply | quality varies | burn-in test each card (30 min GEMM) before it enters the pool |
