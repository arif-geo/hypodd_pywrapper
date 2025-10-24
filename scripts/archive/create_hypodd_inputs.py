"""
Generate HypoDD input files (.inp) programmatically
"""

import os


def create_ph2dt_inp(
    output_file,
    station_file,
    phase_file,
    minwght=0.0,
    maxdist=200.0,
    maxsep=10.0,
    maxngh=10,
    minlnk=8,
    minobs=8,
    maxobs=20
):
    """
    Create ph2dt.inp file for ph2dt program.
    
    Parameters:
    -----------
    output_file : str
        Path to output .inp file
    station_file : str
        Path to station file (can be relative or absolute)
    phase_file : str
        Path to phase file (can be relative or absolute)
    minwght : float
        Minimum pick weight allowed [default: 0]
    maxdist : float
        Maximum distance in km between event pair and stations [default: 200]
    maxsep : float
        Maximum hypocentral separation in km [default: 10]
    maxngh : int
        Maximum number of neighbors per event [default: 10]
    minlnk : int
        Minimum number of links required to define a neighbor [default: 8]
    minobs : int
        Minimum number of links per pair saved [default: 8]
    maxobs : int
        Maximum number of links per pair saved [default: 20]
    
    Returns:
    --------
    str : Path to created file
    """
    
    content = f"""* ph2dt.inp - input control file for program ph2dt
* Input station file:
{station_file}
* Input phase file:
{phase_file}
*MINWGHT: min. pick weight allowed [0]
*MAXDIST: max. distance in km between event pair and stations [200]
*MAXSEP: max. hypocentral separation in km [10]
*MAXNGH: max. number of neighbors per event [10]
*MINLNK: min. number of links required to define a neighbor [8]
*MINOBS: min. number of links per pair saved [8]
*MAXOBS: max. number of links per pair saved [20]
*MINWGHT MAXDIST MAXSEP MAXNGH MINLNK MINOBS MAXOBS
{minwght:8.0f} {maxdist:8.1f} {maxsep:8.1f} {maxngh:5d} {minlnk:6d} {minobs:6d} {maxobs:6d}
"""
    
    # Create directory if needed
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"Created ph2dt.inp: {output_file}")
    print(f"  Station file: {station_file}")
    print(f"  Phase file: {phase_file}")
    print(f"  Parameters: MAXDIST={maxdist} km, MAXSEP={maxsep} km, MINLNK={minlnk}")
    
    return output_file


