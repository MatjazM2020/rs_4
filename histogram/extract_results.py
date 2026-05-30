#!/usr/bin/env python3
"""
Exact histogram stats analysis for the checked-in gem5 stats files.

The stats files have two simulation-stat sections:
  1. kernel execution, containing the useful GPU counters
  2. post-kernel aggregate/reset stats, where the CU counters are zero/nan

This script intentionally reads only section 0 and uses exact stat names from
the current files instead of suffix matching.
"""

from __future__ import annotations

import math
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path


KERNELS = ("naive", "optimized")
CU_COUNTS = (2, 4, 8)
GPU_PREFIX = "system.cpu3"


@dataclass(frozen=True)
class RunStats:
    kernel: str
    cu_count: int
    load_latency_mean: float
    valu_insts_by_cu: tuple[float, ...]
    lds_bank_accesses_by_cu: tuple[float, ...]
    total_cycles_by_cu: tuple[float, ...]
    vpc_by_cu: tuple[float, ...]

    @property
    def valu_insts_total(self) -> float:
        return sum(self.valu_insts_by_cu)

    @property
    def valu_insts_mean(self) -> float:
        return mean(self.valu_insts_by_cu)

    @property
    def lds_bank_accesses_total(self) -> float:
        return sum(self.lds_bank_accesses_by_cu)

    @property
    def lds_bank_accesses_mean(self) -> float:
        return mean(self.lds_bank_accesses_by_cu)

    @property
    def total_cycles_mean(self) -> float:
        return mean(self.total_cycles_by_cu)

    @property
    def vpc_mean(self) -> float:
        return mean(self.vpc_by_cu)

    @property
    def min_vpc(self) -> float:
        return min(self.vpc_by_cu)

    @property
    def max_vpc(self) -> float:
        return max(self.vpc_by_cu)


def mean(values: tuple[float, ...]) -> float:
    return sum(values) / len(values)


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
                value = float(raw_value)
            except ValueError:
                continue
            current[key] = value

    if current is not None:
        raise ValueError(f"{path} has an unterminated simulation-stat section")

    if not sections:
        raise ValueError(f"{path} does not contain any complete stats sections")

    return sections


def parse_first_stats_section(path: Path) -> dict[str, float]:
    sections = parse_stats_sections(path)
    if len(sections) != 2:
        raise ValueError(f"{path} has {len(sections)} sections, expected 2")
    return sections[0]


def require_finite(stats: dict[str, float], key: str, path: Path) -> float:
    try:
        value = stats[key]
    except KeyError as exc:
        raise KeyError(f"{path} is missing required stat {key}") from exc

    if not math.isfinite(value):
        raise ValueError(f"{path} has non-finite value for {key}: {value}")
    return value


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
            f"{path} has {metric} for CUs {actual_cus}, expected {expected_cus}"
        )

    return values


def load_run(root: Path, kernel: str, cu_count: int) -> RunStats:
    path = root / kernel / f"cu_{cu_count}" / "stats.txt"
    stats = parse_first_stats_section(path)

    return RunStats(
        kernel=kernel,
        cu_count=cu_count,
        load_latency_mean=require_finite(
            stats, f"{GPU_PREFIX}.loadLatencyDist::mean", path
        ),
        valu_insts_by_cu=exact_cu_values(stats, "vALUInsts", cu_count, path),
        lds_bank_accesses_by_cu=exact_cu_values(
            stats, "ldsBankAccesses", cu_count, path
        ),
        total_cycles_by_cu=exact_cu_values(stats, "totalCycles", cu_count, path),
        vpc_by_cu=exact_cu_values(stats, "vpc", cu_count, path),
    )


def load_all(root: Path) -> dict[int, dict[str, RunStats]]:
    data: dict[int, dict[str, RunStats]] = {}
    for cu_count in CU_COUNTS:
        data[cu_count] = {}
        for kernel in KERNELS:
            data[cu_count][kernel] = load_run(root, kernel, cu_count)
    return data


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
        ("loadLatencyDist::mean", "load_latency_mean", "Lower is better", 2),
        ("vALUInsts", "valu_insts_mean", "Average across active CUs", 2),
        ("ldsBankAccesses", "lds_bank_accesses_mean", "Average across active CUs", 2),
        ("totalCycles", "total_cycles_mean", "Average across active CUs", 0),
        ("vpc", "vpc_mean", "Average across active CUs", 2),
    ]


