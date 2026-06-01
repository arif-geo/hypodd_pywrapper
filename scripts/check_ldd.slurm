#!/bin/bash
#SBATCH -J check_ldd
#SBATCH -A r00706
#SBATCH -p debug 
#SBATCH -o /N/u/mdaislam/Quartz/Arif-projects/softwares/hypodd_pywrapper/scripts/logs/ldd_check.%j.out
#SBATCH -e /N/u/mdaislam/Quartz/Arif-projects/softwares/hypodd_pywrapper/scripts/logs/ldd_check.%j.err
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1          
#SBATCH --time=00:05:00

srun ldd /N/u/mdaislam/Quartz/Arif-projects/softwares/hypodd_pywrapper/HypoDD-2.1b/src/hypoDD/hypoDD
