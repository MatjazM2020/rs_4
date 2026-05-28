#!/usr/bin/env python3

"""
SpMV Kernel Performance Metrics Extraction and Analysis

This script extracts and analyzes key performance metrics from GEM5 GPU simulations
for SpMV kernels with different work distributions (divergent vs uniform).
Focuses on control flow divergence impact and memory coalescing efficiency.
"""

import re
import os
import json
import math
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Metrics to extract - SpMV specific metrics
# Using system.cpu1.CUs0 prefix for GPU metrics
METRICS = {
    'system.cpu1.CUs0.controlFlowDivergenceDist::mean': 'Control Flow Divergence Mean',
    'system.cpu1.CUs0.controlFlowDivergenceDist::stdev': 'Control Flow Divergence StDev',
    'system.cpu1.CUs0.vALUInsts': 'Vector ALU Instructions',
    'system.cpu1.CUs0.globalReads': 'Global Memory Reads',
    'system.cpu1.CUs0.globalWrites': 'Global Memory Writes',
    'system.cpu1.CUs0.coalsrLineAddresses::total': 'Coalesced Memory Accesses',
    'system.cpu1.CUs0.totalCycles': 'Total Cycles'
}

class MetricsExtractor:
    """Extract performance metrics from GEM5 stats.txt files."""
    
    def __init__(self, stats_file):
        self.stats_file = stats_file
        self.metrics = {}
        self.all_occurrences = defaultdict(list)
        self._parse_stats()
    
    def _parse_stats(self):
        """Parse stats.txt file and extract metrics - get ALL occurrences."""
        if not os.path.exists(self.stats_file):
            print(f"Warning: {self.stats_file} not found")
            return
        
        with open(self.stats_file, 'r') as f:
            content = f.read()
        
        for metric_key, metric_name in METRICS.items():
            # Find ALL occurrences of each metric
            # Pattern: metric_key followed by optional spaces and a number or 'nan'
            pattern = rf'^{re.escape(metric_key)}\s+([\d.eE+-]+|nan)'
            matches = list(re.finditer(pattern, content, re.MULTILINE))
            
            if matches:
                # Store all occurrences
                for i, match in enumerate(matches):
                    value_str = match.group(1)
                    try:
                        if value_str.lower() == 'nan':
                            value = float('nan')
                        else:
                            value = float(value_str)
                        self.all_occurrences[metric_key].append({
                            'occurrence': i + 1,
                            'value': value,
                            'raw': value_str
                        })
                    except ValueError:
                        self.all_occurrences[metric_key].append({
                            'occurrence': i + 1,
                            'value': None,
                            'raw': value_str
                        })
                
                # Use the FIRST occurrence (during first kernel execution)
                first_value_str = matches[0].group(1)
                try:
                    if first_value_str.lower() == 'nan':
                        value = float('nan')
                    else:
                        value = float(first_value_str)
                    self.metrics[metric_key] = {
                        'name': metric_name,
                        'value': value,
                        'raw': first_value_str,
                        'occurrence': 1
                    }
                except ValueError:
                    self.metrics[metric_key] = {
                        'name': metric_name,
                        'value': None,
                        'raw': first_value_str,
                        'occurrence': 1
                    }
    
    def get_metrics(self):
        """Return all extracted metrics (first occurrence only)."""
        return self.metrics
    
    def get_value(self, metric_key, occurrence=1):
        """Get value for a specific metric at a specific occurrence."""
        if metric_key in self.all_occurrences:
            if occurrence <= len(self.all_occurrences[metric_key]):
                return self.all_occurrences[metric_key][occurrence - 1]['value']
        return None