def diagnostic_metric_rows() -> list[tuple[str, str, str, int]]:
    return [
        ("vALUInsts total", "valu_insts_total", "Diagnostic total across active CUs", 0),
        (
            "ldsBankAccesses total",
            "lds_bank_accesses_total",
            "Diagnostic total across active CUs",
            0,
        ),
        ("vpc range", "vpc_range", "Diagnostic min..max across CUs", 2),
    ]


def validate_comparison_rows(
    rows: list[tuple[str, str, str, int]], section_name: str
) -> None:
    has_average = any(
        "Average across active CUs" in note for _label, _attr, note, _dec in rows
    )
    has_total = any(attr.endswith("_total") for _label, attr, _note, _dec in rows)
    if has_average and has_total:
        warnings.warn(
            f"{section_name} mixes average-per-CU assignment values and diagnostic totals",
            RuntimeWarning,
            stacklevel=2,
        )


def metric_value(run: RunStats, attr: str, decimals: int) -> str:
    if attr == "vpc_range":
        return f"{fmt(run.min_vpc, decimals)}..{fmt(run.max_vpc, decimals)}"
    return fmt(getattr(run, attr), decimals)


def metric_number(run: RunStats, attr: str) -> float | None:
    if attr == "vpc_range":
        return None
    return getattr(run, attr)


def print_console_summary(data: dict[int, dict[str, RunStats]]) -> None:
    print("Histogram exact gem5 analysis")
    print("=" * 88)
    print("Section used: first simulation-stat section only")
    print(
        "Assignment metrics: vALUInsts, ldsBankAccesses, totalCycles, "
        "and vpc are averages across active CUs"
    )
    print("Diagnostic totals are printed separately and are not homework-table values")

    for cu_count in CU_COUNTS:
        naive = data[cu_count]["naive"]
        optimized = data[cu_count]["optimized"]
        print(f"\n{cu_count} CUs")
        print("-" * 88)
        print("Assignment metrics")
        print(
            f"{'gem5 stat':<26} {'Naive':>16} "
            f"{'Optimized':>16} {'Optimized vs Naive':>20}"
        )
        validate_comparison_rows(assignment_metric_rows(), "Histogram assignment metrics")
        for label, attr, _note, decimals in assignment_metric_rows():
            naive_num = metric_number(naive, attr)
            optimized_num = metric_number(optimized, attr)
            change = (
                pct_change(optimized_num, naive_num)
                if naive_num is not None and optimized_num is not None
                else "N/A"
            )
            print(
                f"{label:<26} "
                f"{metric_value(naive, attr, decimals):>16} "
                f"{metric_value(optimized, attr, decimals):>16} "
                f"{change:>20}"
            )
        print("\nDiagnostic totals")
        print(
            f"{'Metric':<26} {'Naive':>16} "
            f"{'Optimized':>16} {'Optimized vs Naive':>20}"
        )
        validate_comparison_rows(diagnostic_metric_rows(), "Histogram diagnostic metrics")
        for label, attr, _note, decimals in diagnostic_metric_rows():
            naive_num = metric_number(naive, attr)
            optimized_num = metric_number(optimized, attr)
            change = (
                pct_change(optimized_num, naive_num)
                if naive_num is not None and optimized_num is not None
                else "N/A"
            )
            print(
                f"{label:<26} "
                f"{metric_value(naive, attr, decimals):>16} "
                f"{metric_value(optimized, attr, decimals):>16} "
                f"{change:>20}"
            )


