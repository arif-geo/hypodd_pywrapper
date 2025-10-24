"""
Example usage of create_hypodd_inputs module
"""

from create_hypodd_inputs import (
    create_ph2dt_inp,
    create_hypodd_inp,
    create_hypodd_inp_both
)

# Create ph2dt.inp with default parameters
print("="*60)
print("Create ph2dt.inp with default parameters")
print("="*60)

create_ph2dt_inp(
    output_file='../data/hypoDD_inputs/ph2dt_test.inp',
    station_file='station.dat',  # Will look in same directory as ph2dt.inp
    phase_file='detections.pha',
    minwght=0.0,
    maxdist=500.0,
    maxsep=15.0,
    maxngh=15,
    minlnk=8,
    minobs=8,
    maxobs=50
)

# Create hypoDD.inp using both catalog and cross-correlation data
print("\n"+"="*60)
print("Create hypoDD.inp using both catalog and cross-correlation data")
print("="*60)

