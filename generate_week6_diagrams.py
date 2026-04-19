"""
Week 6 diagrams:
  docs/tco_chart.svg          — Diagram 9:  TCO breakdown (3-year, 4 categories)
  docs/system_context.svg     — Diagram 1:  System context (actors + platform)
  docs/kafka_topology.svg     — Diagram 3:  Kafka stream processing topology
  docs/deployment_topology.svg— Diagram 10: Physical/cloud deployment view
"""

import os
import graphviz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

GRAPHVIZ_BIN = r"C:\Program Files\Graphviz\bin"
os.environ["PATH"] = GRAPHVIZ_BIN + os.pathsep + os.environ.get("PATH", "")

OUT = os.path.join(os.path.dirname(__file__), "docs")
os.makedirs(OUT, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM 9 — TCO (matplotlib, dark theme)
# ══════════════════════════════════════════════════════════════════════════════

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.facecolor": "#1a1d27",
    "figure.facecolor": "#0f1117",
    "text.color": "#e2e8f0",
    "axes.labelcolor": "#e2e8f0",
    "xtick.color": "#94a3b8",
    "ytick.color": "#94a3b8",
    "axes.edgecolor": "#2d3148",
    "grid.color": "#2d3148",
    "axes.titlecolor": "#e2e8f0",
})

fig, axes = plt.subplots(1, 2, figsize=(18, 9))
fig.patch.set_facecolor("#0f1117")

# Cost data (USD/year)
categories  = ["Infrastructure\n(servers)", "Licences\n(OSS stack)", "Development\n(one-time)", "Support &\nmaintenance"]
colors      = ["#3b82f6", "#a78bfa", "#f59e0b", "#34d399"]

year1 = [7_680,  700, 29_500, 12_000]
year2 = [7_680,  700,      0, 12_000]
year3 = [8_160,  700,      0, 13_000]   # slight infra growth Y3

years      = ["Year 1", "Year 2", "Year 3"]
year_totals = [sum(year1), sum(year2), sum(year3)]

# Left: grouped bar chart
ax = axes[0]
x   = np.arange(len(categories))
w   = 0.22
bars1 = ax.bar(x - w,   year1, w, color=colors[0], alpha=0.9, label="Year 1")
bars2 = ax.bar(x,       [y1 if i != 2 else year2[i] for i, y1 in enumerate(year1)],
               w, color=colors[1], alpha=0.9, label="Year 2")
bars3 = ax.bar(x + w,   [y1 if i != 2 else year3[i] for i, y1 in enumerate(year1)],
               w, color=colors[2], alpha=0.9, label="Year 3")

# Replot correctly per category
ax.cla()
for i, (c, col) in enumerate(zip(categories, colors)):
    vals = [year1[i], year2[i], year3[i]]
    b = ax.bar(np.arange(3) + i * 0.25 - 0.37, vals, 0.22, color=col, alpha=0.9, label=c)
    for rect, v in zip(b, vals):
        if v > 0:
            ax.text(rect.get_x() + rect.get_width()/2, rect.get_height() + 300,
                    f"${v:,.0f}", ha="center", va="bottom", fontsize=8, color="#e2e8f0")

ax.set_xticks([0.15, 1.15, 2.15])
ax.set_xticklabels(years, fontsize=12)
ax.set_ylabel("Cost, USD", fontsize=12)
ax.set_title("Annual cost breakdown by category", fontsize=13, pad=12)
ax.legend(fontsize=9, facecolor="#1a1d27", edgecolor="#2d3148", labelcolor="#e2e8f0")
ax.yaxis.grid(True, alpha=0.4)
ax.set_axisbelow(True)

# Right: stacked total + cumulative line
ax2 = axes[1]
bottom1 = np.zeros(3)
for i, (vals, col, cat) in enumerate(zip(
        [[year1[i], year2[i], year3[i]] for i in range(4)], colors, categories)):
    ax2.bar(years, vals, bottom=bottom1, color=col, alpha=0.9, label=cat, width=0.45)
    bottom1 += np.array(vals)

