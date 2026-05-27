# Process Mining Assignment
**CSE346 — Business Process Modeling | Dr. Islam El-Maddah | Spring 2026**

## Overview
This project implements the **Alpha Algorithm** (van der Aalst, 2004) for automated process discovery from event logs, along with a full reporting and visualization pipeline.

---

## Setup

### 1. Install Python dependencies
```bash
cd process_mining_assignment
pip install -r requirements.txt
```

### 2. Run everything
```bash
python main.py
```

This generates all output files in the same folder.

---

## Output Files

| File | Description |
|------|-------------|
| `alpha_algorithm_output.txt` | Full step-by-step Alpha Algorithm trace (Steps 1–8) |
| `pert_chart.png` | Event Network Diagram (PERT Chart), 300 DPI |
| `pert_chart.pdf` | Same chart as PDF |
| `process_mining_report.xlsx` | 4-sheet Excel report (see below) |
| `sample_input.xlsx` | The assignment event log as an Excel file |

### Excel Report Sheets
1. **Event Log** — cleaned and sorted event log
2. **Footprint Matrix** — N×N matrix of →, ←, ||, # relations
3. **Alpha Results** — discovered places, start/end activities
4. **Process Summary** — case count, durations, resource stats

---

## Using Your Own Event Log

1. Prepare an Excel file (`.xlsx`) with these columns:

   | Column | Required | Description |
   |--------|----------|-------------|
   | `Case ID` | Yes | Identifier for each process instance |
   | `Activity` | Yes | Name of the activity performed |
   | `Timestamp` | Yes | Date/time (ISO format: `YYYY-MM-DD HH:MM`) |
   | `Resource` | Yes | Person or system that performed the activity |
   | `Event ID` | No | Unique event identifier — auto-generated if absent |

2. Run the automation — **no code changes needed**, just swap the file:
```bash
python automation.py your_log.xlsx
```

Or from Python:
```python
from automation import run_pipeline
run_pipeline("your_log.xlsx", out_dir="output/")
```

The script validates columns, handles missing values, auto-generates Event IDs if absent, and rejects invalid input with clear error messages.

---

## File Structure

