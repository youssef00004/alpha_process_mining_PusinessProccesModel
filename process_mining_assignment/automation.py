"""
automation.py — Full process mining automation pipeline
CSE346 Business Process Modeling, Spring 2026

Accepts ANY event log Excel file with columns:
  Case ID | Event ID | Timestamp | Activity | Resource

Outputs:
  - alpha_algorithm_output.txt
  - pert_chart.png / pert_chart.pdf
  - process_mining_report.xlsx  (4 sheets)
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict

# Local modules
from alpha_algorithm import run_alpha_algorithm
from pert_chart import draw_pert_chart


REQUIRED_COLUMNS = {"Case ID", "Timestamp", "Activity", "Resource"}


# ── 1. Load & validate ────────────────────────────────────────────────────────

def load_event_log(xlsx_path: str) -> pd.DataFrame:
    print(f"\n[Step 1] Loading event log from: {xlsx_path}")

    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(
            f"\n  ERROR: File not found: {xlsx_path}\n"
            f"  Hint: check the path and re-run: python main.py \"<your-log.xlsx>\""
        )

    try:
        df = pd.read_excel(xlsx_path, engine="openpyxl")
    except Exception as e:
        raise ValueError(
            f"\n  ERROR: Could not read '{xlsx_path}' as an Excel file.\n"
            f"  Details: {e}\n"
            f"  Hint: ensure the file is a valid .xlsx file (not .xls or .csv)."
        ) from e

    print(f"         Raw rows loaded: {len(df)}")

    # Normalise column names: strip whitespace + canonical casing
    _canon = {c.lower(): c for c in REQUIRED_COLUMNS | {"Event ID"}}
    df.columns = [_canon.get(c.strip().lower(), c.strip()) for c in df.columns]
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"\n  ERROR: Missing required column(s): {sorted(missing)}\n"
            f"  Found columns: {list(df.columns)}\n"
            f"  Required: {sorted(REQUIRED_COLUMNS)} (Event ID is optional — auto-generated if absent)"
        )

    # Drop fully empty rows
    df.dropna(how="all", inplace=True)

    if len(df) == 0:
        raise ValueError(
            f"\n  ERROR: Event log '{xlsx_path}' is empty after removing blank rows.\n"
            f"  Hint: ensure the file has at least one data row."
        )

    # Coerce types
    df["Case ID"]   = df["Case ID"].astype(str).str.strip()
    df["Activity"]  = df["Activity"].astype(str).str.strip()
    df["Resource"]  = df["Resource"].astype(str).str.strip()

    try:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    except Exception as e:
        raise ValueError(
            f"\n  ERROR: Could not parse Timestamp column.\n"
            f"  Details: {e}\n"
            f"  Hint: use ISO format 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD HH:MM:SS'."
        ) from e

    # Auto-generate Event ID if not present
    if "Event ID" not in df.columns:
        df.insert(1, "Event ID", [f"E{i+1}" for i in range(len(df))])
    else:
        df["Event ID"] = df["Event ID"].astype(str).str.strip()

    # Drop rows where Case ID or Activity is blank/NaN
    before = len(df)
    df = df[df["Case ID"].str.strip().astype(bool) & df["Activity"].str.strip().astype(bool)]
    dropped = before - len(df)
    if dropped > 0:
        print(f"         WARNING: dropped {dropped} row(s) with blank Case ID or Activity.")

    if len(df) == 0:
        raise ValueError(
            f"\n  ERROR: No valid events remain after cleaning. "
            f"Check that Case ID and Activity columns are populated."
        )

    # Sort by case then time
    df.sort_values(["Case ID", "Timestamp"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    print(f"         Clean rows: {len(df)}")
    print(f"         Cases: {df['Case ID'].nunique()}, Activities: {df['Activity'].nunique()}, Resources: {df['Resource'].nunique()}")
    return df


# ── 2. Build traces dict ──────────────────────────────────────────────────────

def df_to_traces(df: pd.DataFrame) -> dict:
    traces = {}
    for case_id, grp in df.groupby("Case ID"):
        traces[case_id] = list(grp["Activity"])
    return traces


# ── 3. Run Alpha Algorithm ────────────────────────────────────────────────────

def run_alpha(traces: dict, out_txt: str) -> dict:
    print(f"\n[Step 2] Running Alpha Algorithm...")
    result = run_alpha_algorithm(traces, output_file=out_txt)
    print(f"         Discovered {len(result['places'])} places.")
    return result


# ── 4. Generate PERT chart ────────────────────────────────────────────────────

def generate_pert(png_path: str, pdf_path: str, alpha_result: dict = None):
    print(f"\n[Step 3] Generating Event Network Diagram (PERT Chart)...")
    draw_pert_chart(output_png=png_path, output_pdf=pdf_path, alpha_result=alpha_result)


# ── 5. Build footprint DataFrame ─────────────────────────────────────────────

def footprint_to_df(activities, footprint) -> pd.DataFrame:
    rows = []
    for a in activities:
        row = {"Activity": a}
        for b in activities:
            row[b] = footprint[a][b]
        rows.append(row)
    return pd.DataFrame(rows).set_index("Activity")


# ── 6. Alpha results summary DataFrame ───────────────────────────────────────

def alpha_results_to_df(result: dict) -> pd.DataFrame:
    rows = []
    # Start / end activities
    rows.append({"Type": "Start Activities (T_I)", "Value": ", ".join(sorted(result["start_activities"]))})
    rows.append({"Type": "End Activities (T_O)",   "Value": ", ".join(sorted(result["end_activities"]))})
    rows.append({"Type": "All Activities (T_L)",   "Value": ", ".join(result["activities"])})
    rows.append({"Type": "", "Value": ""})
    rows.append({"Type": "--- Discovered Places ---", "Value": ""})
    for idx, (A_set, B_set) in enumerate(result["places"]):
        rows.append({
            "Type": f"Place p{idx+1}",
            "Value": f"Input: {{{', '.join(sorted(A_set))}}}  →  Output: {{{', '.join(sorted(B_set))}}}"
        })
    rows.append({"Type": "p_start (source)", "Value": f"→ {sorted(result['start_activities'])}"})
    rows.append({"Type": "p_end (sink)",     "Value": f"{sorted(result['end_activities'])} →"})
    return pd.DataFrame(rows)


# ── 7. Process summary DataFrame ─────────────────────────────────────────────

def process_summary_to_df(df: pd.DataFrame) -> pd.DataFrame:
    case_durations = []
    for cid, grp in df.groupby("Case ID"):
        dur = (grp["Timestamp"].max() - grp["Timestamp"].min()).total_seconds() / 3600
        case_durations.append(dur)

    rows = [
        {"Metric": "Number of Cases",         "Value": df["Case ID"].nunique()},
        {"Metric": "Number of Events",         "Value": len(df)},
        {"Metric": "Unique Activities",        "Value": df["Activity"].nunique()},
        {"Metric": "Unique Resources",         "Value": df["Resource"].nunique()},
        {"Metric": "Avg Case Duration (hours)","Value": round(float(np.mean(case_durations)), 2)},
        {"Metric": "Min Case Duration (hours)","Value": round(float(np.min(case_durations)), 2)},
        {"Metric": "Max Case Duration (hours)","Value": round(float(np.max(case_durations)), 2)},
        {"Metric": "Date Range Start",         "Value": str(df["Timestamp"].min())},
        {"Metric": "Date Range End",           "Value": str(df["Timestamp"].max())},
    ]
    return pd.DataFrame(rows)


# ── 8. Write Excel report ─────────────────────────────────────────────────────

def write_excel_report(df: pd.DataFrame, result: dict, xlsx_out: str):
    print(f"\n[Step 4] Writing Excel report: {xlsx_out}")

    footprint_df = footprint_to_df(result["activities"], result["footprint"])
    alpha_df     = alpha_results_to_df(result)
    summary_df   = process_summary_to_df(df)

    # Prepare event log sheet (display-friendly timestamps)
    log_sheet = df.copy()
    log_sheet["Timestamp"] = log_sheet["Timestamp"].dt.strftime("%Y-%m-%d %H:%M")

    with pd.ExcelWriter(xlsx_out, engine="openpyxl") as writer:
        log_sheet.to_excel(writer, sheet_name="Event Log", index=False)
        footprint_df.to_excel(writer, sheet_name="Footprint Matrix")
        alpha_df.to_excel(writer, sheet_name="Alpha Results", index=False)
        summary_df.to_excel(writer, sheet_name="Process Summary", index=False)

        # Auto-fit column widths for readability
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for col in ws.columns:
                max_len = max((len(str(cell.value)) if cell.value else 0) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)

    print(f"         [Saved] {xlsx_out}")


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(
    xlsx_input: str,
    out_dir: str = ".",
    txt_out: str = None,
    png_out: str = None,
    pdf_out: str = None,
    xlsx_out: str = None,
):
    txt_out  = txt_out  or os.path.join(out_dir, "alpha_algorithm_output.txt")
    png_out  = png_out  or os.path.join(out_dir, "pert_chart.png")
    pdf_out  = pdf_out  or os.path.join(out_dir, "pert_chart.pdf")
    xlsx_out = xlsx_out or os.path.join(out_dir, "process_mining_report.xlsx")

    print("\n" + "=" * 60)
    print("  Process Mining Automation Pipeline")
    print("  CSE346 Business Process Modeling, Spring 2026")
    print("=" * 60)

    df     = load_event_log(xlsx_input)
    traces = df_to_traces(df)
    result = run_alpha(traces, txt_out)
    generate_pert(png_out, pdf_out, alpha_result=result)
    write_excel_report(df, result, xlsx_out)

    print("\n" + "=" * 60)
    print("  Pipeline complete. Output files:")
    for path in [txt_out, png_out, pdf_out, xlsx_out]:
        status = "OK" if os.path.exists(path) else "MISSING"
        print(f"    [{status}] {path}")
    print("=" * 60)

    return result


if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "sample_input.xlsx"
    try:
        run_pipeline(input_file)
    except (FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n  UNEXPECTED ERROR: {e}", file=sys.stderr)
        raise
