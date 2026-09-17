# scan.py
# Find every calculation directory under a root directory.
# A calculation directory is any directory that contains an INCAR.

import os
import sys

import config


# Walk through root and all its subdirectories.
# Return a sorted list of paths to directories that contain an INCAR.
def find_calc_dirs(root):
    root = os.path.abspath(root)
    calc_dirs = []

    # os.walk visits every directory below root, one at a time.
    # dir_path   : path of the current directory
    # sub_dirs   : names of directories inside it (not used here)
    # file_names : names of files inside it
    for dir_path, sub_dirs, file_names in os.walk(root):
        if config.INCAR_NAME in file_names:
            calc_dirs.append(dir_path)

    calc_dirs.sort()
    return calc_dirs

# Return a list of required input files missing from a directory.
# An empty list means all required files are present.
def find_missing_inputs(calc_dir):
    missing = []

    for name in config.REQUIRED_INPUT_FILES:
        file_path = os.path.join(calc_dir, name)
        if not os.path.isfile(file_path):
            missing.append(name)

    return missing




# Run this file directly to test the scan.
# Example: python3 scan.py /path/to/calculations
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 scan.py /path/to/calculations")
        sys.exit(1)

    root = sys.argv[1]

    if not os.path.isdir(root):
        print("Error: not a directory: " + root)
        sys.exit(1)

    dirs = find_calc_dirs(root)

    print("Calculation directories found: " + str(len(dirs)))
    print("First 10:")
    for path in dirs[:10]:
        print("  " + path)
