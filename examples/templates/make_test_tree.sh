#!/bin/bash
# Build the 10 folder test tree used in the vasp_triage examples.
#
# Usage:
#   bash make_test_tree.sh SOURCE_FOLDER TARGET_FOLDER
#
# SOURCE_FOLDER holds one small working calculation:
#   INCAR, KPOINTS, POSCAR, POTCAR, submit_vasp.sh
# TARGET_FOLDER is created, for example $PSCRATCH/vt_test
#
# Layout made:
#   C11/1 to C11/6, C12/1, C12/2, C44/x, C44/y
#
# Afterwards, see examples/04_edit_inputs.md to make the C12 folders
# run one ionic step, and examples/05_auto_agent_scrontab.md to run
# the test.

if [ $# -ne 2 ]; then
    echo "Usage: bash make_test_tree.sh SOURCE_FOLDER TARGET_FOLDER"
    exit 1
fi

source_dir=$1
target_dir=$2

# Check the source folder has every input file
for name in INCAR KPOINTS POSCAR POTCAR submit_vasp.sh; do
    if [ ! -f "$source_dir/$name" ]; then
        echo "Missing $name in $source_dir"
        exit 1
    fi
done

if [ -e "$target_dir" ]; then
    echo "$target_dir already exists. Remove it or choose another name."
    exit 1
fi

for folder in C11/1 C11/2 C11/3 C11/4 C11/5 C11/6 C12/1 C12/2 C44/x C44/y; do
    mkdir -p "$target_dir/$folder"
    for name in INCAR KPOINTS POSCAR POTCAR submit_vasp.sh; do
        cp "$source_dir/$name" "$target_dir/$folder/"
    done
done

echo "Test tree made in $target_dir"
echo "Folders with INCAR: $(find "$target_dir" -name INCAR | wc -l)"
echo "Next: cd $target_dir && vtriage status"
