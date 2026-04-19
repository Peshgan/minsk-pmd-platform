"""
Generate two A1 algorithm diagrams:
  docs/algo_a_flowchart.svg  — Diagram 4: Algorithm A dangerous driving detector
  docs/algo_b_flowchart.svg  — Diagram 5: Algorithm B blind spot classifier
"""

import os
import graphviz

GRAPHVIZ_BIN = r"C:\Program Files\Graphviz\bin"
os.environ["PATH"] = GRAPHVIZ_BIN + os.pathsep + os.environ.get("PATH", "")

OUT_DIR = os.path.join(os.path.dirname(__file__), "docs")
os.makedirs(OUT_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM 4 — Algorithm A: Dangerous Driving Detector
# ══════════════════════════════════════════════════════════════════════════════

algo_a_dot = r"""
digraph AlgoA {
    graph [
        rankdir  = TB
        fontname = "Arial"
        fontsize = 13
        bgcolor  = "#0f1117"
        pad      = 0.7
        nodesep  = 0.5
        ranksep  = 0.6
        label    = "\nАЛГОРИТМ A — ДЕТЕКТОР ОПАСНОГО ВОЖДЕНИЯ\n(Диаграмма 4 из 9)"
        labelloc = t
        fontcolor = "#e2e8f0"
        fontsize = 17
    ]
    node [fontname="Arial" fontsize=11 style="filled,rounded" margin="0.18,0.12"]
    edge [fontname="Arial" fontsize=10 color="#94a3b8" fontcolor="#94a3b8" penwidth=1.5 arrowsize=0.8]

    // ── Input ──────────────────────────────────────────────────────────────

    start [label="НАЧАЛО\nПоездка загружена" shape=oval
           fillcolor="#1e3a5f" fontcolor="#93c5fd" color="#2563eb"]

    input [label="coords[] — координаты (lon, lat)\ntimestamps[] — метки времени (1 Гц)"
           shape=parallelogram fillcolor="#1e3a8a" fontcolor="#bfdbfe" color="#3b82f6"]

    init [label="speeds[0] ← 0.0\naccels[0] ← 0.0\ni ← 1"
          fillcolor="#1e3a8a" fontcolor="#bfdbfe" color="#3b82f6"]

    // ── Step 1: Kinematics loop ────────────────────────────────────────────

    loop1 [label="i < N ?" shape=diamond
           fillcolor="#312e81" fontcolor="#c7d2fe" color="#6366f1" width=1.5]

    haversine [label="dist ← haversine(coords[i-1], coords[i])\ndt ← timestamps[i] − timestamps[i-1]"
               fillcolor="#3730a3" fontcolor="#e0e7ff" color="#818cf8"]

    speed [label="speeds[i] ← dist / dt\naccels[i] ← (speeds[i] − speeds[i-1]) / dt"
           fillcolor="#3730a3" fontcolor="#e0e7ff" color="#818cf8"]

    inc1 [label="i ← i + 1" fillcolor="#312e81" fontcolor="#c7d2fe" color="#6366f1" shape=box]

    // ── Step 2: Classification loop ────────────────────────────────────────

    init2 [label="labels[] ← ['SAFE'] × N\nj ← 0"
           fillcolor="#1e3a8a" fontcolor="#bfdbfe" color="#3b82f6"]

    loop2 [label="j < N ?" shape=diamond
           fillcolor="#312e81" fontcolor="#c7d2fe" color="#6366f1" width=1.5]

    check_danger [label="|accels[j]| ≥ 3.5 м/с² ?" shape=diamond
                  fillcolor="#4c1d95" fontcolor="#ddd6fe" color="#7c3aed" width=2.2]

    window [label="prev_high ← (j>0) И (|a[j-1]|≥3.5)\nnext_high ← (j<N-1) И (|a[j+1]|≥3.5)"
            fillcolor="#5b21b6" fontcolor="#ede9fe" color="#a78bfa"]

    check_window [label="prev_high ИЛИ next_high ?" shape=diamond
                  fillcolor="#4c1d95" fontcolor="#ddd6fe" color="#7c3aed" width=2.2]

    set_danger [label="labels[j] ← DANGER\n(2+ смежных выброса)" shape=box
                fillcolor="#7f1d1d" fontcolor="#fecaca" color="#ef4444"]

    set_warn_single [label="labels[j] ← WARN\n(одиночный шумовой выброс)" shape=box
                     fillcolor="#78350f" fontcolor="#fde68a" color="#f59e0b"]

    check_warn [label="|accels[j]| ≥ 2.5 м/с² ?" shape=diamond
                fillcolor="#4c1d95" fontcolor="#ddd6fe" color="#7c3aed" width=2.2]

    set_warn [label="labels[j] ← WARN" shape=box
              fillcolor="#78350f" fontcolor="#fde68a" color="#f59e0b"]

    // safe stays SAFE
    inc2 [label="j ← j + 1" fillcolor="#312e81" fontcolor="#c7d2fe" color="#6366f1" shape=box]

    // ── Step 3: Trip verdict ───────────────────────────────────────────────

    verdict_danger [label="∃ label = DANGER ?" shape=diamond
                    fillcolor="#4c1d95" fontcolor="#ddd6fe" color="#7c3aed" width=2.2]

    verdict_warn [label="∃ label = WARN ?" shape=diamond
                  fillcolor="#4c1d95" fontcolor="#ddd6fe" color="#7c3aed" width=2.2]

    out_danger [label="verdict ← DANGER\nПоездка опасна" shape=parallelogram
                fillcolor="#7f1d1d" fontcolor="#fecaca" color="#ef4444"]

    out_warn [label="verdict ← WARN\nПоездка под наблюдением" shape=parallelogram
              fillcolor="#78350f" fontcolor="#fde68a" color="#f59e0b"]

    out_safe [label="verdict ← SAFE\nПоездка безопасна" shape=parallelogram
              fillcolor="#064e3b" fontcolor="#d1fae5" color="#34d399"]

    export [label="Экспорт: GeoJSON с тегами\nanalyzed_trips.geojson\ndangerous_segments.geojson"
            shape=parallelogram fillcolor="#1e3a5f" fontcolor="#93c5fd" color="#2563eb"]

    end [label="КОНЕЦ" shape=oval fillcolor="#1e3a5f" fontcolor="#93c5fd" color="#2563eb"]

    // ── Calibration note ───────────────────────────────────────────────────

    note [label="Калибровка порога 3.5 м/с²:\nDozza M. (2013)\n«Naturalistic bicycle riding study»\nISO 15622 (системы предупреждения)\nF1-score = 0.990 на 500 поездках"
          shape=note fillcolor="#1e1b4b" fontcolor="#a5b4fc" color="#6366f1"]

    // ── Edges ─────────────────────────────────────────────────────────────

    start -> input -> init -> loop1

    loop1 -> haversine [label="Да"]
    loop1 -> init2 [label="Нет"]
    haversine -> speed -> inc1 -> loop1

    init2 -> loop2
    loop2 -> check_danger [label="Да"]
    loop2 -> verdict_danger [label="Нет"]
    check_danger -> window [label="Да"]
    check_danger -> check_warn [label="Нет"]
    window -> check_window
    check_window -> set_danger [label="Да"]
    check_window -> set_warn_single [label="Нет"]
    check_warn -> set_warn [label="Да"]
    set_danger -> inc2
    set_warn_single -> inc2
    set_warn -> inc2
    check_warn -> inc2 [label="Нет (SAFE)"]
    inc2 -> loop2

    verdict_danger -> out_danger [label="Да"]
    verdict_danger -> verdict_warn [label="Нет"]
    verdict_warn -> out_warn [label="Да"]
    verdict_warn -> out_safe [label="Нет"]

    out_danger -> export
    out_warn -> export
    out_safe -> export
    export -> end

    note [pos="8,0!"]
}
"""

src_a = graphviz.Source(algo_a_dot, format="svg")
src_a.render(outfile=os.path.join(OUT_DIR, "algo_a_flowchart.svg"), cleanup=True, quiet=False)
print("Saved: docs/algo_a_flowchart.svg")


# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM 5 — Algorithm B: Blind Spot Classifier
# ══════════════════════════════════════════════════════════════════════════════

algo_b_dot = r"""
digraph AlgoB {
    graph [
        rankdir  = TB
        fontname = "Arial"
        fontsize = 13
        bgcolor  = "#0f1117"
        pad      = 0.7
        nodesep  = 0.5
        ranksep  = 0.65
        label    = "\nАЛГОРИТМ B — КЛАССИФИКАТОР СЛЕПЫХ ЗОН\n(Диаграмма 5 из 9)"
        labelloc = t
        fontcolor = "#e2e8f0"
        fontsize = 17
    ]
    node [fontname="Arial" fontsize=11 style="filled,rounded" margin="0.18,0.12"]
    edge [fontname="Arial" fontsize=10 color="#94a3b8" fontcolor="#94a3b8" penwidth=1.5 arrowsize=0.8]

    // ── Inputs ────────────────────────────────────────────────────────────

    start [label="НАЧАЛО" shape=oval fillcolor="#2e1065" fontcolor="#c4b5fd" color="#7c3aed"]

    in_trips [label="trips.geojson\n500 поездок, 365 925 GPS-точек"
              shape=parallelogram fillcolor="#3b0764" fontcolor="#c4b5fd" color="#7c3aed"]

    in_osm [label="minsk.graphml\n(OSM граф дорог)\n13 696 рёбер"
            shape=cylinder fillcolor="#374151" fontcolor="#f9fafb" color="#6b7280"]

    // ── Phase 1: Density map ───────────────────────────────────────────────

    ph1 [label="ФАЗ 1: ПОСТРОЕНИЕ КАРТЫ ПЛОТНОСТИ"
         shape=box fillcolor="#1e1065" fontcolor="#a5b4fc" color="#4338ca" style="filled"]

    loop_trips [label="Для каждой поездки\n∀ GPS-точки p:" shape=box
                fillcolor="#312e81" fontcolor="#c7d2fe" color="#6366f1"]

    h3cell [label="cell ← H3.latlng_to_cell\n(p.lat, p.lon, resolution=9)\ndensity[cell] += 1"
            fillcolor="#3730a3" fontcolor="#e0e7ff" color="#818cf8"]

    density_result [label="density: Dict[h3_cell → visit_count]\n1 473 уникальных ячеек\nMaximum: 2 469 визитов"
                    shape=parallelogram fillcolor="#312e81" fontcolor="#c7d2fe" color="#6366f1"]

    // ── Phase 2: P75 filter ────────────────────────────────────────────────

    ph2 [label="ФАЗ 2: ФИЛЬТРАЦИЯ ПО P75"
         shape=box fillcolor="#1e1065" fontcolor="#a5b4fc" color="#4338ca" style="filled"]

    p75 [label="threshold ← percentile(density.values(), 75)\nthreshold = 334 визита"
         fillcolor="#3730a3" fontcolor="#e0e7ff" color="#818cf8"]

    filter_cells [label="candidates ← {c: d | d ≥ threshold}\n369 высоконагруженных ячеек" shape=box
                  fillcolor="#3730a3" fontcolor="#e0e7ff" color="#818cf8"]

    build_gdf [label="hex_gdf ← GeoDataFrame(\n  [H3.cell_to_polygon(c) for c in candidates]\n)\nCRS: EPSG:4326"
               fillcolor="#312e81" fontcolor="#c7d2fe" color="#6366f1"]

    // ── Phase 3: Spatial join ──────────────────────────────────────────────

    ph3 [label="ФАЗ 3: ПРОСТРАНСТВЕННОЕ СОЕДИНЕНИЕ С OSM"
         shape=box fillcolor="#1e1065" fontcolor="#a5b4fc" color="#4338ca" style="filled"]

    load_edges [label="edges_gdf ← ox.graph_to_gdfs(G)\nПарсинг: maxspeed → maxspeed_kmh\nhighway → conflict_weight\ncycleway:* → has_infra"
                fillcolor="#374151" fontcolor="#f9fafb" color="#6b7280"]

    sjoin [label="joined ← gpd.sjoin(\n  hex_gdf, edges_gdf,\n  how='left',\n  predicate='intersects'\n)"
           fillcolor="#3730a3" fontcolor="#e0e7ff" color="#818cf8"]

    // ── Phase 4: Classify ──────────────────────────────────────────────────

    ph4 [label="ФАЗ 4: КЛАССИФИКАЦИЯ И РАНЖИРОВАНИЕ"
         shape=box fillcolor="#1e1065" fontcolor="#a5b4fc" color="#4338ca" style="filled"]

    agg [label="Для каждой ячейки c в joined.groupby('h3_cell'):\n  infra_score ← any(has_infra)\n  dom_weight ← max(conflict_weight)"
         fillcolor="#5b21b6" fontcolor="#ede9fe" color="#a78bfa"]

    severity [label="severity(c) = density(c) × dom_weight\nis_blind_spot = (infra_score == 0)"
              fillcolor="#5b21b6" fontcolor="#ede9fe" color="#a78bfa"]

    check_blind [label="is_blind_spot == True ?" shape=diamond
                 fillcolor="#4c1d95" fontcolor="#ddd6fe" color="#7c3aed" width=2.2]

    // ── Output ────────────────────────────────────────────────────────────

    add_blind [label="Добавить в blind_spots[]\n369 слепых зон обнаружено" shape=box
               fillcolor="#7f1d1d" fontcolor="#fecaca" color="#ef4444"]

    skip [label="Пропустить\n(есть инфраструктура)" shape=box
          fillcolor="#064e3b" fontcolor="#d1fae5" color="#34d399"]

    rank [label="Сортировка по severity DESC\nВыбор TOP_N = 10"
          fillcolor="#5b21b6" fontcolor="#ede9fe" color="#a78bfa"]

    export_blind [label="blind_spots.geojson — топ-10 зон\nall_hexes.geojson — все 1 473 ячейки"
                  shape=parallelogram fillcolor="#3b0764" fontcolor="#c4b5fd" color="#7c3aed"]

    end [label="КОНЕЦ" shape=oval fillcolor="#2e1065" fontcolor="#c4b5fd" color="#7c3aed"]

    // ── Conflict weight note ───────────────────────────────────────────────

    cw_table [label="conflict_weight (wc):\n──────────────────────\nmaxspeed > 60 км/ч  → 1.5\nmaxspeed 40–60 км/ч → 1.2\nresidential / без тега → 1.0\n──────────────────────\nH3 resolution 9:\nребро ≈ 174 м\nплощадь ≈ 0.105 км²"
              shape=note fillcolor="#1e1b4b" fontcolor="#a5b4fc" color="#6366f1"]

    results_note [label="Результаты (Минск, 500 поездок):\n──────────────────────────────\nВсего ячеек:     1 473\nПорог P75:         334 визита\nВысоконагруж.:     369\nСлепых зон:        369 (100%)\nTop-1 severity: 2 963\n(2 469 визитов × CW 1.2)"
                  shape=note fillcolor="#1e1b4b" fontcolor="#a5b4fc" color="#6366f1"]

    // ── Edges ─────────────────────────────────────────────────────────────

    start -> in_trips
    in_trips -> ph1 -> loop_trips -> h3cell -> density_result
    density_result -> ph2 -> p75 -> filter_cells -> build_gdf
    in_osm -> load_edges
    build_gdf -> ph3
    ph3 -> load_edges -> sjoin
    sjoin -> ph4 -> agg -> severity -> check_blind
    check_blind -> add_blind [label="Да"]
    check_blind -> skip [label="Нет"]
    add_blind -> rank
    skip -> rank
    rank -> export_blind -> end
}
"""

src_b = graphviz.Source(algo_b_dot, format="svg")
src_b.render(outfile=os.path.join(OUT_DIR, "algo_b_flowchart.svg"), cleanup=True, quiet=False)
print("Saved: docs/algo_b_flowchart.svg")
