#!/usr/bin/env python3
"""
Results extraction for histogram GEM5 benchmarks.

Reads:
  ./results/naive/cu_N/stats.txt
  ./results/optimized/cu_N/stats.txt

For each run, section 0 contains the kernel execution statistics and section 1
is the post-completion aggregate. Only section 0 is used for task 1.
"""

import re
import sys
from pathlib import Path


KERNELS = ["naive", "optimized"]
CU_VALUES = [2, 4, 8]

METRICS = [
    "loadLatencyDist::mean",
    "vALUInsts",
    "ldsBankAccesses",
    "totalCycles",
    "vpc",
]


def parse_stats(filepath):
    """Return list of stat sections. Each section is a dict key->value."""
    sections = []
    current = {}
    in_section = False
    with open(filepath) as f:
        for line in f:
            if line.startswith("---------- Begin"):
                current = {}
                in_section = True
            elif line.startswith("---------- End"):
                if in_section:
                    sections.append(current)
                in_section = False
            elif in_section:
                match = re.match(r"^(\S+)\s+(\S+)", line)
                if match:
                    try:
                        current[match.group(1)] = float(match.group(2))
                    except ValueError:
                        current[match.group(1)] = match.group(2)
    return sections


def extract_metrics(section):
    """Average all per-CU stat keys that end with each metric name."""
    result = {}
    for metric in METRICS:
        matches = [
            value
            for key, value in section.items()
            if isinstance(value, float)
            and (key == metric or key.endswith("." + metric))
        ]
        result[metric] = sum(matches) / len(matches) if matches else None
    return result


def fmt(value, decimals=2):
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}"


def load_data():
    results_root = Path("results")
    if not results_root.exists():
        print(f"Error: '{results_root}' directory not found", file=sys.stderr)
        sys.exit(1)

    data = {}
    for cu in CU_VALUES:
        data[cu] = {}
        for kernel in KERNELS:
            stats_file = results_root / kernel / f"cu_{cu}" / "stats.txt"
            if not stats_file.exists():
                print(f"Warning: {stats_file} not found, skipping", file=sys.stderr)
                continue

            sections = parse_stats(stats_file)
            if not sections:
                print(f"Warning: {stats_file} has no sections", file=sys.stderr)
                continue

            data[cu][kernel] = extract_metrics(sections[0])

        if not data[cu]:
            del data[cu]

    if not data:
        print("No data found.", file=sys.stderr)
        sys.exit(1)

    return data


def print_console_summary(data):
    col_w = 18

    print("=" * 90)
    print("Histogram GEM5 Performance Analysis (averaged across CUs)")
    print("=" * 90)

    for metric in METRICS:
        print(f"\nMetric: {metric}")
        header = (
            f"{'CU':<6}"
            f"{'Naive':>{col_w}}"
            f"{'Optimized':>{col_w}}"
            f"{'Ratio (N/O)':>{col_w}}"
        )
        print(header)
        print("-" * len(header))
        for cu in CU_VALUES:
            if cu not in data:
                print(f"{cu:<6}{'(missing)':>{col_w}}")
                continue
            vn = data[cu].get("naive", {}).get(metric)
            vo = data[cu].get("optimized", {}).get(metric)
            ratio = f"{vn / vo:.3f}" if (vn is not None and vo not in (None, 0)) else "N/A"
            print(f"{cu:<6}{fmt(vn):>{col_w}}{fmt(vo):>{col_w}}{ratio:>{col_w}}")


def generate_markdown_report(data):
    md = []

    md.append("# Histogram GEM5 Performance Analysis")
    md.append("")
    md.append("Simulations run with 2, 4, and 8 compute units.")
    md.append("Values are averaged across all CUs within the kernel execution section.")
    md.append("")

    md.append("## Metrics by Compute Unit")
    md.append("")
    for metric in METRICS:
        md.append(f"### {metric}")
        md.append("")
        md.append("| CU | Naive | Optimized | Ratio (N/O) |")
        md.append("|----|-------|-----------|-------------|")
        for cu in CU_VALUES:
            vn = data.get(cu, {}).get("naive", {}).get(metric)
            vo = data.get(cu, {}).get("optimized", {}).get(metric)
            ratio = f"{vn / vo:.3f}" if (vn is not None and vo not in (None, 0)) else "N/A"
            md.append(f"| {cu} | {fmt(vn)} | {fmt(vo)} | {ratio} |")
        md.append("")

    md.append("## Scalability (Total Cycles)")
    md.append("")
    for kernel, label in [("naive", "Naive"), ("optimized", "Optimized")]:
        md.append(f"### {label}")
        md.append("")
        md.append("| CU | Total Cycles | Speedup vs 2 CU |")
        md.append("|----|--------------|-----------------|")
        base = data.get(CU_VALUES[0], {}).get(kernel, {}).get("totalCycles")
        for cu in CU_VALUES:
            val = data.get(cu, {}).get(kernel, {}).get("totalCycles")
            if val is None:
                md.append(f"| {cu} | N/A | N/A |")
            elif base in (None, 0):
                md.append(f"| {cu} | {fmt(val, 0)} | N/A |")
            else:
                md.append(f"| {cu} | {fmt(val, 0)} | {base / val:.3f}x |")
        md.append("")

    md.append("## Full Comparison per CU")
    md.append("")
    for cu in CU_VALUES:
        if cu not in data:
            continue
        md.append(f"### {cu} Compute Units")
        md.append("")
        md.append("| Metric | Naive | Optimized | Diff (N-O) | Change % |")
        md.append("|--------|-------|-----------|------------|----------|")
        for metric in METRICS:
            vn = data[cu].get("naive", {}).get(metric)
            vo = data[cu].get("optimized", {}).get(metric)
            if vn is None or vo is None:
                md.append(f"| {metric} | {fmt(vn)} | {fmt(vo)} | N/A | N/A |")
                continue
            diff = abs(vn - vo)
            pct = diff / vn * 100 if vn != 0 else 0
            md.append(f"| {metric} | {fmt(vn)} | {fmt(vo)} | {fmt(diff)} | {pct:.1f}% |")
        md.append("")

    report_path = Path("histogram_results.md")
    report_path.write_text("\n".join(md))
    print(f"\nReport saved to: {report_path}")


def main():
    data = load_data()
    print_console_summary(data)
    print("=" * 90)
    generate_markdown_report(data)


if __name__ == "__main__":
    main()
