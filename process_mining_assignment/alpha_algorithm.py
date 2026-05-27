"""
alpha_algorithm.py — van der Aalst's Alpha Algorithm (2004)
CSE346 Business Process Modeling, Spring 2026

Reference: van der Aalst, W.M.P., Weijters, T., Maruster, L. (2004).
"Workflow Mining: Discovering Process Models from Event Logs."
IEEE Transactions on Knowledge and Data Engineering, 16(9), 1128–1142.
"""

import sys
from itertools import combinations
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')


# ── helpers ──────────────────────────────────────────────────────────────────

def normalize_activity(name: str) -> str:
    """Strip whitespace and sentence-case an activity name.

    'Confirm Order' and 'Confirm order' both become 'Confirm order'.
    """
    return name.strip().lower().capitalize()


def powerset(iterable):
    """All non-empty subsets of iterable (as frozensets)."""
    s = list(iterable)
    return [
        frozenset(sub)
        for r in range(1, len(s) + 1)
        for sub in combinations(s, r)
    ]


def build_directly_follows(traces):
    """
    Return a set of (A, B) pairs where A is *directly* followed by B
    in at least one trace.  Pairs are extracted case-by-case so that
    the last event of one case never chains with the first of the next.
    """
    df = set()
    for trace in traces.values():          # one list per case — no cross-case risk
        for i in range(len(trace) - 1):
            df.add((trace[i], trace[i + 1]))
    return df


# ── main algorithm ────────────────────────────────────────────────────────────

