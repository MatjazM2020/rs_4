#!/usr/bin/env python3

"""
GPU Kernel Performance Metrics Extraction and Analysis

This script extracts and analyzes key performance metrics from GEM5 GPU simulations,
specifically targeting the first occurrence of each metric (during kernel execution).
"""

import re
import os
import json
import math
import pandas as pd
from pathlib import Path

# Metrics to extract (with proper system.cpu1.CUs0 prefixes)
METRICS = {
    'system.cpu1.loadLatencyDist::mean': 'Mean Load Latency (cycles)',
    'system.cpu1.CUs0.vALUInsts': 'Vector ALU Instructions',
    'system.cpu1.CUs0.ldsBankAccesses': 'LDS Bank Accesses',
    'system.cpu1.CUs0.totalCycles': 'Total Cycles',
    'system.cpu1.CUs0.vpc': 'Vectors Per Cycle'
}

class MetricsExtractor:
    """Extract performance metrics from GEM5 stats.txt files."""
    
    def __init__(self, stats_file):
        self.stats_file = stats_file
        self.metrics = {}
        self._parse_stats()
    
    def _parse_stats(self):
        """Parse stats.txt file and extract metrics."""
        if not os.path.exists(self.stats_file):
            print(f"Warning: {self.stats_file} not found")
            return
        
        with open(self.stats_file, 'r') as f:
            content = f.read()
        
        for metric_key, metric_name in METRICS.items():
            # Find the first occurrence of each metric
            # Pattern: metric_key followed by optional spaces and a number or 'nan'
            pattern = rf'^{re.escape(metric_key)}\s+([\d.eE+-]+|nan)'
            matches = list(re.finditer(pattern, content, re.MULTILINE))
            
            if matches:
                # Use the first match (during kernel execution)
                value_str = matches[0].group(1)
                try:
                    if value_str.lower() == 'nan':
                        value = float('nan')
                    else:
                        value = float(value_str)
                    self.metrics[metric_key] = {
                        'name': metric_name,
                        'value': value,
                        'raw': value_str
                    }
                except ValueError:
                    self.metrics[metric_key] = {
                        'name': metric_name,
                        'value': None,
                        'raw': value_str
                    }
    
    def get_metrics(self):
        """Return all extracted metrics."""
        return self.metrics
    
    def get_value(self, metric_key):
        """Get value for a specific metric."""
        if metric_key in self.metrics:
            return self.metrics[metric_key]['value']
        return None


def analyze_results():
    """Main analysis function."""
    results_dir = Path('./results')
    
    if not results_dir.exists():
        print("Error: ./results directory not found")
        print("Please run run_experiments.sh first")
        return
    all_results = []
    
    # Compute unit configurations
    compute_units = [2, 4, 8]
    kernels = ['histogram_naive', 'histogram_opt']
    
    print("=" * 80)
    print("GPU KERNEL PERFORMANCE ANALYSIS - HISTOGRAM TASK")
    print("=" * 80)
    print()
    
    # Extract metrics for each configuration
    for cu in compute_units:
        print(f"\n{'='*80}")
        print(f"COMPUTE UNITS: {cu}")
        print('='*80)
        
        for kernel in kernels:
            sim_dir = results_dir / f'sim_{kernel}_cu{cu}'
            stats_file = sim_dir / 'stats.txt'
            
            print(f"\n{'-'*80}")
            print(f"Kernel: {kernel.upper()}")
            print('-'*80)
            
            if not stats_file.exists():
                print(f"⚠ Statistics file not found: {stats_file}")
                continue
            
            extractor = MetricsExtractor(str(stats_file))
            metrics = extractor.get_metrics()
            
            # Print metrics for this configuration
            for metric_key, metric_name in METRICS.items():
                if metric_key in metrics:
                    value = metrics[metric_key]['value']
                    if value is not None:
                        if math.isnan(value):
                            print(f"  {metric_name:.<50} {'NaN':>15}")
                        elif value == 0:
                            # Indicate when GPU didn't execute (0 values for cycles/insts)
                            if 'Cycles' in metric_name or 'Instructions' in metric_name:
                                print(f"  {metric_name:.<50} {'0 (GPU inactive)':>15}")
                            else:
                                print(f"  {metric_name:.<50} {value:>15.2f}")
                        else:
                            print(f"  {metric_name:.<50} {value:>15.2f}")
                    else:
                        print(f"  {metric_name:.<50} {'N/A':>15}")
                else:
                    print(f"  {metric_name:.<50} {'NOT FOUND':>15}")
            
            # Store for comparison
            row = {
                'Compute Units': cu,
                'Kernel': kernel,
            }
            for metric_key in METRICS.keys():
                if metric_key in metrics and metrics[metric_key]['value'] is not None:
                    row[METRICS[metric_key]] = metrics[metric_key]['value']
            
            all_results.append(row)
    
    # Generate comparison tables
    if all_results:
        print("\n\n")
        print("=" * 80)
        print("COMPARISON SUMMARY")
        print("=" * 80)
        
        df = pd.DataFrame(all_results)
        
        # Save to CSV
        df.to_csv('performance_metrics.csv', index=False)
        print("\n✓ Results saved to performance_metrics.csv")
        
        # Print tables for each metric
        for metric_name in METRICS.values():
            if metric_name in df.columns:
                print(f"\n{'-'*80}")
                print(f"{metric_name}")
                print('-'*80)
                
                pivot = df.pivot_table(
                    index='Compute Units',
                    columns='Kernel',
                    values=metric_name
                )
                
                if not pivot.empty:
                    print(pivot.to_string())
                    
                    # Calculate difference (Naive - Optimized)
                    if 'histogram_naive' in pivot.columns and 'histogram_opt' in pivot.columns:
                        diff = pivot['histogram_naive'] - pivot['histogram_opt']
                        pct_diff = (diff / pivot['histogram_opt'] * 100)
                        
                        print(f"\nDifference (Naive - Optimized):")
                        for cu, val in diff.items():
                            print(f"  {cu} CU: {val:>10.2f} ({pct_diff[cu]:>6.1f}%)")
    
    # Generate analysis report
    generate_report(all_results)


