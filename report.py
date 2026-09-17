# report.py
# Write the scan results as CSV files and one Markdown report.
# Uses classify.py to get one record per calculation directory.
# Reports go into a new dated folder inside the vasp_triage folder.

import csv
import datetime
import os
import sys

import classify
import config


# Column names in the CSV files, in order.
CSV_COLUMNS = ["path", "status", "energy_sigma0_eV", "job_id",
               "ENCUT", "EDIFF", "EDIFFG", "NELM",
               "kpoints_scheme", "kpoints_mesh", "missing_files",
               "message_label", "message_file", "message_line","scf_at_nelm"]


# Return the group name for one status, for example "failed".
def get_group(status):
    for group_name, statuses in config.REPORT_GROUPS:
        if status in statuses:
            return group_name
    return "other"


# Return the position of a group in REPORT_GROUPS.
# Used to sort records in report order.
def group_position(group_name):
    position = 0
    for name, statuses in config.REPORT_GROUPS:
        if name == group_name:
            return position
        position = position + 1
    return position


# Turn a value into text for the report. None becomes empty text.
def to_text(value):
    if value is None:
        return ""
    return str(value)


# Turn one record into a list of values, one per CSV column.
def record_to_row(record):
    row = []
    row.append(record["path"])
    row.append(record["status"])
    row.append(to_text(record["energy"]))
    row.append(to_text(record["job_id"]))
    row.append(to_text(record["ENCUT"]))
    row.append(to_text(record["EDIFF"]))
    row.append(to_text(record["EDIFFG"]))
    row.append(to_text(record["NELM"]))
    row.append(record["kpoints_scheme"])
    row.append(record["kpoints_mesh"])
    row.append(" ".join(record["missing"]))
    row.append(to_text(record["message_label"]))
    row.append(to_text(record["message_file"]))
    row.append(to_text(record["message_line"]))
    row.append(str(record["scf_at_nelm"]))
    return row


# Return records sorted by group, then status, then path.
def sort_records(records):
    def sort_key(record):
        group = get_group(record["status"])
        return (group_position(group), record["status"], record["path"])

    return sorted(records, key=sort_key)


# Write one CSV file with a header row and one row per record.
def write_csv(records, file_path):
    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)
        for record in records:
            writer.writerow(record_to_row(record))


# Write the combined CSV and one CSV per group.
# Return the list of file paths written.
def write_all_csv(records, out_dir):
    written = []
    sorted_records = sort_records(records)

    all_path = os.path.join(out_dir, "report_all.csv")
    write_csv(sorted_records, all_path)
    written.append(all_path)

    for group_name, statuses in config.REPORT_GROUPS:
        group_records = []
        for record in sorted_records:
            if record["status"] in statuses:
                group_records.append(record)

        group_path = os.path.join(out_dir, "report_" + group_name + ".csv")
        write_csv(group_records, group_path)
        written.append(group_path)

    return written


# Make text safe inside a Markdown table cell.
def md_cell(value):
    text = to_text(value)
    text = text.replace("|", "/")
    return text


# Write the Markdown report: summary counts, then one table per group.
def write_markdown(records, file_path):
    sorted_records = sort_records(records)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append("# VASP job report")
    lines.append("")
    lines.append("Generated: " + now)
    lines.append("Total directories: " + str(len(records)))
    lines.append("")

    # Summary table: count per status
    lines.append("## Summary")
    lines.append("")
    lines.append("| Group | Status | Count |")
    lines.append("|---|---|---|")
    for group_name, statuses in config.REPORT_GROUPS:
        for status in statuses:
            count = 0
            for record in records:
                if record["status"] == status:
                    count = count + 1
            lines.append("| " + group_name + " | " + status
                         + " | " + str(count) + " |")
    lines.append("")

    # One section per group
    for group_name, statuses in config.REPORT_GROUPS:
        group_records = []
        for record in sorted_records:
            if record["status"] in statuses:
                group_records.append(record)

        lines.append("## " + group_name + " (" + str(len(group_records))
                     + ")")
        lines.append("")

        if len(group_records) == 0:
            lines.append("None.")
            lines.append("")
            continue

        lines.append("| Path | Status | energy(sigma->0) eV | Missing"
                     " | Message |")
        lines.append("|---|---|---|---|---|")

        for record in group_records:
            message = ""
            if record["message_label"] is not None:
                message = (record["message_label"] + " ("
                           + record["message_file"] + "): "
                           + record["message_line"])
            if record["scf_at_nelm"]:
                message = message + " [SCF at NELM]"

            lines.append("| " + md_cell(record["path"])
                         + " | " + md_cell(record["status"])
                         + " | " + md_cell(record["energy"])
                         + " | " + md_cell(" ".join(record["missing"]))
                         + " | " + md_cell(message) + " |")
        lines.append("")

    with open(file_path, "w") as f:
        f.write("\n".join(lines))


# Build a folder name from the current time.
# Example: report_16_Sept_26_1_16PM
def make_report_folder_name():
    now = datetime.datetime.now()

    day = str(now.day)
    month = config.MONTH_NAMES[now.month - 1]
    year = now.strftime("%y")

    # Convert 24 hour time to 12 hour time
    hour = now.hour % 12
    if hour == 0:
        hour = 12
    minute = now.strftime("%M")
    if now.hour < 12:
        am_pm = "AM"
    else:
        am_pm = "PM"

    return ("report_" + day + "_" + month + "_" + year + "_"
            + str(hour) + "_" + minute + am_pm)


# Create a new report folder inside the vasp_triage folder.
# If the name already exists, add _2, _3, and so on.
# Return the full path of the new folder.
def create_report_folder():
    # Folder that holds this report.py file, for example ~/vasp_triage
    code_dir = os.path.dirname(os.path.abspath(__file__))
    name = make_report_folder_name()

    out_dir = os.path.join(code_dir, name)
    number = 2
    while os.path.exists(out_dir):
        out_dir = os.path.join(code_dir, name + "_" + str(number))
        number = number + 1

    os.makedirs(out_dir)
    return out_dir


# Run this file directly to scan and write all reports.
# Example: python3 report.py /path/to/calculations
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 report.py /path/to/calculations")
        sys.exit(1)

    root = sys.argv[1]

    if not os.path.isdir(root):
        print("Error: not a directory: " + root)
        sys.exit(1)

    records = classify.classify_all(root)
    out_dir = create_report_folder()

    written = write_all_csv(records, out_dir)

    md_path = os.path.join(out_dir, "report.md")
    write_markdown(records, md_path)
    written.append(md_path)

    print("Directories: " + str(len(records)))
    print("Files written:")
    for file_path in written:
        print("  " + file_path)
