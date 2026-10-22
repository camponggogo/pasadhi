# PASADHI · ปัสสัทธิ

**A virtual distributed machine for old hardware.** PASADHI turns a room of ageing PCs into one addressable
compute surface — matrix-first, process-layered, and honest about what each generation of CPU can actually do.

> Status: **M0 prototype**. Kernel and pipeline benchmarks run on one host. The distributed plane is specified,
> not yet implemented. Numbers below are measured on the development machine (i7-8550U, 4 cores / 8 threads).

## Why

Cloud GPUs are rented by the hour. Offices already own machines that idle for sixteen hours a day. SUAY proved
the control-plane half of that idea: a token gateway, a node plane, prefix caching, expert routing. PASADHI takes
the half that matters for compute: **the kernel, the pipeline and the scheduler** — and it is not only for LLMs.

## The three ideas

1. **Matrix processor first.** Everything is a matrix operation: dense GEMM, quantised GEMM, block-sparse,
   FFT-as-GEMM, convolution-as-GEMM. One optimised path, many workloads.
2. **Multi-Layer Process.** Work is split into layers (L1 transport, L2 policy, L3 scheduler, L4 kernel,
   L5 storage). Each layer is a process group with its own queue, so a slow layer degrades gracefully instead
   of stalling the machine.
3. **Old hardware is the target, not the excuse.** Haswell-era AVX2, 2–8 GB of usable RAM per box, SATA disks.
   The design budgets for it: int8 before fp32, blocking before threads, streaming before caching.

## Quick start

```bash
python pasadhi/bench/run.py            # kernel + pipeline benchmarks, writes bench/results/*.json
python pasadhi/bench/run.py --quick    # smaller sizes
```

## Layout

```
pasadhi/
  core/matrix.py      blocked / quantised GEMM kernels
  core/layers.py      multi-process layer pipeline with back-pressure
  bench/run.py        the harness that produces every number in docs/
  docs/ARCHITECTURE.md
  docs/ROADMAP.md
```

## Commercial

PASADHI is sold as software and support, not as raw FLOPs — the measurements say why.

| | THB per delivered TFLOP |
|---|---:|
| PASADHI node (60 % duty) | **0.016** |
| Cloud CPU (4 vCPU) | 0.028 |
| Cloud GPU (1× A100) | 0.001 |

We lose to a GPU by 17× on price per FLOP and win against cloud CPU by 1.8×. The product is therefore
**residency, sunk hardware and small bursty jobs**, not a cheaper GPU.

- Business plan, pricing and unit economics (Thai): [`docs/BUSINESS.th.md`](docs/BUSINESS.th.md)
- Sales kit: one-pager, deck outline, objections, quote and SOW (Thai): [`docs/SALES_KIT.th.md`](docs/SALES_KIT.th.md)
- Calculator behind every number: `python pasadhi/commercial/pricing.py`

## GPU layer

Small second-hand cards are a different machine, not a faster node: 1 000 × GTX 1050 2 GB gives
**1.30 PFLOPS f32 (2.60 POPS int8)** for independent jobs, but only **0.16 PFLOPS** if a single GEMM
is sharded across them over 1 GbE — 91.5 % of the card's time would wait for data.

- Design, capacity model and the 1 000-machine reality check: [`docs/GPU_FLEET.md`](docs/GPU_FLEET.md)
- Run the model: `python pasadhi/bench/gpu_model.py`

## Provenance

PASADHI is a fork-in-spirit of [SUAY](https://github.com/camponggogo/suay) (MIT). It keeps SUAY's measurement
discipline — medians, p95, negative results kept in — and replaces the AI-only framing with a general
matrix-compute plane. Code is MIT; see `LICENSE`.

Named after *ปัสสัทธิ* — calm, settled, at rest. The machine should be quiet and the numbers should be boring.