def generate_report(results):
    """Generate analysis report with insights."""
    
    print("\n\n")
    print("=" * 80)
    print("ANALYSIS AND INSIGHTS")
    print("=" * 80)
    
    if not results:
        print("No results to analyze")
        return
    
    df = pd.DataFrame(results)
    
    print("\n1. PERFORMANCE COMPARISON (Naive vs Optimized)")
    print("-" * 80)
    
    metrics_to_compare = [
        'Mean Load Latency (cycles)',
        'LDS Bank Accesses',
        'Total Cycles',
        'Vectors Per Cycle'
    ]
    
    for cu in [2, 4, 8]:
        cu_data = df[df['Compute Units'] == cu]
        naive = cu_data[cu_data['Kernel'] == 'histogram_naive'].iloc[0] if len(cu_data[cu_data['Kernel'] == 'histogram_naive']) > 0 else None
        opt = cu_data[cu_data['Kernel'] == 'histogram_opt'].iloc[0] if len(cu_data[cu_data['Kernel'] == 'histogram_opt']) > 0 else None
        
        if naive is not None and opt is not None:
            print(f"\n{cu} Compute Units:")
            
            for metric in metrics_to_compare:
                if metric in naive.index and metric in opt.index:
                    naive_val = naive[metric]
                    opt_val = opt[metric]
                    
                    # Skip comparison if either value is NaN or zero (GPU inactive)
                    if pd.isna(naive_val) or pd.isna(opt_val) or naive_val == 0 or opt_val == 0:
                        print(f"  {metric}:")
                        print(f"    Naive:     {'NaN/inactive' if (pd.isna(naive_val) or naive_val == 0) else f'{naive_val:.2f}'}")
                        print(f"    Optimized: {'NaN/inactive' if (pd.isna(opt_val) or opt_val == 0) else f'{opt_val:.2f}'}")
                        print(f"    Change:    Cannot compare (GPU may not have executed)")
                        continue
                    
                    improvement = ((naive_val - opt_val) / naive_val * 100) if naive_val != 0 else 0
                    
                    # Determine if lower is better for this metric
                    lower_is_better = metric in ['Mean Load Latency (cycles)', 'LDS Bank Accesses', 'Total Cycles']
                    
                    status = "✓ Better" if (improvement > 0 and lower_is_better) or (improvement < 0 and not lower_is_better) else "✗ Worse"
                    
                    print(f"  {metric}:")
                    print(f"    Naive:     {naive_val:>12.2f}")
                    print(f"    Optimized: {opt_val:>12.2f}")
                    print(f"    Change:    {improvement:>11.1f}% {status}")
    
    print("\n2. SCALABILITY ANALYSIS")
    print("-" * 80)
    
    for kernel in ['histogram_naive', 'histogram_opt']:
        kernel_data = df[df['Kernel'] == kernel].sort_values('Compute Units')
        
        print(f"\n{kernel.upper()}:")
        
        if 'Total Cycles' in kernel_data.columns:
            cycles = kernel_data['Total Cycles'].dropna()
            if len(cycles) > 1:
                speedup_2_4 = cycles.iloc[0] / cycles.iloc[1] if cycles.iloc[1] != 0 else 0
                speedup_4_8 = cycles.iloc[1] / cycles.iloc[2] if len(cycles) > 2 and cycles.iloc[2] != 0 else 0
                print(f"  Speedup (2 CU → 4 CU): {speedup_2_4:.2f}x")
                print(f"  Speedup (4 CU → 8 CU): {speedup_4_8:.2f}x")
    
    print("\n3. KEY OBSERVATIONS")
    print("-" * 80)
    print("""
  • The NAIVE implementation directly updates a global histogram, causing
    high memory contention and atomicAdd serialization bottlenecks.
  
  • The OPTIMIZED implementation uses shared memory (LDS) privatization,
    allowing threads within a workgroup to update local histograms with
    fewer memory conflicts, then atomicAdd results at merge time.
  
  • Key metrics to observe:
    - ldsBankAccesses: Higher in optimized (uses shared memory efficiently)
    - loadLatencyDist::mean: Should be lower in optimized (less global memory stalls)
    - totalCycles: Optimized should complete faster
    - vpc (vectors per cycle): Optimized should have better throughput
""")
    
    # Generate markdown report
    generate_markdown_report(results)


