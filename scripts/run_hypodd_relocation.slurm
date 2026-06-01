#!/bin/bash

#SBATCH -J daughter_dd_cc
#SBATCH -A r00706
#SBATCH -p general 
#SBATCH -o /N/u/mdaislam/Quartz/Arif-projects/softwares/hypodd_pywrapper/scripts/logs/hypodd_run.%j.out
#SBATCH -e /N/u/mdaislam/Quartz/Arif-projects/softwares/hypodd_pywrapper/scripts/logs/hypodd_run.%j.err
#SBATCH --mail-type=NONE
#SBATCH --mail-user=mdaislam@iu.edu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1          
#SBATCH --cpus-per-task=48
#SBATCH --time=05:00:00
#SBATCH --mem=128G

# Load modules (if needed)
# module purge
# module load conda

echo "=========================================="
echo "Starting Event Detection Pipeline"
echo "Job ID: $SLURM_JOB_ID"
echo "Start time: $(date)"
echo "=========================================="

# Change to the working directory
cd /N/u/mdaislam/Quartz/Arif-projects/softwares/hypodd_pywrapper/scripts || exit 1
echo "Current pwd: $(pwd)"

source /N/u/mdaislam/Quartz/conda/bin/activate /N/slate/mdaislam/_conda/envs/eqcorrscan
echo "Current environment: $(which python)"


# Run relocation steps so that next one runs only if the previous one succeeded.
# srun python run_hypodd.py compile && \
# srun python run_hypodd.py prepare && \
srun python run_hypodd.py ph2dt && \
srun python run_hypodd.py hypodd