# Cumulative totals
cumulative = np.cumsum(year_totals)
ax2_r = ax2.twinx()
ax2_r.plot(years, cumulative, "o--", color="#f87171", linewidth=2,
           markersize=8, label="Cumulative TCO")
for x, y in zip(years, cumulative):
    ax2_r.text(x, y + 800, f"${y:,.0f}", ha="center", va="bottom",
               color="#f87171", fontweight="bold", fontsize=10)
ax2_r.set_ylabel("Cumulative TCO, USD", color="#f87171", fontsize=11)
ax2_r.tick_params(axis="y", colors="#f87171")
ax2_r.set_facecolor("#1a1d27")

ax2.set_title("3-year TCO stacked + cumulative", fontsize=13, pad=12)
ax2.legend(loc="upper left", fontsize=9, facecolor="#1a1d27",
           edgecolor="#2d3148", labelcolor="#e2e8f0")
ax2.yaxis.grid(True, alpha=0.4)
ax2.set_axisbelow(True)

# Summary table
summary_text = (
    f"3-Year TCO Summary\n"
    f"{'─'*32}\n"
    f"Year 1 (incl. development): ${year_totals[0]:>8,.0f}\n"
    f"Year 2:                     ${year_totals[1]:>8,.0f}\n"
    f"Year 3:                     ${year_totals[2]:>8,.0f}\n"
    f"{'─'*32}\n"
    f"Total (3 years):            ${sum(year_totals):>8,.0f}\n"
    f"Monthly avg (excl. Y1 dev): ${(year_totals[1]/12):>8,.0f}"
)
fig.text(0.5, 0.02, summary_text, ha="center", va="bottom",
         fontsize=10, color="#e2e8f0", fontfamily="monospace",
         bbox=dict(boxstyle="round,pad=0.5", facecolor="#1a1d27",
                   edgecolor="#2d3148", alpha=0.9))

fig.suptitle(
    "ТЕХНИКО-ЭКОНОМИЧЕСКОЕ ОБОСНОВАНИЕ (ТЭО) ПЛАТФОРМЫ ГЕОАНАЛИТИКИ ПМД\n"
    "Диаграмма 9 из 9  |  БНТУ, Факультет АТФ",
    fontsize=14, fontweight="bold", color="#e2e8f0", y=0.98
)

