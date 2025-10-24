import os
import subprocess
import shutil
import numpy as np
import pandas as pd
from csv_to_hypodd import csv_to_pha, csv_to_cc, create_event_id_mapping, create_station_file, load_catalog

# Paths
script_dir = os.path.dirname(os.path.abspath(__file__))
HYPODD_ROOT = os.path.abspath(f'{script_dir}/../HypoDD-2.1b')
RUN_DIR = os.path.abspath(f'{script_dir}/../data/runs/run_detections_2020')
EXAMPLE_DIR = os.path.abspath(f'{script_dir}/../HypoDD-2.1b/examples/example2')

# CSV inputs
CSV_FILE = f'{script_dir}/../data/input_csvs/nc73818801_fmf_detections_phase_picks.csv'
STATION_CSV = f'{script_dir}/../data/input_csvs/stations_2000_onshore_permanent_50km_cleaned_2022.csv'
CATALOG_CSV = f'{script_dir}/../data/input_csvs/yoon_shelly_ferndale-2022-12-01.csv'


def compile_hypodd():
    """Compile HypoDD Fortran codes."""
    print("Compiling HypoDD...")
    src_dir = f'{HYPODD_ROOT}/src'
    subprocess.run(['make', 'clean'], cwd=src_dir, check=True)
    subprocess.run(['make'], cwd=src_dir, check=True)
    print("Compilation complete.")


def run_example():
    """Run HypoDD example2 to test if everything works."""
    print("Running HypoDD example2...")
    
    ph2dt = f'{HYPODD_ROOT}/src/ph2dt/ph2dt'
    hypodd = f'{HYPODD_ROOT}/src/hypoDD/hypoDD'
    
    if not os.path.exists(ph2dt):
        print(f"ERROR: {ph2dt} not found. Run: python run_hypodd.py compile")
        return
    
    print("\n1. Running ph2dt...")
    result = subprocess.run([ph2dt, 'ph2dt.inp'], cwd=EXAMPLE_DIR, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)
        print(f"ph2dt failed with code {result.returncode}")
        return
    
    print("\n2. Running hypoDD...")
    result = subprocess.run([hypodd, 'hypoDD.inp'], cwd=EXAMPLE_DIR, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)
        print(f"hypoDD failed with code {result.returncode}")
        return
    
    print("\nExample complete. Check example2 outputs.")


def prepare_inputs():
    """Convert CSV to HypoDD formats in run directory."""
    print("Converting CSV to HypoDD formats...")
    
    pha_file = f'{RUN_DIR}/detections.pha'
    cc_file = f'{RUN_DIR}/detections.cc'
    sta_file = f'{RUN_DIR}/station.dat'
    mapping_file = f'{RUN_DIR}/event_id_mapping.csv'
    
    create_station_file(STATION_CSV, sta_file)
    catalog_info = load_catalog(CATALOG_CSV)
    event_mapping = create_event_id_mapping(CSV_FILE, mapping_file)
    csv_to_pha(CSV_FILE, pha_file, catalog_info, event_mapping)
    csv_to_cc(CSV_FILE, cc_file, min_cc=0.6, event_id_mapping=event_mapping)
    
    print(f"Files ready in {RUN_DIR}/")


def run_ph2dt():
    """Run ph2dt to create differential times."""
    print("\nRunning ph2dt...")
    cmd = [f'{HYPODD_ROOT}/src/ph2dt/ph2dt', 'ph2dt.inp']
    subprocess.run(cmd, cwd=RUN_DIR, check=True)
    print("ph2dt complete. Check dt.ct")


def run_hypodd(inp_file='hypoDD.inp'):
    """Run hypoDD relocation."""
    print(f"\nRunning hypoDD with {inp_file}...")
    cmd = [f'{HYPODD_ROOT}/src/hypoDD/hypoDD', inp_file]
    subprocess.run(cmd, cwd=RUN_DIR, check=True)
    print(f"hypoDD complete. Check output in {RUN_DIR}/")


