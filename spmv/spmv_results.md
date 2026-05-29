# SpMV GEM5 Performance Analysis

Simulations run with 2, 4, and 8 compute units.
Section 0 is the divergent/original row order kernel; section 1 is the uniform/sorted row order kernel.
Values are averaged across all CUs within each section.

## Metrics by Compute Unit

### controlFlowDivergenceDist::mean

| CU | Divergent | Uniform | Ratio (D/U) |
|----|-----------|---------|-------------|
| 2 | 33.50 | 61.17 | 0.548 |
| 4 | 33.50 | 61.14 | 0.548 |
| 8 | 33.50 | 60.98 | 0.549 |

### controlFlowDivergenceDist::stdev

| CU | Divergent | Uniform | Ratio (D/U) |
|----|-----------|---------|-------------|
| 2 | 19.05 | 10.11 | 1.884 |
| 4 | 19.05 | 10.15 | 1.876 |
| 8 | 19.05 | 10.32 | 1.846 |

### vALUInsts

| CU | Divergent | Uniform | Ratio (D/U) |
|----|-----------|---------|-------------|
| 2 | 6328.00 | 3448.00 | 1.835 |
| 4 | 3164.00 | 1724.00 | 1.835 |
| 8 | 1582.00 | 862.00 | 1.835 |

### globalReads

| CU | Divergent | Uniform | Ratio (D/U) |
|----|-----------|---------|-------------|
| 2 | 1544.00 | 824.00 | 1.874 |
| 4 | 772.00 | 412.00 | 1.874 |
| 8 | 386.00 | 206.00 | 1.874 |

### globalWrites

| CU | Divergent | Uniform | Ratio (D/U) |
|----|-----------|---------|-------------|
| 2 | 8.00 | 8.00 | 1.000 |
| 4 | 4.00 | 4.00 | 1.000 |
| 8 | 2.00 | 2.00 | 1.000 |

### coalsrLineAddresses::total

| CU | Divergent | Uniform | Ratio (D/U) |
|----|-----------|---------|-------------|
| 2 | 3104.00 | 1664.00 | 1.865 |
| 4 | 3104.00 | 1664.00 | 1.865 |
| 8 | 3104.00 | 1664.00 | 1.865 |

## Divergence Reduction

| CU | Divergent Mean | Uniform Mean | Reduction |
|----|----------------|--------------|-----------|
| 2 | 33.50 | 61.17 | -82.6% |
| 4 | 33.50 | 61.14 | -82.5% |
| 8 | 33.50 | 60.98 | -82.0% |

## Full Comparison per CU

### 2 Compute Units

| Metric | Divergent | Uniform | Diff (D-U) | Change % |
|--------|-----------|---------|------------|----------|
| controlFlowDivergenceDist::mean | 33.50 | 61.17 | 27.67 | 82.6% |
| controlFlowDivergenceDist::stdev | 19.05 | 10.11 | 8.94 | 46.9% |
| vALUInsts | 6328.00 | 3448.00 | 2880.00 | 45.5% |
| globalReads | 1544.00 | 824.00 | 720.00 | 46.6% |
| globalWrites | 8.00 | 8.00 | 0.00 | 0.0% |
| coalsrLineAddresses::total | 3104.00 | 1664.00 | 1440.00 | 46.4% |

### 4 Compute Units

| Metric | Divergent | Uniform | Diff (D-U) | Change % |
|--------|-----------|---------|------------|----------|
| controlFlowDivergenceDist::mean | 33.50 | 61.14 | 27.64 | 82.5% |
| controlFlowDivergenceDist::stdev | 19.05 | 10.15 | 8.90 | 46.7% |
| vALUInsts | 3164.00 | 1724.00 | 1440.00 | 45.5% |
| globalReads | 772.00 | 412.00 | 360.00 | 46.6% |
| globalWrites | 4.00 | 4.00 | 0.00 | 0.0% |
| coalsrLineAddresses::total | 3104.00 | 1664.00 | 1440.00 | 46.4% |

### 8 Compute Units

| Metric | Divergent | Uniform | Diff (D-U) | Change % |
|--------|-----------|---------|------------|----------|
| controlFlowDivergenceDist::mean | 33.50 | 60.98 | 27.48 | 82.0% |
| controlFlowDivergenceDist::stdev | 19.05 | 10.32 | 8.73 | 45.8% |
| vALUInsts | 1582.00 | 862.00 | 720.00 | 45.5% |
| globalReads | 386.00 | 206.00 | 180.00 | 46.6% |
| globalWrites | 2.00 | 2.00 | 0.00 | 0.0% |
| coalsrLineAddresses::total | 3104.00 | 1664.00 | 1440.00 | 46.4% |
