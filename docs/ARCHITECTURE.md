# PASADHI architecture

**One virtual machine, many old PCs.** Four planes, one contract: a matrix operation goes in, a result comes
back, and every hop is measured.

```
┌──────────────────────────────────────────────────────────────────────┐
│ L5  STORAGE      chunk store, content-addressed blocks, local disks   │
├──────────────────────────────────────────────────────────────────────┤
│ L4  KERNEL       GEMM / quantised GEMM / FFT-as-GEMM / conv-as-GEMM   │
├──────────────────────────────────────────────────────────────────────┤
│ L3  SCHEDULER    tiling, placement, back-pressure, retries            │
├──────────────────────────────────────────────────────────────────────┤
│ L2  POLICY       quotas, trust, tenancy, audit (inherited from SUAY)  │
├──────────────────────────────────────────────────────────────────────┤
│ L1  TRANSPORT    TCP with framed messages → shared memory on host     │
└──────────────────────────────────────────────────────────────────────┘
```

## Why layers are processes

A layer that is slow must not stop a layer that is fast. Each layer is a process group with its own bounded
queue; the only unbounded edge is the sink, and the sink is always drained. Back-pressure is explicit: when a
queue is full the producer blocks, which is exactly the signal the scheduler needs.

M0 measured the cost of that decision on one host (256×256 blocks, one hop = one pickle of 256 KB):

| layers | single loop | pipelined | ratio |
|---:|---:|---:|---:|
| 1 | 762 items/s | 294 items/s | 0.39× |
| 2 | 771 items/s | 203 items/s | 0.26× |
| 3 | 416 items/s | 227 items/s | 0.55× |

**A process pipeline loses to a loop when the payload is small.** That is not a failure of the design; it is the
crossover point, and it sets the next milestone: shared-memory transport for on-host hops, and 4–64 MiB tiles for
cross-host hops, where the compute per byte is high enough to pay for the copy.

## The kernel contract

```
gemm(a: f32[n,k], b: f32[k,m]) -> f32[n,m]
gemm(qa: int8[n,k]·scale, qb: int8[k,m]·scale) -> f32[n,m]
```

Measured on an i7-8550U (4 cores / 8 threads, AVX2, 8 MB L3), numpy 2.5.4 with OpenBLAS 0.3.34:

| kernel | GFLOP/s | note |
|---|---:|---|
| f32 via BLAS | **58–74** | the bar every other path must beat |
| explicit 128 tiling over BLAS | 7–11 | Python loop overhead + smaller BLAS calls; BLAS already tiles |
| int8 quantised (numpy) | 1.2 | no packed integer kernel; numpy integer matmul is a fallback |
| int8 relative error vs f32 | 1.0–1.1 % | acceptable for inference, not for accumulation-heavy work |

Thread scaling (n = 1024): 1 thread 38.1, 2 threads 59.0, 4 threads **83.3**, 8 threads 78.4 GFLOP/s. Four
threads is the sweet spot on this part; the eighth hyper-thread competes for the same vector units.

## Old-hardware rules

1. **Memory bandwidth is the ceiling, not FLOPs.** A 4c/8t laptop with DDR4-2400 delivers ~35 GB/s; a 1 024²
   f32 matrix is 4 MiB, so a tiled kernel must keep the working set inside the 8 MB L3.
2. **int8 first, but only with a packed kernel.** Four times the elements per cache line is a real win — once the
   inner loop is C with `vpmaddubsw`/`vpmaddwd`, not numpy.
3. **Never trust one host's clock.** Turbo, thermal throttling and the OS scheduler move results by ±15 %; the
   harness takes the best of three and reports the host.
4. **Idle is the resource.** A machine that is busy 10 % of the day contributes 90 % of its capacity to the pool;
   the scheduler must be able to evict in under a second.

## The distributed step (M1)

The matrix plane shards by **block rows of the output**, not by the model:

```
A (n×k) is split into row panels of 256 rows; each machine owns one panel
B (k×m) is broadcast once, or streamed in column blocks of 4 MiB
each worker returns its panel; the coordinator never holds the full output
```

This is the same arithmetic as model-parallel inference, but the unit is a matrix and the contract is a
retry-safe tile id, so a machine that dies mid-panel is simply re-queued. Transport: length-prefixed frames over
TCP with a 4 MiB cap, then `mmap` on the same host when both ends are local.

## Inheritance from SUAY

PASADHI keeps SUAY's control plane (tokens, scopes, budgets, audit) and its measurement discipline (medians, p95,
negative results kept in). It replaces the AI-only framing with the matrix contract above. Attribution and the
MIT licence are preserved in `NOTICE`.
