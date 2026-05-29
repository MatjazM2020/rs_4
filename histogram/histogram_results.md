# Histogram GEM5 Performance Analysis

Simulations run with 2, 4, and 8 compute units.
Values are averaged across all CUs within the kernel execution section.

## Metrics by Compute Unit

### loadLatencyDist::mean

| CU | Naive | Optimized | Ratio (N/O) |
|----|-------|-----------|-------------|
| 2 | 6268409.67 | 1334480.22 | 4.697 |
| 4 | 12246139.77 | 2868275.51 | 4.270 |
| 8 | 23756984.01 | 7077776.37 | 3.357 |

### vALUInsts

| CU | Naive | Optimized | Ratio (N/O) |
|----|-------|-----------|-------------|
| 2 | 22528.00 | 28672.00 | 0.786 |
| 4 | 11264.00 | 14336.00 | 0.786 |
| 8 | 5632.00 | 7168.00 | 0.786 |

### ldsBankAccesses

| CU | Naive | Optimized | Ratio (N/O) |
|----|-------|-----------|-------------|
| 2 | 0.00 | 393216.00 | 0.000 |
| 4 | 0.00 | 196608.00 | 0.000 |
| 8 | 0.00 | 98304.00 | 0.000 |

### totalCycles

| CU | Naive | Optimized | Ratio (N/O) |
|----|-------|-----------|-------------|
| 2 | 830444.00 | 296969.00 | 2.796 |
| 4 | 808753.50 | 253232.00 | 3.194 |
| 8 | 787977.00 | 251832.50 | 3.129 |

### vpc

| CU | Naive | Optimized | Ratio (N/O) |
|----|-------|-----------|-------------|
| 2 | 3.79 | 16.77 | 0.226 |
| 4 | 1.94 | 9.83 | 0.198 |
| 8 | 1.00 | 4.94 | 0.202 |

## Scalability (Total Cycles)

### Naive

| CU | Total Cycles | Speedup vs 2 CU |
|----|--------------|-----------------|
| 2 | 830444 | 1.000x |
| 4 | 808754 | 1.027x |
| 8 | 787977 | 1.054x |

### Optimized

| CU | Total Cycles | Speedup vs 2 CU |
|----|--------------|-----------------|
| 2 | 296969 | 1.000x |
| 4 | 253232 | 1.173x |
| 8 | 251832 | 1.179x |

## Full Comparison per CU

### 2 Compute Units

| Metric | Naive | Optimized | Diff (N-O) | Change % |
|--------|-------|-----------|------------|----------|
| loadLatencyDist::mean | 6268409.67 | 1334480.22 | 4933929.44 | 78.7% |
| vALUInsts | 22528.00 | 28672.00 | 6144.00 | 27.3% |
| ldsBankAccesses | 0.00 | 393216.00 | 393216.00 | 0.0% |
| totalCycles | 830444.00 | 296969.00 | 533475.00 | 64.2% |
| vpc | 3.79 | 16.77 | 12.98 | 342.8% |

### 4 Compute Units

| Metric | Naive | Optimized | Diff (N-O) | Change % |
|--------|-------|-----------|------------|----------|
| loadLatencyDist::mean | 12246139.77 | 2868275.51 | 9377864.26 | 76.6% |
| vALUInsts | 11264.00 | 14336.00 | 3072.00 | 27.3% |
| ldsBankAccesses | 0.00 | 196608.00 | 196608.00 | 0.0% |
| totalCycles | 808753.50 | 253232.00 | 555521.50 | 68.7% |
| vpc | 1.94 | 9.83 | 7.89 | 405.7% |

### 8 Compute Units

| Metric | Naive | Optimized | Diff (N-O) | Change % |
|--------|-------|-----------|------------|----------|
| loadLatencyDist::mean | 23756984.01 | 7077776.37 | 16679207.64 | 70.2% |
| vALUInsts | 5632.00 | 7168.00 | 1536.00 | 27.3% |
| ldsBankAccesses | 0.00 | 98304.00 | 98304.00 | 0.0% |
| totalCycles | 787977.00 | 251832.50 | 536144.50 | 68.0% |
| vpc | 1.00 | 4.94 | 3.95 | 395.4% |
