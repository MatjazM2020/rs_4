# Matrix Transpose GEM5 Performance Analysis

Simulations run with 2, 4, and 8 compute units.
Values are averaged across all CUs within each section.

## Metrics by Compute Unit

### loadLatencyDist::mean

| CU | Naive | Shared | Ratio (N/S) |
|----|-------|--------|-------------|
| 2 | 20921133.79 | 5799950.20 | 3.607 |
| 4 | 41459984.86 | 12115865.97 | 3.422 |
| 8 | 84761997.80 | 25255891.85 | 3.356 |

### vALUInsts

| CU | Naive | Shared | Ratio (N/S) |
|----|-------|--------|-------------|
| 2 | 36864.00 | 53248.00 | 0.692 |
| 4 | 18432.00 | 26624.00 | 0.692 |
| 8 | 9216.00 | 13312.00 | 0.692 |

### ldsBankAccesses

| CU | Naive | Shared | Ratio (N/S) |
|----|-------|--------|-------------|
| 2 | 0.00 | 262144.00 | 0.000 |
| 4 | 0.00 | 131072.00 | 0.000 |
| 8 | 0.00 | 65536.00 | 0.000 |

### totalCycles

| CU | Naive | Shared | Ratio (N/S) |
|----|-------|--------|-------------|
| 2 | 1259682.50 | 610289.50 | 2.064 |
| 4 | 1263212.25 | 616540.75 | 2.049 |
| 8 | 1331884.38 | 615565.62 | 2.164 |

### vpc

| CU | Naive | Shared | Ratio (N/S) |
|----|-------|--------|-------------|
| 2 | 3.12 | 11.38 | 0.274 |
| 4 | 1.56 | 5.63 | 0.276 |
| 8 | 0.74 | 2.82 | 0.262 |

## Scalability (Total Cycles)

### Naive

| CU | Total Cycles | Speedup vs 2 CU |
|----|-------------|-----------------|
| 2 | 1259682 | 1.000x |
| 4 | 1263212 | 0.997x |
| 8 | 1331884 | 0.946x |

### Shared Memory

| CU | Total Cycles | Speedup vs 2 CU |
|----|-------------|-----------------|
| 2 | 610290 | 1.000x |
| 4 | 616541 | 0.990x |
| 8 | 615566 | 0.991x |

## Full Comparison per CU

### 2 Compute Units

| Metric | Naive | Shared | Diff (N-S) | Change % |
|--------|-------|--------|------------|----------|
| loadLatencyDist::mean | 20921133.79 | 5799950.20 | 15121183.59 | 72.3% |
| vALUInsts | 36864.00 | 53248.00 | 16384.00 | 44.4% |
| ldsBankAccesses | 0.00 | 262144.00 | 262144.00 | 0.0% |
| totalCycles | 1259682.50 | 610289.50 | 649393.00 | 51.6% |
| vpc | 3.12 | 11.38 | 8.26 | 264.7% |

### 4 Compute Units

| Metric | Naive | Shared | Diff (N-S) | Change % |
|--------|-------|--------|------------|----------|
| loadLatencyDist::mean | 41459984.86 | 12115865.97 | 29344118.90 | 70.8% |
| vALUInsts | 18432.00 | 26624.00 | 8192.00 | 44.4% |
| ldsBankAccesses | 0.00 | 131072.00 | 131072.00 | 0.0% |
| totalCycles | 1263212.25 | 616540.75 | 646671.50 | 51.2% |
| vpc | 1.56 | 5.63 | 4.08 | 262.0% |

### 8 Compute Units

| Metric | Naive | Shared | Diff (N-S) | Change % |
|--------|-------|--------|------------|----------|
| loadLatencyDist::mean | 84761997.80 | 25255891.85 | 59506105.96 | 70.2% |
| vALUInsts | 9216.00 | 13312.00 | 4096.00 | 44.4% |
| ldsBankAccesses | 0.00 | 65536.00 | 65536.00 | 0.0% |
| totalCycles | 1331884.38 | 615565.62 | 716318.75 | 53.8% |
| vpc | 0.74 | 2.82 | 2.08 | 282.3% |

## Discussion
From the results we can see that the shared memory version of the kernel has load latency that is 3.4-3.6x lower, from the fewer cache line conflicts. Total cycles drop
by ~50% despite the shared kernel executing 44% more vector ALU instructions. The extra index arithmetic is a good off trade for eliminating stalls on non-coalesced writes. Vectors per cycle is alo 3.6-3.8x higher, showing the shared kernel keeps the execution units much busier. LDS bank accesses go from 0 (naive) to 262K per CU at 2 CU, matching the 512x512 element count.

It also seems that neither kernel scales with additional compute units. With minimal total cycle changes between different CU counts, but load latency roughly doubles with each CU doubling. This indicates that both kernels are bound by the memory bandwith.