def analyze_results():
    """Main analysis function."""
    results_dir = Path('./spmv/results')
    
    if not results_dir.exists():
        print("Error: ./spmv/results directory not found")
        print("Please run sbatch spmv/run_experiments.sh first")
        return
    
    all_results = []
    
    # Compute unit configurations
    compute_units = [2, 4, 8]
    
    print("=" * 90)
    print("GPU SPMV KERNEL PERFORMANCE ANALYSIS - THREAD DIVERGENCE IMPACT")
    print("=" * 90)
    print()
    
    # Extract metrics for each configuration
    for cu in compute_units:
        print(f"\n{'='*90}")
        print(f"COMPUTE UNITS: {cu}")
        print('='*90)
        
        # SpMV runs with both divergent and uniform implementations
        # But they're in the same binary, so we get both from one simulation
        sim_dir = results_dir / f'sim_spmv_cu{cu}'
        stats_file = sim_dir / 'stats.txt'
        
        print(f"\nSimulation Directory: {sim_dir}")
        
        if not stats_file.exists():
            print(f"⚠ Statistics file not found: {stats_file}")
            continue
        
        extractor = MetricsExtractor(str(stats_file))
        metrics = extractor.get_metrics()
        
        # Print metrics for this configuration
        print(f"\n{'-'*90}")
        print(f"Metrics (First Kernel Execution - Divergent Implementation)")
        print('-'*90)
        
        for metric_key, metric_name in METRICS.items():
            if metric_key in metrics:
                value = metrics[metric_key]['value']
                if value is not None:
                    if math.isnan(value):
                        print(f"  {metric_name:.<60} {'NaN':>20}")
                    elif value == 0 and 'Cycles' in metric_name:
                        print(f"  {metric_name:.<60} {'0 (GPU inactive)':>20}")
                    elif value >= 1e6 or value <= 1e-6 and value > 0:
                        print(f"  {metric_name:.<60} {value:>20.3e}")
                    else:
                        print(f"  {metric_name:.<60} {value:>20.2f}")
                else:
                    print(f"  {metric_name:.<60} {'N/A':>20}")
            else:
                print(f"  {metric_name:.<60} {'NOT FOUND':>20}")
        
        # Now check for second kernel execution (Uniform implementation)
        print(f"\n{'-'*90}")
        print(f"Metrics (Second Kernel Execution - Uniform Implementation)")
        print('-'*90)
        
        divergence_comparison = {}
        memory_comparison = {}
        
        for metric_key, metric_name in METRICS.items():
            # Get first occurrence (divergent)
            first_val = extractor.get_value(metric_key, occurrence=1)
            # Get second occurrence (uniform)
            second_val = extractor.get_value(metric_key, occurrence=2)
            
            if second_val is not None:
                if math.isnan(second_val):
                    print(f"  {metric_name:.<60} {'NaN':>20}")
                elif second_val == 0 and 'Cycles' in metric_name:
                    print(f"  {metric_name:.<60} {'0 (GPU inactive)':>20}")
                elif second_val >= 1e6 or (second_val <= 1e-6 and second_val > 0):
                    print(f"  {metric_name:.<60} {second_val:>20.3e}")
                else:
                    print(f"  {metric_name:.<60} {second_val:>20.2f}")
                
                # Store for comparison
                if 'Divergence' in metric_name:
                    divergence_comparison[metric_name] = {
                        'divergent': first_val,
                        'uniform': second_val
                    }
                elif 'Global' in metric_name or 'Coalesced' in metric_name:
                    memory_comparison[metric_name] = {
                        'divergent': first_val,
                        'uniform': second_val
                    }
            else:
                print(f"  {metric_name:.<60} {'N/A (2nd kernel not executed)':>20}")
        
        # Store for comparison table
        row = {
            'Compute Units': cu,
        }
        
        # Add divergent implementation metrics
        for metric_key in METRICS.keys():
            if metric_key in metrics and metrics[metric_key]['value'] is not None:
                col_name = METRICS[metric_key] + ' (Divergent)'
                row[col_name] = metrics[metric_key]['value']
        
        # Add uniform implementation metrics
        for metric_key in METRICS.keys():
            second_val = extractor.get_value(metric_key, occurrence=2)
            if second_val is not None:
                col_name = METRICS[metric_key] + ' (Uniform)'
                row[col_name] = second_val
        
        all_results.append(row)
        
        # Print comparison within this CU configuration
        if divergence_comparison:
            print(f"\n{'-'*90}")
            print(f"Thread Divergence Comparison (Divergent vs Uniform)")
            print('-'*90)
            
            for metric_name, values in divergence_comparison.items():
                div_val = values['divergent']
                unif_val = values['uniform']
                
                if div_val is not None and unif_val is not None and not math.isnan(div_val) and not math.isnan(unif_val):
                    # For divergence, lower is better
                    improvement = ((div_val - unif_val) / div_val * 100) if div_val != 0 else 0
                    status = "✓ Better" if improvement > 0 else "✗ Worse"
                    
                    print(f"\n  {metric_name}:")
                    print(f"    Divergent: {div_val:>15.4f}")
                    print(f"    Uniform:   {unif_val:>15.4f}")
                    print(f"    Reduction: {improvement:>14.1f}% {status}")
    
    # Generate comparison tables
    if all_results:
        print("\n\n")
        print("=" * 90)
        print("COMPARISON SUMMARY")
        print("=" * 90)
        
        df = pd.DataFrame(all_results)
        
        # Save to CSV
        df.to_csv('spmv_performance_metrics.csv', index=False)
        print("\n✓ Results saved to spmv_performance_metrics.csv")
    
    # Generate analysis report
    generate_report(all_results)


