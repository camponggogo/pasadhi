# PASADHI roadmap

Hardware target: Haswell-era office PCs (4c/8t, 8–16 GB RAM, SATA SSD), one 1 GbE switch, no GPU.
Every milestone ends with a number, a figure and a "what did not work" paragraph.

## M0 — the baseline (done, 2026-10-22)

- [x] f32 GEMM baseline via BLAS: **58–74 GFLOP/s** on the i7-8550U
- [x] explicit tiling and int8 quantised GEMM, both **slower** than BLAS (7–11 and 1.2 GFLOP/s)
- [x] thread scaling 1 → 8: 38 / 59 / 83 / 78 GFLOP/s, sweet spot at four threads
- [x] multi-layer process pipeline with back-pressure, measured against a single loop: **0.26–0.55×**
- [x] harness writes `bench/results/summary.json` and one white figure

Exit criterion: a reproducible baseline that any later claim is measured against. Met.

## M1 — a packed int8 kernel in C (next)

The numpy fallback at 1.2 GFLOP/s is the largest single opportunity: AVX2 `vpmaddubsw` + `vpmaddwd` with 6×16
blocking should reach **25–45 GFLOP/s** on this part, a 20–35× gain over the fallback and 3–5× the f32 BLAS path
for the same accuracy budget.

- [ ] C kernel + ctypes binding, `-O3 -mavx2 -mfma`
- [ ] pack/quantise once per weight, reuse across items
- [ ] correctness gate: max relative error ≤ 1.5 % against f32 on 2 048² random matrices
- [ ] benchmark at 256/512/1024/2048 and publish the roofline against DDR4 bandwidth

## M2 — shared memory transport (on-host)

The pipeline loses because every hop pickles 256 KB. Replace `mp.Queue` with a ring buffer in
`multiprocessing.shared_memory` for arrays above 64 KiB.

- [ ] zero-copy handoff for same-host layers
- [ ] target: pipeline ≥ 1.5× the single loop at 512² blocks
- [ ] fallback to pickling below the threshold, with the crossover point measured, not guessed

## M2.5 — GPU layer: 1 000 × GTX 1050 2 GB

Small cards are a different machine, not a faster node. The model (`core/gpu.py`, `bench/gpu_model.py`) says:

- independent jobs: **1.30 PFLOPS f32 / 2.60 POPS int8** across 1 000 cards
- sharded GEMM on 1 GbE: **0.16 PFLOPS (8.5 %)** — 91.5 % of the card's time waits for data
- sharded GEMM on 10 GbE: 0.89 PFLOPS f32, 2.41 POPS int8 (48 % / 64.9 %)
- crossover: n ≈ 177 000 on 1 GbE f32 (impossible in 2 GB), n ≈ 8 900 with int8 on 10 GbE
- cost: ฿0.0003 per delivered TFLOP on cost basis → ฿0.0010 at 70 % margin, i.e. **parity with a rented A100**

- [ ] discovery via `nvidia-ml-py`, DP4A path through cupy/numba
- [ ] VRAM-aware bin packing in the scheduler (`plan_bins`)
- [ ] prove independent mode on 10 cards before any sharding work
- [ ] burn-in test for second-hand cards (30 min GEMM, reject on ECC/thermal faults)
- [ ] publish the supported matrix: card × driver × CUDA version

## M2.6 — one scheduler for 1050s and A100s

Fifteen hundred cards of five generations, one placement decision. The simulation (`core/hetero.py`) says:

- 2 % of jobs need 35 GB → only ten A100s can run them → **92 % utilisation on those cards while 1 440 idle**;
  the makespan is 13.19 s regardless of policy
- with the tail removed, policy is worth **19×**: best_fit 0.38 s vs worst_fit 7.31 s
- aggregate: 9.54 PFLOPS f32, 47.7 POPS int8, 143.5 kW, ฿0.00007 per delivered TFLOP (cost basis)

- [ ] split any job larger than the largest spare card (tile / split-K) instead of queueing it
- [ ] policy hook in the scheduler (`hetero.choose`), best_fit as the default
- [ ] per-class utilisation on the dashboard; total FLOPs hides the idle fleet
- [ ] 10/25 GbE for the big cards only; 1 GbE stays for the 1050 tier

## M3 — distributed matrix plane (two hosts, then ten)

- [ ] row-panel sharding of the output, 256-row panels, retry-safe tile ids
- [ ] length-prefixed TCP frames, 4 MiB cap, checksum per frame
- [ ] coordinator never materialises the full output
- [ ] measure: GFLOP/s per machine, end-to-end latency, recovery time after killing a worker mid-panel
- [ ] target: 10 machines × 40 GFLOP/s int8 ≈ **350–400 GFLOP/s** aggregate on 1 GbE (bandwidth budget: a
      1 024² f32 panel is 4 MiB, so a 4 MiB/s link caps at ~1 panel per second — the arithmetic has to be
      checked before the claim)

## M4 — workloads beyond AI

- [ ] convolution as GEMM (im2col) — image filters on old hardware
- [ ] FFT as GEMM for small transforms; direct FFT above 4 096 points
- [ ] block-sparse GEMM for graph and PDE workloads
- [ ] one CLI: `pasadhi run job.toml`, one dashboard, one quota system (inherited from SUAY)

## M5 — the virtual machine

- [ ] one address space across machines: `pasadhi matmul --rows 65536 --cols 65536 --workers 10`
- [ ] placement aware of RAM, current load and link speed
- [ ] checkpoint the tile graph so a reboot costs minutes, not the job
- [ ] publish a paper: "Matrix-first virtual machines on hardware that was written off"

## Rules for every milestone

1. A number without a host name and a date is not a number.
2. Keep the failed configurations in the repository; they are the documentation.
3. If a layer cannot be measured in isolation, it is not a layer yet.
