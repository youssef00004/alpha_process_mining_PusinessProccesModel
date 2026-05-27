"""
main.py — Entry point for the Process Mining assignment
CSE346 Business Process Modeling, Spring 2026

Prompts you to pick an Excel event log from the folder, then runs the full
pipeline and names every output file after the chosen log, e.g.:

  Input chosen : Input.xlsx
  Outputs      : pert_chart_Input.png / .pdf
                 alpha_algorithm_output_Input.txt
                 process_mining_report_Input.xlsx

Required Excel columns (case-insensitive):
  Case ID | Timestamp | Activity | Resource   (Event ID is optional)
"""

import os
import sys
import glob

BASE = os.path.dirname(os.path.abspath(__file__))

# Stems that belong to pipeline outputs — never offered as inputs
_OUTPUT_STEMS = {
    "process_mining_report",
}


def _list_candidates() -> list:
    """Return sorted list of .xlsx paths in BASE that are not pipeline outputs."""
    all_xlsx = sorted(glob.glob(os.path.join(BASE, "*.xlsx")))
    return [
        p for p in all_xlsx
        if os.path.splitext(os.path.basename(p))[0].lower()
        not in {s.lower() for s in _OUTPUT_STEMS}
        # also skip any file whose name starts with a known output prefix
        and not any(
            os.path.basename(p).lower().startswith(s.lower())
            for s in _OUTPUT_STEMS
        )
    ]


def _pick_input_file() -> str:
    """
    Return the chosen Excel file path:
      - If sys.argv[1] was provided, use it directly (non-interactive).
      - Otherwise show the available files and prompt the user.
    """
    # ── Non-interactive: file passed as argument ──────────────────────────
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if not os.path.isabs(path):
            path = os.path.join(BASE, path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        return path

    # ── Interactive: show menu ────────────────────────────────────────────
    candidates = _list_candidates()

    if not candidates:
        raise FileNotFoundError(
            f"No .xlsx event-log files found in:\n  {BASE}\n\n"
            f"  Drop an Excel event log there and re-run."
        )

    print("\n  Available Excel event logs:")
    for i, path in enumerate(candidates, 1):
        print(f"    [{i}] {os.path.basename(path)}")

    print()
    raw = input("  Enter the file name (or its number): ").strip()

    # Accept a number
    if raw.isdigit():
        idx = int(raw) - 1
        if not (0 <= idx < len(candidates)):
            raise ValueError(f"Invalid selection '{raw}'. Choose 1–{len(candidates)}.")
        return candidates[idx]

    # Accept a bare stem ("Input") or a full name ("Input.xlsx")
    name = raw if raw.lower().endswith(".xlsx") else raw + ".xlsx"
    path = os.path.join(BASE, name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"'{name}' not found in {BASE}.\n"
            f"  Available: {[os.path.basename(c) for c in candidates]}"
        )
    return path


def main():
    print("\n" + "=" * 60)
    print("  CSE346 — Business Process Modeling")
    print("  Alpha Algorithm & PERT Chart Generator")
    print("  Dr. Islam El-Maddah, Spring 2026")
    print("=" * 60)

    try:
        input_file = _pick_input_file()
    except (FileNotFoundError, ValueError) as e:
        print(f"\n  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    stem = os.path.splitext(os.path.basename(input_file))[0]

    # Output files are named after the chosen log
    txt_out  = os.path.join(BASE, f"alpha_algorithm_output_{stem}.txt")
    png_out  = os.path.join(BASE, f"pert_chart_{stem}.png")
    pdf_out  = os.path.join(BASE, f"pert_chart_{stem}.pdf")
    xlsx_out = os.path.join(BASE, f"process_mining_report_{stem}.xlsx")

    print(f"\n  Input : {os.path.basename(input_file)}")
    print(f"  Outputs will be named with suffix  _{stem}.*")

    from automation import run_pipeline
    run_pipeline(
        xlsx_input=input_file,
        out_dir=BASE,
        txt_out=txt_out,
        png_out=png_out,
        pdf_out=pdf_out,
        xlsx_out=xlsx_out,
    )

    print("\n" + "=" * 60)
    print("  ALL DONE — Output files:")
    for path in [txt_out, png_out, pdf_out, xlsx_out]:
        status = "[OK]" if os.path.exists(path) else "[MISSING]"
        print(f"    {status}  {os.path.basename(path)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