def reloc_to_csv(reloc_file, output_dir=None, method_suffix='', event_id_mapping_file=None):
    """
    Convert HypoDD relocation output (.reloc) to CSV format.
    
    Parameters:
    -----------
    reloc_file : str
        Path to the hypoDD.reloc file
    output_dir : str, optional
        Directory to save the CSV file. Default: '../data/hypoDD_outputs'
    method_suffix : str, optional
        Suffix to add to filename (e.g., '_cc', '_cat'). Default: ''
    event_id_mapping_file : str, optional
        Path to event_id_mapping.csv to convert synthetic IDs back to original IDs
    
    Returns:
    --------
    DataFrame with relocated events
    """
    # Set default output directory
    if output_dir is None:
        output_dir = os.path.abspath(f'{script_dir}/../data/hypoDD_outputs')
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nConverting {reloc_file} to CSV...")
    
    # Read the relocation file
    # Format: ID LAT LON DEPTH X Y Z EX EY EZ YR MO DY HR MI SC MAG NCCP NCCS NCTP NCTS RCC RCT CID
    data = []
    with open(reloc_file, 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 24:  # Full format
                data.append({
                    'event_id': int(parts[0]),
                    'latitude': float(parts[1]),
                    'longitude': float(parts[2]),
                    'depth': float(parts[3]),
                    'x_m': float(parts[4]),
                    'y_m': float(parts[5]),
                    'z_m': float(parts[6]),
                    'ex_m': float(parts[7]),
                    'ey_m': float(parts[8]),
                    'ez_m': float(parts[9]),
                    'year': int(parts[10]),
                    'month': int(parts[11]),
                    'day': int(parts[12]),
                    'hour': int(parts[13]),
                    'minute': int(parts[14]),
                    'second': float(parts[15]),
                    'magnitude': float(parts[16]),
                    'n_cc_p': int(parts[17]),
                    'n_cc_s': int(parts[18]),
                    'n_cat_p': int(parts[19]),
                    'n_cat_s': int(parts[20]),
                    'rms_cc': float(parts[21]),
                    'rms_cat': float(parts[22]),
                    'cluster_id': int(parts[23])
                })
    
    df = pd.DataFrame(data)
    
    if len(df) == 0:
        print("WARNING: No events found in relocation file!")
        return df
    
    # Rename the ID column from relocation file to hypodd_id
    df.rename(columns={'event_id': 'hypodd_id'}, inplace=True)
    
    # Map HypoDD IDs back to original event IDs if mapping file provided
    if event_id_mapping_file and os.path.exists(event_id_mapping_file):
        mapping_df = pd.read_csv(event_id_mapping_file)
        
        # Try both old and new column naming conventions
        if 'synthetic_id' in mapping_df.columns and 'original_id' in mapping_df.columns:
            # Old naming: synthetic_id -> original_id
            id_map = mapping_df.set_index('synthetic_id')['original_id'].to_dict()
        elif 'hypodd_id' in mapping_df.columns and 'event_id' in mapping_df.columns:
            # New naming: hypodd_id -> event_id
            id_map = mapping_df.set_index('hypodd_id')['event_id'].to_dict()
        else:
            print(f"WARNING: Unexpected columns in mapping file: {mapping_df.columns.tolist()}")
            id_map = {}
        
        # Add original event_id column
        df['event_id'] = df['hypodd_id'].map(id_map)
        
        # Reorder columns to put event_id and hypodd_id first
        cols = ['event_id', 'hypodd_id'] + [col for col in df.columns if col not in ['event_id', 'hypodd_id']]
        df = df[cols]
    else:
        # If no mapping file, just keep hypodd_id
        cols = ['hypodd_id'] + [col for col in df.columns if col != 'hypodd_id']
        df = df[cols]
    
    # Create origin_time column
    df['origin_time'] = df.apply(
        lambda row: f"{int(row['year']):04d}-{int(row['month']):02d}-{int(row['day']):02d}T"
                   f"{int(row['hour']):02d}:{int(row['minute']):02d}:{row['second']:06.3f}Z",
        axis=1
    )
    
    # Generate output filename
    base_name = os.path.basename(reloc_file).replace('.reloc', '')
    output_file = f'{output_dir}/{base_name}{method_suffix}.csv'
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    
    print(f"✅ Converted {len(df)} relocated events to CSV")
    print(f"   Output: {output_file}")
    print(f"\nSummary statistics:")
    print(f"   Latitude range:  {df['latitude'].min():.5f} to {df['latitude'].max():.5f}")
    print(f"   Longitude range: {df['longitude'].min():.5f} to {df['longitude'].max():.5f}")
    print(f"   Depth range:     {df['depth'].min():.2f} to {df['depth'].max():.2f} km")
    print(f"   Clusters:        {df['cluster_id'].nunique()}")
    
    return df


def prepare_inputs_catalog_only():
    """Convert CSV to HypoDD formats with lag-corrected travel times for catalog-only method."""
    print("Converting CSV to HypoDD formats (with lag correction for catalog-only method)...")
    
    pha_file = f'{RUN_DIR}/detections_cat.pha'
    cc_file = f'{RUN_DIR}/detections.cc'
    sta_file = f'{RUN_DIR}/station.dat'
    mapping_file = f'{RUN_DIR}/event_id_mapping.csv'
    
    # Station file and mapping are same as before
    create_station_file(STATION_CSV, sta_file)
    catalog_info = load_catalog(CATALOG_CSV)
    event_mapping = create_event_id_mapping(CSV_FILE, mapping_file)
    
    # Generate lag-corrected .pha file
    csv_to_pha(CSV_FILE, pha_file, catalog_info, event_mapping, apply_lag_correction=True)
    csv_to_cc(CSV_FILE, cc_file, min_cc=0.6, event_id_mapping=event_mapping)
    
    print(f"Lag-corrected files ready in {RUN_DIR}/")
    print(f"  - {pha_file} (travel times adjusted by lag for detected events)")


def compare_relocations(reloc_file1, reloc_file2, label1='Method 1', label2='Method 2'):
    """
    Compare two HypoDD relocation files and report differences.
    
    Returns: DataFrame with comparison statistics
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


def run_comparison_test():
    """Run both CC-only and catalog-only methods and compare results."""
    print("\n" + "="*70)
    print("RUNNING COMPARISON TEST: CC-only vs Catalog-only methods")
    print("="*70 + "\n")
    
    # Step 1: Prepare inputs for both methods
    print("STEP 1: Preparing inputs for CC-only method...")
    prepare_inputs()
    
    print("\nSTEP 2: Preparing inputs for catalog-only method...")
    prepare_inputs_catalog_only()
    
    # Step 3: Run ph2dt (needed for both)
    print("\nSTEP 3: Running ph2dt...")
    run_ph2dt()
    
    # Step 4: Run CC-only method
    print("\nSTEP 4: Running HypoDD with CC-only (IDAT=1)...")
    print("Using hypoDD_cc.inp configuration...")
    run_hypodd('hypoDD_cc.inp')
    
    # Rename output
    shutil.copy(f'{RUN_DIR}/hypoDD.reloc', f'{RUN_DIR}/hypoDD_cc.reloc')
    print(f"Saved results to: {RUN_DIR}/hypoDD_cc.reloc")
    
    # Convert to CSV
    reloc_to_csv(
        f'{RUN_DIR}/hypoDD_cc.reloc',
        method_suffix='_cc',
        event_id_mapping_file=f'{RUN_DIR}/event_id_mapping.csv'
    )
    
    # Step 5: Run catalog-only method (need to re-run ph2dt with corrected .pha)
    print("\nSTEP 5: Re-running ph2dt with lag-corrected catalog...")
    # First, backup original .pha and use corrected one
    shutil.copy(f'{RUN_DIR}/detections.pha', f'{RUN_DIR}/detections_original.pha')
    shutil.copy(f'{RUN_DIR}/detections_cat.pha', f'{RUN_DIR}/detections.pha')
    run_ph2dt()
    
    print("\nSTEP 6: Running HypoDD with catalog-only (IDAT=2)...")
    print("Using hypoDD_cat.inp configuration...")
    run_hypodd('hypoDD_cat.inp')
    
    # Rename output
    shutil.copy(f'{RUN_DIR}/hypoDD.reloc', f'{RUN_DIR}/hypoDD_cat.reloc')
    print(f"Saved results to: {RUN_DIR}/hypoDD_cat.reloc")
    
    # Convert to CSV
    reloc_to_csv(
        f'{RUN_DIR}/hypoDD_cat.reloc',
        method_suffix='_cat',
        event_id_mapping_file=f'{RUN_DIR}/event_id_mapping.csv'
    )
    
    # Restore original .pha
    shutil.copy(f'{RUN_DIR}/detections_original.pha', f'{RUN_DIR}/detections.pha')
    
    # Step 7: Compare results
    print("\nSTEP 7: Comparing results...")
    compare_relocations(
        f'{RUN_DIR}/hypoDD_cc.reloc',
        f'{RUN_DIR}/hypoDD_cat.reloc',
        label1='CC-only (IDAT=1)',
        label2='Catalog-only (IDAT=2)'
    )
    
    print("\n✅ Comparison test complete!")
    print(f"Output files saved in: {RUN_DIR}/")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        step = sys.argv[1]
        if step == 'compile':
            compile_hypodd()
        elif step == 'example':
            run_example()
        elif step == 'prepare':
            prepare_inputs()
        elif step == 'prepare_catalog':
            prepare_inputs_catalog_only()
        elif step == 'ph2dt':
            run_ph2dt()
        elif step == 'hypodd':
            run_hypodd()
        elif step == 'test_comparison' or step == 'compare':
            run_comparison_test()
        elif step == 'convert' or step == 'to_csv':
            # Convert relocation file(s) to CSV
            if len(sys.argv) > 2:
                # User provided specific file
                reloc_file = sys.argv[2]
                method_suffix = sys.argv[3] if len(sys.argv) > 3 else ''
                reloc_to_csv(
                    reloc_file, 
                    method_suffix=method_suffix,
                    event_id_mapping_file=f'{RUN_DIR}/event_id_mapping.csv'
                )
            else:
                # Convert all .reloc files in RUN_DIR
                import glob
                reloc_files = glob.glob(f'{RUN_DIR}/*.reloc')
                if len(reloc_files) == 0:
                    print(f"No .reloc files found in {RUN_DIR}")
                else:
                    for reloc_file in reloc_files:
                        # Determine suffix from filename
                        basename = os.path.basename(reloc_file)
                        if '_cc' in basename:
                            suffix = '_cc'
                        elif '_cat' in basename:
                            suffix = '_cat'
                        else:
                            suffix = ''
                        reloc_to_csv(
                            reloc_file,
                            method_suffix=suffix,
                            event_id_mapping_file=f'{RUN_DIR}/event_id_mapping.csv'
                        )
        else:
            print("Usage: python run_hypodd.py [compile|example|prepare|prepare_catalog|ph2dt|hypodd|test_comparison|convert]")
            print("\nCommands:")
            print("  compile           - Compile HypoDD Fortran codes")
            print("  example           - Run HypoDD example2 test")
            print("  prepare           - Convert CSV to HypoDD input files")
            print("  prepare_catalog   - Convert CSV with lag corrections for catalog-only method")
            print("  ph2dt             - Run ph2dt to create differential times")
            print("  hypodd            - Run hypoDD relocation")
            print("  test_comparison   - Run both CC and catalog methods and compare")
            print("  convert [file]    - Convert .reloc file(s) to CSV")
            print("                      If file not specified, converts all .reloc files in run directory")
    else:
        # Run all
        prepare_inputs()
        run_ph2dt()
        run_hypodd('hypoDD_cc.inp')
        reloc_to_csv(f'{RUN_DIR}/hypoDD_cat.reloc', event_id_mapping_file=f'{RUN_DIR}/event_id_mapping.csv')