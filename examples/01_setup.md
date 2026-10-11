# 1. Setup

## Install

Log in to the cluster and clone the repo into your home folder:

```
cd ~
git clone https://github.com/Gaurav-Arora-MatSci/vasp_triage.git
echo 'export PATH=$HOME/vasp_triage:$PATH' >> ~/.bashrc
source ~/.bashrc
which vtriage
```

which vtriage should print /global/homes/u/user/vasp_triage/vtriage
or your own home path. Nothing else is needed: no pip, no conda, no
network. Python 3.5 or newer, and SLURM.

## Per machine settings

Settings that differ between clusters go in local_settings.py in the
repo folder. git ignores this file, so a git pull never overwrites
it. Copy the template:

```
cp ~/vasp_triage/examples/templates/local_settings_example.py ~/vasp_triage/local_settings.py
nano ~/vasp_triage/local_settings.py
```

The most used values:

| Setting | Meaning | Example |
|---|---|---|
| MAX_SUBMIT | largest number of jobs per submit command | 20 |
| QUEUE_LIMIT | largest number of your jobs in the queue for submit | 15 |
| AUTO_BATCH | new jobs per auto agent cycle | 20 |
| AUTO_QUEUE_LIMIT | largest number of your jobs in the queue for the auto agent | 30 |
| AUTO_EMAIL | address for the completion email, empty means none | you@example.com |
| AUTO_EMAIL_SBATCH_OPTIONS | sbatch options for the one minute email job | see template |
| ACTIVITY_LOG_DIR | folder of the shared activity log, empty means off | ~/vasp_triage_logs |
| MACHINE_NAME | machine name used in the activity log | perlmutter |

## What every calculation folder needs

1. A file named INCAR. Any folder with an INCAR is a calculation.
2. KPOINTS, POSCAR, POTCAR.
3. A job script named submit_vasp.sh that runs VASP in its own
   folder, with no hard coded path to somewhere else.
4. SLURM output named slurm-JOBID.out, with no separate error file:

```
#SBATCH --output=slurm-%j.out
```

One calculation per folder. To keep a folder out of the scan,
rename its INCAR, for example to INCAR.bak.

## Short names for long paths (optional)

Make working_dirs_list.txt in the repo folder:

```
bcc = /pscratch/sd/u/user/campaigns/BCC
test = /scratch/user/vt_test
```

Then vtriage status test works from anywhere, and the menu accepts
test when you change the root folder.

## First check on a new tree

```
cd /scratch/user/vt_test
vtriage status
find . -name INCAR | wc -l
```

The folder count from vtriage status and the INCAR count must
agree. Output on the fresh test tree:

```
$ vtriage status
Jobs from this folder: 0

All my jobs in the queue: 2
  running: 2
  free slots under limit 15: 13

Folders under /scratch/user/vt_test: 10
  not submitted: 10

$ find . -name INCAR | wc -l
10
```

All my jobs in the queue counts every job you have, from any
folder. Jobs from this folder counts only jobs started under the
current folder.

## Updating

```
cd ~/vasp_triage
git pull
```

local_settings.py and working_dirs_list.txt stay as they are.