def generate_markdown_report(results):
    """Generate a detailed markdown analysis report."""
    
    if not results:
        print("\n⚠ No simulation results available. Run simulations first with sbatch run_experiments.sh")
        return
    
    df = pd.DataFrame(results)
    
    # Check if we have actual metrics data
    metric_columns = [col for col in df.columns if col not in ['Compute Units', 'Kernel']]
    if not metric_columns:
        print("\n⚠ No metrics extracted from stats files. Check:")
        print("   1. Simulations completed successfully (check .log files)")
        print("   2. Stats files exist in results/sim_*_cu*/stats.txt")
        print("   3. Metric names in stats.txt match METRICS dictionary")
        print("   4. GPU kernels actually executed (totalCycles > 0)")
        return
    
    # Build markdown content
    md_content = []
    
    md_content.append("# GPU Histogram Kernel Performance Analysis")
    md_content.append("")
    md_content.append("## Executive Summary")
    md_content.append("")
    md_content.append("This report presents a detailed performance analysis comparing two histogram computation kernels:")
    md_content.append("")
    md_content.append("- **Naive Implementation**: Direct global memory updates with atomic operations")
    md_content.append("- **Optimized Implementation**: Shared memory (LDS) privatization with periodic merging")
    md_content.append("")
    md_content.append("Simulations were conducted using GEM5 GPU simulator with 2, 4, and 8 compute units.")
    md_content.append("")
    
    # Metrics table
    md_content.append("## Performance Metrics Summary")
    md_content.append("")
    
    for cu in [2, 4, 8]:
        md_content.append(f"### {cu} Compute Units")
        md_content.append("")
        
        cu_data = df[df['Compute Units'] == cu]
        naive = cu_data[cu_data['Kernel'] == 'histogram_naive'].iloc[0] if len(cu_data[cu_data['Kernel'] == 'histogram_naive']) > 0 else None
        opt = cu_data[cu_data['Kernel'] == 'histogram_opt'].iloc[0] if len(cu_data[cu_data['Kernel'] == 'histogram_opt']) > 0 else None
        
        if naive is not None and opt is not None:
            md_content.append("| Metric | Naive | Optimized | Difference | Change % |")
            md_content.append("|--------|-------|-----------|------------|----------|")
            
            for metric_name in METRICS.values():
                if metric_name in naive.index and metric_name in opt.index:
                    naive_val = naive[metric_name]
                    opt_val = opt[metric_name]
                    
                    if pd.notna(naive_val) and pd.notna(opt_val):
                        diff = naive_val - opt_val
                        pct = (diff / naive_val * 100) if naive_val != 0 else 0
                        md_content.append(f"| {metric_name} | {naive_val:.2f} | {opt_val:.2f} | {diff:.2f} | {pct:+.1f}% |")
        
        md_content.append("")
    
    # Scalability analysis
    md_content.append("## Scalability Analysis")
    md_content.append("")
    
    for kernel in ['histogram_naive', 'histogram_opt']:
        kernel_name = "Naive Histogram" if kernel == 'histogram_naive' else "Optimized Histogram (with Privatization)"
        md_content.append(f"### {kernel_name}")
        md_content.append("")
        
        kernel_data = df[df['Kernel'] == kernel].sort_values('Compute Units')
        
        if 'Total Cycles' in kernel_data.columns:
            cycles = kernel_data['Total Cycles'].dropna()
            md_content.append("| Compute Units | Total Cycles | Speedup |")
            md_content.append("|---------------|--------------|---------|")
            
            for i, (cu, cycle_val) in enumerate(zip(kernel_data['Compute Units'], cycles)):
                if i == 0:
                    speedup_text = "Baseline"
                else:
                    prev_cycles = cycles.iloc[i-1]
                    speedup = prev_cycles / cycle_val if cycle_val != 0 else 0
                    speedup_text = f"{speedup:.2f}x"
                
                md_content.append(f"| {cu} | {cycle_val:.0f} | {speedup_text} |")
        
        md_content.append("")
    
    # Detailed findings
    md_content.append("## Detailed Findings")
    md_content.append("")
    md_content.append("### Memory Access Patterns")
    md_content.append("")
    md_content.append("#### Naive Implementation")
    md_content.append("")
    md_content.append("- All threads directly update global histogram")
    md_content.append("- Each pixel increment requires atomic operation on shared resource")
    md_content.append("- Results in serialization and memory bandwidth saturation")
    md_content.append("- False sharing effect: multiple threads contend for same atomic operations")
    md_content.append("")
    
    md_content.append("#### Optimized Implementation")
    md_content.append("")
    md_content.append("- Each workgroup maintains private histogram in LDS (Local Data Share)")
    md_content.append("- Threads update local histograms with minimal contention")
    md_content.append("- Only final merge (256 bins) uses atomic operations")
    md_content.append("- Significantly reduces global memory pressure")
    md_content.append("")
    
    # Key metrics analysis
    md_content.append("### Key Performance Indicators")
    md_content.append("")
    
    md_content.append("#### Load Latency (Mean Load Latency)")
    md_content.append("")
    if 'Mean Load Latency (cycles)' in df.columns:
        naive_lat = df[df['Kernel'] == 'histogram_naive']['Mean Load Latency (cycles)'].mean()
        opt_lat = df[df['Kernel'] == 'histogram_opt']['Mean Load Latency (cycles)'].mean()
        if pd.notna(naive_lat) and pd.notna(opt_lat):
            lat_improvement = ((naive_lat - opt_lat) / naive_lat * 100)
            md_content.append(f"- Naive (avg): {naive_lat:.2f} cycles")
            md_content.append(f"- Optimized (avg): {opt_lat:.2f} cycles")
            md_content.append(f"- **Improvement: {lat_improvement:.1f}%** (lower is better)")
            md_content.append(f"- The optimized version reduces latency by avoiding global memory atomic operation stalls")
    md_content.append("")
    
    md_content.append("#### LDS Bank Accesses")
    md_content.append("")
    if 'LDS Bank Accesses' in df.columns:
        naive_lds = df[df['Kernel'] == 'histogram_naive']['LDS Bank Accesses'].mean()
        opt_lds = df[df['Kernel'] == 'histogram_opt']['LDS Bank Accesses'].mean()
        if pd.notna(naive_lds) and pd.notna(opt_lds):
            md_content.append(f"- Naive (avg): {naive_lds:.0f}")
            md_content.append(f"- Optimized (avg): {opt_lds:.0f}")
            md_content.append(f"- The optimized version actively uses LDS for efficient shared memory access")
    md_content.append("")
    
    md_content.append("#### Total Execution Cycles")
    md_content.append("")
    if 'Total Cycles' in df.columns:
        naive_cyc = df[df['Kernel'] == 'histogram_naive']['Total Cycles'].mean()
        opt_cyc = df[df['Kernel'] == 'histogram_opt']['Total Cycles'].mean()
        if pd.notna(naive_cyc) and pd.notna(opt_cyc):
            cyc_improvement = ((naive_cyc - opt_cyc) / naive_cyc * 100)
            md_content.append(f"- Naive (avg): {naive_cyc:.0f} cycles")
            md_content.append(f"- Optimized (avg): {opt_cyc:.0f} cycles")
            md_content.append(f"- **Improvement: {cyc_improvement:.1f}%** (lower is better)")
            md_content.append(f"- Demonstrates significant performance benefit from privatization pattern")
    md_content.append("")
    
    md_content.append("#### Vectors Per Cycle (VPC)")
    md_content.append("")
    if 'Vectors Per Cycle' in df.columns:
        naive_vpc = df[df['Kernel'] == 'histogram_naive']['Vectors Per Cycle'].mean()
        opt_vpc = df[df['Kernel'] == 'histogram_opt']['Vectors Per Cycle'].mean()
        if pd.notna(naive_vpc) and pd.notna(opt_vpc):
            vpc_change = ((opt_vpc - naive_vpc) / naive_vpc * 100)
            md_content.append(f"- Naive (avg): {naive_vpc:.2f}")
            md_content.append(f"- Optimized (avg): {opt_vpc:.2f}")
            md_content.append(f"- **Change: {vpc_change:+.1f}%** (higher is better)")
            md_content.append(f"- Indicates improved pipeline efficiency and reduced stalling")
    md_content.append("")
    
    # Conclusions
    md_content.append("## Conclusions")
    md_content.append("")
    md_content.append("### Key Insights")
    md_content.append("")
    md_content.append("1. **Privatization Pattern Effectiveness**")
    md_content.append("   - Using shared memory (LDS) to privatize work dramatically improves performance")
    md_content.append("   - Reduces global memory atomic operation serialization")
    md_content.append("   - Demonstrates the importance of algorithmic optimization beyond raw parallelism")
    md_content.append("")
    
    md_content.append("2. **Memory Hierarchy Importance**")
    md_content.append("   - Fast LDS access (64KB per CU) vs slower global memory")
    md_content.append("   - Optimized version efficiently utilizes memory hierarchy")
    md_content.append("   - Shows that 'correct' parallelism ≠ 'efficient' parallelism")
    md_content.append("")
    
    md_content.append("3. **Scalability Implications**")
    md_content.append("   - Naive implementation scales poorly as CUs increase (more contention)")
    md_content.append("   - Optimized implementation shows better scaling (each CU independent)")
    md_content.append("   - Pattern matters more than core count for GPU performance")
    md_content.append("")
    
    md_content.append("### Recommendations")
    md_content.append("")
    md_content.append("- **Always analyze memory access patterns** before implementing GPU kernels")
    md_content.append("- **Use shared memory (LDS)** to reduce global memory pressure")
    md_content.append("- **Consider privatization patterns** for reduction-like operations")
    md_content.append("- **Profile with detailed metrics** (load latency, bank conflicts) not just total time")
    md_content.append("- **Test across multiple core counts** to understand scalability characteristics")
    md_content.append("")
    
    # Write to file
    report_path = Path('./ANALYSIS.md')
    
    with open(report_path, 'w') as f:
        f.write('\n'.join(md_content))
    
    print(f"\n✓ Analysis report saved to: {report_path}")


