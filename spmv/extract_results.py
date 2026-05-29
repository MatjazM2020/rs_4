#!/usr/bin/env python3
"""
Results extraction for SpMV GEM5 benchmarks.

Reads: ./results/cu_N/stats.txt  (N = 2, 4, 8)

Section layout per README:
  section 0 = kernel 1 (divergent/original row order)
  section 1 = kernel 2 (uniform/sorted row order)
  section 2 = post-completion aggregate
"""

import re
import sys
from pathlib import Path


KERNELS = ["divergent", "uniform"]
CU_VALUES = [2, 4, 8]

METRICS = [
    "controlFlowDivergenceDist::mean",
    "controlFlowDivergenceDist::stdev",
    "vALUInsts",
    "globalReads",
    "globalWrites",
    "coalsrLineAddresses::total",
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
        stats_file = results_root / f"cu_{cu}" / "stats.txt"
        if not stats_file.exists():
            print(f"Warning: {stats_file} not found, skipping", file=sys.stderr)
            continue

        sections = parse_stats(stats_file)
        if len(sections) < 2:
            print(
                f"Warning: {stats_file} has only {len(sections)} section(s), expected >= 2",
                file=sys.stderr,
            )
            continue

        data[cu] = {
            "divergent": extract_metrics(sections[0]),
            "uniform": extract_metrics(sections[1]),
        }

    if not data:
        print("No data found.", file=sys.stderr)
        sys.exit(1)

    return data


def print_console_summary(data):
    col_w = 18

    print("=" * 96)
    print("SpMV GEM5 Performance Analysis (averaged across CUs)")
    print("=" * 96)

    for metric in METRICS:
        print(f"\nMetric: {metric}")
        header = (
            f"{'CU':<6}"
            f"{'Divergent':>{col_w}}"
            f"{'Uniform':>{col_w}}"
            f"{'Ratio (D/U)':>{col_w}}"
        )
        print(header)
        print("-" * len(header))
        for cu in CU_VALUES:
            if cu not in data:
                print(f"{cu:<6}{'(missing)':>{col_w}}")
                continue
            vd = data[cu]["divergent"].get(metric)
            vu = data[cu]["uniform"].get(metric)
            ratio = f"{vd / vu:.3f}" if (vd is not None and vu not in (None, 0)) else "N/A"
            print(f"{cu:<6}{fmt(vd):>{col_w}}{fmt(vu):>{col_w}}{ratio:>{col_w}}")


def generate_markdown_report(data):
    md = []

    md.append("# SpMV GEM5 Performance Analysis")
    md.append("")
    md.append("Simulations run with 2, 4, and 8 compute units.")
    md.append("Section 0 is the divergent/original row order kernel; section 1 is the uniform/sorted row order kernel.")
    md.append("Values are averaged across all CUs within each section.")
    md.append("")

    md.append("## Metrics by Compute Unit")
    md.append("")
    for metric in METRICS:
        md.append(f"### {metric}")
        md.append("")
        md.append("| CU | Divergent | Uniform | Ratio (D/U) |")
        md.append("|----|-----------|---------|-------------|")
        for cu in CU_VALUES:
            vd = data.get(cu, {}).get("divergent", {}).get(metric)
            vu = data.get(cu, {}).get("uniform", {}).get(metric)
            ratio = f"{vd / vu:.3f}" if (vd is not None and vu not in (None, 0)) else "N/A"
            md.append(f"| {cu} | {fmt(vd)} | {fmt(vu)} | {ratio} |")
        md.append("")

    md.append("## Divergence Reduction")
    md.append("")
    md.append("| CU | Divergent Mean | Uniform Mean | Reduction |")
    md.append("|----|----------------|--------------|-----------|")
    for cu in CU_VALUES:
        vd = data.get(cu, {}).get("divergent", {}).get("controlFlowDivergenceDist::mean")
        vu = data.get(cu, {}).get("uniform", {}).get("controlFlowDivergenceDist::mean")
        if vd is None or vu is None or vd == 0:
            md.append(f"| {cu} | {fmt(vd)} | {fmt(vu)} | N/A |")
        else:
            md.append(f"| {cu} | {fmt(vd)} | {fmt(vu)} | {(vd - vu) / vd * 100:.1f}% |")
    md.append("")

    md.append("## Full Comparison per CU")
    md.append("")
    for cu in CU_VALUES:
        if cu not in data:
            continue
        md.append(f"### {cu} Compute Units")
        md.append("")
        md.append("| Metric | Divergent | Uniform | Diff (D-U) | Change % |")
        md.append("|--------|-----------|---------|------------|----------|")
        for metric in METRICS:
            vd = data[cu]["divergent"].get(metric)
            vu = data[cu]["uniform"].get(metric)
            if vd is None or vu is None:
                md.append(f"| {metric} | {fmt(vd)} | {fmt(vu)} | N/A | N/A |")
                continue
            diff = abs(vd - vu)
            pct = diff / vd * 100 if vd != 0 else 0
            md.append(f"| {metric} | {fmt(vd)} | {fmt(vu)} | {fmt(diff)} | {pct:.1f}% |")
        md.append("")

    report_path = Path("spmv_results.md")
    report_path.write_text("\n".join(md))
    print(f"\nReport saved to: {report_path}")


def main():
    data = load_data()
    print_console_summary(data)
    print("=" * 96)
    generate_markdown_report(data)


if __name__ == "__main__":
    main()
