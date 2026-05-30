# SpMV Exact GEM5 Performance Analysis

This report is generated from the first two simulation-stat sections in each `stats.txt` file.
Section 0 is the original row order SpMV kernel, section 1 is the sorted row order kernel, and section 2 is ignored because it contains post-kernel zero or `nan` CU counters.

The assignment table reports `controlFlowDivergenceDist::mean`, `controlFlowDivergenceDist::stdev`, `vALUInsts`, `globalReads`, `globalWrites`, and `coalsrLineAddresses::total`.
Control-flow divergence is combined across active CUs using the per-CU distribution samples; assignment counters are summed across active CUs.

## Assignment Metrics

### 2 Compute Units

| gem5 stat | Divergent | Uniform | Uniform vs Divergent | Note |
|--------|-----------|---------|----------------------|------|
| controlFlowDivergenceDist::mean | 33.50 | 61.18 | +82.6% | Sample-weighted across active CUs |
| controlFlowDivergenceDist::stdev | 19.05 | 10.10 | -47.0% | Combined across active CUs |
| vALUInsts | 12656 | 6896 | -45.5% | Total across active CUs |
| globalReads | 3088 | 1648 | -46.6% | Total across active CUs |
| globalWrites | 16 | 16 | +0.0% | Total across active CUs |
| coalsrLineAddresses::total | 3104 | 1664 | -46.4% | GPU-level total |

### 4 Compute Units

| gem5 stat | Divergent | Uniform | Uniform vs Divergent | Note |
|--------|-----------|---------|----------------------|------|
| controlFlowDivergenceDist::mean | 33.50 | 61.18 | +82.6% | Sample-weighted across active CUs |
| controlFlowDivergenceDist::stdev | 19.05 | 10.10 | -47.0% | Combined across active CUs |
| vALUInsts | 12656 | 6896 | -45.5% | Total across active CUs |
| globalReads | 3088 | 1648 | -46.6% | Total across active CUs |
| globalWrites | 16 | 16 | +0.0% | Total across active CUs |
| coalsrLineAddresses::total | 3104 | 1664 | -46.4% | GPU-level total |

### 8 Compute Units

| gem5 stat | Divergent | Uniform | Uniform vs Divergent | Note |
|--------|-----------|---------|----------------------|------|
| controlFlowDivergenceDist::mean | 33.50 | 61.18 | +82.6% | Sample-weighted across active CUs |
| controlFlowDivergenceDist::stdev | 19.05 | 10.11 | -47.0% | Combined across active CUs |
| vALUInsts | 12656 | 6896 | -45.5% | Total across active CUs |
| globalReads | 3088 | 1648 | -46.6% | Total across active CUs |
| globalWrites | 16 | 16 | +0.0% | Total across active CUs |
| coalsrLineAddresses::total | 3104 | 1664 | -46.4% | GPU-level total |

## Diagnostic Metrics

### 2 Compute Units

| Metric | Divergent | Uniform | Uniform vs Divergent | Note |
|--------|-----------|---------|----------------------|------|
| active lane efficiency | 52.3 | 95.6 | +82.6% | Mean active lanes divided by 64 |
| globalMemInsts | 3104 | 1664 | -46.4% | Diagnostic reads plus writes |
| totalCycles max | 174047 | 176528 | +1.4% | Diagnostic max across active CUs |
| totalCycles mean | 173816 | 166102 | -4.4% | Diagnostic average across active CUs |
| vpc | 2.04 | 2.14 | +4.7% | Diagnostic average across active CUs |
| vpc range | 2.04..2.05 | 2.13..2.15 | N/A | Diagnostic min..max across CUs |

### 4 Compute Units

| Metric | Divergent | Uniform | Uniform vs Divergent | Note |
|--------|-----------|---------|----------------------|------|
| active lane efficiency | 52.3 | 95.6 | +82.6% | Mean active lanes divided by 64 |
| globalMemInsts | 3104 | 1664 | -46.4% | Diagnostic reads plus writes |
| totalCycles max | 92298 | 102610 | +11.2% | Diagnostic max across active CUs |
| totalCycles mean | 92080 | 87434 | -5.0% | Diagnostic average across active CUs |
| vpc | 1.93 | 2.03 | +5.3% | Diagnostic average across active CUs |
| vpc range | 1.92..1.94 | 1.99..2.06 | N/A | Diagnostic min..max across CUs |

### 8 Compute Units

| Metric | Divergent | Uniform | Uniform vs Divergent | Note |
|--------|-----------|---------|----------------------|------|
| active lane efficiency | 52.3 | 95.6 | +82.6% | Mean active lanes divided by 64 |
| globalMemInsts | 3104 | 1664 | -46.4% | Diagnostic reads plus writes |
| totalCycles max | 60344 | 65640 | +8.8% | Diagnostic max across active CUs |
| totalCycles mean | 59782 | 53078 | -11.2% | Diagnostic average across active CUs |
| vpc | 1.49 | 1.64 | +10.6% | Diagnostic average across active CUs |
| vpc range | 1.47..1.50 | 1.28..1.90 | N/A | Diagnostic min..max across CUs |


## Scaling by Kernel

### Divergent