def generate_report(results):
    """Generate analysis report with insights."""
    
    print("\n\n")
    print("=" * 90)
    print("ANALYSIS AND INSIGHTS")
    print("=" * 90)
    
    if not results:
        print("No results to analyze")
        return
    
    df = pd.DataFrame(results)
    
    print("\n1. CONTROL FLOW DIVERGENCE ANALYSIS")
    print("-" * 90)
    
    divergence_metrics = [
        'Control Flow Divergence Mean (Divergent)',
        'Control Flow Divergence Mean (Uniform)',
        'Control Flow Divergence StDev (Divergent)',
        'Control Flow Divergence StDev (Uniform)'
    ]
    
    for cu in [2, 4, 8]:
        cu_data = df[df['Compute Units'] == cu]
        
        if len(cu_data) > 0:
            row = cu_data.iloc[0]
            
            print(f"\n{cu} Compute Units:")
            
            div_mean_div = row.get('Control Flow Divergence Mean (Divergent)')
            div_mean_unif = row.get('Control Flow Divergence Mean (Uniform)')
            
            if pd.notna(div_mean_div) and pd.notna(div_mean_unif):
                improvement = ((div_mean_div - div_mean_unif) / div_mean_div * 100) if div_mean_div != 0 else 0
                print(f"  Control Flow Divergence Mean:")
                print(f"    Divergent Implementation: {div_mean_div:>12.4f}")
                print(f"    Uniform Implementation:   {div_mean_unif:>12.4f}")
                print(f"    Improvement:              {improvement:>11.1f}% ✓" if improvement > 0 else f"    Improvement:              {improvement:>11.1f}% ✗")
            
            div_std_div = row.get('Control Flow Divergence StDev (Divergent)')
            div_std_unif = row.get('Control Flow Divergence StDev (Uniform)')
            
            if pd.notna(div_std_div) and pd.notna(div_std_unif):
                improvement = ((div_std_div - div_std_unif) / div_std_div * 100) if div_std_div != 0 else 0
                print(f"  Control Flow Divergence StDev:")
                print(f"    Divergent Implementation: {div_std_div:>12.4f}")
                print(f"    Uniform Implementation:   {div_std_unif:>12.4f}")
                print(f"    Improvement:              {improvement:>11.1f}% ✓" if improvement > 0 else f"    Improvement:              {improvement:>11.1f}% ✗")
    
    print("\n2. MEMORY ACCESS EFFICIENCY")
    print("-" * 90)
    
    for cu in [2, 4, 8]:
        cu_data = df[df['Compute Units'] == cu]
        
        if len(cu_data) > 0:
            row = cu_data.iloc[0]
            
            print(f"\n{cu} Compute Units:")
            
            gr_div = row.get('Global Memory Reads (Divergent)')
            gr_unif = row.get('Global Memory Reads (Uniform)')
            gw_div = row.get('Global Memory Writes (Divergent)')
            gw_unif = row.get('Global Memory Writes (Uniform)')
            coal_div = row.get('Coalesced Memory Accesses (Divergent)')
            coal_unif = row.get('Coalesced Memory Accesses (Uniform)')
            
            if pd.notna(gr_div) and pd.notna(gr_unif):
                print(f"  Global Reads:")
                print(f"    Divergent: {gr_div:>12.0f}")
                print(f"    Uniform:   {gr_unif:>12.0f}")
            
            if pd.notna(gw_div) and pd.notna(gw_unif):
                print(f"  Global Writes:")
                print(f"    Divergent: {gw_div:>12.0f}")
                print(f"    Uniform:   {gw_unif:>12.0f}")
            
            if pd.notna(coal_div) and pd.notna(coal_unif):
                coal_ratio_div = coal_div / (gr_div + gw_div) if (gr_div + gw_div) > 0 else 0
                coal_ratio_unif = coal_unif / (gr_unif + gw_unif) if (gr_unif + gw_unif) > 0 else 0
                print(f"  Coalesced Accesses:")
                print(f"    Divergent: {coal_div:>12.0f} ({coal_ratio_div:>6.1%} of total)")
                print(f"    Uniform:   {coal_unif:>12.0f} ({coal_ratio_unif:>6.1%} of total)")
    
    print("\n3. KEY OBSERVATIONS")
    print("-" * 90)
    print("""
  • DIVERGENT IMPLEMENTATION:
    - Rows processed in original order (1, 2, 3, ..., 64, 1, 2, ...)
    - Variable row lengths create work imbalance within wavefront
    - Threads with short rows finish early, others continue → divergence
    - Memory access patterns are irregular and non-coalesced
  
  • UNIFORM IMPLEMENTATION:
    - Rows sorted by non-zero count before launch
    - Similar-length rows grouped together → uniform work distribution
    - All threads in wavefront progress together → reduced divergence
    - Improved memory coalescing due to more uniform access patterns
  
  • METRICS TO OBSERVE:
    - controlFlowDivergenceDist::mean: Should be LOWER for uniform
    - controlFlowDivergenceDist::stdev: Should be LOWER for uniform (more predictable)
    - globalReads/globalWrites: May differ due to memory access patterns
    - coalsrLineAddresses::total: Higher for uniform (better coalescing)
""")
    
    # Generate markdown report
    generate_markdown_report(results)


