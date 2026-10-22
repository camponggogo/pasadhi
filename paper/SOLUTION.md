# PASADHI: one pool from the machines you already own

**A solution paper · v1.0 · 23 October 2026** · PASADHI contributors · MIT for the open core

## Abstract

Organisations already own the hardware they need; what they lack is a way to use it as one machine. PASADHI
turns office PCs, servers, laptops and small GPUs into a single compute pool with four properties: it is
**matrix-first**, **layered as processes**, **priced by measured impact**, and **honest about the physics**.
On a 50-machine test bed we measure 15.7 req/s from one gateway worker and 22.3–24.8 req/s from two; a content
addressed prefix cache lifts time-to-first-token on an 8 000-token document from 111.4 s to 0.71 s (157×); a
document-aware router reaches 90.15 % accuracy in 31.5 µs; and a mixed fleet of 1 450 cards (2 GB to 40 GB)
aggregates 9.54 PFLOPS f32 and 47.7 POPS int8 at 143.5 kW. The design rule that survives every measurement is
simple: **the inner loop stays local, and the price follows the measurement**.

## 1. The problem, stated exactly

A cloud GPU is rented by the hour and priced per token. An office already owns machines that idle for sixteen
hours a day. The naive arithmetic — sum the RAM, sum the FLOPs — fails for a reason that has nothing to do with
silicon: coordination cost. Our first 50-machine run made this visible in one table: throughput sat at 12 req/s
while latency grew linearly, and at 50 concurrent clients **96.5 % of the response time was queueing** above a
174 ms service floor. The fleet was not slow; the control path was.

## 2. The solution in one picture

```
 L5 storage     content-addressed blocks, local disks
 L4 kernel      GEMM · int8 GEMM · FFT/conv as GEMM
 L3 scheduler   tiling, placement, back-pressure, retries
 L2 policy      identity, scopes, budgets, audit
 L1 transport   framed TCP; shared memory on the same host
```

Each layer is a process group with its own bounded queue. A slow layer blocks its producer, which is the signal
the scheduler needs; no layer can stall another. The gateway and the node plane are separate processes, so a
heartbeat storm cannot delay an inference request.

## 3. What we measured, and what it bought

| Change | Before | After |
|---|---|---|
| Node plane separated from the gateway | 44 req/s heartbeat, 210 ms at C=1 | **161 req/s per shard, 105 ms** |
| Live node list cached for 5 s | 4.9 req/s at C=8 | **15.0 req/s** |
| Two gateway workers | 15.7 req/s | **22.3 / 24.8 req/s** (C=8 / C=16) |
| Prefix cache, 8 000-token document | 111.4 s to first token | **0.71 s, 88.2 % reuse** |
| Document-aware router | — | **90.15 %, 31.5 µs** |
| Domain experts instead of a mixture | 86 machines, infeasible | **32 machines, 0.64 req/s (10.7×)** |
| Mixed fleet of 1 450 cards | — | **9.54 PFLOPS f32, 47.7 POPS, 143.5 kW** |

Three numbers deserve emphasis because they decide architecture, not tuning:

1. **The gateway ceiling is the event loop.** A raw health endpoint serves 58.7–71.2 req/s; a completion costs
   ≈60 ms of loop time. Workers scale until the host does: four workers peak at 29.1 req/s at C=8 and fall to
   20.5 at C=32.
2. **Prefix reuse is the largest single win.** 157× on the median, with p95 unchanged — the cache fixes the
   median, not the tail.
3. **Ports are not throughput.** Two ports beat two workers by 16 % because each process owns its accept queue;
   a userspace proxy gives the gain back (−25 %), and a hundred ports buy 4.4 GiB of memory and no extra
   request per second.

## 4. Capacity, priced by impact

Contributions are paid by what they actually contribute, weighted from the same sweep that produced the
performance numbers: **CPU 98.0 %**, RAM 0.4 %, disk 1.0 %, network 0.6 % on a CPU-only node; **CPU 56.6 %,
GPU 42.2 %** once a GTX 1050 is present. A four-thread machine shared at 100 % earns exactly 2.50 THB per hour;
an eight-thread machine at 35 % earns ≈711 THB per month.

That honesty changes the commercial model. At a 30 % share a 150-machine office earns 53 460 THB per month
against a 149 745 THB subscription, so the break-even share is ≈60 %, or the group price must fall to ≈350 THB
per machine. The product is therefore sold three ways: **share and use free**, **rent monthly/yearly**, or
**buy an on-prem licence** scoped to a group, unlimited machines, departments rolled up, multi-licence merge for
enterprises.

## 5. The fleet we would build

| Tier | What | Why |
|---|---|---|
| Office tier | 100–200 desktops and laptops, 20–30 % each | the capacity already exists and is paid for |
| Accelerator tier | small cards (2–16 GB) for independent jobs | 22× per card on the same job; independent jobs need no network |
| Anchor tier | a few 24–80 GB cards | the only place a 35 GB job can run; without them the tail owns the clock |
| Network | 1 GbE for the office tier, 10 GbE only for the anchor tier | sharded GEMM keeps 6.9 % of compute across an antipodal fibre link and 32.3 % over LEO; the inner loop must stay local |

## 6. What is deliberately not in the product

- **No 50-way pipeline sharding.** S* is 3–10 stages, overhead is 150 ms per step, and activation traffic would
  be 65.5 Mbit/s — 1 922× the measured gateway traffic.
- **No interplanetary inner loop.** A 4 096³ GEMM keeps 0.004 % of compute across Earth–Mars; only
  store-and-forward, checkpointed work crosses that link.
- **No claim of cheaper FLOPs than a GPU.** A used-card fleet lands at ฿0.0010 per delivered TFLOP, the same as
  a rented A100. The margin comes from software, support and residency, not from silicon.

## 7. Roadmap

| Milestone | Evidence it is done |
|---|---|
| M1 packed int8 kernel in C/AVX2 | 25–45 GFLOP/s on the reference part, ≤1.5 % error |
| M2 shared-memory transport | pipeline ≥1.5× the single loop at 512² blocks |
| M2.7 group controller | join tokens, quotas, offline autonomy, per-department billing |
| M3 distributed matrix plane | row-panel sharding, retry-safe tiles, recovery after a mid-panel kill |
| M6 public network | redundant execution 2× + 5 % spot checks, credit ledger with a daily Merkle root |

## 8. Limits

Every number here comes from one host (8 vCPU, Docker Desktop), a mock backend and published card
specifications. The fleet ceilings move with the host; the shape of the results does not. Where a figure is
modelled rather than measured, the text says so.

## Appendix: where each number lives

`report/RPS_LIMIT.md` (gateway ceiling), `report/MULTIPORT_100.md` (ports), `report/KV_CACHE.md` (prefix reuse),
`report/EXPERTS_WHITEPAPER.md` (router), `report/HETERO_FLEET.md` (mixed fleet), `report/IMPACT_PRICING.th.md`
(weights), `report/GROUP.th.md` (group economics), `pasadhi/core/orbit.py` (link budgets).