| CU | totalCycles mean | Ratio vs 2 CU | totalCycles max |
|----|------------------|---------------|-----------------|
| 2 | 173816 | 1.000x | 174047 |
| 4 | 92080 | 1.888x | 92298 |
| 8 | 59782 | 2.907x | 60344 |

### Uniform

| CU | totalCycles mean | Ratio vs 2 CU | totalCycles max |
|----|------------------|---------------|-----------------|
| 2 | 166102 | 1.000x | 176528 |
| 4 | 87434 | 1.900x | 102610 |
| 8 | 53078 | 3.129x | 65640 |

## Per-CU Details

### Divergent, 2 CUs

| CU | vALUInsts | globalReads | globalWrites | totalCycles | vpc | controlFlowDivergenceDist::mean | controlFlowDivergenceDist::stdev |
|----|-----------|-------------|--------------|-------------|-----|----------------------------------|-----------------------------------|
| 0 | 6328 | 1544 | 8 | 174047 | 2.04 | 33.50 | 19.05 |
| 1 | 6328 | 1544 | 8 | 173584 | 2.05 | 33.50 | 19.05 |

### Uniform, 2 CUs

| CU | vALUInsts | globalReads | globalWrites | totalCycles | vpc | controlFlowDivergenceDist::mean | controlFlowDivergenceDist::stdev |
|----|-----------|-------------|--------------|-------------|-----|----------------------------------|-----------------------------------|
| 0 | 3256 | 776 | 8 | 155675 | 2.15 | 61.01 | 10.37 |
| 1 | 3640 | 872 | 8 | 176528 | 2.13 | 61.33 | 9.86 |

### Divergent, 4 CUs

| CU | vALUInsts | globalReads | globalWrites | totalCycles | vpc | controlFlowDivergenceDist::mean | controlFlowDivergenceDist::stdev |
|----|-----------|-------------|--------------|-------------|-----|----------------------------------|-----------------------------------|
| 0 | 3164 | 772 | 4 | 91961 | 1.93 | 33.50 | 19.05 |
| 1 | 3164 | 772 | 4 | 91799 | 1.94 | 33.50 | 19.05 |
| 2 | 3164 | 772 | 4 | 92298 | 1.92 | 33.50 | 19.05 |
| 3 | 3164 | 772 | 4 | 92262 | 1.93 | 33.50 | 19.05 |

### Uniform, 4 CUs

| CU | vALUInsts | globalReads | globalWrites | totalCycles | vpc | controlFlowDivergenceDist::mean | controlFlowDivergenceDist::stdev |
|----|-----------|-------------|--------------|-------------|-----|----------------------------------|-----------------------------------|
| 0 | 1436 | 340 | 4 | 73752 | 1.99 | 60.62 | 10.97 |
| 1 | 1628 | 388 | 4 | 81328 | 2.06 | 61.01 | 10.37 |
| 2 | 1820 | 436 | 4 | 92044 | 2.04 | 61.33 | 9.86 |
| 3 | 2012 | 484 | 4 | 102610 | 2.03 | 61.58 | 9.41 |

### Divergent, 8 CUs

| CU | vALUInsts | globalReads | globalWrites | totalCycles | vpc | controlFlowDivergenceDist::mean | controlFlowDivergenceDist::stdev |
|----|-----------|-------------|--------------|-------------|-----|----------------------------------|-----------------------------------|
| 0 | 1582 | 386 | 2 | 59703 | 1.49 | 33.50 | 19.05 |
| 1 | 1582 | 386 | 2 | 59334 | 1.50 | 33.50 | 19.05 |
| 2 | 1582 | 386 | 2 | 59488 | 1.49 | 33.50 | 19.05 |
| 3 | 1582 | 386 | 2 | 59442 | 1.49 | 33.50 | 19.05 |
| 4 | 1582 | 386 | 2 | 60102 | 1.48 | 33.50 | 19.05 |
| 5 | 1582 | 386 | 2 | 60344 | 1.47 | 33.50 | 19.05 |
| 6 | 1582 | 386 | 2 | 60237 | 1.47 | 33.50 | 19.05 |
| 7 | 1582 | 386 | 2 | 59606 | 1.49 | 33.50 | 19.05 |

### Uniform, 8 CUs

| CU | vALUInsts | globalReads | globalWrites | totalCycles | vpc | controlFlowDivergenceDist::mean | controlFlowDivergenceDist::stdev |
|----|-----------|-------------|--------------|-------------|-----|----------------------------------|-----------------------------------|
| 0 | 526 | 122 | 2 | 41306 | 1.28 | 59.41 | 12.58 |
| 1 | 622 | 146 | 2 | 44288 | 1.43 | 60.11 | 11.70 |
| 2 | 718 | 170 | 2 | 48436 | 1.52 | 60.62 | 10.98 |
| 3 | 814 | 194 | 2 | 50161 | 1.67 | 61.01 | 10.37 |
| 4 | 910 | 218 | 2 | 55941 | 1.68 | 61.33 | 9.86 |
| 5 | 1006 | 242 | 2 | 58143 | 1.79 | 61.58 | 9.41 |
| 6 | 1102 | 266 | 2 | 60712 | 1.88 | 61.79 | 9.02 |
| 7 | 1198 | 290 | 2 | 65640 | 1.90 | 61.96 | 8.68 |
