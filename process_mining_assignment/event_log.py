"""
event_log.py — Structured event log for CSE346 Business Process Modeling
Assignment data from Spring 2026 course (Dr. Islam El-Maddah)

DMS = centralized Data Management System
SYS1, SYS2 = separate computer systems (automated resources)
"""

from datetime import datetime

def parse_ts(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M")

# Each event: case_id, event_id, timestamp, activity, resource
RAW_EVENTS = [
    # Case 1 — stock available, retrieved from warehouse
    ("1", "Ch-4680555556-1", "2012-07-30 11:14", "Check stock availability",       "SYS1"),
    ("1", "Re-5972222222-1", "2012-07-30 14:20", "Retrieve product from warehouse", "Rick"),
    ("1", "Co-6319444444-1", "2012-07-30 15:10", "Confirm order",                   "Chuck"),
    ("1", "Em-6402777778-1", "2012-07-30 15:22", "Emit invoice",                    "SYS2"),
    ("1", "Ge-6555555556-1", "2012-07-30 15:44", "Get shipping address",             "SYS2"),
    ("1", "Re-4180555556-1", "2012-08-04 10:02", "Receive payment",                 "SYS2"),
    ("1", "Sh-4659722222-1", "2012-08-05 11:11", "Ship product",                    "Susi"),
    ("1", "Ar-3833333333-1", "2012-08-06 09:12", "Archive order",                   "DMS"),

    # Case 2 — materials needed, full manufacturing cycle
    ("2", "Ch-4055555556-2", "2012-08-01 09:44", "Check stock availability",       "SYS1"),
    ("2", "Ch-4208333333-2", "2012-08-01 10:06", "Check materials availability",   "SYS1"),
    ("2", "Re-4666666667-2", "2012-08-01 11:12", "Request raw materials",           "Ringo"),
    ("2", "Ob-3263888889-2", "2012-08-03 07:50", "Obtain raw materials",            "Olaf"),
    ("2", "Ma-6131944444-2", "2012-08-04 14:43", "Manufacture product",             "SYS1"),
    ("2", "Co-6187615741-2", "2012-08-04 14:51", "Confirm order",                   "Conny"),
    ("2", "Em-6388888888-2", "2012-08-04 15:20", "Emit invoice",                    "SYS2"),
    ("2", "Ge-6439814815-2", "2012-08-04 15:27", "Get shipping address",             "SYS2"),
    ("2", "Sh-7277777778-2", "2012-08-04 17:28", "Ship product",                    "Sara"),
    ("2", "Re-3611111111-2", "2012-08-07 08:40", "Receive payment",                 "SYS2"),
    ("2", "Ar-3680555556-2", "2012-08-07 08:50", "Archive order",                   "DMS"),

    # Case 3 — materials available, manufacture without procurement
    ("3", "Ch-4208333333-3", "2012-08-02 10:06", "Check stock availability",       "SYS1"),
    ("3", "Ch-4243055556-3", "2012-08-02 10:11", "Check materials availability",   "SYS1"),
    ("3", "Ma-6694444444-3", "2012-08-02 16:04", "Manufacture product",             "SYS1"),
    ("3", "Co-6751157407-3", "2012-08-02 16:12", "Confirm order",                   "Chuck"),
    ("3", "Em-6895833333-3", "2012-08-02 16:33", "Emit invoice",                    "SYS2"),
    ("3", "Ge-7013888889-3", "2012-08-02 16:50", "Get shipping address",             "SYS2"),
    ("3", "Re-4305555556-3", "2012-08-02 16:58", "Receive payment",                 "SYS2"),
    ("3", "Sh-7069444444-3", "2012-08-06 10:20", "Ship product",                    "Emil"),
    ("3", "Ar-4340277778-3", "2012-08-06 10:25", "Archive order",                   "DMS"),

    # Case 4 — stock available, retrieved automatically by SYS1
    ("4", "Ch-3409722222-4", "2012-08-04 08:11", "Check stock availability",       "SYS1"),
    ("4", "Re-5000115741-4", "2012-08-04 12:00", "Retrieve product from warehouse", "SYS1"),
    ("4", "Co-5041898148-4", "2012-08-04 12:06", "Confirm order",                   "Hans"),
    ("4", "Em-5180000000-4", "2012-08-04 12:20", "Emit invoice",                    "SYS2"),
    ("4", "Ge-5223148148-4", "2012-08-04 12:32", "Get shipping address",             "SYS2"),
    ("4", "Sh-4034837963-4", "2012-08-08 09:41", "Ship product",                    "Susi"),
    ("4", "Re-4180555556-4", "2012-08-08 13:43", "Receive payment",                 "SYS2"),
    ("4", "Ar-5888888889-4", "2012-08-08 14:08", "Archive order",                   "DMS"),
]

# Build the canonical list of event dicts, parsing timestamps
EVENT_LOG = [
    {
        "case_id":   case_id,
        "event_id":  event_id,
        "timestamp": parse_ts(ts),
        "activity":  activity,
        "resource":  resource,
    }
    for case_id, event_id, ts, activity, resource in RAW_EVENTS
]


def get_cases():
    """Return events grouped by case_id, sorted by timestamp."""
    from collections import defaultdict
    cases = defaultdict(list)
    for e in EVENT_LOG:
        cases[e["case_id"]].append(e)
    for k in cases:
        cases[k].sort(key=lambda x: x["timestamp"])
    return dict(cases)


def get_traces():
    """Return ordered list of activity names per case."""
    cases = get_cases()
    return {cid: [e["activity"] for e in events] for cid, events in cases.items()}


if __name__ == "__main__":
    traces = get_traces()
    for cid, trace in traces.items():
        print(f"Case {cid}: {' → '.join(trace)}")
