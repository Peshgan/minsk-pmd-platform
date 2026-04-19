"""
Generate functional_schema_A1.svg — functional diagram of the PMD geoanalytics platform.
Three swim-lane clusters (LR), Cyrillic labels, A1-proportioned output.
"""

import os
import sys

# Add Graphviz bin to PATH before importing graphviz package
GRAPHVIZ_BIN = r"C:\Program Files\Graphviz\bin"
os.environ["PATH"] = GRAPHVIZ_BIN + os.pathsep + os.environ.get("PATH", "")

import graphviz

DOT_PATH = os.path.join(GRAPHVIZ_BIN, "dot.exe")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "docs")
OUT_NAME = "functional_schema_A1"

os.makedirs(OUT_DIR, exist_ok=True)

# ── DOT source ─────────────────────────────────────────────────────────────────

dot_source = r"""
digraph PMD_Platform {

    // Global graph settings
    graph [
        rankdir   = LR
        fontname  = "Arial"
        fontsize  = 13
        splines   = ortho
        nodesep   = 0.5
        ranksep   = 1.2
        bgcolor   = "#0f1117"
        pad       = 0.6
        label     = "\nФУНКЦИОНАЛЬНАЯ СХЕМА ПЛАТФОРМЫ ГЕОАНАЛИТИКИ ПМД\n(БНТУ, Факультет АТФ)"
        labelloc  = t
        labeljust = c
        fontcolor = "#e2e8f0"
        fontsize  = 18
    ]

    node [
        fontname  = "Arial"
        fontsize  = 11
        style     = "filled,rounded"
        shape     = box
        margin    = "0.2,0.12"
    ]

    edge [
        fontname  = "Arial"
        fontsize  = 10
        color     = "#94a3b8"
        fontcolor = "#94a3b8"
        penwidth  = 1.5
        arrowsize = 0.8
    ]

    // ── External actors ────────────────────────────────────────────────────────

    operator [
        label     = "Оператор\nшеринга\n(Bolt / Whoosh)"
        shape     = box
        style     = "filled,rounded"
        fillcolor = "#374151"
        fontcolor = "#f9fafb"
        color     = "#6b7280"
        width     = 1.6
    ]

    iot [
        label     = "IoT-устройство\n(GPS-модуль)"
        shape     = box
        style     = "filled,rounded"
        fillcolor = "#374151"
        fontcolor = "#f9fafb"
        color     = "#6b7280"
        width     = 1.6
    ]

    osm [
        label     = "OpenStreetMap\n(граф дорог)"
        shape     = cylinder
        style     = "filled"
        fillcolor = "#374151"
        fontcolor = "#f9fafb"
        color     = "#6b7280"
        width     = 1.6
    ]

    cup_user [
        label     = "ЦУП-оператор\n(городская служба)"
        shape     = box
        style     = "filled,rounded"
        fillcolor = "#374151"
        fontcolor = "#f9fafb"
        color     = "#6b7280"
        width     = 1.6
    ]

    // ── CLUSTER 1: Data Layer ──────────────────────────────────────────────────

    subgraph cluster_data {
        label     = "УРОВЕНЬ 1: СБОР И НОРМАЛИЗАЦИЯ ДАННЫХ (Data Layer)"
        style     = "filled,rounded"
        fillcolor = "#1e3a5f"
        color     = "#2563eb"
        penwidth  = 2.5
        fontcolor = "#93c5fd"
        fontsize  = 12
        fontname  = "Arial Bold"
        margin    = 18

        mds [
            label     = "MDS Provider API\n(REST / HTTPS)\nJSON GeoJSON"
            fillcolor = "#1d4ed8"
            fontcolor = "#eff6ff"
            color     = "#60a5fa"
        ]

        gbfs [
            label     = "GBFS 2.3 Feed\n(JSON, real-time\nдоступность СИМ)"
            fillcolor = "#1d4ed8"
            fontcolor = "#eff6ff"
            color     = "#60a5fa"
        ]

        nmea [
            label     = "Парсер NMEA/GPX\n(прямое подключение\nустройств)"
            fillcolor = "#1d4ed8"
            fontcolor = "#eff6ff"
            color     = "#60a5fa"
        ]

        mqtt [
            label     = "MQTT-брокер\n(IoT pub/sub,\nlow latency)"
            fillcolor = "#1e40af"
            fontcolor = "#eff6ff"
            color     = "#3b82f6"
        ]

        kafka [
            label     = "Apache Kafka\nTopic: pmd-trips\n(гарантированная\nдоставка)"
            shape     = cylinder
            fillcolor = "#1e40af"
            fontcolor = "#eff6ff"
            color     = "#3b82f6"
            width     = 1.8
        ]

        faust [
            label     = "Faust Stream Processor\n──────────────────\nnorm. WGS-84\nсегментация трека\nvᵢ = d(pᵢ₋₁,pᵢ)/Δtᵢ"
            fillcolor = "#1e3a8a"
            fontcolor = "#bfdbfe"
            color     = "#60a5fa"
            width     = 2.2
        ]

        norm_out [
            label     = "Нормализованный\nпоток событий"
            shape     = parallelogram
            style     = "filled"
            fillcolor = "#172554"
            fontcolor = "#93c5fd"
            color     = "#3b82f6"
        ]
    }

    // ── CLUSTER 2: Analytics Layer ─────────────────────────────────────────────

    subgraph cluster_analytics {
        label     = "УРОВЕНЬ 2: АНАЛИТИЧЕСКИЙ ДВИЖОК (Analytics Layer) — Оригинальная разработка"
        style     = "filled,rounded"
        fillcolor = "#2e1065"
        color     = "#7c3aed"
        penwidth  = 2.5
        fontcolor = "#c4b5fd"
        fontsize  = 12
        fontname  = "Arial Bold"
        margin    = 18

        algo_a [
            label     = "Алгоритм A\nДетектор опасного вождения\n──────────────────────\nСкользящее окно w=2\naᵢ = (vᵢ − vᵢ₋₁)/Δtᵢ\n|a|≥3.5 м/с² → DANGER\n|a|≥2.5 м/с² → WARN\nF1 = 0.990"
            fillcolor = "#5b21b6"
            fontcolor = "#ede9fe"
            color     = "#a78bfa"
            width     = 2.4
        ]

        algo_b [
            label     = "Алгоритм B\nКлассификатор слепых зон\n──────────────────────\nH3 grid, res=9 (~174м)\ndensity(c) > P₇₅\nSpatial Join с OSM\nseverity = density × wc\nwc: 1.5/1.2/1.0"
            fillcolor = "#5b21b6"
            fontcolor = "#ede9fe"
            color     = "#a78bfa"
            width     = 2.4
        ]

        algo_c [
            label     = "Алгоритм C\nКомпоновщик тепловой карты\n──────────────────────\nВзвешенная суперпозиция\nA + B → растр безопасности\nGeoJSON-экспорт"
            fillcolor = "#5b21b6"
            fontcolor = "#ede9fe"
            color     = "#a78bfa"
            width     = 2.4
        ]

        geojson [
            label     = "GeoJSON-файлы\nanalyzed_trips.geojson\nblind_spots.geojson\ndangerous_segments.geojson"
            shape     = parallelogram
            style     = "filled"
            fillcolor = "#3b0764"
            fontcolor = "#c4b5fd"
            color     = "#7c3aed"
            width     = 2.6
        ]

        threshold_table [
            label     = "Пороговые значения\n──────────────────────\nWARN:   |a| ≥ 2.5 м/с²\nDANGER: |a| ≥ 3.5 м/с², 2+ точки\nСлепая зона: density > P₇₅\n             infra_score = 0"
            shape     = note
            style     = "filled"
            fillcolor = "#1e1b4b"
            fontcolor = "#a5b4fc"
            color     = "#6366f1"
            width     = 2.6
        ]
    }

    // ── CLUSTER 3: Presentation Layer ──────────────────────────────────────────

    subgraph cluster_presentation {
        label     = "УРОВЕНЬ 3: ЦЕНТР УПРАВЛЕНИЯ ПЕРЕВОЗКАМИ (Presentation Layer)"
        style     = "filled,rounded"
        fillcolor = "#052e16"
        color     = "#059669"
        penwidth  = 2.5
        fontcolor = "#6ee7b7"
        fontsize  = 12
        fontname  = "Arial Bold"
        margin    = 18

        react [
            label     = "React 18 SPA\n+ deck.gl 9\n──────────────────\nMapLibre GL JS\n(CartoDBDarkMatter)"
            fillcolor = "#065f46"
            fontcolor = "#d1fae5"
            color     = "#34d399"
            width     = 2.2
        ]

        layer_h3 [
            label     = "H3HexagonLayer\nТепловая карта плотности\n+ слепые зоны (severity)"
            fillcolor = "#064e3b"
            fontcolor = "#a7f3d0"
            color     = "#10b981"
        ]

        layer_path [
            label     = "PathLayer\nОпасные сегменты\nDANGER=красный / WARN=янтарный"
            fillcolor = "#064e3b"
            fontcolor = "#a7f3d0"
            color     = "#10b981"
        ]

        layer_trips [
            label     = "TripsLayer\nАнимация поездок\n8× скорость / след 60с\nPlay / Pause"
            fillcolor = "#064e3b"
            fontcolor = "#a7f3d0"
            color     = "#10b981"
        ]

        alert_panel [
            label     = "Alert Panel\nТоп-5 слепых зон\n(zone_id / density\n/ conflict_weight\n/ рекомендация)"
            fillcolor = "#064e3b"
            fontcolor = "#a7f3d0"
            color     = "#10b981"
        ]
    }

    // ── Edges: external → Data Layer ──────────────────────────────────────────

    operator -> mds  [label="MDS Trip API\nHTTPS/JSON"]
    operator -> gbfs [label="GBFS feed\nHTTPS/JSON"]
    iot      -> nmea [label="NMEA 0183\n/ GPX"]
    iot      -> mqtt [label="MQTT\npub/sub"]

    mds  -> kafka [label="normalized\nevents"]
    gbfs -> kafka [label="availability\nevents"]
    nmea -> mqtt
    mqtt -> kafka [label="telemetry\nstream"]

    kafka -> faust [label="consume\npmd-trips"]
    faust -> norm_out

    // ── Edges: Data Layer → Analytics Layer ───────────────────────────────────

    norm_out -> algo_a [label="GPS stream\n(1 Hz)"]
    norm_out -> algo_b [label="GPS stream\n(1 Hz)"]
    algo_a   -> algo_c
    algo_b   -> algo_c

    algo_a -> geojson [label="tagged\nsegments"]
    algo_b -> geojson [label="blind spots\n+ severity"]
    algo_c -> geojson [label="heatmap\ntiles"]

    osm -> algo_b [label="road graph\n(GraphML)\nspatial join" color="#94a3b8" style=dashed]

    // ── Edges: Analytics Layer → Presentation Layer ───────────────────────────

    geojson -> react [label="static\nGeoJSON\nfiles"]

    react -> layer_h3
    react -> layer_path
    react -> layer_trips
    react -> alert_panel

    layer_h3    -> cup_user [style=invis]
    layer_path  -> cup_user [style=invis]
    layer_trips -> cup_user [style=invis]
    alert_panel -> cup_user [label="интерактивная\nкарта + алерты"]

    threshold_table -> algo_a [style=dashed color="#6366f1" arrowhead=none]
    threshold_table -> algo_b [style=dashed color="#6366f1" arrowhead=none]
}
"""

# ── Render ─────────────────────────────────────────────────────────────────────

src = graphviz.Source(
    dot_source,
    filename=OUT_NAME,
    directory=OUT_DIR,
    engine="dot",
    format="svg",
)
src.render(
    outfile=os.path.join(OUT_DIR, OUT_NAME + ".svg"),
    cleanup=True,
    quiet=False,
    engine="dot",
    renderer=None,
    formatter=None,
    neato_no_op=None,
)

print(f"\nSchema saved: {os.path.join(OUT_DIR, OUT_NAME + '.svg')}")