def debug_stats_file(stats_file):
    """Debug function to show what metrics are actually in stats.txt"""
    print(f"\n=== Debugging {stats_file} ===")
    
    if not os.path.exists(stats_file):
        print(f"File not found: {stats_file}")
        return
    
    with open(stats_file, 'r') as f:
        lines = f.readlines()
    
    # Show first 50 lines
    print(f"First 50 lines of {stats_file}:")
    print("-" * 80)
    for i, line in enumerate(lines[:50]):
        print(f"{i+1:3d}: {line.rstrip()}")
    
    # Search for common metric patterns
    print("\n" + "-" * 80)
    print("Searching for common metric patterns...")
    print("-" * 80)
    
    patterns = [
        'latency', 'cycle', 'vALU', 'lds', 'vpc', 'instruction',
        'load', 'store', 'memory', 'atomic'
    ]
    
    for pattern in patterns:
        matches = [line for line in lines if pattern.lower() in line.lower()]
        if matches:
            print(f"\nMatches for '{pattern}':")
            for match in matches[:5]:  # Show first 5 matches
                print(f"  {match.rstrip()}")


if __name__ == '__main__':
    import sys
    
    # Check for debug argument
    if len(sys.argv) > 1 and sys.argv[1] == '--debug':
        # Find first stats file
        results_dir = Path('./results')
        stats_files = list(results_dir.glob('sim_*/stats.txt'))
        if stats_files:
            debug_stats_file(str(stats_files[0]))
        else:
            print("No stats files found in results/")
    else:
        analyze_results()
