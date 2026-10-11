#!/bin/bash
# Short job script for testing vasp_triage on NERSC Perlmutter CPU nodes.
# Small cell, 8 MPI ranks, debug queue. Replace YOUR_ACCOUNT.
# For production runs, use your normal script. vasp_triage only needs
# the file name submit_vasp.sh and the output name slurm-JOBID.out.
#SBATCH -N 1
#SBATCH -C cpu
#SBATCH -q debug
#SBATCH -t 00:10:00
#SBATCH --output=slurm-%j.out
#SBATCH --job-name=test
#SBATCH --account=YOUR_ACCOUNT

# --- Write job info immediately ---
echo "Job ID      : $SLURM_JOB_ID"     >  JOBID
echo "Job Name    : $SLURM_JOB_NAME"   >> JOBID
echo "Submit Dir  : $SLURM_SUBMIT_DIR" >> JOBID
echo "Start Time  : $(date)"           >> JOBID

log_file="job.log_${SLURM_JOB_ID}"
start=$(date +%s.%N)

module load vasp/6.4.3-cpu
export OMP_NUM_THREADS=1

srun -n 8 -c 2 --cpu_bind=cores stdbuf --output=L vasp_std > "$log_file"

echo "Done."

duration=$(echo "$(date +%s.%N) - $start" | bc)
echo "End Time    : $(date)"           >> JOBID
echo "Duration    : $duration s"       >> JOBID
