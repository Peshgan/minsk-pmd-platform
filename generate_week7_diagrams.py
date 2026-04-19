"""
Week 7 — remaining A1 diagrams:
  docs/ingestion_nmea.svg     — Diagram 2: Ingestion + NMEA/GPX parsing
  docs/algo_c_heatmap.svg     — Diagram 6: Algorithm C heat-map compositor
  docs/dashboard_wireframe.svg— Diagram 8: CUP dashboard wireframes
"""

import os
import graphviz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

GRAPHVIZ_BIN = r"C:\Program Files\Graphviz\bin"
os.environ["PATH"] = GRAPHVIZ_BIN + os.pathsep + os.environ.get("PATH", "")

OUT = os.path.join(os.path.dirname(__file__), "docs")
os.makedirs(OUT, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM 2 — Ingestion Layer + NMEA/GPX parsing pipeline
# ══════════════════════════════════════════════════════════════════════════════

nmea_dot = r"""
digraph Ingestion {
    graph [
        rankdir  = LR  fontname="Arial"  fontsize=12
        bgcolor  = "#0f1117"  pad=0.8  nodesep=0.55  ranksep=1.0
        label    = "\nАРХИТЕКТУРА УРОВНЯ ИНГЕСТА ДАННЫХ И РАЗБОР ПРОТОКОЛОВ NMEA/GPX\n(Диаграмма 2 из 9)"
        labelloc = t  fontcolor="#e2e8f0"  fontsize=16
        splines  = polyline
    ]
    node [fontname="Arial" fontsize=10 style="filled,rounded" margin="0.18,0.12"]
    edge [fontname="Arial" fontsize=9 color="#94a3b8" fontcolor="#94a3b8" penwidth=1.4 arrowsize=0.7]

    // ── Source devices ─────────────────────────────────────────────────────

    subgraph cluster_sources {
        label="ИСТОЧНИКИ ДАННЫХ"
        style="filled,rounded"  fillcolor="#1c1917"  color="#78716c"
        fontcolor="#d6d3d1"  fontsize=11  margin=16

        gps_hw [label="GPS-модуль\n(u-blox NEO-M9N)\n1 Гц, NMEA 0183"
                fillcolor="#374151" fontcolor="#f9fafb" color="#6b7280" shape=box]

        mobile [label="Мобильное приложение\n(Bolt / Whoosh)\nGPX-трек поездки"
                fillcolor="#374151" fontcolor="#f9fafb" color="#6b7280" shape=box]

        mds_src[label="MDS Provider API\n(REST, poll 1 мин)\nJSON GeoJSON LineString"
                fillcolor="#374151" fontcolor="#f9fafb" color="#6b7280" shape=box]
    }

    // ── NMEA parsing cluster ───────────────────────────────────────────────

    subgraph cluster_nmea {
        label="РАЗБОР NMEA 0183"
        style="filled,rounded"  fillcolor="#1e3a5f"  color="#2563eb"
        fontcolor="#93c5fd"  fontsize=11  margin=16

        nmea_recv [label="NMEA-приёмник\n(serial / TCP)"
                   fillcolor="#1d4ed8" fontcolor="#eff6ff" color="#60a5fa"]

        nmea_split[label="Разбивка по типу предложения:\n$GPGGA — позиция + высота\n$GPRMC — позиция + скорость\n$GPVTG — курс + скорость"
                   fillcolor="#1e40af" fontcolor="#eff6ff" color="#3b82f6" width=2.8]

        gga [label="GGA parser\nlat/lon (DDMM.MMMMM)\nalt, fix quality, HDOP"
             fillcolor="#1e3a8a" fontcolor="#bfdbfe" color="#60a5fa"]

        rmc [label="RMC parser\nlat/lon + speed (knots)\ncourse, date/time UTC"
             fillcolor="#1e3a8a" fontcolor="#bfdbfe" color="#60a5fa"]

        vtg [label="VTG parser\ncourse (true/mag)\nspeed km/h + knots"
             fillcolor="#1e3a8a" fontcolor="#bfdbfe" color="#60a5fa"]

        nmea_checksum [label="Контрольная сумма XOR\n$GP...* HH\nОтклонение -> DROP"
                       shape=diamond fillcolor="#312e81" fontcolor="#c7d2fe" color="#6366f1" width=2.0]

        coord_conv [label="Конвертация координат\nDDMM.MMMMM -> DD.DDDDDD\nlat = D + M/60\nlon = D + M/60"
                    fillcolor="#1d4ed8" fontcolor="#eff6ff" color="#60a5fa" width=2.4]
    }

    // ── GPX parsing cluster ────────────────────────────────────────────────

    subgraph cluster_gpx {
        label="РАЗБОР GPX 1.1 (XML)"
        style="filled,rounded"  fillcolor="#2e1065"  color="#7c3aed"
        fontcolor="#c4b5fd"  fontsize=11  margin=14

        gpx_parse [label="XML SAX-парсер\n<trkpt lat=.. lon=..>\n  <ele>, <time>"
                   fillcolor="#5b21b6" fontcolor="#ede9fe" color="#a78bfa" width=2.4]

        gpx_resamp[label="Ресемплинг до 1 Гц\n(линейная интерполяция\nпо временным меткам)"
                   fillcolor="#4c1d95" fontcolor="#ddd6fe" color="#7c3aed"]
    }

    // ── MDS / normalization ────────────────────────────────────────────────

    subgraph cluster_mds {
        label="MDS ADAPTER (REST)"
        style="filled,rounded"  fillcolor="#052e16"  color="#059669"
        fontcolor="#6ee7b7"  fontsize=11  margin=14

        mds_poll [label="HTTP GET\n/trips?start_time=&end_time=\npoll interval: 60 s"
                  fillcolor="#065f46" fontcolor="#d1fae5" color="#34d399"]

        mds_parse[label="GeoJSON LineString\n-> coordinates[][]\n-> timestamps[]"
                  fillcolor="#064e3b" fontcolor="#d1fae5" color="#10b981"]
    }

    // ── Normalization pipeline ─────────────────────────────────────────────

    subgraph cluster_norm {
        label="НОРМАЛИЗАЦИЯ И ВАЛИДАЦИЯ"
        style="filled,rounded"  fillcolor="#1e3a5f"  color="#2563eb"
        fontcolor="#93c5fd"  fontsize=11  margin=14

        wgs84  [label="Приведение к WGS-84\n(EPSG:4326)"
                fillcolor="#1d4ed8" fontcolor="#eff6ff" color="#60a5fa"]

        valid  [label="Валидация:\n|lat| <= 90, |lon| <= 180\ndt > 0, speed < 50 м/с\nHDOP < 5 (только NMEA)"
                shape=diamond fillcolor="#312e81" fontcolor="#c7d2fe" color="#6366f1" width=2.4]

        drop   [label="DROP\n(некорректная точка)"
                fillcolor="#7f1d1d" fontcolor="#fecaca" color="#ef4444"]

        schema [label="Унифицированная схема:\n{\n  trip_id, lon, lat,\n  timestamp_s (Unix),\n  speed_ms, source\n}"
                fillcolor="#1e3a8a" fontcolor="#bfdbfe" color="#3b82f6" width=2.6]
    }

    // ── Output ─────────────────────────────────────────────────────────────

    mqtt_out [label="MQTT Broker\n(Mosquitto)\nTopic: pmd/telemetry"
              shape=cylinder fillcolor="#78350f" fontcolor="#fde68a" color="#f59e0b"]

    kafka_out[label="Apache Kafka\nTopic: pmd-raw-telemetry"
              shape=cylinder fillcolor="#3730a3" fontcolor="#e0e7ff" color="#818cf8"]

    // ── Edges ─────────────────────────────────────────────────────────────

    gps_hw  -> nmea_recv [label="RS-232\n/ TCP"]
    nmea_recv -> nmea_split
    nmea_split -> gga
    nmea_split -> rmc
    nmea_split -> vtg
    gga -> nmea_checksum
    rmc -> nmea_checksum
    vtg -> nmea_checksum
    nmea_checksum -> coord_conv [label="OK"]
    nmea_checksum -> drop [label="FAIL"]
    coord_conv -> wgs84

    mobile  -> gpx_parse [label="GPX XML\nfile / stream"]
    gpx_parse -> gpx_resamp -> wgs84

    mds_src -> mds_poll [label="HTTPS"]
    mds_poll -> mds_parse -> wgs84

    wgs84 -> valid
    valid -> schema [label="OK"]
    valid -> drop   [label="FAIL"]

    schema -> mqtt_out  [label="IoT path"]
    schema -> kafka_out [label="API path"]

    // NMEA sentence reference note
    nmea_ref [
        label="NMEA 0183 — пример:\n$GPRMC,123519,A,4807.038,N\n,01131.000,E,022.4,084.4\n,230394,003.1,W*6A\n──────────────────────\nПоля:\n  UTC=12:35:19\n  lat=48.1173N\n  lon=11.5167E\n  speed=22.4 уз=11.5 м/с\n  course=84.4°\n  date=23.03.94"
        shape=note fillcolor="#1e1b4b" fontcolor="#a5b4fc" color="#6366f1" fontsize=9
    ]
}
"""

graphviz.Source(nmea_dot, format="svg").render(
    outfile=os.path.join(OUT, "ingestion_nmea.svg"), cleanup=True, quiet=False)
print("Saved: docs/ingestion_nmea.svg")


# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM 6 — Algorithm C: Safety Heat-Map Compositor
# ══════════════════════════════════════════════════════════════════════════════

algoc_dot = r"""
digraph AlgoC {
    graph [
        rankdir  = TB  fontname="Arial"  fontsize=12
        bgcolor  = "#0f1117"  pad=0.8  nodesep=0.55  ranksep=0.7
        label    = "\nАЛГОРИТМ C — КОМПОНОВЩИК СВОДНОЙ ТЕПЛОВОЙ КАРТЫ БЕЗОПАСНОСТИ\n(Диаграмма 6 из 9)"
        labelloc = t  fontcolor="#e2e8f0"  fontsize=16
    ]
    node [fontname="Arial" fontsize=10 style="filled,rounded" margin="0.18,0.12"]
    edge [fontname="Arial" fontsize=9 color="#94a3b8" fontcolor="#94a3b8" penwidth=1.5 arrowsize=0.8]

    // ── Inputs ────────────────────────────────────────────────────────────

    in_density [label="all_hexes.geojson\nКарта плотности (Алгоритм B)\n1 473 H3-ячейки\n{h3_cell, visit_count}"
                shape=parallelogram fillcolor="#1e3a5f" fontcolor="#93c5fd" color="#2563eb"]

    in_blind [label="blind_spots.geojson\nСлепые зоны (Алгоритм B)\n{h3_cell, severity, conflict_weight}"
              shape=parallelogram fillcolor="#7f1d1d" fontcolor="#fecaca" color="#ef4444"]

    in_danger[label="dangerous_segments.geojson\nОпасные сегменты (Алгоритм A)\n{trip_id, verdict, peak_accel, coords}"
              shape=parallelogram fillcolor="#78350f" fontcolor="#fde68a" color="#f59e0b"]

    // ── Phase 1: H3 aggregation of danger events ───────────────────────────

    ph1 [label="ФАЗ 1: H3-АГРЕГАЦИЯ ОПАСНЫХ СОБЫТИЙ"
         shape=box fillcolor="#1e1065" fontcolor="#a5b4fc" color="#4338ca" style="filled"]

    seg_to_h3 [label="Для каждого опасного сегмента:\n  для каждой координаты p сегмента:\n    cell = H3.latlng_to_cell(p, res=9)\n    danger_count[cell] += weight(verdict)"
               fillcolor="#3730a3" fontcolor="#e0e7ff" color="#818cf8" width=3.2]

    weight_def [label="weight(verdict):\n  DANGER -> 2.0\n  WARN   -> 1.0"
                shape=note fillcolor="#1e1b4b" fontcolor="#a5b4fc" color="#6366f1"]

    // ── Phase 2: normalization ─────────────────────────────────────────────

    ph2 [label="ФАЗ 2: НОРМАЛИЗАЦИЯ КОМПОНЕНТОВ [0, 1]"
         shape=box fillcolor="#1e1065" fontcolor="#a5b4fc" color="#4338ca" style="filled"]

    norm_density[label="S_density(c) = visit_count(c) / max(visit_count)\n-> [0.0 .. 1.0]"
                 fillcolor="#312e81" fontcolor="#c7d2fe" color="#6366f1" width=3.2]

    norm_blind  [label="S_blind(c) = severity(c) / max(severity)  если blind_spot\n             0.0                          иначе"
                 fillcolor="#4c1d95" fontcolor="#ddd6fe" color="#7c3aed" width=3.4]

    norm_danger [label="S_danger(c) = danger_count(c) / max(danger_count)\n-> [0.0 .. 1.0]"
                 fillcolor="#78350f" fontcolor="#fde68a" color="#f59e0b" width=3.2]

    // ── Phase 3: weighted composite ────────────────────────────────────────

    ph3 [label="ФАЗ 3: ВЗВЕШЕННАЯ СУПЕРПОЗИЦИЯ"
         shape=box fillcolor="#1e1065" fontcolor="#a5b4fc" color="#4338ca" style="filled"]

    formula [label="safety_risk(c) =\n  w1 * S_density(c) +\n  w2 * S_blind(c)   +\n  w3 * S_danger(c)\n────────────────────────\n  w1 = 0.30  (плотность трафика)\n  w2 = 0.45  (инфра-дефицит)  ← главный вес\n  w3 = 0.25  (зафиксированные события)"
             fillcolor="#5b21b6" fontcolor="#ede9fe" color="#a78bfa" width=3.4]

    check_w [label="sum(w1,w2,w3) == 1.0 ?" shape=diamond
             fillcolor="#4c1d95" fontcolor="#ddd6fe" color="#7c3aed" width=2.2]

    // ── Phase 4: classification ────────────────────────────────────────────

    ph4 [label="ФАЗ 4: КЛАССИФИКАЦИЯ ЯЧЕЕК ПО УРОВНЮ РИСКА"
         shape=box fillcolor="#1e1065" fontcolor="#a5b4fc" color="#4338ca" style="filled"]

    classify [label="risk_class(c):\n  safety_risk >= 0.75  ->  CRITICAL  (красный)\n  safety_risk >= 0.50  ->  HIGH      (оранжевый)\n  safety_risk >= 0.25  ->  MEDIUM    (жёлтый)\n  иначе                ->  LOW       (синий)"
              fillcolor="#5b21b6" fontcolor="#ede9fe" color="#a78bfa" width=3.6]

    // ── Output ─────────────────────────────────────────────────────────────

    out [label="safety_heatmap.geojson\n{h3_cell, safety_risk, risk_class,\n S_density, S_blind, S_danger}"
         shape=parallelogram fillcolor="#064e3b" fontcolor="#d1fae5" color="#34d399" width=3.4]

    dashboard_layer [label="H3HexagonLayer (deck.gl)\nЦвет  = risk_class\nВысота = safety_risk * 500 м"
                     shape=box fillcolor="#065f46" fontcolor="#d1fae5" color="#34d399" width=3.0]

    // ── Rationale note ─────────────────────────────────────────────────────

    rationale [
        label="Обоснование весов:\n──────────────────────\nw2 (инфра-дефицит) = 0.45:\nглавный вклад — системная проблема,\nне случайное событие.\n\nw1 (плотность) = 0.30:\nбольше трафика = больше риска\nдаже без событий.\n\nw3 (события) = 0.25:\nнаименьший вес — одиночные события\nмогут быть GPS-артефактами."
        shape=note fillcolor="#1e1b4b" fontcolor="#a5b4fc" color="#6366f1" fontsize=9
    ]

    // ── Edges ─────────────────────────────────────────────────────────────

    in_density -> ph1 [style=invis]
    in_danger  -> ph1
    ph1 -> seg_to_h3 -> ph2

    in_density -> norm_density
    in_blind   -> norm_blind
    seg_to_h3  -> norm_danger
    ph2 -> norm_density
    ph2 -> norm_blind
    ph2 -> norm_danger
    norm_density -> ph3
    norm_blind   -> ph3
    norm_danger  -> ph3
    ph3 -> formula -> check_w
    check_w -> ph4 [label="Да (всегда)"]
    ph4 -> classify -> out -> dashboard_layer
    weight_def -> seg_to_h3 [style=dashed color="#6366f1"]
    rationale -> formula [style=dashed color="#6366f1" arrowhead=none]
}
"""

graphviz.Source(algoc_dot, format="svg").render(
    outfile=os.path.join(OUT, "algo_c_heatmap.svg"), cleanup=True, quiet=False)
print("Saved: docs/algo_c_heatmap.svg")


# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM 8 — CUP Dashboard Wireframes (matplotlib)
# ══════════════════════════════════════════════════════════════════════════════

fig = plt.figure(figsize=(22, 13))
fig.patch.set_facecolor("#0f1117")

BG     = "#0f1117"
PANEL  = "#1a1d27"
BORDER = "#2d3148"
TEXT   = "#e2e8f0"
MUTED  = "#64748b"
BLUE   = "#3b82f6"
RED    = "#ef4444"
AMBER  = "#f59e0b"
GREEN  = "#10b981"
PURPLE = "#6366f1"

def box(ax, x, y, w, h, color=PANEL, border=BORDER, radius=0.01, lw=1.2, alpha=1.0):
    p = FancyBboxPatch((x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=color, edgecolor=border, linewidth=lw, alpha=alpha,
        transform=ax.transAxes, clip_on=False)
    ax.add_patch(p)
    return p

def label(ax, x, y, txt, size=9, color=TEXT, ha="left", va="center", bold=False):
    w = "bold" if bold else "normal"
    ax.text(x, y, txt, transform=ax.transAxes,
            fontsize=size, color=color, ha=ha, va=va, fontweight=w,
            fontfamily="monospace")

ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.axis("off")
ax.set_facecolor(BG)

# ── Title bar ──────────────────────────────────────────────────────────────
box(ax, 0.01, 0.91, 0.98, 0.07, color="#1a1d27", border=BORDER)
label(ax, 0.03, 0.946, "PMD Analytics Dashboard — Minsk", size=13, bold=True)
label(ax, 0.75, 0.946, "500 synthetic scooter trips  |  H3 res-9", size=9, color=MUTED)

# ── Map area ───────────────────────────────────────────────────────────────
box(ax, 0.01, 0.03, 0.72, 0.87, color="#141824", border=BORDER)

# Fake map grid lines
map_ax = ax
for i in np.linspace(0.03, 0.73, 9):
    ax.plot([i, i], [0.03, 0.90], color=BORDER, lw=0.4, transform=ax.transAxes)
for j in np.linspace(0.03, 0.90, 6):
    ax.plot([0.01, 0.73], [j, j], color=BORDER, lw=0.4, transform=ax.transAxes)

# Simulated H3 hexagons (density heatmap)
np.random.seed(42)
hex_x = np.random.uniform(0.06, 0.69, 40)
hex_y = np.random.uniform(0.07, 0.86, 40)
intensity = np.random.exponential(0.4, 40)
intensity = np.clip(intensity, 0, 1)
for hx, hy, iv in zip(hex_x, hex_y, intensity):
    size = 0.025 + iv * 0.02
    c_r = int(99 + 156 * iv); c_g = int(179 - 116 * iv); c_b = int(237 - 200 * iv)
    color_h = f"#{c_r:02x}{max(0,c_g):02x}{max(0,c_b):02x}"
    hex_patch = plt.Polygon(
        [(hx + size*np.cos(np.pi/6 + np.pi/3*k),
          hy + size*np.sin(np.pi/6 + np.pi/3*k)) for k in range(6)],
        transform=ax.transAxes, facecolor=color_h,
        edgecolor="#1a1d27", linewidth=0.5, alpha=0.75 + 0.25*iv)
    ax.add_patch(hex_patch)

# Top-3 blind spot hexes (red)
blind_x = [0.22, 0.45, 0.33]; blind_y = [0.55, 0.38, 0.72]
for i, (bx, by) in enumerate(zip(blind_x, blind_y)):
    sz = 0.038
    bp = plt.Polygon(
        [(bx + sz*np.cos(np.pi/6 + np.pi/3*k),
          by + sz*np.sin(np.pi/6 + np.pi/3*k)) for k in range(6)],
        transform=ax.transAxes, facecolor=RED,
        edgecolor="#ff6b6b", linewidth=1.5, alpha=0.85)
    ax.add_patch(bp)
    label(ax, bx, by, f"#{i+1}", size=7, color="white", ha="center", va="center")

# Dangerous segment paths
segs = [([0.15, 0.25, 0.32], [0.62, 0.58, 0.50]),
        ([0.40, 0.50, 0.55], [0.30, 0.28, 0.35]),
        ([0.55, 0.62, 0.68], [0.65, 0.60, 0.55])]
for seg_x, seg_y in segs:
    ax.plot(seg_x, seg_y, transform=ax.transAxes,
            color=RED, lw=2.5, alpha=0.9, solid_capstyle="round")

# Animated trip trails (blue)
for _ in range(12):
    tx = np.random.uniform(0.08, 0.68, 5)
    ty = np.random.uniform(0.08, 0.84, 5)
    tx.sort()
    ax.plot(tx, ty, transform=ax.transAxes,
            color=BLUE, lw=1.0, alpha=0.35, solid_capstyle="round")

# Scooter position dots
for _ in range(18):
    sx = np.random.uniform(0.08, 0.68)
    sy = np.random.uniform(0.08, 0.84)
    ax.plot(sx, sy, "o", transform=ax.transAxes,
            color=BLUE, markersize=3.5, alpha=0.8)

# Deck.gl attribution
label(ax, 0.03, 0.042, "deck.gl 9  +  MapLibre GL JS  +  CartoDB Dark Matter",
      size=7, color=MUTED)

# ── Playback bar ───────────────────────────────────────────────────────────
box(ax, 0.18, 0.045, 0.36, 0.038, color="#1a1d27cc", border=BORDER, radius=0.02)
# Play button
play_circle = plt.Circle((0.205, 0.064), 0.012, transform=ax.transAxes,
                          facecolor=PURPLE, edgecolor="none")
ax.add_patch(play_circle)
ax.text(0.205, 0.064, "▶", transform=ax.transAxes,
        fontsize=7, color="white", ha="center", va="center")
# Progress bar bg
box(ax, 0.225, 0.060, 0.22, 0.008, color=BORDER, border=BORDER, radius=0.004)
# Progress fill (42%)
box(ax, 0.225, 0.060, 0.22*0.42, 0.008, color=PURPLE, border=PURPLE, radius=0.004)
label(ax, 0.455, 0.064, "582s", size=8, color=MUTED)

# ── Sidebar ────────────────────────────────────────────────────────────────
box(ax, 0.745, 0.03, 0.245, 0.87, color=PANEL, border=BORDER)

sy = 0.875

# Section: Layers
label(ax, 0.758, sy, "LAYERS", size=8, color=MUTED, bold=True); sy -= 0.035
layers = [
    (BLUE,   "Trip replay         ☑"),
    ("#4299e1","Density heatmap    ☑"),
    (RED,    "Blind spots (top10) ☑"),
    (AMBER,  "Dangerous segments  ☐"),
]
for col, txt in layers:
    ax.plot(0.762, sy, "s", transform=ax.transAxes,
            color=col, markersize=6, markeredgecolor="none")
    label(ax, 0.772, sy, txt, size=8, color=TEXT); sy -= 0.028
sy -= 0.008

# Divider
ax.plot([0.748, 0.988], [sy, sy], color=BORDER, lw=0.8, transform=ax.transAxes)
sy -= 0.02

# Section: Stats
label(ax, 0.758, sy, "STATS", size=8, color=MUTED, bold=True); sy -= 0.032
stats = [("500", "Total trips"), ("100", "Dangerous"), ("1 473", "H3 hexagons"), ("369", "Blind spots")]
for i, (val, lbl) in enumerate(stats):
    col = 0.755 + (i % 2) * 0.12
    row_y = sy - (i // 2) * 0.065
    box(ax, col, row_y - 0.045, 0.108, 0.058, color=BG, border=BORDER, radius=0.008)
    c = RED if lbl in ("Dangerous", "Blind spots") else TEXT
    label(ax, col + 0.054, row_y - 0.016, val, size=12, color=c, ha="center", bold=True)
    label(ax, col + 0.054, row_y - 0.036, lbl, size=7, color=MUTED, ha="center")
sy -= 0.145

# Divider
ax.plot([0.748, 0.988], [sy, sy], color=BORDER, lw=0.8, transform=ax.transAxes)
sy -= 0.022

# Section: Blind spot list
label(ax, 0.758, sy, "TOP-10 BLIND SPOTS", size=8, color=MUTED, bold=True); sy -= 0.030
blind_data = [
    ("#1", "Sev 2963", "2469 visits · CW 1.2"),
    ("#2", "Sev 2736", "2280 visits · CW 1.2"),
    ("#3", "Sev 2415", "1610 visits · CW 1.5"),
    ("#4", "Sev 2056", "1713 visits · CW 1.2"),
    ("#5", "Sev 1916", "1597 visits · CW 1.2"),
]
for rank, sev, meta in blind_data:
    is_sel = rank == "#1"
    bc = "#1e1f3a" if is_sel else BG
    bc_edge = PURPLE if is_sel else BORDER
    box(ax, 0.752, sy - 0.048, 0.232, 0.052,
        color=bc, border=bc_edge, radius=0.008, lw=1.5 if is_sel else 1.0)
    label(ax, 0.760, sy - 0.018, rank, size=7, color=MUTED)
    label(ax, 0.760, sy - 0.033, sev, size=9, color=RED, bold=True)
    label(ax, 0.870, sy - 0.033, meta, size=7, color=MUTED)
    sy -= 0.058

sy -= 0.005
# Divider
ax.plot([0.748, 0.988], [sy, sy], color=BORDER, lw=0.8, transform=ax.transAxes)
sy -= 0.022

# Section: Legend
label(ax, 0.758, sy, "LEGEND", size=8, color=MUTED, bold=True); sy -= 0.028
legend_items = [
    (BLUE,   "Safe trip trail"),
    (RED,    "Dangerous trip trail"),
    ("#4299e1", "Visit density"),
    (RED,    "Blind spot severity"),
    (RED,    "DANGER segment"),
    (AMBER,  "WARN segment"),
]
for col, lbl in legend_items:
    box(ax, 0.758, sy - 0.007, 0.032, 0.010, color=col, border=col, radius=0.003)
    label(ax, 0.798, sy - 0.002, lbl, size=8, color=TEXT)
    sy -= 0.024

# ── Figure title ───────────────────────────────────────────────────────────
fig.text(0.5, 0.99,
    "ЦУП-ДАШБОРД: МАКЕТ ПОЛЬЗОВАТЕЛЬСКОГО ИНТЕРФЕЙСА ПЛАТФОРМЫ ГЕОАНАЛИТИКИ ПМД\n"
    "Диаграмма 8 из 9  |  React 18 + deck.gl 9 + MapLibre GL JS  |  БНТУ, Факультет АТФ",
    ha="center", va="top", fontsize=12, fontweight="bold", color=TEXT,
    fontfamily="monospace")

plt.tight_layout(rect=[0, 0, 1, 0.97])
fig.savefig(os.path.join(OUT, "dashboard_wireframe.svg"),
            format="svg", bbox_inches="tight", dpi=150)
plt.close()
print("Saved: docs/dashboard_wireframe.svg")