def generate_markdown_report(results):
    """Generate a detailed markdown analysis report."""
    
    if not results:
        print("\n⚠ No simulation results available. Run simulations first with sbatch spmv/run_experiments.sh")
        return
    
    df = pd.DataFrame(results)
    
    # Check if we have actual metrics data
    metric_columns = [col for col in df.columns if col not in ['Compute Units']]
    if not metric_columns:
        print("\n⚠ No metrics extracted from stats files. Check:")
        print("   1. Simulations completed successfully (check .log files)")
        print("   2. Stats files exist in results/sim_*_cu*/stats.txt")
        print("   3. Metric names in stats.txt match METRICS dictionary")
        print("   4. GPU kernels actually executed (totalCycles > 0)")
        return
    
    # Build markdown content
    md_content = []
    
    md_content.append("# SpMV Kernel Performance Analysis: Thread Divergence Impact")
    md_content.append("")
    md_content.append("## Executive Summary")
    md_content.append("")
    md_content.append("This report presents a detailed performance analysis comparing two sparse matrix-vector")
    md_content.append("multiplication (SpMV) kernel implementations with different work distributions:")
    md_content.append("")
    md_content.append("- **Divergent Implementation**: Processes rows in original order (variable length)")
    md_content.append("- **Uniform Implementation**: Sorts rows by non-zero count (balanced workload)")
    md_content.append("")
    md_content.append("Simulations were conducted using GEM5 GPU simulator with 2, 4, and 8 compute units.")
    md_content.append("The analysis focuses on control flow divergence and memory coalescing efficiency.")
    md_content.append("")
    
    # Test configuration details
    md_content.append("## Matrix Configuration")
    md_content.append("")
    md_content.append("- **Size**: 1024 × 1024")
    md_content.append("- **Non-zero Pattern**: Row i contains (i % 64 + 1) non-zeros")
    md_content.append("- **Total Non-zeros**: 33,280")
    md_content.append("- **Average Non-zeros per Row**: 32.5")
    md_content.append("- **Wavefront Width**: 64 threads (AMD GCN)")
    md_content.append("")
    
    # Metrics summary tables
    md_content.append("## Performance Metrics")
    md_content.append("")
    
    for cu in [2, 4, 8]:
        md_content.append(f"### {cu} Compute Units")
        md_content.append("")
        
        cu_data = df[df['Compute Units'] == cu]
        if len(cu_data) > 0:
            row = cu_data.iloc[0]
            
            # Build comparison table
            md_content.append("| Metric | Divergent | Uniform | Difference | Change % |")
            md_content.append("|--------|-----------|---------|------------|----------|")
            
            # Control Flow Divergence
            div_mean_div = row.get('Control Flow Divergence Mean (Divergent)')
            div_mean_unif = row.get('Control Flow Divergence Mean (Uniform)')
            if pd.notna(div_mean_div) and pd.notna(div_mean_unif):
                diff = div_mean_div - div_mean_unif
                pct = (diff / div_mean_div * 100) if div_mean_div != 0 else 0
                md_content.append(f"| Control Flow Divergence Mean | {div_mean_div:.4f} | {div_mean_unif:.4f} | {diff:.4f} | {pct:+.1f}% |")
            
            # Divergence StDev
            div_std_div = row.get('Control Flow Divergence StDev (Divergent)')
            div_std_unif = row.get('Control Flow Divergence StDev (Uniform)')
            if pd.notna(div_std_div) and pd.notna(div_std_unif):
                diff = div_std_div - div_std_unif
                pct = (diff / div_std_div * 100) if div_std_div != 0 else 0
                md_content.append(f"| Control Flow Divergence StDev | {div_std_div:.4f} | {div_std_unif:.4f} | {diff:.4f} | {pct:+.1f}% |")
            
            # Vector ALU Instructions
            valu_div = row.get('Vector ALU Instructions (Divergent)')
            valu_unif = row.get('Vector ALU Instructions (Uniform)')
            if pd.notna(valu_div) and pd.notna(valu_unif):
                diff = valu_div - valu_unif
                pct = (diff / valu_div * 100) if valu_div != 0 else 0
                md_content.append(f"| Vector ALU Instructions | {valu_div:.0f} | {valu_unif:.0f} | {diff:.0f} | {pct:+.1f}% |")
            
            # Global Reads
            gr_div = row.get('Global Memory Reads (Divergent)')
            gr_unif = row.get('Global Memory Reads (Uniform)')
            if pd.notna(gr_div) and pd.notna(gr_unif):
                diff = gr_div - gr_unif
                pct = (diff / gr_div * 100) if gr_div != 0 else 0
                md_content.append(f"| Global Memory Reads | {gr_div:.0f} | {gr_unif:.0f} | {diff:.0f} | {pct:+.1f}% |")
            
            # Global Writes
            gw_div = row.get('Global Memory Writes (Divergent)')
            gw_unif = row.get('Global Memory Writes (Uniform)')
            if pd.notna(gw_div) and pd.notna(gw_unif):
                diff = gw_div - gw_unif
                pct = (diff / gw_div * 100) if gw_div != 0 else 0
                md_content.append(f"| Global Memory Writes | {gw_div:.0f} | {gw_unif:.0f} | {diff:.0f} | {pct:+.1f}% |")
            
            # Coalesced Accesses
            coal_div = row.get('Coalesced Memory Accesses (Divergent)')
            coal_unif = row.get('Coalesced Memory Accesses (Uniform)')
            if pd.notna(coal_div) and pd.notna(coal_unif):
                diff = coal_div - coal_unif
                pct = (diff / coal_div * 100) if coal_div != 0 else 0
                md_content.append(f"| Coalesced Memory Accesses | {coal_div:.0f} | {coal_unif:.0f} | {diff:+.0f} | {pct:+.1f}% |")
            
            # Total Cycles
            cycles_div = row.get('Total Cycles (Divergent)')
            cycles_unif = row.get('Total Cycles (Uniform)')
            if pd.notna(cycles_div) and pd.notna(cycles_unif):
                diff = cycles_div - cycles_unif
                pct = (diff / cycles_div * 100) if cycles_div != 0 else 0
                speedup = cycles_div / cycles_unif if cycles_unif != 0 else 0
                md_content.append(f"| Total Cycles | {cycles_div:.0f} | {cycles_unif:.0f} | {diff:.0f} | {pct:+.1f}% (Speedup: {speedup:.2f}x) |")
        
        md_content.append("")
    
    # Scalability analysis
    md_content.append("## Scalability Analysis")
    md_content.append("")
    
    for impl_name, col_suffix in [("Divergent", "Divergent"), ("Uniform", "Uniform")]:
        md_content.append(f"### {impl_name} Implementation")
        md_content.append("")
        
        cycles_col = f'Total Cycles ({col_suffix})'
        if cycles_col in df.columns:
            cycles_data = df[cycles_col].dropna()
            if len(cycles_data) > 0:
                md_content.append("| Compute Units | Total Cycles | Speedup from 2 CU |")
                md_content.append("|---------------|--------------|-------------------|")
                
                baseline = cycles_data.iloc[0] if len(cycles_data) > 0 else None
                for cu, cycle_val in zip(df['Compute Units'], df[cycles_col]):
                    if pd.notna(cycle_val) and baseline is not None:
                        speedup = baseline / cycle_val if cycle_val != 0 else 0
                        md_content.append(f"| {cu} | {cycle_val:.0f} | {speedup:.2f}x |")
        
        md_content.append("")
    
    # Detailed findings
    md_content.append("## Detailed Findings")
    md_content.append("")
    
    md_content.append("### Control Flow Divergence")
    md_content.append("")
    md_content.append("Control flow divergence occurs when threads within the same wavefront take different")
    md_content.append("execution paths, causing execution serialization. In SpMV:")
    md_content.append("")
    md_content.append("**Divergent Implementation**:")
    md_content.append("- Threads process rows with variable lengths (1 to 64 non-zeros)")
    md_content.append("- Short row: thread finishes inner loop quickly → goes idle")
    md_content.append("- Long row: thread takes many iterations → blocks other threads")
    md_content.append("- Result: HIGH divergence, many stalled threads")
    md_content.append("")
    md_content.append("**Uniform Implementation**:")
    md_content.append("- Rows sorted by non-zero count before kernel launch")
    md_content.append("- All threads in wavefront process similar-length rows")
    md_content.append("- Inner loop iterations are balanced → threads progress together")
    md_content.append("- Result: LOW divergence, efficient wavefront utilization")
    md_content.append("")
    
    md_content.append("### Memory Access Patterns")
    md_content.append("")
    md_content.append("**Global Memory Coalescing**:")
    md_content.append("- Coalesced accesses: consecutive threads access consecutive memory addresses")
    md_content.append("- Uncoalesced: random access patterns require multiple memory transactions")
    md_content.append("")
    md_content.append("**Divergent**: Non-uniform row selection → irregular memory access patterns")
    md_content.append("")
    md_content.append("**Uniform**: Grouped row processing may improve spatial locality")
    md_content.append("")
    
    md_content.append("### Execution Efficiency")
    md_content.append("")
    md_content.append("**Metric Interpretation**:")
    md_content.append("")
    md_content.append("- **controlFlowDivergenceDist::mean**: Average thread divergence per cycle")
    md_content.append("  - Lower is better (means threads are synchronized)")
    md_content.append("")
    md_content.append("- **controlFlowDivergenceDist::stdev**: Consistency of divergence across time")
    md_content.append("  - Lower indicates more predictable execution")
    md_content.append("")
    md_content.append("- **vALUInsts**: Vector ALU instructions executed")
    md_content.append("  - Reflects actual computation work (should be similar for both)")
    md_content.append("")
    md_content.append("- **globalReads/globalWrites**: Memory transactions")
    md_content.append("  - Both should be similar (same algorithm, same data)")
    md_content.append("  - Difference indicates irregular access patterns")
    md_content.append("")
    md_content.append("- **coalsrLineAddresses::total**: Coalesced cache line accesses")
    md_content.append("  - Higher is better (better memory efficiency)")
    md_content.append("")
    md_content.append("- **totalCycles**: Total execution time")
    md_content.append("  - Lower indicates faster execution")
    md_content.append("  - Improvement comes from reduced divergence overhead")
    md_content.append("")
    
    # Conclusions
    md_content.append("## Conclusions")
    md_content.append("")
    md_content.append("The comparison between divergent and uniform SpMV implementations demonstrates the")
    md_content.append("critical impact of load balancing on GPU kernel performance:")
    md_content.append("")
    md_content.append("1. **Thread Divergence**: Uniform implementation significantly reduces control flow")
    md_content.append("   divergence by ensuring all threads in a wavefront have similar execution paths.")
    md_content.append("")
    md_content.append("2. **Performance Scaling**: Better divergence reduction typically leads to improved")
    md_content.append("   performance scaling with more compute units.")
    md_content.append("")
    md_content.append("3. **Memory Efficiency**: Ordered row processing may improve memory coalescing,")
    md_content.append("   reducing memory transaction overhead.")
    md_content.append("")
    md_content.append("4. **Trade-off Consideration**: Sorting overhead vs. execution improvement - for")
    md_content.append("   single SpMV operation, sorting may be negligible compared to improved execution.")
    md_content.append("")
    
    # Write to file
    output_file = Path('./spmv/ANALYSIS.md')
    with open(output_file, 'w') as f:
        f.write('\n'.join(md_content))
    
    print(f"\n✓ Detailed analysis report generated: {output_file}")


if __name__ == '__main__':
    analyze_results()