plt.tight_layout(rect=[0, 0.13, 1, 0.95])
fig.savefig(os.path.join(OUT, "tco_chart.svg"), format="svg", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: docs/tco_chart.svg")


# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM 1 — System Context
# ══════════════════════════════════════════════════════════════════════════════

ctx_dot = r"""
digraph SystemContext {
    graph [
        rankdir  = LR  fontname="Arial"  fontsize=13
        bgcolor  = "#0f1117"  pad=0.8  nodesep=0.7  ranksep=1.4
        label    = "\nКОНТЕКСТНАЯ ДИАГРАММА СИСТЕМЫ\n(Диаграмма 1 из 9)"
        labelloc = t  fontcolor="#e2e8f0"  fontsize=17
    ]
    node [fontname="Arial" fontsize=11 style="filled,rounded" margin="0.2,0.14"]
    edge [fontname="Arial" fontsize=10 color="#94a3b8" fontcolor="#94a3b8"
          penwidth=1.5 arrowsize=0.8]

    // Central system
    platform [
        label="ПЛАТФОРМА\nГЕОАНАЛИТИКИ ПМД\n──────────────────\nСбор телеметрии\nДетекция опасных событий\nКлассификация слепых зон\nЦУП-дашборд"
        shape=box  style="filled,rounded"
        fillcolor="#312e81"  fontcolor="#e0e7ff"  color="#818cf8"
        width=3.0  height=2.0
    ]

    // Operators (input)
    bolt  [label="Bolt\n(оператор шеринга)"  fillcolor="#374151" fontcolor="#f9fafb" color="#6b7280" shape=box style="filled,rounded"]
    whoosh[label="Whoosh\n(оператор шеринга)"fillcolor="#374151" fontcolor="#f9fafb" color="#6b7280" shape=box style="filled,rounded"]
    iot   [label="IoT GPS-модуль\n(устройство СИМ)"  fillcolor="#374151" fontcolor="#f9fafb" color="#6b7280" shape=box style="filled,rounded"]

    // External data
    osm  [label="OpenStreetMap\n(граф дорог Минска)"  fillcolor="#374151" fontcolor="#f9fafb" color="#6b7280" shape=cylinder]

    // Users/consumers
    cup    [label="ЦУП-оператор\n(служба транспорта)"      fillcolor="#064e3b" fontcolor="#d1fae5" color="#34d399" shape=box style="filled,rounded"]
    plan   [label="Городской планировщик\n(комитет по инфраструктуре)" fillcolor="#064e3b" fontcolor="#d1fae5" color="#34d399" shape=box style="filled,rounded"]
    admin  [label="Системный\nадминистратор"               fillcolor="#1e3a5f" fontcolor="#93c5fd" color="#2563eb" shape=box style="filled,rounded"]

    // Protocols
    bolt   -> platform [label="MDS Trip API\nHTTPS / JSON"]
    whoosh -> platform [label="GBFS 2.3 Feed\nHTTPS / JSON"]
    iot    -> platform [label="MQTT / NMEA\nпрямое подключение"]
    osm    -> platform [label="GraphML\nPBF-снимок" style=dashed]

    platform -> cup  [label="Интерактивная карта\n(deck.gl дашборд)"]
    platform -> plan [label="Отчёт: топ-10 слепых зон\nJSON / PDF"]
    platform -> admin[label="Логи / мониторинг\nGrafana / Kafka UI" style=dashed]

    // Standards callout
    standards [
        label="Стандарты обмена:\nMDS Provider API v1.1\nGBFS 2.3\nNMEA 0183 / GPX\nGeoJSON RFC 7946\nH3 (Uber, resolution 9)"
        shape=note  fillcolor="#1e1b4b"  fontcolor="#a5b4fc"  color="#6366f1"
    ]
}
"""

graphviz.Source(ctx_dot, format="svg").render(
    outfile=os.path.join(OUT, "system_context.svg"), cleanup=True, quiet=False)
print("Saved: docs/system_context.svg")


# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM 3 — Kafka Stream Processing Topology
# ══════════════════════════════════════════════════════════════════════════════

kafka_dot = r"""
digraph KafkaTopology {
    graph [
        rankdir  = LR  fontname="Arial"  fontsize=12
        bgcolor  = "#0f1117"  pad=0.7  nodesep=0.5  ranksep=1.0
        label    = "\nТОПОЛОГИЯ ПОТОКОВОЙ ОБРАБОТКИ ДАННЫХ (Apache Kafka + Faust)\n(Диаграмма 3 из 9)"
        labelloc = t  fontcolor="#e2e8f0"  fontsize=16
        splines  = ortho
    ]
    node [fontname="Arial" fontsize=10 style="filled,rounded" margin="0.16,0.1"]
    edge [fontname="Arial" fontsize=9 color="#94a3b8" fontcolor="#94a3b8" penwidth=1.4 arrowsize=0.7]

    // Producers
    subgraph cluster_producers {
        label="PRODUCERS (источники данных)"
        style="filled,rounded"  fillcolor="#1e3a5f"  color="#2563eb"
        fontcolor="#93c5fd"  fontsize=11  margin=14

        p_mds  [label="MDS Adapter\n(REST poll, 1 min)" fillcolor="#1d4ed8" fontcolor="#eff6ff" color="#60a5fa"]
        p_gbfs [label="GBFS Consumer\n(websocket)"      fillcolor="#1d4ed8" fontcolor="#eff6ff" color="#60a5fa"]
        p_mqtt [label="MQTT Bridge\n(IoT gateway)"       fillcolor="#1d4ed8" fontcolor="#eff6ff" color="#60a5fa"]
    }

    // Kafka cluster
    subgraph cluster_kafka {
        label="APACHE KAFKA CLUSTER (3 брокера)"
        style="filled,rounded"  fillcolor="#1e1065"  color="#4338ca"
        fontcolor="#a5b4fc"  fontsize=11  margin=14

        t_raw  [label="Topic:\npmd-raw-telemetry\n(retention: 7 days)"  shape=cylinder fillcolor="#3730a3" fontcolor="#e0e7ff" color="#818cf8"]
        t_norm [label="Topic:\npmd-normalized\n(retention: 30 days)"   shape=cylinder fillcolor="#3730a3" fontcolor="#e0e7ff" color="#818cf8"]
        t_alert[label="Topic:\npmd-alerts\n(retention: 90 days)"       shape=cylinder fillcolor="#4c1d95" fontcolor="#ddd6fe" color="#7c3aed"]
    }

    // Faust processors
    subgraph cluster_faust {
        label="FAUST STREAM PROCESSORS"
        style="filled,rounded"  fillcolor="#2e1065"  color="#7c3aed"
        fontcolor="#c4b5fd"  fontsize=11  margin=14

        f_norm [label="Normalizer\nWGS-84 norm.\nсегментация\nvᵢ = d/Δt"
                fillcolor="#5b21b6" fontcolor="#ede9fe" color="#a78bfa"]
        f_algA [label="Algo A Worker\nДетектор опасного\nвождения\n|a|≥3.5 → DANGER"
                fillcolor="#5b21b6" fontcolor="#ede9fe" color="#a78bfa"]
        f_algB [label="Algo B Worker\nH3 агрегация\nspatial join OSM\nseverity rank"
                fillcolor="#5b21b6" fontcolor="#ede9fe" color="#a78bfa"]
    }

    // Sinks
    subgraph cluster_sinks {
        label="SINKS (потребители результатов)"
        style="filled,rounded"  fillcolor="#052e16"  color="#059669"
        fontcolor="#6ee7b7"  fontsize=11  margin=14

        s_postgis [label="PostGIS\n(геоиндексы\nGIST)"       shape=cylinder fillcolor="#065f46" fontcolor="#d1fae5" color="#34d399"]
        s_geojson [label="GeoJSON\nСтатические файлы\n→ frontend"      fillcolor="#064e3b" fontcolor="#d1fae5" color="#34d399"]
        s_cup     [label="ЦУП Dashboard\n(React + deck.gl)\nreal-time alerts"  fillcolor="#064e3b" fontcolor="#d1fae5" color="#34d399"]
    }

    // Schema callout
    schema [
        label="Схема события (pmd-normalized):\n────────────────────────────────\n{\n  trip_id:    string (UUID)\n  timestamp:  int64 (Unix ms)\n  lon, lat:   float64 (WGS-84)\n  speed_ms:   float32\n  accel_ms2:  float32\n  label:      enum {SAFE,WARN,DANGER}\n  h3_cell:    string (res=9)\n}"
        shape=note  fillcolor="#1e1b4b"  fontcolor="#a5b4fc"  color="#6366f1"
        fontsize=9
    ]

    // Edges
    p_mds  -> t_raw [label="JSON\nevents"]
    p_gbfs -> t_raw [label="availability\nevents"]
    p_mqtt -> t_raw [label="NMEA\ntelemetry"]

    t_raw -> f_norm [label="consume\ngroup: normalizer"]
    f_norm -> t_norm [label="produce\nnorm. events"]

    t_norm -> f_algA [label="consume\ngroup: algo-a"]
    t_norm -> f_algB [label="consume\ngroup: algo-b"]

    f_algA -> t_alert [label="produce\nDANGER events"]
    f_algA -> s_postgis [label="upsert\nsegments"]
    f_algA -> s_geojson [label="export"]

    f_algB -> s_postgis [label="upsert\nhexagons"]
    f_algB -> s_geojson [label="export\nblind_spots"]

    t_alert -> s_cup [label="push\nalerts"]
    s_postgis -> s_geojson [label="nightly\nexport job" style=dashed]
    s_geojson -> s_cup [label="static\nfiles"]
}
"""

graphviz.Source(kafka_dot, format="svg").render(
    outfile=os.path.join(OUT, "kafka_topology.svg"), cleanup=True, quiet=False)
print("Saved: docs/kafka_topology.svg")


# ══════════════════════════════════════════════════════════════════════════════
# DIAGRAM 10 — Deployment Topology
# ══════════════════════════════════════════════════════════════════════════════

deploy_dot = r"""
digraph Deployment {
    graph [
        rankdir  = TB  fontname="Arial"  fontsize=12
        bgcolor  = "#0f1117"  pad=0.8  nodesep=0.6  ranksep=0.8
        label    = "\nТОПОЛОГИЯ РАЗВЁРТЫВАНИЯ ПЛАТФОРМЫ\n(Диаграмма 10 из 9  |  Physical + Cloud View)"
        labelloc = t  fontcolor="#e2e8f0"  fontsize=16
    ]
    node [fontname="Arial" fontsize=10 style="filled,rounded" margin="0.18,0.12"]
    edge [fontname="Arial" fontsize=9 color="#94a3b8" fontcolor="#94a3b8" penwidth=1.4 arrowsize=0.7]

    // Internet / operators
    subgraph cluster_internet {
        label="ИНТЕРНЕТ / ВНЕШНИЕ ИСТОЧНИКИ"
        style="filled,rounded"  fillcolor="#1c1917"  color="#78716c"
        fontcolor="#d6d3d1"  fontsize=11  margin=16

        op_bolt  [label="Bolt API\n(MDS endpoint)"   fillcolor="#374151" fontcolor="#f9fafb" color="#6b7280"]
        op_whoosh[label="Whoosh API\n(GBFS endpoint)" fillcolor="#374151" fontcolor="#f9fafb" color="#6b7280"]
        op_iot   [label="IoT-устройства\n(GPS модули)" fillcolor="#374151" fontcolor="#f9fafb" color="#6b7280"]
        osm_tile [label="OSM / CartoDB\n(карточная подложка)" fillcolor="#374151" fontcolor="#f9fafb" color="#6b7280"]
    }

    // DMZ / API Gateway
    subgraph cluster_dmz {
        label="DMZ — ШЛЮЗ / БАЛАНСИРОВЩИК"
        style="filled,rounded"  fillcolor="#1c1917"  color="#d97706"
        fontcolor="#fcd34d"  fontsize=11  margin=14

        nginx  [label="nginx\n(reverse proxy\nTLS termination)"  fillcolor="#78350f" fontcolor="#fde68a" color="#f59e0b"]
        mqtt_gw[label="MQTT Broker\n(Mosquitto)\nport 8883 TLS"   fillcolor="#78350f" fontcolor="#fde68a" color="#f59e0b"]
    }

    // App servers
    subgraph cluster_app {
        label="APP SERVERS (2x, active-passive HA)"
        style="filled,rounded"  fillcolor="#1e3a5f"  color="#2563eb"
        fontcolor="#93c5fd"  fontsize=11  margin=14

        app1 [label="App Server 1\n4 CPU / 16 GB\nFaust workers\nMDS adapter\nGBFS consumer"  fillcolor="#1d4ed8" fontcolor="#eff6ff" color="#60a5fa"]
        app2 [label="App Server 2\n4 CPU / 16 GB\n(standby / scale-out)"                      fillcolor="#1e40af" fontcolor="#eff6ff" color="#3b82f6" style="filled,rounded,dashed"]
    }

    // Kafka cluster
    subgraph cluster_kafka_d {
        label="KAFKA CLUSTER (3 брокера)"
        style="filled,rounded"  fillcolor="#1e1065"  color="#4338ca"
        fontcolor="#a5b4fc"  fontsize=11  margin=14

        k1 [label="Kafka Broker 1\n4 CPU / 8 GB"  fillcolor="#3730a3" fontcolor="#e0e7ff" color="#818cf8" shape=cylinder]
        k2 [label="Kafka Broker 2\n4 CPU / 8 GB"  fillcolor="#3730a3" fontcolor="#e0e7ff" color="#818cf8" shape=cylinder]
        k3 [label="Kafka Broker 3\n(ZooKeeper)\n4 CPU / 8 GB" fillcolor="#312e81" fontcolor="#c7d2fe" color="#6366f1" shape=cylinder]
    }

    // Database
    subgraph cluster_db {
        label="DATABASE SERVER"
        style="filled,rounded"  fillcolor="#2e1065"  color="#7c3aed"
        fontcolor="#c4b5fd"  fontsize=11  margin=14

        pg [label="PostgreSQL 16\n+ PostGIS 3.4\n8 CPU / 32 GB\nGIST spatial index"  fillcolor="#5b21b6" fontcolor="#ede9fe" color="#a78bfa" shape=cylinder]
        pg_replica [label="PG Replica\n(read-only\nfor analytics)"                    fillcolor="#4c1d95" fontcolor="#ddd6fe" color="#7c3aed" shape=cylinder style="filled,dashed"]
    }

    // Static / CDN
    subgraph cluster_cdn {
        label="STATIC / CDN"
        style="filled,rounded"  fillcolor="#052e16"  color="#059669"
        fontcolor="#6ee7b7"  fontsize=11  margin=14

        cdn  [label="Nginx Static\n(GeoJSON files\nReact SPA bundle)"  fillcolor="#065f46" fontcolor="#d1fae5" color="#34d399"]
        cf   [label="Cloudflare CDN\n(edge cache\nDDoS protection)"   fillcolor="#064e3b" fontcolor="#d1fae5" color="#10b981"]
    }

    // Client
    subgraph cluster_client {
        label="КЛИЕНТСКАЯ СЕТЬ (ЦУП)"
        style="filled,rounded"  fillcolor="#1c1917"  color="#78716c"
        fontcolor="#d6d3d1"  fontsize=11  margin=14

        browser [label="Браузер ЦУП-оператора\n(Chrome / Firefox)\nReact + deck.gl" fillcolor="#374151" fontcolor="#f9fafb" color="#6b7280"]
    }

    // Monitoring
    subgraph cluster_mon {
        label="МОНИТОРИНГ"
        style="filled,rounded"  fillcolor="#1c1917"  color="#6b7280"
        fontcolor="#9ca3af"  fontsize=10  margin=10

        grafana [label="Grafana\n+ Prometheus"  fillcolor="#292524" fontcolor="#d6d3d1" color="#6b7280"]
    }

    // Edges
    op_bolt   -> nginx [label="HTTPS\nMDS API"]
    op_whoosh -> nginx [label="HTTPS\nGBFS"]
    op_iot    -> mqtt_gw [label="MQTT TLS\n8883"]
    osm_tile  -> cf [label="map tiles\nHTTPS" style=dashed]

    nginx    -> app1 [label="REST\nproxy"]
    mqtt_gw  -> k1   [label="telemetry\nevents"]
    app1     -> k1   [label="produce\nevents"]
    app1     -> k2   [label="produce\nevents"]
    app2     -> k1   [label="standby" style=dashed]

    k1 -> app1 [label="consume\nFaust" dir=both]
    k2 -> app1 [label="consume\nFaust" dir=both]
    k3 -> k1   [label="ZK\ncoord" style=dashed arrowhead=none]
    k3 -> k2   [label="ZK\ncoord" style=dashed arrowhead=none]

    app1 -> pg  [label="upsert\nresults"]
    pg   -> pg_replica [label="streaming\nreplication" style=dashed]
    pg_replica -> app1 [label="read\nqueries" style=dashed]

    app1 -> cdn [label="export\nGeoJSON"]
    cdn  -> cf  [label="cache\npush"]
    cf   -> browser [label="HTTPS\nSPA + data"]

    app1 -> grafana [label="metrics" style=dashed]
    k1   -> grafana [label="lag metrics" style=dashed]
    pg   -> grafana [label="DB metrics" style=dashed]
}
"""

graphviz.Source(deploy_dot, format="svg").render(
    outfile=os.path.join(OUT, "deployment_topology.svg"), cleanup=True, quiet=False)
print("Saved: docs/deployment_topology.svg")
