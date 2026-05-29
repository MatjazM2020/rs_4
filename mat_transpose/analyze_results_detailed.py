#!/usr/bin/env python3
"""
Results extraction for matrix transpose GEM5 benchmarks.

Reads: ./results/cu_N/stats.txt  (N = 2, 4, 8)

Section layout per stats.txt (per README):
  section 0 = kernel 1 (naive transpose)         <- use this
  section 1 = kernel 2 (shared memory transpose)  <- use this
  section 2 = post-completion aggregate            <- skip

Each metric appears once per CU within a section; values are averaged.
"""

import re
import sys
from pathlib import Path


KERNELS = ['naive', 'shared']
CU_VALUES = [2, 4, 8]

METRICS = [
    'loadLatencyDist::mean',
    'vALUInsts',
    'ldsBankAccesses',
    'totalCycles',
    'vpc',
]


def parse_stats(filepath):
    """Return list of stat sections. Each section is a dict key->value."""
    sections = []
    current = {}
    in_section = False
    with open(filepath) as f:
        for line in f:
            if line.startswith('---------- Begin'):
                current = {}
                in_section = True
            elif line.startswith('---------- End'):
                if in_section:
                    sections.append(current)
                in_section = False
            elif in_section:
                m = re.match(r'^(\S+)\s+(\S+)', line)
                if m:
                    try:
                        current[m.group(1)] = float(m.group(2))
                    except ValueError:
                        current[m.group(1)] = m.group(2)
    return sections


def extract_metrics(sec):
    """
    For each metric, collect all keys that end with the metric name
    (one per CU, e.g. CU0.ldsBankAccesses, CU1.ldsBankAccesses, ...)
    and return their average.
    """
    result = {}
    for metric in METRICS:
        suffix = metric
        matches = [v for k, v in sec.items()
                   if isinstance(v, float) and (k == suffix or k.endswith('.' + suffix))]
        if matches:
            result[metric] = sum(matches) / len(matches)
        else:
            result[metric] = None
    return result


def fmt(v, decimals=2):
    if v is None:
        return 'N/A'
    return f'{v:.{decimals}f}'


def main():
    results_root = Path('results')
    if not results_root.exists():
        print(f"Error: '{results_root}' directory not found", file=sys.stderr)
        sys.exit(1)

    data = {}

    for cu in CU_VALUES:
        stats_file = results_root / f'cu_{cu}' / 'stats.txt'
        if not stats_file.exists():
            print(f"Warning: {stats_file} not found, skipping", file=sys.stderr)
            continue

        sections = parse_stats(stats_file)

        if len(sections) < 2:
            print(f"Warning: {stats_file} has only {len(sections)} section(s), expected >= 2", file=sys.stderr)
            continue

        data[cu] = {
            'naive':  extract_metrics(sections[0]),
            'shared': extract_metrics(sections[1]),
        }

    if not data:
        print("No data found.", file=sys.stderr)
        sys.exit(1)

    col_w = 18

    print('=' * 90)
    print('Matrix Transpose GEM5 Performance Analysis (averaged across CUs)')
    print('=' * 90)

    for metric in METRICS:
        print(f'\nMetric: {metric}')
        header = f"{'CU':<6}" + f"{'Naive':>{col_w}}" + f"{'Shared':>{col_w}}" + f"{'Ratio (N/S)':>{col_w}}"
        print(header)
        print('-' * len(header))
        for cu in CU_VALUES:
            if cu not in data:
                print(f"{cu:<6}{'(missing)':>{col_w}}")
                continue
            vn = data[cu]['naive'].get(metric)
            vs = data[cu]['shared'].get(metric)
            ratio = f'{vn / vs:.3f}' if (vn is not None and vs is not None and vs != 0) else 'N/A'
            print(f"{cu:<6}{fmt(vn):>{col_w}}{fmt(vs):>{col_w}}{ratio:>{col_w}}")

    print('=' * 90)
    generate_markdown_report(data)


def generate_markdown_report(data):
    md = []

    md.append('# Matrix Transpose GEM5 Performance Analysis')
    md.append('')
    md.append('Simulations run with 2, 4, and 8 compute units.')
    md.append('Values are averaged across all CUs within each section.')
    md.append('')

    # Per-metric tables
    md.append('## Metrics by Compute Unit')
    md.append('')

    col_labels = {'naive': 'Naive', 'shared': 'Shared Memory'}

    for metric in METRICS:
        md.append(f'### {metric}')
        md.append('')
        md.append('| CU | Naive | Shared | Ratio (N/S) |')
        md.append('|----|-------|--------|-------------|')
        for cu in CU_VALUES:
            if cu not in data:
                md.append(f'| {cu} | N/A | N/A | N/A |')
                continue
            vn = data[cu]['naive'].get(metric)
            vs = data[cu]['shared'].get(metric)
            ratio = f'{vn / vs:.3f}' if (vn is not None and vs is not None and vs != 0) else 'N/A'
            md.append(f'| {cu} | {fmt(vn)} | {fmt(vs)} | {ratio} |')
        md.append('')

    # Scalability: totalCycles per kernel
    md.append('## Scalability (Total Cycles)')
    md.append('')
    for kernel in KERNELS:
        md.append(f'### {col_labels[kernel]}')
        md.append('')
        md.append('| CU | Total Cycles | Speedup vs 2 CU |')
        md.append('|----|-------------|-----------------|')
        base = data.get(CU_VALUES[0], {}).get(kernel, {}).get('totalCycles')
        for cu in CU_VALUES:
            val = data.get(cu, {}).get(kernel, {}).get('totalCycles')
            if val is None:
                md.append(f'| {cu} | N/A | N/A |')
            elif base is None or base == 0:
                md.append(f'| {cu} | {fmt(val, 0)} | N/A |')
            else:
                speedup = base / val
                md.append(f'| {cu} | {fmt(val, 0)} | {speedup:.3f}x |')
        md.append('')

    # Per-CU comparison table (all metrics side by side)
    md.append('## Full Comparison per CU')
    md.append('')
    for cu in CU_VALUES:
        if cu not in data:
            continue
        md.append(f'### {cu} Compute Units')
        md.append('')
        md.append('| Metric | Naive | Shared | Diff (N-S) | Change % |')
        md.append('|--------|-------|--------|------------|----------|')
        for metric in METRICS:
            vn = data[cu]['naive'].get(metric)
            vs = data[cu]['shared'].get(metric)
            if vn is None or vs is None:
                md.append(f'| {metric} | {fmt(vn)} | {fmt(vs)} | N/A | N/A |')
                continue
            diff = abs(vn - vs)
            pct = (diff / vn * 100) if vn != 0 else 0
            md.append(f'| {metric} | {fmt(vn)} | {fmt(vs)} | {fmt(diff)} | {pct:.1f}% |')
        md.append('')

    report_path = Path('transpose_results.md')
    report_path.write_text('\n'.join(md))
    print(f'\nReport saved to: {report_path}')


if __name__ == '__main__':
    main()