def create_hypodd_inp(
    output_file,
    data_files,
    output_dir='.',
    # Clustering parameters
    obscc=0, obsct=0,
    # Weighting parameters
    wtccp=1.0, wtccs=0.5, wtctp=1.0, wtcts=0.5,
    # Distance weighting
    wdcc=8.0, wdct=8.0,
    # Data selection
    maxdist=500.0,
    maxsep=10.0,
    # Iteration parameters
    istart=1, isolv=2,
    niter=5,
    # Damping
    damp=100.0,
    # Model
    mod_nl=1,
    mod_ratio=1.73,
    mod_v=6.0,
    mod_top=0.0,
    # Location constraints
    lat_center=None, lon_center=None,
    # Event fixing
    iphase=3,  # 1=P, 2=S, 3=P&S
    # Output controls
    iplot=1, idata=3
):
    """
    Create hypoDD.inp file for hypoDD program.
    
    Parameters:
    -----------
    output_file : str
        Path to output .inp file
    data_files : dict
        Dictionary with keys: 'dt_cc', 'dt_ct', 'event', 'station'
        Example: {'dt_ct': 'dt.ct', 'event': 'event.dat', 'station': 'station.dat'}
    output_dir : str
        Directory for output files [default: '.']
    obscc : int
        Use cross-correlation data (0=no, 1=yes) [default: 0]
    obsct : int
        Use catalog data (0=no, 1=yes) [default: 0]
    wtccp : float
        Weight for CC P-wave data [default: 1.0]
    wtccs : float
        Weight for CC S-wave data [default: 0.5]
    wtctp : float
        Weight for catalog P-wave data [default: 1.0]
    wtcts : float
        Weight for catalog S-wave data [default: 0.5]
    wdcc : float
        Distance weighting exponent for CC data [default: 8.0]
    wdct : float
        Distance weighting exponent for catalog data [default: 8.0]
    maxdist : float
        Maximum distance in km for station pairs [default: 500]
    maxsep : float
        Maximum event separation in km [default: 10]
    istart : int
        Initial locations (1=from catalog, 2=from cluster centroid) [default: 1]
    isolv : int
        Solution method (1=SVD, 2=LSQR) [default: 2]
    niter : int
        Number of iterations [default: 5]
    damp : float
        Damping parameter [default: 100]
    mod_nl : int
        Number of model layers [default: 1]
    mod_ratio : float or list
        Vp/Vs ratio(s) [default: 1.73]
    mod_v : float or list
        P-wave velocity(ies) in km/s [default: 6.0]
    mod_top : float or list
        Top depth(s) of layer(s) in km [default: 0.0]
    lat_center : float
        Center latitude for cluster search [default: None]
    lon_center : float
        Center longitude for cluster search [default: None]
    iphase : int
        Phase types to use (1=P, 2=S, 3=P&S) [default: 3]
    iplot : int
        Plot output (0=no, 1=yes) [default: 1]
    idata : int
        Data type (1=CC only, 2=CT only, 3=both) [default: 3]
    
    Returns:
    --------
    str : Path to created file
    """
    
    # Handle list inputs for velocity model
    if not isinstance(mod_ratio, list):
        mod_ratio = [mod_ratio]
    if not isinstance(mod_v, list):
        mod_v = [mod_v]
    if not isinstance(mod_top, list):
        mod_top = [mod_top]
    
    # Ensure all model arrays have same length
    mod_nl = len(mod_v)
    
    # Build velocity model section
    velocity_model = f"{mod_nl}\n"
    for i in range(mod_nl):
        velocity_model += f"{mod_v[i]:.2f} {mod_ratio[i]:.2f}\n"
    
    # Get data filenames
    dt_cc = data_files.get('dt_cc', 'dt.cc')
    dt_ct = data_files.get('dt_ct', 'dt.ct')
    event_file = data_files.get('event', 'event.dat')
    station_file = data_files.get('station', 'station.dat')
    
    # Build input file
    content = f"""* hypoDD.inp - input control file for hypoDD
* Input file names
* cross correlation diff times:
{dt_cc if obscc else ''}
* catalog travel time diff times:
{dt_ct if obsct else ''}
* event file:
{event_file}
* station file:
{station_file}
*
* Output file names
* original locations:
{output_dir}/hypoDD.loc
* relocations:
{output_dir}/hypoDD.reloc
* station information:
{output_dir}/hypoDD.sta
* residuals:
{output_dir}/hypoDD.res
* source parameters:
{output_dir}/hypoDD.src
*
* Data type and phase
* IDAT IPHASE MINOBS (0=CC, 1=CT, 2=CC&CT; 1=P, 2=S, 3=P&S)
{idata} {iphase} 1
*
* Distance and clustering parameters
* MAXDIST MAXSEP MINOBS MAXNGH
{maxdist:.1f} {maxsep:.1f} 8 10
*
* Iteration control
* ISTART ISOLV
{istart} {isolv}
*
* Weighting
* WTCCP WTCCS WTCTP WTCTS WDCC WDCT WRCC WRCT
{wtccp:.2f} {wtccs:.2f} {wtctp:.2f} {wtcts:.2f} {wdcc:.1f} {wdct:.1f} -9 -9
*
* Iteration parameters
* NITER DAMP
{niter} {damp:.1f}
*
* 1D Velocity model
* # of layers, Vp, Vp/Vs
{velocity_model.rstrip()}
"""
    
    # Create directory if needed
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"Created hypoDD.inp: {output_file}")
    print(f"  Data type: {'CC' if obscc else ''}{'&' if obscc and obsct else ''}{'CT' if obsct else ''}")
    print(f"  Phase: {'P' if iphase==1 else 'S' if iphase==2 else 'P&S'}")
    print(f"  Iterations: {niter}, Damping: {damp}")
    print(f"  Velocity model: {mod_nl} layer(s)")
    
    return output_file


# Quick preset configurations

def create_ph2dt_inp_default(output_file, station_file, phase_file):
    """Create ph2dt.inp with conservative default parameters."""
    return create_ph2dt_inp(
        output_file, station_file, phase_file,
        maxdist=200, maxsep=10, minlnk=8
    )


def create_ph2dt_inp_loose(output_file, station_file, phase_file):
    """Create ph2dt.inp with loose parameters for sparse data."""
    return create_ph2dt_inp(
        output_file, station_file, phase_file,
        maxdist=500, maxsep=15, minlnk=4, minobs=4
    )


def create_hypodd_inp_catalog_only(output_file, data_files, output_dir='.'):
    """Create hypoDD.inp using only catalog data (no cross-correlation)."""
    return create_hypodd_inp(
        output_file, data_files, output_dir,
        obscc=0, obsct=1, idata=1
    )


def create_hypodd_inp_cc_only(output_file, data_files, output_dir='.'):
    """Create hypoDD.inp using only cross-correlation data."""
    return create_hypodd_inp(
        output_file, data_files, output_dir,
        obscc=1, obsct=0, idata=0
    )


def create_hypodd_inp_both(output_file, data_files, output_dir='.'):
    """Create hypoDD.inp using both catalog and cross-correlation data."""
    return create_hypodd_inp(
        output_file, data_files, output_dir,
        obscc=1, obsct=1, idata=3
    )
