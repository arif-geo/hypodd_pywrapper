import os
import subprocess
import sys
from csv_hypodd import csv_to_pha, csv_to_cc, create_event_id_mapping, create_station_file, load_catalog, reloc_to_csv
from compare_utils import compare_relocations, run_comparison_test

# Paths
script_dir  = os.path.dirname(os.path.abspath(__file__))
HYPODD_ROOT = os.path.abspath(f'{script_dir}/../HypoDD-2.1b')
# RUN_DIR     = '/N/u/mdaislam/Quartz/Arif-projects/softwares/hypodd_pywrapper/HypoDD-2.1b/examples/run_detections_test' 
RUN_DIR     = os.path.abspath(f'{script_dir}/../data/runs/run_detections_2020')
EXAMPLE_DIR = os.path.abspath(f'{script_dir}/../HypoDD-2.1b/examples/example2')

# CSV inputs
input_dir   = f'{RUN_DIR}/../input_csvs'
CSV_FILE    = f'{input_dir}/nc73818801_fmf_detections_phase_picks.csv'
STATION_CSV = f'{input_dir}/stations_2000_onshore_permanent_50km_cleaned_2022.csv'
CATALOG_CSV = f'{input_dir}/yoon_shelly_ferndale-2022-12-01.csv'


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
    result = subprocess.run(cmd, cwd=RUN_DIR, capture_output=True, text=True)
    
    # Print output
    print(result.stdout)
    
    # Check for errors
    if result.returncode != 0:
        print("STDERR:", result.stderr)
        print(f"hypoDD failed with code {result.returncode}")
        return
    
    print(f"✅ hypoDD complete. Check output in {RUN_DIR}/")


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


if __name__ == '__main__':
    COMMANDS = {
        'compile': compile_hypodd,
        'example': run_example,
        'prepare': prepare_inputs,
        'prepare_catalog': prepare_inputs_catalog_only,
        'ph2dt': run_ph2dt,
    }
    
    if len(sys.argv) < 2:
        # Default: run full workflow
        prepare_inputs()
        run_ph2dt()
        run_hypodd('hypoDD.inp')
        reloc_to_csv(f'{RUN_DIR}/hypoDD.reloc', event_id_mapping_file=f'{RUN_DIR}/event_id_mapping.csv')
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    # Simple commands (no arguments)
    if cmd in COMMANDS:
        COMMANDS[cmd]()
    
    # hypodd command (requires .inp file)
    elif cmd == 'hypodd':
        inp_file = sys.argv[2] if len(sys.argv) > 2 else 'hypoDD.inp'
        run_hypodd(inp_file)
    
    # convert command (optional .reloc file)
    elif cmd == 'convert':
        if len(sys.argv) > 2:
            reloc_file = sys.argv[2]
            method_suffix = sys.argv[3] if len(sys.argv) > 3 else ''
            reloc_to_csv(reloc_file, method_suffix=method_suffix, 
                        event_id_mapping_file=f'{RUN_DIR}/event_id_mapping.csv')
        else:
            print("Usage: python run_hypodd.py convert <reloc_file> [suffix]")
            sys.exit(1)
    
    # compare/test_comparison command
    elif cmd in ['compare', 'test_comparison']:
        run_comparison_test(RUN_DIR, HYPODD_ROOT, prepare_inputs, prepare_inputs_catalog_only,
                          run_ph2dt, run_hypodd, reloc_to_csv)
    
    # Unknown command - show help
    else:
        print("Usage: python run_hypodd.py <command> [args]")
        print("\nCommands:")
        print("  compile             - Compile HypoDD Fortran codes")
        print("  example             - Run HypoDD example2 test")
        print("  prepare             - Convert CSV to HypoDD input files")
        print("  prepare_catalog     - Convert CSV with lag corrections")
        print("  ph2dt               - Run ph2dt to create differential times")
        print("  hypodd [inp_file]   - Run hypoDD relocation (default: hypoDD.inp)")
        print("  convert <file> [sfx]- Convert .reloc to CSV")
        print("  compare             - Run both CC and catalog methods and compare")
        print("\nDefault (no command): prepare → ph2dt → hypodd → convert")
        sys.exit(1)