```
process_mining_assignment/
├── main.py                    # Entry point — run this
├── event_log.py               # Hardcoded event log (4 cases)
├── alpha_algorithm.py         # Alpha Algorithm implementation
├── pert_chart.py              # PERT / Event Network Diagram
├── automation.py              # Full pipeline (Excel in → reports out)
├── create_sample_input.py     # Generates sample_input.xlsx
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## Why Python?

Python was selected for this project because it offers the best combination of capabilities for the specific tasks required:

| Requirement | Python capability |
|-------------|-------------------|
| Load and sort event log from Excel | `pandas.read_excel()` — clean, one-line import with automatic type inference |
| Set-theoretic Alpha Algorithm logic | Native `frozenset`, `itertools.combinations`, and set comprehensions map directly to the mathematical definitions in van der Aalst (2004) |
| Footprint matrix construction | Dictionary-of-dictionaries with O(n²) pair iteration — readable and matches the formal notation |
| Graph-based PERT chart | `networkx` for graph construction + `matplotlib` for publication-quality rendering with manual layout control |
| Excel report output | `pandas` + `openpyxl` for multi-sheet workbooks with auto-formatted columns |
| Automation / reusability | A single `run_pipeline(xlsx_path)` call processes any conforming event log without modifying source code |

**Alternatives considered:**

- **Excel VBA**: Can handle tabular data manipulation but has no built-in graph visualization and the algorithmic logic (powersets, causal pair enumeration) is cumbersome in VBA.
- **Power BI / Tableau**: Excellent for interactive dashboards but cannot be scripted to implement the Alpha Algorithm's enumeration logic or export programmatically generated PERT charts.
- **R**: Comparable data-handling capability (`dplyr`, `ggraph`) but Python's process mining ecosystem (and `pm4py`) is more mature, and Python is the standard in the course.

Python's `requirements.txt` ensures full reproducibility — any machine with Python 3.8+ can reproduce all results with a single `pip install`.

---

## Alpha Algorithm Steps (van der Aalst, 2004)

| Step | Description |
|------|-------------|
| 1 | Extract all activities T_L from the event log |
| 2 | Extract start activities T_I (first activity in each trace) |
| 3 | Extract end activities T_O (last activity in each trace) |
| 4 | Build footprint matrix: classify each (A,B) pair as →, ←, \|\|, or # |
| 5 | Enumerate candidate places: (A_set, B_set) pairs satisfying causal and independence conditions |
| 6 | Remove non-maximal places (keep only maximal pairs) |
| 7 | Construct Petri net: add source/sink places and compile arc list |
| 8 | Output complete result summary |

---

## Process Model Interpretation

### Discovered process summary

The Alpha Algorithm applied to the 4-case event log discovers a **two-path order fulfillment process** with a concurrent tail:

**Path A — Stock Available (Cases 1 & 4):**
> Check stock availability → Retrieve product from warehouse → Confirm order → …

**Path B — Manufacturing Required (Cases 2 & 3):**
> Check stock availability → Check materials availability → [optional: Request raw materials → Obtain raw materials] → Manufacture product → Confirm order → …

After Confirm order, both paths merge and the process continues with two concurrent sub-processes.

### Generated PERT Chart

The chart below is generated by `pert_chart.py` directly from the Alpha Algorithm output. The post-Confirm-order section (nodes 8+) is built algorithmically from the discovered places.

![PERT Chart](pert_chart.png)

**Legend:**
- 🟢 Node 0: Start | 🔴 Node 11: End | 🟠 Node 10: AND-join (all paths must complete)
- Purple = Path A (Cases 1,4) | Orange = Path B (Cases 2,3) | Red = Path B2 (Case 2 only)
- Teal = Concurrent α (Emit invoice → Receive payment)
- Blue = Concurrent β (Get shipping address → Ship product)

### Concurrency discovered (|| relations)

The footprint matrix reveals **two concurrent activity pairs**:

| Activity pair | Relation | Business interpretation |
|---|---|---|
| Emit invoice \|\| Get shipping address | `\|\|` (parallel) | After the order is confirmed, the system simultaneously triggers invoice generation and address retrieval. Cases 1 & 4 process address first; Cases 2 & 3 process invoice first — neither is a prerequisite for the other. |
| Receive payment \|\| Ship product | `\|\|` (parallel) | Payment collection and physical dispatch proceed in parallel. Cases 1 & 4 collect payment before shipping (prepayment model); Cases 2 & 3 ship before payment (credit/invoice model). Both must complete before the order is archived. |

The PERT chart makes these parallel paths explicit with two concurrent branches (teal and blue paths) after node 7, joining at the AND-join node 10 before Archive order.

### Case-by-case Petri net replay

To verify the discovered model is correct, here is a token replay of Case 2 through the Petri net:

| Step | Activity fires | Tokens consumed from | Tokens produced in |
|------|---------------|----------------------|--------------------|
| 1 | Check stock availability | p_start | p2 |
| 2 | Check materials availability | p2 | p1, p10 |
| 3 | Request raw materials | p1 | p8 (p10 still holds a token) |
| 4 | Obtain raw materials | p8 | p10 (now 2 tokens in p10) |
| 5 | Manufacture product | p1(via p10 token 1), p10(token 2) | p11 |
| 6 | Confirm order | p11 | p3, p4 |
| 7 | Emit invoice | p3 | p5 |
| 8 | Get shipping address | p4 | p6 |
| 9 | Ship product | p6 | p9 |
| 10 | Receive payment | p5 | p7 |
| 11 | Archive order | p7, p9 (AND-join) | p_end |

Case 2 replays correctly — all tokens are consumed and p_end receives exactly one token. ✅

**Case 1 replay summary:** Check stock → (p2) → Retrieve from warehouse → (p11) → Confirm order → (p3,p4) → Emit invoice + Get shipping address (concurrent) → (p5,p6) → Receive payment + Ship product (concurrent) → (p7,p9) → Archive order ✅

### No loops detected

No activity appears as both a direct predecessor and direct successor of another single activity in a way that forms a cycle. The discovered Petri net is **acyclic** — consistent with a linear, non-repeating order fulfillment process. The footprint matrix confirms this: no activity pair has a cycle relationship.

### Process anomalies and Alpha Algorithm limitations

- **OR-split behaviour**: The branch after "Check stock availability" is modelled as an AND-split in the Petri net (p2 enables both Retrieve from warehouse AND Check materials availability simultaneously). In reality only ONE path is taken per case. This is a known limitation of the Alpha Algorithm — it cannot distinguish XOR-splits from AND-splits based purely on the directly-follows relation.
- **Materials availability branch**: In Case 3, Manufacture product occurs directly after Check materials availability without procurement. In Case 2, raw materials must first be obtained. The algorithm correctly discovers both possibilities via places p1 (short route) and p10 (procurement route).
- **Archive order AND-join**: Places p7 `{Receive payment} → {Archive order}` and p9 `{Ship product} → {Archive order}` together enforce that **both** payment and shipment must complete before archiving — correctly modelling that neither step can be skipped regardless of which completes first.

---

## Resource Key

| Resource | Type |
|----------|------|
| SYS1 | Automated system 1 (stock/materials checks, manufacturing) |
| SYS2 | Automated system 2 (invoice, shipping address, payment) |
| DMS | Data Management System (archive) |
| Rick, Chuck, Hans, Susi | Human workers — warehouse/confirmation/shipping |
| Ringo, Olaf, Conny, Sara, Emil | Human workers — procurement/manufacturing/shipping |

---

## Reference
van der Aalst, W.M.P., Weijters, T., & Maruster, L. (2004).
*Workflow Mining: Discovering Process Models from Event Logs.*
IEEE Transactions on Knowledge and Data Engineering, 16(9), 1128–1142.
