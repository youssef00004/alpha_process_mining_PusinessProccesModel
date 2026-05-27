"""
pert_chart.py — Event Network Diagram (PERT Chart)
CSE346 Business Process Modeling, Spring 2026

The ENTIRE graph (nodes and edges) is derived algorithmically from the Alpha
Algorithm output via build_pert_graph_from_alpha().

AoA PERT:
  Fan-out (one source → same activity → multiple destinations):
    → one labelled edge to a grey split-event node + dummy arcs onward.
  Fan-in (multiple sources → same activity → same destination):
    → dummy arcs to a grey merge-event node + one labelled edge out.
  This guarantees every activity label appears EXACTLY ONCE.
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
from collections import defaultdict


# ── Edge colour palette ───────────────────────────────────────────────────────
# Tags are assigned dynamically from graph structure — no hardcoded names.

_EDGE_COLOURS = {
    "common": "#2c3e50",   # start/end and unclassified activities
    "pathA":  "#8e44ad",   # activities that enable a concurrent split
    "pathB":  "#e67e22",   # activities enabled by a concurrent join place
}

_TAG_LABELS = {
    "common": "Common / start / end activity",
    "pathA":  "Concurrent split activity",
    "pathB":  "Concurrent join activity",
}


# ── Dynamic tag assignment (no hardcoded activity names) ─────────────────────

def _get_activity_tag(activity, alpha_result):
    """
    Assign a colour tag from graph structure alone — works on any event log.

    common : activity is a start/end activity, or has no special structure
    pathA  : activity is in A_set of a place whose B_set has >1 activity
             (it produces into a place that fans out — concurrent split)
    pathB  : activity is in B_set of a place whose A_set has >1 activity
             (it is enabled by a place that merges — concurrent join)
    """
    start_acts = set(alpha_result.get("start_activities", []))
    end_acts   = set(alpha_result.get("end_activities",   []))

    if activity in start_acts or activity in end_acts:
        return "common"

    for A_set, B_set in alpha_result.get("places", []):
        if activity in A_set and len(B_set) > 1:
            return "pathA"
        if activity in B_set and len(A_set) > 1:
            return "pathB"

    return "common"


# ── Core builder: alpha places → PERT graph ───────────────────────────────────

def build_pert_graph_from_alpha(alpha_result):
    """
    Derive the complete AoA PERT graph from the Alpha Algorithm output.

    Returns (G, node_labels_dict, pos_dict, merge_node_ids, split_node_ids)

    Each edge in G carries:
      label      – display string (empty for dummy arcs)
      tag        – colour tag derived from graph structure
      dummy      – True for dependency arcs with no activity label
      label_list – list of labels when parallel arcs share the same node pair
      tag_list   – matching list of colour tags
    """
    places     = alpha_result["places"]
    start_acts = alpha_result["start_activities"]
    end_acts   = alpha_result["end_activities"]
    n_places   = len(places)

    # ── 1. Map each activity to its input/output place-IDs ───────────────────
    act_in  = defaultdict(list)   # activity → places it reads FROM
    act_out = defaultdict(list)   # activity → places it writes TO

    for idx, (A_set, B_set) in enumerate(places):
        pid = f"p{idx + 1}"
        for a in A_set:
            act_out[a].append(pid)
        for b in B_set:
            act_in[b].append(pid)

    for a in start_acts:
        act_in[a].append("p_start")
    end_node_ids = {}
    for a in end_acts:
        end_node_id = f"p_end_{a.replace(' ', '_')}"
        end_node_ids[a] = end_node_id
        act_out[a].append(end_node_id)

    # ── 2. Build raw directed edges ───────────────────────────────────────────
    raw_edges = []
    for act in sorted(set(act_in) | set(act_out)):
        tag = _get_activity_tag(act, alpha_result)
        for ip in act_in.get(act, []):
            for op in act_out.get(act, []):
                raw_edges.append((ip, op, act, tag))

    # ── Fan-out: same label + same source → split node ────────────────────────
    by_label_src = defaultdict(list)
    for e in raw_edges:
        by_label_src[(e[2], e[0])].append(e)

    real_after_fanout = []
    dummy_fanout      = []
    split_node_ids    = []
    seen_splits       = set()

    for e in raw_edges:
        lbl, src = e[2], e[0]
        group = by_label_src[(lbl, src)]
        if len(group) <= 1:
            real_after_fanout.append(e)
        else:
            slug     = lbl.replace(" ", "_")
            split_id = f"_spl_{slug}"
            if split_id not in split_node_ids:
                split_node_ids.append(split_id)
            if split_id not in seen_splits:
                seen_splits.add(split_id)
                real_after_fanout.append((src, split_id, lbl, e[3]))
            dummy_fanout.append((split_id, e[1], "", "common"))

    # ── Fan-in: same label + same destination → merge node ───────────────────
    by_label_dst = defaultdict(list)
    for e in real_after_fanout:
        by_label_dst[(e[2], e[1])].append(e)

    edges          = list(dummy_fanout)
    merge_node_ids = []
    for (lbl, dst), group in by_label_dst.items():
        if len(group) == 1:
            edges.append(group[0])
        else:
            slug     = lbl.replace(" ", "_")
            merge_id = f"_mrg_{slug}"
            if merge_id not in merge_node_ids:
                merge_node_ids.append(merge_id)
            for src, _, _, tag in group:
                edges.append((src, merge_id, "", "common"))
            edges.append((merge_id, dst, lbl, group[0][3]))

    # ── 3. Compute node positions ─────────────────────────────────────────────
    all_node_ids = (["p_start"]
                    + [f"p{i+1}" for i in range(n_places)]
                    + split_node_ids
                    + merge_node_ids
                    + sorted(end_node_ids.values()))

    G_layout = nx.DiGraph()
    for nid in all_node_ids:
        G_layout.add_node(nid)
    for src, dst, _, _ in edges:
        G_layout.add_edge(src, dst)

    # Virtual sink connects all end nodes — used only for layout centering
    G_layout.add_node("_v_sink")
    for end_nid in end_node_ids.values():
        G_layout.add_edge(end_nid, "_v_sink")

    pos = _topological_layout(G_layout, "p_start", "_v_sink",
                              merge_node_ids=merge_node_ids)
    pos.pop("_v_sink", None)

    # ── 4. Deterministic node numbering: topo sort + node-ID tie-break ───────
    try:
        topo      = list(nx.topological_sort(G_layout))
        topo_rank = {n: i for i, n in enumerate(topo)}
        sorted_nodes = sorted(all_node_ids,
                              key=lambda n: (topo_rank.get(n, 0), n))
    except nx.NetworkXUnfeasible:
        sorted_nodes = sorted(all_node_ids,
                              key=lambda n: (round(pos[n][0], 1),
                                             -round(pos[n][1], 1)))

    end_node_id_set = set(end_node_ids.values())
    node_labels = {}
    for display_num, nid in enumerate(sorted_nodes):
        if nid == "p_start":
            node_labels[nid] = "0\n(Start)"
        elif nid in end_node_id_set:
            node_labels[nid] = f"{display_num}\n(End)"
        else:
            node_labels[nid] = str(display_num)

    # ── 5. Build drawing graph — store label_list/tag_list per edge ───────────
    G = nx.DiGraph()
    for nid in all_node_ids:
        G.add_node(nid, label=node_labels[nid])
    for src, dst, lbl, tag in edges:
        if G.has_edge(src, dst):
            G[src][dst]["label_list"].append(lbl)
            G[src][dst]["tag_list"].append(tag)
            if lbl:
                if G[src][dst]["label"]:
                    G[src][dst]["label"] += f"\n{lbl}"
                else:
                    G[src][dst]["label"] = lbl
                G[src][dst]["dummy"] = False
        else:
            G.add_edge(src, dst, label=lbl, tag=tag, dummy=(lbl == ""),
                       label_list=[lbl], tag_list=[tag])

    return G, node_labels, pos, merge_node_ids, split_node_ids


# ── Layout ────────────────────────────────────────────────────────────────────

def _topological_layout(G, source, sink, merge_node_ids=None):
    try:
        topo = list(nx.topological_sort(G))
    except nx.NetworkXUnfeasible:
        return nx.spring_layout(G, seed=42)

    depths = {source: 0}
    for n in topo:
        d = depths.get(n, 0)
        for s in G.successors(n):
            depths[s] = max(depths.get(s, 0), d + 1)

    branch_group = {source: 0.0}
    assigned = {source}

    for n in topo:
        preds = list(G.predecessors(n))
        if len(preds) > 1 and n not in assigned:
            known = [branch_group[p] for p in preds if p in branch_group]
            if known:
                branch_group[n] = sum(known) / len(known)
                assigned.add(n)
        elif len(preds) == 1 and n not in assigned:
            p = preds[0]
            if p in branch_group:
                branch_group[n] = branch_group[p]
                assigned.add(n)
        if n not in branch_group:
            branch_group[n] = 0.0
            assigned.add(n)

        succs = list(G.successors(n))
        if len(succs) <= 1:
            for s in succs:
                if s not in assigned:
                    branch_group[s] = branch_group[n]
                    assigned.add(s)
        else:
            # Separate end nodes from real successor nodes
            # End nodes inherit parent band — not spread
            end_succs  = [s for s in succs
                          if s.startswith("p_end_")]
            real_succs = [s for s in succs
                          if not s.startswith("p_end_")]

            # Spread only real successors
            real_succs_sorted = sorted(real_succs)
            count  = len(real_succs_sorted)
            if count > 0:
                spread = [(i - (count-1)/2)
                          for i in range(count)]
                for s, offset in zip(real_succs_sorted, spread):
                    if s not in assigned:
                        branch_group[s] = branch_group[n] + offset
                        assigned.add(s)

            # End nodes inherit parent band
            for s in end_succs:
                if s not in assigned:
                    branch_group[s] = branch_group[n]
                    assigned.add(s)

    if merge_node_ids:
        for n in merge_node_ids:
            succs = list(G.successors(n))
            if succs:
                succ_band = branch_group.get(succs[0], 0.0)
                curr_band = branch_group.get(n, 0.0)
                if abs(curr_band - succ_band) > 0.8:
                    branch_group[n] = succ_band + (
                        0.8 if curr_band > succ_band else -0.8)

    # Separate nodes that share same band AND same depth
    depth_band_groups = defaultdict(list)
    for n in G.nodes():
        key = (depths.get(n, 0), round(branch_group.get(n, 0.0), 3))
        depth_band_groups[key].append(n)

    for (depth, band), nodes in depth_band_groups.items():
        if len(nodes) > 1:
            count = len(nodes)
            nodes_sorted = sorted(nodes)
            for j, node in enumerate(nodes_sorted):
                offset = (j - (count - 1) / 2) * 0.4
                branch_group[node] = band + offset

    levels = defaultdict(list)
    for n in G.nodes():
        levels[depths.get(n, 0)].append(n)

    # Dynamic y scale — compress when few branches
    all_bands = [branch_group.get(n, 0.0) for n in G.nodes()]
    max_band = max(abs(b) for b in all_bands) if all_bands else 1.0
    if max_band > 0:
        y_scale = min(3.5, max(1.5, 1.5 / max_band))
    else:
        y_scale = 2.5
    pos = {}
    for depth, nodes in sorted(levels.items()):
        x = depth * 2.5
        nodes_sorted = sorted(nodes,
            key=lambda n: branch_group.get(n, 0.0),
            reverse=True)
        for node in nodes_sorted:
            y = branch_group.get(node, 0.0) * y_scale
            pos[node] = (x, y)

    return pos


# ── Arc helpers ───────────────────────────────────────────────────────────────

def _arc_label_pos(x1, y1, x2, y2, rad, t=0.45):
    """
    Point on the quadratic Bézier arc (arc3 connectionstyle) at parameter t.
    Matches matplotlib's Arc3 control-point formula exactly:
      control = (mid_x - rad*dy,  mid_y + rad*dx)
    """
    dx = x2 - x1
    dy = y2 - y1
    cx = (x1 + x2) / 2 - rad * dy
    cy = (y1 + y2) / 2 + rad * dx
    bx = (1 - t)**2 * x1 + 2 * (1 - t) * t * cx + t**2 * x2
    by = (1 - t)**2 * y1 + 2 * (1 - t) * t * cy + t**2 * y2
    return bx, by


def _edge_rads(src, dst, pos, n_parallel):
    """
    Arc radii for n_parallel activities on the same (src, dst) pair.
    Single edge: straight for adjacent nodes, gently curved for long hops.
    Multiple edges: spread symmetrically so no two arcs overlap.
    """
    if n_parallel == 1:
        depth_diff = abs(pos[dst][0] - pos[src][0]) / 2.5
        if depth_diff > 3:
            return [0.15]   # gentle curve only — avoids off-canvas arcs on long hops
        return [0.0 if depth_diff <= 1 else 0.15]
    spread = {2: [-0.25, 0.25], 3: [-0.30, 0.0, 0.30]}
    if n_parallel in spread:
        return spread[n_parallel]
    step = 0.60 / (n_parallel - 1)
    return [-0.30 + step * i for i in range(n_parallel)]


# ── Validation ────────────────────────────────────────────────────────────────

def validate_against_alpha(alpha_result):
    places = alpha_result["places"]
    print("\n  [PERT] Alpha places → PERT nodes:")
    print(f"  {'Place':5s}  {'A_set':45s}  B_set")
    print("  " + "-" * 90)
    print(f"  {'p_str':5s}  {'[source]':45s}  {sorted(alpha_result['start_activities'])}")
    for i, (A_set, B_set) in enumerate(places):
        print(f"  p{i+1:<4d}  {str(sorted(A_set)):45s}  {sorted(B_set)}")
    print(f"  {'p_end':5s}  {str(sorted(alpha_result['end_activities'])):45s}  [sink]")
    print(f"\n  [PERT] {len(places)} alpha places → graph built dynamically.")


# ── Drawing ───────────────────────────────────────────────────────────────────

def draw_pert_chart(output_png="pert_chart.png", output_pdf="pert_chart.pdf",
                   alpha_result=None):
    """
    Generate and save the PERT / Event Network Diagram.
    Graph structure, positions, colours, and labels are all derived from
    alpha_result — no hardcoded activity names, coordinates, or node counts.
    """
    if alpha_result is None:
        _draw_standalone(output_png, output_pdf)
        return

    validate_against_alpha(alpha_result)
    G, node_labels, pos, merge_node_ids, split_node_ids = \
        build_pert_graph_from_alpha(alpha_result)

    n_places     = len(alpha_result["places"])
    n_split      = len(split_node_ids)
    n_merge      = len(merge_node_ids)
    helper_nodes = set(split_node_ids + merge_node_ids)

    if n_split:
        print(f"  [PERT] {n_split} split node(s): fan-out activities drawn once each.")
    if n_merge:
        print(f"  [PERT] {n_merge} merge node(s): fan-in activities drawn once each.")

    # ── Node colours ──────────────────────────────────────────────────────────
    node_color_map = []
    for n in G.nodes():
        lbl = node_labels.get(n, "")
        if "Start" in lbl:
            node_color_map.append("#2ecc71")
        elif "End" in lbl:
            node_color_map.append("#e74c3c")
        elif n in helper_nodes:
            node_color_map.append("#95a5a6")
        else:
            node_color_map.append("#3498db")

    real_edges  = [(u, v) for u, v in G.edges() if not G[u][v].get("dummy", False)]
    dummy_edges = [(u, v) for u, v in G.edges() if G[u][v].get("dummy", False)]

    fig, ax = plt.subplots(figsize=(36, 14))
    ax.set_facecolor("#f8f9fa")
    fig.patch.set_facecolor("#ffffff")

    # ── Dummy arcs (dashed, grey) ─────────────────────────────────────────────
    if dummy_edges:
        nx.draw_networkx_edges(
            G, pos, ax=ax, edgelist=dummy_edges,
            edge_color="#aaaaaa",
            arrows=True, arrowstyle="-|>", arrowsize=14,
            width=1.2, style="dashed",
            connectionstyle="arc3,rad=0.0",
            min_source_margin=26, min_target_margin=26,
        )

    # ── Real arcs: one draw call per arc for individual radius + colour ───────
    edge_label_annotations = []

    for u, v in real_edges:
        label_list = G[u][v].get("label_list", [G[u][v]["label"]])
        tag_list   = G[u][v].get("tag_list",   [G[u][v].get("tag", "common")])
        rads       = _edge_rads(u, v, pos, len(label_list))
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        for lbl, tag, rad in zip(label_list, tag_list, rads):
            color = _EDGE_COLOURS.get(tag, "#2c3e50")
            col_dist = abs(x2 - x1) / 2.5
            if col_dist > 3:
                eff_rad = 0.0
            elif y2 > y1 + 1:
                eff_rad = 0.2
            elif y2 < y1 - 1:
                eff_rad = -0.2
            else:
                eff_rad = rad
            nx.draw_networkx_edges(
                G, pos, ax=ax, edgelist=[(u, v)],
                edge_color=[color],
                arrows=True, arrowstyle="-|>", arrowsize=18,
                width=2.0,
                connectionstyle=f"arc3,rad={eff_rad}",
                min_source_margin=26, min_target_margin=26,
            )
            if lbl:
                lx, ly = _arc_label_pos(x1, y1, x2, y2, eff_rad)
                edge_label_annotations.append((lx, ly, lbl))

    # ── Nodes ─────────────────────────────────────────────────────────────────
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_color_map,
        node_size=1600, alpha=0.95,
    )
    nx.draw_networkx_labels(
        G, pos, ax=ax,
        labels=node_labels,
        font_size=7, font_color="white", font_weight="bold",
    )

    # ── Edge labels placed on the arc (not on the chord) ─────────────────────
    for lx, ly, lbl in edge_label_annotations:
        ax.text(lx, ly, lbl,
                fontsize=7, color="#1a1a1a", ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.80, ec="none"),
                clip_on=False)

    # ── AoA annotation ────────────────────────────────────────────────────────
    ax.annotate(
        "AoA PERT notation:\n"
        "• Dashed arcs = dummy dependency (zero duration)\n"
        "• Grey split nodes  = fan-out: one activity → multiple paths\n"
        "• Grey merge nodes = fan-in:  multiple paths → one activity",
        xy=(0.01, 0.03), xycoords="axes fraction",
        fontsize=7.5, color="#555",
        bbox=dict(boxstyle="round,pad=0.4", fc="#fffde7", alpha=0.85, ec="#cccc99"),
    )

    # ── Dynamic legend: only tags present in this graph ───────────────────────
    seen_tags: set = set()
    for u, v in G.edges():
        if not G[u][v].get("dummy", False):
            for tag in G[u][v].get("tag_list", [G[u][v].get("tag", "common")]):
                seen_tags.add(tag)

    legend_handles = [
        mpatches.Patch(color="#2ecc71", label="Start event"),
        mpatches.Patch(color="#e74c3c", label="End event"),
        mpatches.Patch(color="#3498db", label="Intermediate event (alpha place)"),
        mpatches.Patch(color="#95a5a6", label="Split / Merge event node"),
    ]
    for tag in sorted(seen_tags):
        legend_handles.append(
            mpatches.Patch(color=_EDGE_COLOURS.get(tag, "#999"),
                           label=_TAG_LABELS.get(tag, f"Path: {tag}"))
        )
    ax.legend(handles=legend_handles, loc="upper right", fontsize=8.5, framealpha=0.9)

    # ── Title ─────────────────────────────────────────────────────────────────
    total_nodes = n_places + 2 + n_split + n_merge
    ax.set_title(
        f"Event Network Diagram (PERT Chart) — Fully derived from Alpha Algorithm output\n"
        f"{n_places} alpha places + {n_split} split + {n_merge} merge → "
        f"{total_nodes} event nodes | "
        "van der Aalst (2004) | CSE346 Business Process Modeling, Spring 2026",
        fontsize=12, fontweight="bold", pad=14,
    )
    ax.axis("off")
    plt.tight_layout()

    fig.savefig(output_png, dpi=300, bbox_inches="tight")
    fig.savefig(output_pdf, bbox_inches="tight")
    plt.close(fig)
    print(f"  [Saved] {output_png}")
    print(f"  [Saved] {output_pdf}")


def _draw_standalone(output_png, output_pdf):
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.text(0.5, 0.5,
            "Run via main.py or automation.py to generate\n"
            "the full algorithm-derived PERT chart.",
            ha="center", va="center", fontsize=12)
    ax.axis("off")
    fig.savefig(output_png, dpi=150, bbox_inches="tight")
    fig.savefig(output_pdf, bbox_inches="tight")
    plt.close(fig)
    print(f"  [Saved] {output_png}  (standalone placeholder)")
    print(f"  [Saved] {output_pdf}")


if __name__ == "__main__":
    draw_pert_chart()
