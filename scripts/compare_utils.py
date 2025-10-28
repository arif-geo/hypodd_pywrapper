"""
Utilities for comparing HypoDD relocation results.
"""
import os
import shutil
import numpy as np
import pandas as pd


def compare_relocations(reloc_file1, reloc_file2, label1='Method 1', label2='Method 2'):
    """
    Compare two HypoDD relocation files and report differences.
    
    Args:
        reloc_file1: Path to first .reloc file
        reloc_file2: Path to second .reloc file
        label1: Label for first method
        label2: Label for second method
    
    Returns: 
        DataFrame with comparison statistics
    """
    print(f"\n{'='*70}")
    print(f"Comparing relocations: {label1} vs {label2}")
    print(f"{'='*70}")
    
    # Parse relocation files
    def parse_reloc(file):
        events = []
        with open(file, 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 4:
                    event_id = int(parts[0])
                    lat = float(parts[1])
                    lon = float(parts[2])
                    depth = float(parts[3])
                    events.append({'id': event_id, 'lat': lat, 'lon': lon, 'depth': depth})
        return pd.DataFrame(events)
    
    df1 = parse_reloc(reloc_file1)
    df2 = parse_reloc(reloc_file2)
    
    # Merge on event ID
    merged = df1.merge(df2, on='id', suffixes=('_1', '_2'))
    
    if len(merged) == 0:
        print("ERROR: No common events found in both relocation files!")
        return None
    
    # Calculate differences (in meters, approximate)
    # 1 degree latitude ≈ 111 km
    # 1 degree longitude ≈ 111 km * cos(lat)
    merged['dlat_m'] = (merged['lat_2'] - merged['lat_1']) * 111000
    merged['dlon_m'] = (merged['lon_2'] - merged['lon_1']) * 111000 * np.cos(np.radians(merged['lat_1']))
    merged['ddepth_m'] = (merged['depth_2'] - merged['depth_1']) * 1000
    merged['horizontal_diff_m'] = np.sqrt(merged['dlat_m']**2 + merged['dlon_m']**2)
    merged['3d_diff_m'] = np.sqrt(merged['dlat_m']**2 + merged['dlon_m']**2 + merged['ddepth_m']**2)
    
    # Print statistics
    print(f"\nNumber of relocated events compared: {len(merged)}")
    print(f"\nHorizontal differences (meters):")
    print(f"  Mean:   {merged['horizontal_diff_m'].mean():8.3f}")
    print(f"  Median: {merged['horizontal_diff_m'].median():8.3f}")
    print(f"  Max:    {merged['horizontal_diff_m'].max():8.3f}")
    print(f"  Min:    {merged['horizontal_diff_m'].min():8.3f}")
    
    print(f"\nDepth differences (meters):")
    print(f"  Mean:   {merged['ddepth_m'].mean():8.3f}")
    print(f"  Median: {merged['ddepth_m'].median():8.3f}")
    print(f"  Max:    {merged['ddepth_m'].max():8.3f}")
    print(f"  Min:    {merged['ddepth_m'].min():8.3f}")
    
    print(f"\n3D differences (meters):")
    print(f"  Mean:   {merged['3d_diff_m'].mean():8.3f}")
    print(f"  Median: {merged['3d_diff_m'].median():8.3f}")
    print(f"  Max:    {merged['3d_diff_m'].max():8.3f}")
    print(f"  Min:    {merged['3d_diff_m'].min():8.3f}")
    
    # Find events with large differences
    threshold = 10.0  # meters
    large_diff = merged[merged['3d_diff_m'] > threshold]
    if len(large_diff) > 0:
        print(f"\n⚠️  {len(large_diff)} events with 3D difference > {threshold}m:")
        for _, row in large_diff.iterrows():
            print(f"  Event {row['id']}: {row['3d_diff_m']:.2f}m difference")
    else:
        print(f"\n✅ All events agree within {threshold}m!")
    
    print(f"{'='*70}\n")
    
    return merged


def run_comparison_test(run_dir, hypodd_root, prepare_inputs_func, prepare_catalog_func, 
                       run_ph2dt_func, run_hypodd_func, reloc_to_csv_func):
    """
    Run both CC-only and catalog-only methods and compare results.
    
    Args:
        run_dir: Run directory path
        hypodd_root: HypoDD installation root
        prepare_inputs_func: Function to prepare standard inputs
        prepare_catalog_func: Function to prepare catalog inputs
        run_ph2dt_func: Function to run ph2dt
        run_hypodd_func: Function to run hypoDD
        reloc_to_csv_func: Function to convert .reloc to CSV
    """
    print("\n" + "="*70)
    print("RUNNING COMPARISON TEST: CC-only vs Catalog-only methods")
    print("="*70 + "\n")
    
    # Step 1: Prepare inputs for both methods
    print("STEP 1: Preparing inputs for CC-only method...")
    prepare_inputs_func()
    
    print("\nSTEP 2: Preparing inputs for catalog-only method...")
    prepare_catalog_func()
    
    # Step 3: Run ph2dt (needed for both)
    print("\nSTEP 3: Running ph2dt...")
    run_ph2dt_func()
    
    # Step 4: Run CC-only method
    print("\nSTEP 4: Running HypoDD with CC-only (IDAT=1)...")
    print("Using hypoDD_cc.inp configuration...")
    run_hypodd_func('hypoDD_cc.inp')
    
    # Rename output
    shutil.copy(f'{run_dir}/hypoDD.reloc', f'{run_dir}/hypoDD_cc.reloc')
    print(f"Saved results to: {run_dir}/hypoDD_cc.reloc")
    
    # Convert to CSV
    reloc_to_csv_func(
        f'{run_dir}/hypoDD_cc.reloc',
        method_suffix='_cc',
        event_id_mapping_file=f'{run_dir}/event_id_mapping.csv'
    )
    
    # Step 5: Run catalog-only method (need to re-run ph2dt with corrected .pha)
    print("\nSTEP 5: Re-running ph2dt with lag-corrected catalog...")
    # First, backup original .pha and use corrected one
    shutil.copy(f'{run_dir}/detections.pha', f'{run_dir}/detections_original.pha')
    shutil.copy(f'{run_dir}/detections_cat.pha', f'{run_dir}/detections.pha')
    run_ph2dt_func()
    
    print("\nSTEP 6: Running HypoDD with catalog-only (IDAT=2)...")
    print("Using hypoDD_cat.inp configuration...")
    run_hypodd_func('hypoDD_cat.inp')
    
    # Rename output
    shutil.copy(f'{run_dir}/hypoDD.reloc', f'{run_dir}/hypoDD_cat.reloc')
    print(f"Saved results to: {run_dir}/hypoDD_cat.reloc")
    
    # Convert to CSV
    reloc_to_csv_func(
        f'{run_dir}/hypoDD_cat.reloc',
        method_suffix='_cat',
        event_id_mapping_file=f'{run_dir}/event_id_mapping.csv'
    )
    
    # Restore original .pha
    shutil.copy(f'{run_dir}/detections_original.pha', f'{run_dir}/detections.pha')
    
    # Step 7: Compare results
    print("\nSTEP 7: Comparing results...")
    compare_relocations(
        f'{run_dir}/hypoDD_cc.reloc',
        f'{run_dir}/hypoDD_cat.reloc',
        label1='CC-only (IDAT=1)',
        label2='Catalog-only (IDAT=2)'
    )
    
    print("\n✅ Comparison test complete!")
    print(f"Output files saved in: {run_dir}/")
