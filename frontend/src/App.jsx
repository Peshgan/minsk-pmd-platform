import { useState, useEffect, useCallback } from 'react'
import DeckGL from '@deck.gl/react'
import { Map } from 'react-map-gl/maplibre'
import { H3HexagonLayer } from '@deck.gl/geo-layers'
import { PathLayer, ScatterplotLayer } from '@deck.gl/layers'
import 'maplibre-gl/dist/maplibre-gl.css'
import './App.css'

const MINSK_VIEW = {
  longitude: 27.5615,
  latitude: 53.9006,
  zoom: 11.5,
  pitch: 40,
  bearing: 0,
}

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'

function severityColor(sev, maxSev) {
  const t = Math.min(sev / maxSev, 1)
  const r = Math.round(248 * t + 99 * (1 - t))
  const g = Math.round(113 * (1 - t) + 99 * (1 - t))
  const b = Math.round(113 * (1 - t))
  return [r, g, b, 200]
}

export default function App() {
  const [allHexes, setAllHexes]         = useState([])
  const [blindSpots, setBlindSpots]     = useState([])
  const [dangerSegs, setDangerSegs]     = useState([])
  const [tooltip, setTooltip]           = useState(null)
  const [selected, setSelected]         = useState(null)
  const [viewState, setViewState]       = useState(MINSK_VIEW)

  const [showHeatmap, setShowHeatmap]   = useState(true)
  const [showBlind, setShowBlind]       = useState(true)
  const [showDanger, setShowDanger]     = useState(true)

  useEffect(() => {
    fetch('/data/all_hexes.geojson')
      .then(r => r.json())
      .then(fc => setAllHexes(fc.features.map(f => ({
        hex: f.properties.h3_cell,
        count: f.properties.visit_count,
      }))))

    fetch('/data/blind_spots.geojson')
      .then(r => r.json())
      .then(fc => setBlindSpots(fc.features.map(f => f.properties)))

    fetch('/data/dangerous_segments.geojson')
      .then(r => r.json())
      .then(fc => setDangerSegs(fc.features.map(f => ({
        path: f.geometry.coordinates,
        verdict: f.properties.verdict,
        peak: f.properties.peak_accel_ms2,
        speed: f.properties.peak_speed_ms,
        tripId: f.properties.trip_id,
      }))))
  }, [])

  const maxCount = allHexes.length ? Math.max(...allHexes.map(h => h.count)) : 1
  const maxSev   = blindSpots.length ? Math.max(...blindSpots.map(b => b.severity)) : 1

  const layers = [
    showHeatmap && new H3HexagonLayer({
      id: 'heatmap',
      data: allHexes,
      getHexagon: d => d.hex,
      getFillColor: d => {
        const t = d.count / maxCount
        return [
          Math.round(99 + 80 * t),
          Math.round(179 - 100 * t),
          Math.round(255 - 200 * t),
          Math.round(60 + 140 * t),
        ]
      },
      extruded: true,
      getElevation: d => d.count * 0.3,
      elevationScale: 1,
      pickable: true,
      onHover: ({ object, x, y }) => {
        setTooltip(object ? {
          x, y,
          title: 'Density hex',
          rows: [
            ['Visits', object.count],
            ['H3 cell', object.hex.slice(0, 12) + '...'],
          ],
        } : null)
      },
    }),

    showBlind && new H3HexagonLayer({
      id: 'blind-spots',
      data: blindSpots,
      getHexagon: d => d.h3_cell,
      getFillColor: d => severityColor(d.severity, maxSev),
      extruded: true,
      getElevation: d => d.severity * 0.5,
      elevationScale: 1,
      pickable: true,
      wireframe: false,
      onHover: ({ object, x, y }) => {
        setTooltip(object ? {
          x, y,
          title: `Blind spot #${object.rank}`,
          rows: [
            ['Visits', object.visit_count],
            ['Severity', object.severity.toFixed(0)],
            ['Conflict weight', object.conflict_weight.toFixed(1)],
          ],
        } : null)
      },
      onClick: ({ object }) => {
        if (!object) return
        setSelected(object.h3_cell)
        const lat = object.centroid_lat
        const lon = object.centroid_lon
        setViewState(vs => ({ ...vs, longitude: lon, latitude: lat, zoom: 14, transitionDuration: 600 }))
      },
    }),

    showDanger && new PathLayer({
      id: 'danger-segments',
      data: dangerSegs,
      getPath: d => d.path,
      getColor: d => d.verdict === 'DANGER' ? [239, 68, 68, 220] : [251, 191, 36, 180],
      getWidth: 4,
      widthMinPixels: 2,
      pickable: true,
      onHover: ({ object, x, y }) => {
        setTooltip(object ? {
          x, y,
          title: `${object.verdict} segment`,
          rows: [
            ['Trip', object.tripId],
            ['Peak accel', `${object.peak} m/s²`],
            ['Peak speed', `${(object.speed * 3.6).toFixed(1)} km/h`],
          ],
        } : null)
      },
    }),
  ].filter(Boolean)

  const stats = {
    trips: 500,
    dangerous: 100,
    hexes: allHexes.length,
    blindSpots: blindSpots.length,
  }

  return (
    <div className="dashboard">
      <div className="topbar">
        <h1>PMD Analytics Dashboard — Minsk</h1>
        <span>500 synthetic scooter trips | H3 res-9</span>
      </div>

      <div className="main">
        <div className="map-container">
          <DeckGL
            viewState={viewState}
            onViewStateChange={({ viewState: vs }) => setViewState(vs)}
            controller={true}
            layers={layers}
          >
            <Map mapStyle={MAP_STYLE} />
          </DeckGL>

          {tooltip && (
            <div className="tooltip" style={{ left: tooltip.x + 12, top: tooltip.y - 10 }}>
              <strong>{tooltip.title}</strong>
              {tooltip.rows.map(([label, val]) => (
                <div className="t-row" key={label}>
                  <span>{label}</span>
                  <span className="t-val">{val}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="sidebar">
          <div className="sidebar-section">
            <h2>Layers</h2>
            <label className="layer-toggle">
              <input type="checkbox" checked={showHeatmap} onChange={e => setShowHeatmap(e.target.checked)} />
              <span className="dot" style={{ background: '#63b3ed' }} />
              Density heatmap
            </label>
            <label className="layer-toggle">
              <input type="checkbox" checked={showBlind} onChange={e => setShowBlind(e.target.checked)} />
              <span className="dot" style={{ background: '#f87171' }} />
              Blind spots (top 10)
            </label>
            <label className="layer-toggle">
              <input type="checkbox" checked={showDanger} onChange={e => setShowDanger(e.target.checked)} />
              <span className="dot" style={{ background: '#ef4444' }} />
              Dangerous segments
            </label>
          </div>

          <div className="sidebar-section">
            <h2>Stats</h2>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="value">{stats.trips}</div>
                <div className="label">Total trips</div>
              </div>
              <div className="stat-card">
                <div className="value" style={{ color: '#f87171' }}>{stats.dangerous}</div>
                <div className="label">Dangerous</div>
              </div>
              <div className="stat-card">
                <div className="value">{stats.hexes.toLocaleString()}</div>
                <div className="label">H3 hexagons</div>
              </div>
              <div className="stat-card">
                <div className="value" style={{ color: '#f87171' }}>{stats.blindSpots}</div>
                <div className="label">Blind spots</div>
              </div>
            </div>
          </div>

          <div className="sidebar-section">
            <h2>Top-10 Blind Spots</h2>
            <div className="blind-spot-list">
              {blindSpots
                .slice()
                .sort((a, b) => a.rank - b.rank)
                .map(bs => (
                  <div
                    key={bs.h3_cell}
                    className={`blind-spot-item${selected === bs.h3_cell ? ' selected' : ''}`}
                    onClick={() => {
                      setSelected(bs.h3_cell)
                      setViewState(vs => ({
                        ...vs,
                        longitude: bs.centroid_lon,
                        latitude: bs.centroid_lat,
                        zoom: 14,
                        transitionDuration: 600,
                      }))
                    }}
                  >
                    <div className="rank">#{bs.rank}</div>
                    <div className="severity">Severity {bs.severity.toFixed(0)}</div>
                    <div className="meta">
                      {bs.visit_count} visits &middot; CW {bs.conflict_weight.toFixed(1)}
                    </div>
                  </div>
                ))}
            </div>
          </div>

          <div className="sidebar-section">
            <h2>Legend</h2>
            <div className="legend">
              <div className="legend-row">
                <div className="legend-swatch" style={{ background: 'linear-gradient(90deg, rgba(99,179,237,0.3), rgba(63,131,248,1))' }} />
                <span>Visit density</span>
              </div>
              <div className="legend-row">
                <div className="legend-swatch" style={{ background: 'linear-gradient(90deg, #c084fc, #ef4444)' }} />
                <span>Blind spot severity</span>
              </div>
              <div className="legend-row">
                <div className="legend-swatch" style={{ background: '#ef4444' }} />
                <span>DANGER segment</span>
              </div>
              <div className="legend-row">
                <div className="legend-swatch" style={{ background: '#fbbf24' }} />
                <span>WARN segment</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