def markdown_report(data: dict[int, dict[str, RunStats]]) -> str:
    lines = [
        "# Histogram Exact GEM5 Performance Analysis",
        "",
        "This report is generated from the first simulation-stat section in each stats.txt file.",
        "The second section is ignored because its CU counters are zero or `nan` after the kernel finishes.",
        "",
        "The assignment table uses `loadLatencyDist::mean` plus averages across active CUs for `vALUInsts`, `ldsBankAccesses`, `totalCycles`, and `vpc`.",
        "Diagnostic total counters are reported separately and are not used as homework-table values.",
        "",
        "## Assignment Metrics",
        "",
    ]

    validate_comparison_rows(assignment_metric_rows(), "Histogram assignment metrics")
    for cu_count in CU_COUNTS:
        naive = data[cu_count]["naive"]
        optimized = data[cu_count]["optimized"]
        lines.extend(
            [
                f"### {cu_count} Compute Units",
                "",
                "| gem5 stat | Naive | Optimized | Optimized vs Naive | Note |",
                "|--------|-------|-----------|--------------------|------|",
            ]
        )
        for label, attr, note, decimals in assignment_metric_rows():
            naive_num = metric_number(naive, attr)
            optimized_num = metric_number(optimized, attr)
            change = (
                pct_change(optimized_num, naive_num)
                if naive_num is not None and optimized_num is not None
                else "N/A"
            )
            lines.append(
                f"| {label} | {metric_value(naive, attr, decimals)} | "
                f"{metric_value(optimized, attr, decimals)} | {change} | {note} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Diagnostic Totals",
            "",
        ]
    )
    validate_comparison_rows(diagnostic_metric_rows(), "Histogram diagnostic metrics")
    for cu_count in CU_COUNTS:
        naive = data[cu_count]["naive"]
        optimized = data[cu_count]["optimized"]
        lines.extend(
            [
                f"### {cu_count} Compute Units",
                "",
                "| Metric | Naive | Optimized | Optimized vs Naive | Note |",
                "|--------|-------|-----------|--------------------|------|",
            ]
        )
        for label, attr, note, decimals in diagnostic_metric_rows():
            naive_num = metric_number(naive, attr)
            optimized_num = metric_number(optimized, attr)
            change = (
                pct_change(optimized_num, naive_num)
                if naive_num is not None and optimized_num is not None
                else "N/A"
            )
            lines.append(
                f"| {label} | {metric_value(naive, attr, decimals)} | "
                f"{metric_value(optimized, attr, decimals)} | {change} | {note} |"
            )
        lines.append("")

    lines.extend(["## Scaling by Kernel", ""])
    for kernel in KERNELS:
        label = kernel.capitalize()
        base = data[CU_COUNTS[0]][kernel].total_cycles_mean
        lines.extend(
            [
                f"### {label}",
                "",
                "| CU | average totalCycles | Ratio vs 2 CU |",
                "|----|---------------------|---------------|",
            ]
        )
        for cu_count in CU_COUNTS:
            run = data[cu_count][kernel]
            lines.append(
                f"| {cu_count} | {fmt(run.total_cycles_mean, 0)} | "
                f"{ratio(base, run.total_cycles_mean)} |"
            )
        lines.append("")

    lines.extend(["## Per-CU Details", ""])
    for cu_count in CU_COUNTS:
        for kernel in KERNELS:
            run = data[cu_count][kernel]
            lines.extend(
                [
                    f"### {kernel.capitalize()}, {cu_count} CUs",
                    "",
                    "| CU | vALUInsts | ldsBankAccesses | totalCycles | vpc |",
                    "|----|-----------|-------------------|-------------|-----|",
                ]
            )
            for cu in range(cu_count):
                lines.append(
                    f"| {cu} | {fmt(run.valu_insts_by_cu[cu], 0)} | "
                    f"{fmt(run.lds_bank_accesses_by_cu[cu], 0)} | "
                    f"{fmt(run.total_cycles_by_cu[cu], 0)} | "
                    f"{fmt(run.vpc_by_cu[cu])} |"
                )
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    histogram_dir = Path(__file__).resolve().parent
    results_root = histogram_dir / "results"
    report_path = histogram_dir / "exact_results.md"

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
