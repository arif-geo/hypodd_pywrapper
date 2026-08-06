import os
import subprocess
import sys
from hypodd_pywrapper.legacy.csv_hypodd import csv_to_pha, csv_to_cc, daughter_csv_to_cc, create_event_id_mapping, create_station_file, load_catalog, reloc_to_csv

# Paths
script_dir  = os.path.dirname(os.path.abspath(__file__))
HYPODD_ROOT = os.path.abspath(f'{script_dir}/../HypoDD-2.1b')
RUN_DIR     = os.path.abspath(f'{script_dir}/../runs/ferndale_10yr') # ******* POINTING TO NEW RUN DIR *****
EXAMPLE_DIR = os.path.abspath(f'{script_dir}/../HypoDD-2.1b/examples/example2')
os.makedirs(RUN_DIR, exist_ok=True)

# CSV inputs
FMF_RESULTS = os.path.abspath(f'{script_dir}/../../../Match-Filter-Event-Detection/event_detection/results')
FMF_DATA    = os.path.abspath(f'{script_dir}/../../../Match-Filter-Event-Detection/event_detection/data')

CSV_FILE    = f'{FMF_RESULTS}/stage_f_master_catalog/master_phase_picks_2013_2022_10yr.csv' # Main phase picks (10-year)
DAUGHTER_CC = f'{FMF_RESULTS}/stage_g_global_cc/global_pairs_cc_2013_2022_10yr.csv' # Global all-to-all CCs (10-year)
STATION_CSV = f'{FMF_DATA}/stations_2000_onshore_permanent_50km_cleaned_2022.csv'
CATALOG_CSV = f'{FMF_DATA}/Yoon_Shelly_2024_catalog/yoon_shelley_20221219_reloc_buffered_25km.csv' # Template catalog (also used for event metadata like origin time, depth, etc. in pha file)


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
    
    # We need to compute mapping over both datasets if new IDs could exist in daughter_pairs. 
    # Usually CSV_FILE has all template and detected events.
    event_mapping = create_event_id_mapping(CSV_FILE, mapping_file)
    
    # Convert phase catalog (also outputs parent-to-daughter pair CCs inside later step if needed)
    csv_to_pha(CSV_FILE, pha_file, catalog_info, event_mapping)
    
    # Write template-to-daughter pairs
    csv_to_cc(CSV_FILE, cc_file, min_cc=0.6, event_id_mapping=event_mapping)
    
    # Append daughter-to-daughter pairs if file exists
    if os.path.exists(DAUGHTER_CC):
        daughter_csv_to_cc(DAUGHTER_CC, cc_file, event_mapping, min_cc=0.6, append=True)
    
    print(f"Files ready in {RUN_DIR}/")


def run_ph2dt():
    """Run ph2dt to create differential times."""
    print("\nRunning ph2dt...")
    cmd = [f'{HYPODD_ROOT}/src/ph2dt/ph2dt', 'ph2dt.inp']
    result = subprocess.run(cmd, cwd=RUN_DIR, capture_output=True, text=True)
    
    # Print output
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)
        print(f"hypoDD failed with code {result.returncode}")
        return
    
    print("✅ ph2dt complete. Check dt.ct and event.dat")


def run_hypodd(inp_file):
    """Run hypoDD relocation.
    
    Note: hypoDD cannot handle absolute paths for input file.
    We must pass only the filename and run from the directory containing the file.
    """
    # Extract just the filename (no path)
    inp_filename = os.path.basename(inp_file)
    if not os.path.exists(f'{RUN_DIR}/{inp_filename}'):
        print(f"ERROR: {RUN_DIR}/{inp_filename} not found.")
        return
    
    print(f"\nRunning hypoDD with {inp_filename} in {RUN_DIR}...")
    cmd = [f'{HYPODD_ROOT}/src/hypoDD/hypoDD', inp_filename]
    result = subprocess.run(cmd, cwd=RUN_DIR, capture_output=True, text=True, errors='replace')
    
    # Print output
    print(result.stdout)
    
    # Check for errors
    if result.returncode != 0:
        print("STDERR:", result.stderr)
        print(f"hypoDD failed with code {result.returncode}")
        return
    
    print(f"✅ hypoDD complete. Check output in {RUN_DIR}/")
    
    # Moving accesory output (hypodd.reloc.001.001-hypodd.reloc.xxx.xxx) to an archive folder
    archive_dir = f'{RUN_DIR}/hypodd_output_archive'
    os.makedirs(archive_dir, exist_ok=True)
    cmd = f'mv {RUN_DIR}/hypoDD.reloc.* {archive_dir}/'
    subprocess.run(cmd, shell=True, check=True)
    print(f"Moved hypoDD output files to {archive_dir}/")


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
    
    if os.path.exists(DAUGHTER_CC):
        daughter_csv_to_cc(DAUGHTER_CC, cc_file, event_mapping, min_cc=0.6, append=True)
    
    print(f"Lag-corrected files ready in {RUN_DIR}/")
    print(f"  - {pha_file} (travel times adjusted by lag for detected events)")


if __name__ == '__main__':
    hypoinp_file = 'hypoDD.inp'
    hypoout_file = f'{RUN_DIR}/hypoDD.reloc'
    try:
        if sys.argv[1] == 'example':
            run_example()
        elif sys.argv[1] == 'compile':
            compile_hypodd()
        elif sys.argv[1] == 'prepare':
            prepare_inputs()
        elif sys.argv[1] == 'prepare_catalog':
            prepare_inputs_catalog_only()
        elif sys.argv[1] == 'ph2dt':
            run_ph2dt()
        elif sys.argv[1] == 'hypodd':
            try:
                run_hypodd(hypoinp_file)
            except Exception as e:
                print(f"ERROR: {e}\nCheck that {hypoinp_file} exists in:\n{RUN_DIR}\n")
        elif sys.argv[1] == 'convert':
            if sys.argv[2]:
                outfile_suffix = f'_{sys.argv[2]}'
            else:
                outfile_suffix = ''
            try:
                reloc_to_csv(hypoout_file, outfile_suffix=outfile_suffix, event_id_mapping_file=f'{RUN_DIR}/event_id_mapping.csv')
            except Exception as e:
                print(f"ERROR: {e}\nCheck that {hypoout_file} exists in:\n{RUN_DIR}\n")
        else:
            print("Usage: python run_hypodd.py <command> [args]")
            print("\nCommands:")
            print("  compile             - Compile HypoDD Fortran codes")
            print("  example             - Run HypoDD example2 test")
            print("  prepare             - Convert CSV to HypoDD input files (for catalog+CC method)")
            print("  prepare_catalog     - Convert CSV with lag corrections (for catalog-only method)")
            print("  ph2dt               - Run ph2dt to create differential times")
            print("  hypodd              - Run hypoDD relocation (default: hypoDD.inp, edit file name in python script)")
            print("  convert             - Convert .reloc to CSV (default: hypoDD.reloc, edit file name in python script)")
            print("  compare             - Run both CC and catalog methods and compare")
            
    except Exception as e:
        print(f"ERROR: {e}\n\n")