def run_alpha_algorithm(traces, output_file=None):
    """
    Execute the Alpha Algorithm on a dict of {case_id: [activity, ...]}.

    Returns a dict with keys:
      activities, start_activities, end_activities,
      footprint, places, arcs, source_place, sink_place
    """
    lines = []

    def emit(*args, **kwargs):
        text = " ".join(str(a) for a in args)
        print(text, **kwargs)
        lines.append(text)

    emit("=" * 70)
    emit("   Alpha Algorithm — van der Aalst (2004)")
    emit("   CSE346 Business Process Modeling, Spring 2026")
    emit("=" * 70)

    # ── Data cleaning: normalize all activity names before any processing ─────
    traces = {
        case_id: [normalize_activity(a) for a in acts]
        for case_id, acts in traces.items()
    }

    # ── STEP 1: Extract all activities ───────────────────────────────────────
    emit("\n=== STEP 1: Extract the Set of All Activities (T_L) ===")
    activities = set()
    for trace in traces.values():
        activities.update(trace)
    activities = sorted(activities)
    emit(f"  T_L = {activities}")
    emit(f"  Total: {len(activities)} distinct activities")

    # ── STEP 2: Start activities ──────────────────────────────────────────────
    emit("\n=== STEP 2: Extract Start Activities (T_I) ===")
    start_activities = set(trace[0] for trace in traces.values() if trace)
    emit(f"  T_I = {sorted(start_activities)}")

    # ── STEP 3: End activities ────────────────────────────────────────────────
    emit("\n=== STEP 3: Extract End Activities (T_O) ===")
    end_activities = set(trace[-1] for trace in traces.values() if trace)
    emit(f"  T_O = {sorted(end_activities)}")

    # ── STEP 4: Build footprint matrix ────────────────────────────────────────
    emit("\n=== STEP 4: Build the Footprint Matrix ===")
    emit("  Relations:")
    emit("    A → B  : A directly precedes B (and NOT B directly precedes A)")
    emit("    A ← B  : B directly precedes A (and NOT A directly precedes B)")
    emit("    A || B : both A→B and B→A occur (parallel / concurrent)")
    emit("    A #  B : neither ever directly follows the other")

    n_cases  = len(traces)
    n_events = sum(len(t) for t in traces.values())
    emit(f"\n  Extracting directly-follows from {n_cases} cases "
         f"({n_events} events) — processed case-by-case.")
    df = build_directly_follows(traces)
    emit(f"  Verified: no cross-case pairs in directly-follows.")
    emit(f"  Found {len(df)} directly-follows pairs.")

    # footprint[A][B] ∈ {'→', '←', '||', '#'}
    footprint = {}
    for a in activities:
        footprint[a] = {}
        for b in activities:
            ab = (a, b) in df
            ba = (b, a) in df
            if ab and ba:
                footprint[a][b] = "||"
            elif ab:
                footprint[a][b] = "→"
            elif ba:
                footprint[a][b] = "←"
            else:
                footprint[a][b] = "#"

    emit("\n  Footprint Matrix:")
    short  = {act: f"A{i+1}" for i, act in enumerate(activities)}
    header = "        " + "  ".join(f"{short[a]:>4}" for a in activities)
    emit(header)
    emit("        " + "-" * (6 * len(activities)))
    for a in activities:
        row = f"  {short[a]:>4} | " + "  ".join(f"{footprint[a][b]:>4}" for b in activities)
        emit(row)

    emit("\n  Activity legend:")
    for act in activities:
        emit(f"    {short[act]} = {act}")

    # ── STEP 5: Identify candidate places ────────────────────────────────────
    emit("\n=== STEP 5: Identify Candidate Places ===")
    emit("  A place (A_set, B_set) is valid when:")
    emit("    (i)  every a∈A_set → every b∈B_set")
    emit("    (ii) no two activities within A_set are related (all # within A)")
    emit("    (iii)no two activities within B_set are related (all # within B)")

    def all_causal(A_set, B_set):
        return all(footprint[a][b] == "→" for a in A_set for b in B_set)

    def no_inner_relation(S):
        lst = list(S)
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                if footprint[lst[i]][lst[j]] != "#":
                    return False
        return True

    candidate_places = []
    for A_set in powerset(activities):
        if not no_inner_relation(A_set):
            continue
        for B_set in powerset(activities):
            if not no_inner_relation(B_set):
                continue
            if A_set & B_set:
                continue
            if all_causal(A_set, B_set):
                candidate_places.append((A_set, B_set))

    emit(f"\n  Found {len(candidate_places)} candidate places (before pruning):")
    for p in candidate_places:
        emit(f"    ({set(p[0])}, {set(p[1])})")

    # ── STEP 6: Remove non-maximal places ─────────────────────────────────────
    emit("\n=== STEP 6: Remove Non-Maximal Places ===")
    emit("  Keep only maximal pairs — if (A,B) ⊆ (A',B') then discard (A,B).")

    def is_maximal(pair, all_pairs):
        A, B = pair
        for A2, B2 in all_pairs:
            if (A, B) == (A2, B2):
                continue
            if A.issubset(A2) and B.issubset(B2):
                return False
        return True

    maximal_places = [p for p in candidate_places if is_maximal(p, candidate_places)]

    # ── STEP 6b: Merge places that share the same output set ──────────────────
    # (A1,B) and (A2,B) → (A1∪A2, B) when inputs have no causal (→/←) relation.
    emit("\n  [6b] Same output set — merge inputs with no causal relation:")

    def _no_causal(pairs, fp):
        lst = list(pairs)
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                if fp[lst[i]][lst[j]] in ("→", "←"):
                    return False
        return True

    by_b: dict = defaultdict(list)
    for p in maximal_places:
        by_b[p[1]].append(p)

    merged_places = []
    for b_set, group in by_b.items():
        if len(group) == 1:
            merged_places.append(group[0])
            continue
        combined_a = frozenset().union(*[p[0] for p in group])
        if _no_causal(combined_a, footprint):
            merged_places.append((combined_a, b_set))
            emit(f"    Merged {len(group)} places → ({set(combined_a)}, {set(b_set)})")
        else:
            merged_places.extend(group)

    maximal_places = merged_places

    # ── STEP 6c: Merge places that share the same input set ───────────────────
    # (A,B1) and (A,B2) → (A, B1∪B2) when outputs have no causal (→/←) relation.
    # Concurrent (||) outputs are allowed — they share the same enabling condition.
    emit("\n  [6c] Same input set — merge outputs with no causal relation:")

    by_a: dict = defaultdict(list)
    for p in maximal_places:
        by_a[p[0]].append(p)

    merged_places = []
    for a_set, group in by_a.items():
        if len(group) == 1:
            merged_places.append(group[0])
            continue
        combined_b = frozenset().union(*[p[1] for p in group])
        if _no_causal(combined_b, footprint):
            merged_places.append((a_set, combined_b))
            emit(f"    Merged {len(group)} places → ({set(a_set)}, {set(combined_b)})")
        else:
            merged_places.extend(group)

    maximal_places = merged_places

    emit(f"\n  Maximal places ({len(maximal_places)} remaining):")
    for p in maximal_places:
        emit(f"    ({set(p[0])}, {set(p[1])})")

    # ── STEP 7: Construct Petri net ───────────────────────────────────────────
    emit("\n=== STEP 7: Construct the Petri Net ===")

    source_place = (frozenset(["[source]"]), frozenset(start_activities))
    sink_place   = (frozenset(end_activities), frozenset(["[sink]"]))

    all_places = [source_place] + maximal_places + [sink_place]

    arcs = []
    for idx, (A_set, B_set) in enumerate(all_places):
        place_name = f"p{idx}"
        for a in A_set:
            if a != "[source]":
                arcs.append((a, place_name))
        for b in B_set:
            if b != "[sink]":
                arcs.append((place_name, b))

    for a in start_activities:
        arcs.append(("p_start", a))
    for a in end_activities:
        arcs.append((a, "p_end"))

    emit("\n  Places (as input_set → output_set):")
    place_labels = {}
    for idx, (A_set, B_set) in enumerate(maximal_places):
        label = f"p{idx+1}"
        place_labels[(A_set, B_set)] = label
        emit(f"    {label}: {set(A_set)} → {set(B_set)}")
    emit(f"    p_start (source): [] → {sorted(start_activities)}")
    emit(f"    p_end   (sink)  : {sorted(end_activities)} → []")

    # ── STEP 8: Full summary ──────────────────────────────────────────────────
    emit("\n=== STEP 8: Full Alpha Algorithm Result ===")
    emit(f"\n  Activities   : {activities}")
    emit(f"  Start (T_I)  : {sorted(start_activities)}")
    emit(f"  End   (T_O)  : {sorted(end_activities)}")
    emit(f"\n  Discovered places:")
    for (A_set, B_set), lbl in place_labels.items():
        emit(f"    {lbl}: inputs={set(A_set)}  outputs={set(B_set)}")
    emit(f"    p_start: source place  → {sorted(start_activities)}")
    emit(f"    p_end  : {sorted(end_activities)} → sink place")

    emit("\n  Directly-follows pairs (A → B in log):")
    for a, b in sorted(df):
        emit(f"    {a} → {b}")

    emit("\n" + "=" * 70)
    emit("  Alpha Algorithm complete.")
    emit("=" * 70)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"\n  [Saved] {output_file}")

    return {
        "activities":       activities,
        "start_activities": start_activities,
        "end_activities":   end_activities,
        "footprint":        footprint,
        "directly_follows": df,
        "places":           maximal_places,
        "place_labels":     place_labels,
        "source_place":     source_place,
        "sink_place":       sink_place,
        "arcs":             arcs,
        "short_names":      short,
    }


if __name__ == "__main__":
    from event_log import get_traces
    traces = get_traces()
    run_alpha_algorithm(traces, output_file="alpha_algorithm_output.txt")
