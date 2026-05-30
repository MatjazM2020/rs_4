#!/usr/bin/env python3
"""
Exact SpMV stats analysis for the checked-in gem5 stats files.

Each stats.txt file has three simulation-stat sections:
  1. original row order SpMV kernel (divergent)
  2. sorted row order SpMV kernel (uniform)
  3. post-kernel aggregate/reset stats with zero or nan CU counters

This script intentionally reads only sections 0 and 1 and uses exact stat
names from the current files instead of suffix matching across sections.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path


KERNELS = ("divergent", "uniform")
CU_COUNTS = (2, 4, 8)
GPU_PREFIX = "system.cpu3"


@dataclass(frozen=True)
class Distribution:
    samples: float
    mean: float
    stdev: float


@dataclass(frozen=True)
class KernelStats:
    kernel: str
    cu_count: int
    load_latency: Distribution
    coalesced_cache_line_requests: float
    valu_insts_by_cu: tuple[float, ...]
    global_reads_by_cu: tuple[float, ...]
    global_writes_by_cu: tuple[float, ...]
    global_mem_insts_by_cu: tuple[float, ...]
    total_cycles_by_cu: tuple[float, ...]
    vpc_by_cu: tuple[float, ...]
    divergence_by_cu: tuple[Distribution, ...]

    @property
    def active_lane_mean(self) -> float:
        return weighted_mean(self.divergence_by_cu)

    @property
    def active_lane_stdev(self) -> float:
        return combined_stdev(self.divergence_by_cu)

    @property
    def active_lane_efficiency(self) -> float:
        return self.active_lane_mean / 64 * 100

    @property
    def valu_insts_total(self) -> float:
        return sum(self.valu_insts_by_cu)

    @property
    def global_reads_total(self) -> float:
        return sum(self.global_reads_by_cu)

    @property
    def global_writes_total(self) -> float:
        return sum(self.global_writes_by_cu)

    @property
    def global_mem_insts_total(self) -> float:
        return sum(self.global_mem_insts_by_cu)

    @property
    def elapsed_cycles(self) -> float:
        return max(self.total_cycles_by_cu)

    @property
    def mean_cu_cycles(self) -> float:
        return mean(self.total_cycles_by_cu)

    @property
    def mean_vpc(self) -> float:
        return mean(self.vpc_by_cu)

    @property
    def min_vpc(self) -> float:
        return min(self.vpc_by_cu)

    @property
    def max_vpc(self) -> float:
        return max(self.vpc_by_cu)


def mean(values: tuple[float, ...]) -> float:
    return sum(values) / len(values)


def weighted_mean(distributions: tuple[Distribution, ...]) -> float:
    total_samples = sum(dist.samples for dist in distributions)
    if total_samples == 0:
        raise ValueError("cannot compute weighted mean with zero samples")
    return sum(dist.mean * dist.samples for dist in distributions) / total_samples


def combined_stdev(distributions: tuple[Distribution, ...]) -> float:
    total_samples = sum(dist.samples for dist in distributions)
    if total_samples == 0:
        raise ValueError("cannot compute stdev with zero samples")

    combined_mean = weighted_mean(distributions)
    variance = (
        sum(
            dist.samples * (dist.stdev**2 + (dist.mean - combined_mean) ** 2)
            for dist in distributions
        )
        / total_samples
    )
    return math.sqrt(variance)


def parse_stats_sections(path: Path) -> list[dict[str, float]]:
    sections: list[dict[str, float]] = []
    current: dict[str, float] | None = None

    with path.open(encoding="utf-8") as stats_file:
        for line in stats_file:
            if line.startswith("---------- Begin Simulation Statistics ----------"):
                current = {}
                continue

            if line.startswith("---------- End Simulation Statistics"):
                if current is not None:
                    sections.append(current)
                    current = None
                continue

            if current is None:
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            key, raw_value = parts[0], parts[1]
            try:
                current[key] = float(raw_value)
            except ValueError:
                continue

    if current is not None:
        raise ValueError(f"{path} has an unterminated simulation-stat section")

    return sections


def require_finite(stats: dict[str, float], key: str, path: Path) -> float:
    try:
        value = stats[key]
    except KeyError as exc:
        raise KeyError(f"{path} is missing required stat {key}") from exc

    if not math.isfinite(value):
        raise ValueError(f"{path} has non-finite value for {key}: {value}")
    return value


def require_distribution(stats: dict[str, float], base_key: str, path: Path) -> Distribution:
    return Distribution(
        samples=require_finite(stats, f"{base_key}::samples", path),
        mean=require_finite(stats, f"{base_key}::mean", path),
        stdev=require_finite(stats, f"{base_key}::stdev", path),
    )


def exact_cu_values(
    stats: dict[str, float],
    metric: str,
    cu_count: int,
    path: Path,
) -> tuple[float, ...]:
    prefix = f"{GPU_PREFIX}.CUs"
    expected_keys = [f"{prefix}{cu}.{metric}" for cu in range(cu_count)]
    values = tuple(require_finite(stats, key, path) for key in expected_keys)

    actual_cus = sorted(
        int(key.removeprefix(prefix).split(".", 1)[0])
        for key in stats
        if key.startswith(prefix)
        and key.endswith(f".{metric}")
        and key.removeprefix(prefix).split(".", 1)[0].isdigit()
    )
    expected_cus = list(range(cu_count))
    if actual_cus != expected_cus:
        raise ValueError(
            f"{path} section has {metric} for CUs {actual_cus}, "
            f"expected {expected_cus}"
        )

    return values


def exact_cu_distributions(
    stats: dict[str, float],
    metric: str,
    cu_count: int,
    path: Path,
) -> tuple[Distribution, ...]:
    prefix = f"{GPU_PREFIX}.CUs"
    actual_cus = sorted(
        int(key.removeprefix(prefix).split(".", 1)[0])
        for key in stats
        if key.startswith(prefix)
        and f".{metric}::" in key
        and key.removeprefix(prefix).split(".", 1)[0].isdigit()
    )
    actual_cus = sorted(set(actual_cus))
    expected_cus = list(range(cu_count))
    if actual_cus != expected_cus:
        raise ValueError(
            f"{path} section has {metric} for CUs {actual_cus}, "
            f"expected {expected_cus}"
        )

    return tuple(
        require_distribution(stats, f"{GPU_PREFIX}.CUs{cu}.{metric}", path)
        for cu in range(cu_count)
    )


def load_kernel(
    path: Path,
    stats: dict[str, float],
    kernel: str,
    cu_count: int,
) -> KernelStats:
    return KernelStats(
        kernel=kernel,
        cu_count=cu_count,
        load_latency=require_distribution(stats, f"{GPU_PREFIX}.loadLatencyDist", path),
        coalesced_cache_line_requests=require_finite(
            stats, f"{GPU_PREFIX}.coalsrLineAddresses::total", path
        ),
        valu_insts_by_cu=exact_cu_values(stats, "vALUInsts", cu_count, path),
        global_reads_by_cu=exact_cu_values(stats, "globalReads", cu_count, path),
        global_writes_by_cu=exact_cu_values(stats, "globalWrites", cu_count, path),
        global_mem_insts_by_cu=exact_cu_values(stats, "globalMemInsts", cu_count, path),
        total_cycles_by_cu=exact_cu_values(stats, "totalCycles", cu_count, path),
        vpc_by_cu=exact_cu_values(stats, "vpc", cu_count, path),
        divergence_by_cu=exact_cu_distributions(
            stats, "controlFlowDivergenceDist", cu_count, path
        ),
    )


def load_run(root: Path, cu_count: int) -> dict[str, KernelStats]:
    path = root / f"cu_{cu_count}" / "stats.txt"
    sections = parse_stats_sections(path)
    if len(sections) != 3:
        raise ValueError(f"{path} has {len(sections)} sections, expected 3")

    return {
        kernel: load_kernel(path, sections[index], kernel, cu_count)
        for index, kernel in enumerate(KERNELS)
    }


def load_all(root: Path) -> dict[int, dict[str, KernelStats]]:
    return {cu_count: load_run(root, cu_count) for cu_count in CU_COUNTS}


def fmt(value: float, decimals: int = 2) -> str:
    if decimals == 0:
        return f"{value:.0f}"
    return f"{value:.{decimals}f}"


def ratio(numerator: float, denominator: float) -> str:
    if denominator == 0:
        return "N/A"
    return f"{numerator / denominator:.3f}x"


def pct_change(new: float, old: float) -> str:
    if old == 0:
        return "N/A"
    return f"{(new - old) / old * 100:+.1f}%"


def assignment_metric_rows() -> list[tuple[str, str, str, int]]:
    return [
        (
            "controlFlowDivergenceDist::mean",
            "active_lane_mean",
            "Sample-weighted across active CUs",
            2,
        ),
        (
            "controlFlowDivergenceDist::stdev",
            "active_lane_stdev",
            "Combined across active CUs",
            2,
        ),
        ("vALUInsts", "valu_insts_total", "Total across active CUs", 0),
        ("globalReads", "global_reads_total", "Total across active CUs", 0),
        ("globalWrites", "global_writes_total", "Total across active CUs", 0),
        (
            "coalsrLineAddresses::total",
            "coalesced_cache_line_requests",
            "GPU-level total",
            0,
        ),
    ]


def diagnostic_metric_rows() -> list[tuple[str, str, str, int]]:
    return [
        (
            "active lane efficiency",
            "active_lane_efficiency",
            "Mean active lanes divided by 64",
            1,
        ),
        ("globalMemInsts", "global_mem_insts_total", "Diagnostic reads plus writes", 0),
        ("totalCycles max", "elapsed_cycles", "Diagnostic max across active CUs", 0),
        ("totalCycles mean", "mean_cu_cycles", "Diagnostic average across active CUs", 0),
        ("vpc", "mean_vpc", "Diagnostic average across active CUs", 2),
        ("vpc range", "vpc_range", "Diagnostic min..max across CUs", 2),
    ]


def metric_number(run: KernelStats, attr: str) -> float | None:
    if attr == "vpc_range":
        return None
    if attr == "load_latency.mean":
        return run.load_latency.mean
    return getattr(run, attr)


def metric_value(run: KernelStats, attr: str, decimals: int) -> str:
    if attr == "vpc_range":
        return f"{fmt(run.min_vpc, decimals)}..{fmt(run.max_vpc, decimals)}"

    value = metric_number(run, attr)
    if value is None:
        return "N/A"
    return fmt(value, decimals)


def print_console_summary(data: dict[int, dict[str, KernelStats]]) -> None:
    print("SpMV exact gem5 analysis")
    print("=" * 94)
    print("Sections used: 0 = original row order, 1 = sorted row order")
    print("Section 2 is ignored because its CU counters are zero or nan")
    print("Assignment counters are summed across active CUs")

    for cu_count in CU_COUNTS:
        divergent = data[cu_count]["divergent"]
        uniform = data[cu_count]["uniform"]
        print(f"\n{cu_count} CUs")
        print("-" * 94)
        print("Assignment metrics")
        print(
            f"{'gem5 stat':<36} {'Divergent':>16} "
            f"{'Uniform':>16} {'Uniform vs Div':>16}"
        )
        for label, attr, _note, decimals in assignment_metric_rows():
            divergent_num = metric_number(divergent, attr)
            uniform_num = metric_number(uniform, attr)
            change = (
                pct_change(uniform_num, divergent_num)
                if divergent_num is not None and uniform_num is not None
                else "N/A"
            )
            print(
                f"{label:<36} "
                f"{metric_value(divergent, attr, decimals):>16} "
                f"{metric_value(uniform, attr, decimals):>16} "
                f"{change:>16}"
            )
        print("\nDiagnostic metrics")
        print(f"{'Metric':<36} {'Divergent':>16} {'Uniform':>16} {'Uniform vs Div':>16}")
        for label, attr, _note, decimals in diagnostic_metric_rows():
            divergent_num = metric_number(divergent, attr)
            uniform_num = metric_number(uniform, attr)
            change = (
                pct_change(uniform_num, divergent_num)
                if divergent_num is not None and uniform_num is not None
                else "N/A"
            )
            print(
                f"{label:<36} "
                f"{metric_value(divergent, attr, decimals):>16} "
                f"{metric_value(uniform, attr, decimals):>16} "
                f"{change:>16}"
            )


def markdown_report(data: dict[int, dict[str, KernelStats]]) -> str:
    lines = [
        "# SpMV Exact GEM5 Performance Analysis",
        "",
        "This report is generated from the first two simulation-stat sections in each `stats.txt` file.",
        "Section 0 is the original row order SpMV kernel, section 1 is the sorted row order kernel, and section 2 is ignored because it contains post-kernel zero or `nan` CU counters.",
        "",
        "The assignment table reports `controlFlowDivergenceDist::mean`, `controlFlowDivergenceDist::stdev`, `vALUInsts`, `globalReads`, `globalWrites`, and `coalsrLineAddresses::total`.",
        "Control-flow divergence is combined across active CUs using the per-CU distribution samples; assignment counters are summed across active CUs.",
        "",
        "## Assignment Metrics",
        "",
    ]

    for cu_count in CU_COUNTS:
        divergent = data[cu_count]["divergent"]
        uniform = data[cu_count]["uniform"]
        lines.extend(
            [
                f"### {cu_count} Compute Units",
                "",
                "| gem5 stat | Divergent | Uniform | Uniform vs Divergent | Note |",
                "|--------|-----------|---------|----------------------|------|",
            ]
        )
        for label, attr, note, decimals in assignment_metric_rows():
            divergent_num = metric_number(divergent, attr)
            uniform_num = metric_number(uniform, attr)
            change = (
                pct_change(uniform_num, divergent_num)
                if divergent_num is not None and uniform_num is not None
                else "N/A"
            )
            lines.append(
                f"| {label} | {metric_value(divergent, attr, decimals)} | "
                f"{metric_value(uniform, attr, decimals)} | {change} | {note} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Diagnostic Metrics",
            "",
        ]
    )
    for cu_count in CU_COUNTS:
        divergent = data[cu_count]["divergent"]
        uniform = data[cu_count]["uniform"]
        lines.extend(
            [
                f"### {cu_count} Compute Units",
                "",
                "| Metric | Divergent | Uniform | Uniform vs Divergent | Note |",
                "|--------|-----------|---------|----------------------|------|",
            ]
        )
        for label, attr, note, decimals in diagnostic_metric_rows():
            divergent_num = metric_number(divergent, attr)
            uniform_num = metric_number(uniform, attr)
            change = (
                pct_change(uniform_num, divergent_num)
                if divergent_num is not None and uniform_num is not None
                else "N/A"
            )
            lines.append(
                f"| {label} | {metric_value(divergent, attr, decimals)} | "
                f"{metric_value(uniform, attr, decimals)} | {change} | {note} |"
            )
        lines.append("")

    lines.extend(["", "## Scaling by Kernel", ""])
    for kernel in KERNELS:
        label = "Divergent" if kernel == "divergent" else "Uniform"
        base = data[CU_COUNTS[0]][kernel].mean_cu_cycles
        lines.extend(
            [
                f"### {label}",
                "",
                "| CU | totalCycles mean | Ratio vs 2 CU | totalCycles max |",
                "|----|------------------|---------------|-----------------|",
            ]
        )
        for cu_count in CU_COUNTS:
            run = data[cu_count][kernel]
            lines.append(
                f"| {cu_count} | {fmt(run.mean_cu_cycles, 0)} | "
                f"{ratio(base, run.mean_cu_cycles)} | {fmt(run.elapsed_cycles, 0)} |"
            )
        lines.append("")

    lines.extend(["## Per-CU Details", ""])
    for cu_count in CU_COUNTS:
        for kernel in KERNELS:
            run = data[cu_count][kernel]
            label = "Divergent" if kernel == "divergent" else "Uniform"
            lines.extend(
                [
                    f"### {label}, {cu_count} CUs",
                    "",
                    "| CU | vALUInsts | globalReads | globalWrites | totalCycles | vpc | controlFlowDivergenceDist::mean | controlFlowDivergenceDist::stdev |",
                    "|----|-----------|-------------|--------------|-------------|-----|----------------------------------|-----------------------------------|",
                ]
            )
            for cu in range(cu_count):
                lines.append(
                    f"| {cu} | {fmt(run.valu_insts_by_cu[cu], 0)} | "
                    f"{fmt(run.global_reads_by_cu[cu], 0)} | "
                    f"{fmt(run.global_writes_by_cu[cu], 0)} | "
                    f"{fmt(run.total_cycles_by_cu[cu], 0)} | "
                    f"{fmt(run.vpc_by_cu[cu])} | "
                    f"{fmt(run.divergence_by_cu[cu].mean)} | "
                    f"{fmt(run.divergence_by_cu[cu].stdev)} |"
                )
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    spmv_dir = Path(__file__).resolve().parent
    results_root = spmv_dir / "results"
    report_path = spmv_dir / "spmv_results.md"

    try:
        data = load_all(results_root)
    except (KeyError, ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print_console_summary(data)
    report_path.write_text(markdown_report(data), encoding="utf-8")
    print(f"\nReport saved to: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
