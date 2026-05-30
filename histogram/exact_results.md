# Histogram Exact GEM5 Performance Analysis

This report is generated from the first simulation-stat section in each stats.txt file.
The second section is ignored because its CU counters are zero or `nan` after the kernel finishes.

The assignment table uses `loadLatencyDist::mean` plus averages across active CUs for `vALUInsts`, `ldsBankAccesses`, `totalCycles`, and `vpc`.
Diagnostic total counters are reported separately and are not used as homework-table values.

## Assignment Metrics

### 2 Compute Units

| gem5 stat | Naive | Optimized | Optimized vs Naive | Note |
|--------|-------|-----------|--------------------|------|
| loadLatencyDist::mean | 6268409.67 | 1334480.22 | -78.7% | Lower is better |
| vALUInsts | 22528.00 | 28672.00 | +27.3% | Average across active CUs |
| ldsBankAccesses | 0.00 | 393216.00 | N/A | Average across active CUs |
| totalCycles | 830444 | 296969 | -64.2% | Average across active CUs |
| vpc | 3.79 | 16.77 | +342.8% | Average across active CUs |

### 4 Compute Units

| gem5 stat | Naive | Optimized | Optimized vs Naive | Note |
|--------|-------|-----------|--------------------|------|
| loadLatencyDist::mean | 12246139.77 | 2868275.51 | -76.6% | Lower is better |
| vALUInsts | 11264.00 | 14336.00 | +27.3% | Average across active CUs |
| ldsBankAccesses | 0.00 | 196608.00 | N/A | Average across active CUs |
| totalCycles | 808754 | 253232 | -68.7% | Average across active CUs |
| vpc | 1.94 | 9.83 | +405.7% | Average across active CUs |

### 8 Compute Units

| gem5 stat | Naive | Optimized | Optimized vs Naive | Note |
|--------|-------|-----------|--------------------|------|
| loadLatencyDist::mean | 23756984.01 | 7077776.37 | -70.2% | Lower is better |
| vALUInsts | 5632.00 | 7168.00 | +27.3% | Average across active CUs |
| ldsBankAccesses | 0.00 | 98304.00 | N/A | Average across active CUs |
| totalCycles | 787977 | 251832 | -68.0% | Average across active CUs |
| vpc | 1.00 | 4.94 | +395.4% | Average across active CUs |

## Diagnostic Totals

### 2 Compute Units

| Metric | Naive | Optimized | Optimized vs Naive | Note |
|--------|-------|-----------|--------------------|------|
| vALUInsts total | 45056 | 57344 | +27.3% | Diagnostic total across active CUs |
| ldsBankAccesses total | 0 | 786432 | N/A | Diagnostic total across active CUs |
| vpc range | 3.79..3.79 | 16.67..16.87 | N/A | Diagnostic min..max across CUs |

### 4 Compute Units

| Metric | Naive | Optimized | Optimized vs Naive | Note |
|--------|-------|-----------|--------------------|------|
| vALUInsts total | 45056 | 57344 | +27.3% | Diagnostic total across active CUs |
| ldsBankAccesses total | 0 | 786432 | N/A | Diagnostic total across active CUs |
| vpc range | 1.94..1.95 | 9.80..9.87 | N/A | Diagnostic min..max across CUs |

### 8 Compute Units

| Metric | Naive | Optimized | Optimized vs Naive | Note |
|--------|-------|-----------|--------------------|------|
| vALUInsts total | 45056 | 57344 | +27.3% | Diagnostic total across active CUs |
| ldsBankAccesses total | 0 | 786432 | N/A | Diagnostic total across active CUs |
| vpc range | 0.97..1.02 | 4.80..5.09 | N/A | Diagnostic min..max across CUs |

## Scaling by Kernel

### Naive

| CU | average totalCycles | Ratio vs 2 CU |
|----|---------------------|---------------|
| 2 | 830444 | 1.000x |
| 4 | 808754 | 1.027x |
| 8 | 787977 | 1.054x |

### Optimized

| CU | average totalCycles | Ratio vs 2 CU |
|----|---------------------|---------------|
| 2 | 296969 | 1.000x |
| 4 | 253232 | 1.173x |
| 8 | 251832 | 1.179x |

## Per-CU Details

### Naive, 2 CUs

| CU | vALUInsts | ldsBankAccesses | totalCycles | vpc |
|----|-----------|-------------------|-------------|-----|
| 0 | 22528 | 0 | 830611 | 3.79 |
| 1 | 22528 | 0 | 830277 | 3.79 |

### Optimized, 2 CUs

| CU | vALUInsts | ldsBankAccesses | totalCycles | vpc |
|----|-----------|-------------------|-------------|-----|
| 0 | 28896 | 396288 | 297466 | 16.87 |
| 1 | 28448 | 390144 | 296472 | 16.67 |

### Naive, 4 CUs

| CU | vALUInsts | ldsBankAccesses | totalCycles | vpc |
|----|-----------|-------------------|-------------|-----|
| 0 | 11264 | 0 | 804741 | 1.95 |
| 1 | 11264 | 0 | 810771 | 1.94 |
| 2 | 11264 | 0 | 810636 | 1.94 |
| 3 | 11264 | 0 | 808866 | 1.94 |

### Optimized, 4 CUs

| CU | vALUInsts | ldsBankAccesses | totalCycles | vpc |
|----|-----------|-------------------|-------------|-----|
| 0 | 14336 | 196608 | 252203 | 9.87 |
| 1 | 14336 | 196608 | 252901 | 9.85 |
| 2 | 14336 | 196608 | 253717 | 9.82 |
| 3 | 14336 | 196608 | 254107 | 9.80 |

### Naive, 8 CUs

| CU | vALUInsts | ldsBankAccesses | totalCycles | vpc |
|----|-----------|-------------------|-------------|-----|
| 0 | 5632 | 0 | 790919 | 0.99 |
| 1 | 5632 | 0 | 787616 | 1.00 |
| 2 | 5632 | 0 | 787395 | 1.00 |
| 3 | 5632 | 0 | 788721 | 1.00 |
| 4 | 5632 | 0 | 783449 | 1.00 |
| 5 | 5456 | 0 | 784072 | 0.97 |
| 6 | 5632 | 0 | 790256 | 1.00 |
| 7 | 5808 | 0 | 791388 | 1.02 |

### Optimized, 8 CUs

| CU | vALUInsts | ldsBankAccesses | totalCycles | vpc |
|----|-----------|-------------------|-------------|-----|
| 0 | 7392 | 101376 | 252212 | 5.09 |
| 1 | 7168 | 98304 | 250694 | 4.97 |
| 2 | 7168 | 98304 | 251549 | 4.95 |
| 3 | 7168 | 98304 | 251770 | 4.95 |
| 4 | 7168 | 98304 | 252433 | 4.93 |
| 5 | 6944 | 95232 | 251357 | 4.80 |
| 6 | 7168 | 98304 | 251991 | 4.94 |
| 7 | 7168 | 98304 | 252654 | 4.93 |
