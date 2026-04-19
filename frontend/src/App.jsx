import { useState, useEffect, useRef, useCallback } from 'react'
import DeckGL from '@deck.gl/react'
import { Map } from 'react-map-gl/maplibre'
import { H3HexagonLayer, TripsLayer } from '@deck.gl/geo-layers'
import { PathLayer } from '@deck.gl/layers'
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

const SIM_SPEED = 8
const TRAIL_LENGTH = 60

// 1 USD = 3.27 BYN (апрель 2026, Нацбанк РБ)
const USD_TO_BYN = 3.27

function usdToByn(usd) {
  return Math.round(usd * USD_TO_BYN).toLocaleString('ru-RU')
}

function severityColor(sev, maxSev) {
  const t = Math.min(sev / maxSev, 1)
  return [
    Math.round(99 + 149 * t),
    Math.round(99 * (1 - t)),
    Math.round(113 * (1 - t)),
    200,
  ]
}

export default function App() {
  const [allHexes, setAllHexes]       = useState([])
  const [blindSpots, setBlindSpots]   = useState([])
  const [dangerSegs, setDangerSegs]   = useState([])
  const [trips, setTrips]             = useState([])
  const [maxTime, setMaxTime]         = useState(0)

  const [tooltip, setTooltip]         = useState(null)
  const [selected, setSelected]       = useState(null)
  const [viewState, setViewState]     = useState(MINSK_VIEW)

  const [showHeatmap, setShowHeatmap] = useState(true)
  const [showBlind, setShowBlind]     = useState(true)
  const [showDanger, setShowDanger]   = useState(false)
  const [showTrips, setShowTrips]     = useState(true)

  const [playing, setPlaying]         = useState(true)
  const [currentTime, setCurrentTime] = useState(0)
  const rafRef                        = useRef(null)
  const lastTsRef                     = useRef(null)
  const playingRef                    = useRef(true)
  const currentTimeRef                = useRef(0)
  const maxTimeRef                    = useRef(1)

  useEffect(() => { playingRef.current = playing }, [playing])
  useEffect(() => { maxTimeRef.current = maxTime }, [maxTime])

  useEffect(() => {
    fetch('data/all_hexes.geojson')
      .then(r => r.json())
      .then(fc => setAllHexes(fc.features.map(f => ({
        hex: f.properties.h3_cell,
        count: f.properties.visit_count,
      }))))

    fetch('data/blind_spots.geojson')
      .then(r => r.json())
      .then(fc => setBlindSpots(fc.features.map(f => f.properties)))

    fetch('data/dangerous_segments.geojson')
      .then(r => r.json())
      .then(fc => setDangerSegs(fc.features.map(f => ({
        path: f.geometry.coordinates,
        verdict: f.properties.verdict,
        peak: f.properties.peak_accel_ms2,
        speed: f.properties.peak_speed_ms,
        tripId: f.properties.trip_id,
      }))))

    fetch('data/trips.geojson')
      .then(r => r.json())
      .then(fc => {
        let max = 0
        const data = fc.features.map(f => {
          const coords = f.geometry.coordinates
          const ts = f.properties.timestamps_s
          const lastT = ts[ts.length - 1]
          if (lastT > max) max = lastT
          return {
            waypoints: coords.map((c, i) => ({ coordinates: c, timestamp: ts[i] })),
            dangerous: f.properties.has_dangerous_event,
          }
        })
        setTrips(data)
        setMaxTime(max)
        maxTimeRef.current = max
      })
  }, [])

  useEffect(() => {
    function tick(ts) {
      if (playingRef.current) {
        const dt = lastTsRef.current ? (ts - lastTsRef.current) / 1000 : 0
        lastTsRef.current = ts
        const next = (currentTimeRef.current + dt * SIM_SPEED) % (maxTimeRef.current || 1)
        currentTimeRef.current = next
        setCurrentTime(next)
      } else {
        lastTsRef.current = null
      }
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [])

  const togglePlay = useCallback(() => {
    setPlaying(p => !p)
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
          Math.round(40 + 80 * t),
        ]
      },
      extruded: true,
      getElevation: d => d.count * 0.3,
      pickable: true,
      onHover: ({ object, x, y }) => setTooltip(object ? {
        x, y,
        title: 'Ячейка плотности',
        rows: [['Визиты', object.count], ['H3', object.hex.slice(0, 14) + '...']],
      } : null),
    }),

    showBlind && new H3HexagonLayer({
      id: 'blind-spots',
      data: blindSpots,
      getHexagon: d => d.h3_cell,
      getFillColor: d => severityColor(d.severity, maxSev),
      extruded: true,
      getElevation: d => d.severity * 0.5,
      pickable: true,
      onHover: ({ object, x, y }) => setTooltip(object ? {
        x, y,
        title: `Слепая зона #${object.rank}`,
        rows: [
          ['Визиты', object.visit_count],
          ['Индекс', object.severity.toFixed(0)],
          ['Коэф. опасности', object.conflict_weight.toFixed(1)],
        ],
      } : null),
      onClick: ({ object }) => {
        if (!object) return
        setSelected(object.h3_cell)
        setViewState(vs => ({
          ...vs, longitude: object.centroid_lon, latitude: object.centroid_lat,
          zoom: 14, transitionDuration: 600,
        }))
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
      onHover: ({ object, x, y }) => setTooltip(object ? {
        x, y,
        title: object.verdict === 'DANGER' ? 'Опасный сегмент' : 'Предупреждение',
        rows: [
          ['Поездка', object.tripId],
          ['Макс. ускорение', `${object.peak} м/с\u00b2`],
          ['Макс. скорость', `${(object.speed * 3.6).toFixed(1)} км/ч`],
        ],
      } : null),
    }),

    showTrips && trips.length > 0 && new TripsLayer({
      id: 'trips',
      data: trips,
      getPath: d => d.waypoints.map(w => w.coordinates),
      getTimestamps: d => d.waypoints.map(w => w.timestamp),
      getColor: d => d.dangerous ? [239, 68, 68] : [99, 179, 237],
      currentTime,
      trailLength: TRAIL_LENGTH,
      widthMinPixels: 2,
      capRounded: true,
      jointRounded: true,
      pickable: false,
    }),
  ].filter(Boolean)

  const stats = {
    trips: 500,
    dangerous: 100,
    hexes: allHexes.length,
    blindSpots: blindSpots.length,
  }

  const progress = maxTime > 0 ? currentTime / maxTime : 0

  return (
    <div className="dashboard">
      <div className="topbar">
        <h1>Аналитика СИМ — Минск</h1>
        <span>500 синтетических поездок на самокатах&nbsp;·&nbsp;H3 уровень 9&nbsp;·&nbsp;OSM Минск</span>
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

          {/* Панель воспроизведения */}
          <div className="playbar">
            <button className="play-btn" onClick={togglePlay} title={playing ? 'Пауза' : 'Воспроизвести'}>
              {playing ? (
                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                  <rect x="5" y="4" width="4" height="16" rx="1"/>
                  <rect x="15" y="4" width="4" height="16" rx="1"/>
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                  <path d="M6 4l14 8-14 8V4z"/>
                </svg>
              )}
            </button>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress * 100}%` }} />
            </div>
            <span className="time-label">{Math.round(currentTime)}с</span>
          </div>

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
          {/* Слои */}
          <div className="sidebar-section">
            <h2>Слои</h2>
            <label className="layer-toggle">
              <input type="checkbox" checked={showTrips} onChange={e => setShowTrips(e.target.checked)} />
              <span className="dot" style={{ background: '#63b3ed' }} />
              Воспроизведение поездок
            </label>
            <label className="layer-toggle">
              <input type="checkbox" checked={showHeatmap} onChange={e => setShowHeatmap(e.target.checked)} />
              <span className="dot" style={{ background: '#4299e1' }} />
              Тепловая карта плотности
            </label>
            <label className="layer-toggle">
              <input type="checkbox" checked={showBlind} onChange={e => setShowBlind(e.target.checked)} />
              <span className="dot" style={{ background: '#f87171' }} />
              Слепые зоны (топ-10)
            </label>
            <label className="layer-toggle">
              <input type="checkbox" checked={showDanger} onChange={e => setShowDanger(e.target.checked)} />
              <span className="dot" style={{ background: '#ef4444' }} />
              Опасные сегменты
            </label>
          </div>

          {/* Статистика */}
          <div className="sidebar-section">
            <h2>Статистика</h2>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="value">{stats.trips}</div>
                <div className="label">Поездок всего</div>
              </div>
              <div className="stat-card">
                <div className="value" style={{ color: '#f87171' }}>{stats.dangerous}</div>
                <div className="label">Опасных</div>
              </div>
              <div className="stat-card">
                <div className="value">{stats.hexes.toLocaleString('ru-RU')}</div>
                <div className="label">Ячеек H3</div>
              </div>
              <div className="stat-card">
                <div className="value" style={{ color: '#f87171' }}>{stats.blindSpots}</div>
                <div className="label">Слепых зон</div>
              </div>
            </div>
          </div>

          {/* Топ-10 слепых зон */}
          <div className="sidebar-section">
            <h2>Топ-10 слепых зон</h2>
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
                    <div className="severity">Индекс {bs.severity.toFixed(0)}</div>
                    <div className="meta">
                      {bs.visit_count} визитов · КО {bs.conflict_weight.toFixed(1)}
                    </div>
                  </div>
                ))}
            </div>
          </div>

          {/* Легенда */}
          <div className="sidebar-section">
            <h2>Легенда</h2>
            <div className="legend">
              <div className="legend-row">
                <div className="legend-swatch" style={{ background: '#63b3ed' }} />
                <span>Безопасная поездка</span>
              </div>
              <div className="legend-row">
                <div className="legend-swatch" style={{ background: '#ef4444' }} />
                <span>Опасная поездка</span>
              </div>
              <div className="legend-row">
                <div className="legend-swatch" style={{ background: 'linear-gradient(90deg,rgba(99,179,237,.3),rgba(63,131,248,1))' }} />
                <span>Плотность трафика</span>
              </div>
              <div className="legend-row">
                <div className="legend-swatch" style={{ background: 'linear-gradient(90deg,#c084fc,#ef4444)' }} />
                <span>Опасность слепой зоны</span>
              </div>
            </div>
          </div>

          {/* Экономика */}
          <div className="sidebar-section">
            <h2>Экономика платформы</h2>
            <div className="econ-table">
              <div className="econ-row">
                <span>ТЦВ (3 года)</span>
                <span className="econ-val">{usdToByn(92120)} BYN</span>
              </div>
              <div className="econ-row">
                <span>Окупаемость</span>
                <span className="econ-val">2,2 мес.</span>
              </div>
              <div className="econ-row">
                <span>1 ДТП с пострадавшими</span>
                <span className="econ-val">{usdToByn(8000)} BYN</span>
              </div>
              <div className="econ-row">
                <span>Курс</span>
                <span className="econ-val">1 USD = {USD_TO_BYN} BYN</span>
              </div>
            </div>
          </div>

          {/* О проекте */}
          <div className="sidebar-section">
            <h2>О проекте</h2>
            <div className="about-text">
              <p>Дипломный проект БНТУ, 2026. Цифровая платформа сбора и анализа данных о движении средств индивидуальной мобильности (СИМ) в Минске.</p>
              <div className="about-layers">
                <div className="about-item">
                  <span className="about-dot" style={{ background: '#63b3ed' }} />
                  <div>
                    <b>Поездки</b> — анимация 500 маршрутов. Алгоритм A детектирует опасное вождение по ускорению (|a| ≥ 3,5 м/с²). F1&nbsp;=&nbsp;0,990.
                  </div>
                </div>
                <div className="about-item">
                  <span className="about-dot" style={{ background: '#4299e1' }} />
                  <div>
                    <b>Тепловая карта</b> — шестиугольная сетка H3 (ребро 174 м). Высота и цвет пропорциональны числу визитов самокатов.
                  </div>
                </div>
                <div className="about-item">
                  <span className="about-dot" style={{ background: '#f87171' }} />
                  <div>
                    <b>Слепые зоны</b> — Алгоритм B. Зоны с трафиком выше P75 и без велоинфраструктуры по OSM. Найдено 369 из 369 (100%).
                  </div>
                </div>
                <div className="about-item">
                  <span className="about-dot" style={{ background: '#ef4444' }} />
                  <div>
                    <b>Опасные сегменты</b> — участки с резким торможением или разгоном. Красный&nbsp;— DANGER, жёлтый&nbsp;— WARN.
                  </div>
                </div>
              </div>
              <p className="about-footer">
                Данные: OSM Минск · 365 925 GPS-точек · H3 res-9
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
