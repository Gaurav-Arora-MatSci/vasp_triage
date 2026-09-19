# scan.py
# Find every calculation directory under a root directory.
# A calculation directory is any directory that contains an INCAR.

import os
import sys

import config

# Name of the file that holds short names for long folder paths.
# It sits in the same folder as the scripts.
ALIAS_FILE = "working_dirs_list.txt"


# Read working_dirs_list.txt and return a dictionary of names to paths.
# Return an empty dictionary if the file does not exist.
def read_aliases():
    code_dir = os.path.dirname(os.path.abspath(__file__))
    alias_path = os.path.join(code_dir, ALIAS_FILE)

    aliases = {}
    if not os.path.isfile(alias_path):
        return aliases

    with open(alias_path, "r", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            if "=" not in line:
                continue

            name, path = line.split("=", 1)
            aliases[name.strip()] = path.strip()

    return aliases


# Turn a short name into its full path.
# A path that is not a known name is returned unchanged.
def resolve_path(text):
    aliases = read_aliases()
    if text in aliases:
        return aliases[text]
    return text


# Walk through root and all its subdirectories.
# Return a sorted list of paths to directories that contain an INCAR.
# Report folders made by this tool are skipped.
def find_calc_dirs(root):
    root = os.path.abspath(resolve_path(root))
    calc_dirs = []

    for dir_path, sub_dirs, file_names in os.walk(root):
        # Do not walk into report folders made by report.py
        kept = []
        for name in sub_dirs:
            if not name.startswith(config.REPORT_PREFIX):
                kept.append(name)
        sub_dirs[:] = kept

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
