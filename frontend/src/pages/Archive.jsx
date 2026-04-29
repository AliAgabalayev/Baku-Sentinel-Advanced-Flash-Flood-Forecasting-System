import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts'
import { format, subDays, parseISO, startOfDay, endOfDay } from 'date-fns'
import { api } from '../api/client.js'

const ZONES      = ['High Relief', 'Moderate Relief', 'Low Relief']
const ZONE_COLORS = { 'High Relief': '#00e87a', 'Moderate Relief': '#ffaa00', 'Low Relief': '#ff3344' }

// ── Custom Tooltip ─────────────────────────────────────────────────────────────
function ArchiveTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="glass rounded-xl px-3 py-2.5" style={{ border: '1px solid rgba(0,204,255,0.2)', minWidth: 180 }}>
      <div className="font-mono text-[10px] mb-2" style={{ color: '#00ccff' }}>{label}</div>
      {payload.map(p => (
        <div key={p.dataKey} className="flex justify-between gap-4 font-mono text-[10px]">
          <span style={{ color: p.color }}>{p.name}</span>
          <span style={{ color: '#b8d4e8' }}>{typeof p.value === 'number' ? p.value.toFixed(2) : p.value}</span>
        </div>
      ))}
    </div>
  )
}

// ── Date Picker ────────────────────────────────────────────────────────────────
function DateRangePicker({ start, end, onStartChange, onEndChange }) {
  const inputStyle = {
    background: 'rgba(0,204,255,0.05)',
    border: '1px solid rgba(0,204,255,0.15)',
    borderRadius: '10px',
    padding: '8px 12px',
    color: '#b8d4e8',
    fontFamily: '"JetBrains Mono", monospace',
    fontSize: '12px',
    outline: 'none',
    colorScheme: 'dark',
  }

  return (
    <div className="flex items-center gap-3 flex-wrap">
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] tracking-wider" style={{ color: '#3a6a8a' }}>FROM</span>
        <input type="date" value={start} onChange={e => onStartChange(e.target.value)} style={inputStyle} />
      </div>
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] tracking-wider" style={{ color: '#3a6a8a' }}>TO</span>
        <input type="date" value={end} onChange={e => onEndChange(e.target.value)} style={inputStyle} />
      </div>
    </div>
  )
}

// ── Zone Pill ──────────────────────────────────────────────────────────────────
function ZonePill({ zone, active, onClick }) {
  const color = ZONE_COLORS[zone]
  return (
    <button
      onClick={onClick}
      className="px-3 py-1.5 rounded-full font-ui text-xs transition-all duration-200"
      style={{
        background: active ? `${color}20` : 'rgba(0,204,255,0.04)',
        border: `1px solid ${active ? color : 'rgba(0,204,255,0.12)'}`,
        color: active ? color : '#3a6a8a',
        boxShadow: active ? `0 0 10px ${color}40` : 'none',
      }}
    >
      {zone}
    </button>
  )
}

// ── Event Badge ────────────────────────────────────────────────────────────────
function EventBadge({ label }) {
  return (
    <div
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[9px]"
      style={{ background: 'rgba(255,51,68,0.1)', border: '1px solid rgba(255,51,68,0.3)', color: '#ff3344' }}
    >
      <span>🌊</span> {label}
    </div>
  )
}

// ── Summary Stats ──────────────────────────────────────────────────────────────
function SummaryStats({ data, zone }) {
  const zoneData = data.filter(d => d.zone === zone)
  if (!zoneData.length) return null

  const maxPrecip    = Math.max(...zoneData.map(d => d.precipitation)).toFixed(1)
  const floodEvents  = zoneData.filter(d => d.is_flood === 1).length
  const detected     = zoneData.filter(d => d.is_flood === 1 && d.flood_pred === 1).length
  const missed       = zoneData.filter(d => d.is_flood === 1 && d.flood_pred === 0).length

  const stats = [
    { label: 'PEAK RAIN',    value: `${maxPrecip} mm`, color: '#00ccff' },
    { label: 'FLOOD EVENTS', value: floodEvents,        color: '#ff3344' },
    { label: 'DETECTED',     value: detected,           color: '#00e87a' },
    { label: 'MISSED',       value: missed,             color: '#ffaa00' },
  ]

  return (
    <div className="grid grid-cols-4 gap-3">
      {stats.map(s => (
        <div
          key={s.label}
          className="rounded-xl px-4 py-3 text-center"
          style={{ background: `${s.color}08`, border: `1px solid ${s.color}1a` }}
        >
          <div className="font-display text-2xl leading-none" style={{ color: s.color }}>{s.value}</div>
          <div className="font-mono text-[9px] mt-1 tracking-wider" style={{ color: '#3a6a8a' }}>{s.label}</div>
        </div>
      ))}
    </div>
  )
}

// ── Comparison Table ───────────────────────────────────────────────────────────
function ComparisonTable({ data, zone }) {
  const rows = data
    .filter(d => d.zone === zone && (d.is_flood === 1 || d.flood_pred === 1))
    .slice(0, 20)

  if (!rows.length) {
    return (
      <div className="text-center py-8 font-mono text-xs" style={{ color: '#1e4060' }}>
        No flood events or model alerts in this range for {zone}
      </div>
    )
  }

  const getStatus = (row) => {
    if (row.is_flood === 1 && row.flood_pred === 1) return { label: 'DETECTED',    color: '#00e87a' }
    if (row.is_flood === 1 && row.flood_pred === 0) return { label: 'MISSED',      color: '#ff3344' }
    return                                                  { label: 'FALSE ALARM', color: '#ffaa00' }
  }

  return (
    <div className="overflow-hidden rounded-xl" style={{ border: '1px solid rgba(0,204,255,0.1)' }}>
      {/* Header */}
      <div
        className="grid grid-cols-5 px-4 py-2 font-mono text-[9px] tracking-widest"
        style={{ background: 'rgba(0,204,255,0.05)', color: '#3a6a8a', borderBottom: '1px solid rgba(0,204,255,0.08)' }}
      >
        <span>DATE · TIME</span>
        <span>RAIN (mm)</span>
        <span>FLOOD PRED</span>
        <span>ACTUAL FLOOD</span>
        <span>STATUS</span>
      </div>

      {rows.map((row, i) => {
        const status = getStatus(row)
        return (
          <motion.div
            key={i}
            className="grid grid-cols-5 px-4 py-2.5 font-mono text-xs items-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.03 }}
            style={{
              background: i % 2 === 0 ? 'transparent' : 'rgba(0,204,255,0.02)',
              borderBottom: '1px solid rgba(0,204,255,0.04)',
            }}
          >
            <div>
              <div style={{ color: '#b8d4e8' }}>{format(parseISO(row.time), 'MMM d')}</div>
              <div style={{ color: '#3a6a8a', fontSize: '9px' }}>{format(parseISO(row.time), 'HH:mm')}</div>
              {row.event_label && <EventBadge label={row.event_label} />}
            </div>
            <div style={{ color: '#00ccff' }}>{row.precipitation.toFixed(1)}</div>
            <div>
              <span
                className="px-2 py-0.5 rounded-full text-[10px]"
                style={{
                  background: row.flood_pred === 1 ? 'rgba(255,51,68,0.12)' : 'rgba(0,232,122,0.08)',
                  color:      row.flood_pred === 1 ? '#ff3344' : '#00e87a',
                  border:     `1px solid ${row.flood_pred === 1 ? 'rgba(255,51,68,0.3)' : 'rgba(0,232,122,0.2)'}`,
                }}
              >
                {row.flood_pred === 1 ? 'FLOOD' : 'CLEAR'}
              </span>
            </div>
            <div>
              <span
                className="px-2 py-0.5 rounded-full text-[10px]"
                style={{
                  background: row.is_flood === 1 ? 'rgba(255,51,68,0.12)' : 'rgba(0,232,122,0.08)',
                  color:      row.is_flood === 1 ? '#ff3344' : '#00e87a',
                  border:     `1px solid ${row.is_flood === 1 ? 'rgba(255,51,68,0.3)' : 'rgba(0,232,122,0.2)'}`,
                }}
              >
                {row.is_flood === 1 ? 'FLOOD' : 'NO FLOOD'}
              </span>
            </div>
            <div>
              <span
                className="px-2 py-0.5 rounded-full text-[10px]"
                style={{
                  background: `${status.color}12`,
                  color: status.color,
                  border: `1px solid ${status.color}30`,
                }}
              >
                {status.label}
              </span>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}

// ── Main Chart ─────────────────────────────────────────────────────────────────
function HistoricalChart({ data, zone }) {
  const zoneData = data.filter(d => d.zone === zone)

  const chartData = useMemo(() => {
    return zoneData.map(d => ({
      label:     format(parseISO(d.time), 'MMM d HH:mm'),
      predicted: parseFloat((d.predicted_score * 100).toFixed(1)),
      actual:    parseFloat((d.actual_score * 100).toFixed(1)),
      precip:    parseFloat(d.precipitation.toFixed(2)),
    }))
  }, [zoneData])

  const color = ZONE_COLORS[zone]

  return (
    <div style={{ height: 220 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="precipGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor="#00ccff" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#00ccff" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 8, fill: '#3a6a8a', fontFamily: '"JetBrains Mono"' }}
            interval={Math.floor(chartData.length / 8)}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fontSize: 8, fill: '#3a6a8a', fontFamily: '"JetBrains Mono"' }}
            tickLine={false}
            axisLine={false}
            domain={[0, 100]}
            tickFormatter={v => `${v}%`}
          />
          <Tooltip content={<ArchiveTooltip />} />
          <Legend
            wrapperStyle={{ fontFamily: '"JetBrains Mono"', fontSize: '9px', color: '#3a6a8a', paddingTop: '8px' }}
          />
          <ReferenceLine y={60} stroke="rgba(255,51,68,0.3)" strokeDasharray="4 4" label={{ value: 'HIGH', fill: '#ff334460', fontSize: 8 }} />
          <ReferenceLine y={30} stroke="rgba(255,170,0,0.2)"  strokeDasharray="4 4" />
          <Area
            type="monotone"
            dataKey="precip"
            name="Rain (mm)"
            stroke="#00ccff"
            strokeWidth={1}
            fill="url(#precipGrad)"
            dot={false}
            yAxisId={0}
          />
          <Line
            type="monotone"
            dataKey="predicted"
            name="AI Forecast (%)"
            stroke={color}
            strokeWidth={2}
            dot={false}
            strokeDasharray="5 3"
          />
          <Line
            type="monotone"
            dataKey="actual"
            name="Actual Risk (%)"
            stroke="#e8f4ff"
            strokeWidth={1.5}
            dot={false}
            opacity={0.7}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────
export default function Archive() {
  const [start, setStart] = useState('2022-11-01')
  const [end,   setEnd]   = useState('2022-12-31')
  const [zone,  setZone]  = useState('Low Relief')
  const [data,  setData]  = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api.getHistorical(start, end).then(d => {
      if (!cancelled) { setData(d); setLoading(false) }
    }).catch(() => setLoading(false))
    return () => { cancelled = true }
  }, [start, end])

  return (
    <div
      className="w-full h-full overflow-y-auto"
      style={{ background: '#020d1a' }}
    >
      {/* Subtle background texture */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: `
            radial-gradient(ellipse 80% 60% at 20% 20%, rgba(0,60,120,0.12) 0%, transparent 60%),
            radial-gradient(ellipse 60% 80% at 80% 80%, rgba(0,30,60,0.10) 0%, transparent 60%)
          `,
        }}
      />

      <div className="relative max-w-6xl mx-auto px-6 py-8">

        {/* Page header */}
        <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="font-mono text-xs tracking-widest mb-1" style={{ color: '#3a6a8a' }}>
            BAKU SENTINEL / ARCHIVE
          </div>
          <h1 className="font-display text-5xl tracking-widest leading-none" style={{ color: '#e8f4ff' }}>
            HISTORICAL RECORD
          </h1>
          <p className="font-ui text-sm mt-2 max-w-xl" style={{ color: '#3a6a8a' }}>
            Browse past rain events, compare AI predictions against real outcomes, and track how Baku's risk zones evolved over time.
          </p>
        </motion.div>

        {/* Controls bar */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass rounded-2xl px-5 py-4 mb-6 flex flex-wrap items-center justify-between gap-4"
        >
          <DateRangePicker
            start={start} end={end}
            onStartChange={setStart} onEndChange={setEnd}
          />

          <div className="flex gap-2 flex-wrap">
            {ZONES.map(z => (
              <ZonePill key={z} zone={z} active={zone === z} onClick={() => setZone(z)} />
            ))}
          </div>

          {loading && (
            <div className="font-mono text-xs" style={{ color: '#00ccff' }}>
              <span style={{ animation: 'breathe 1s ease-in-out infinite' }}>⬤</span> Loading…
            </div>
          )}
        </motion.div>

        {/* Summary stats */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="mb-6"
        >
          <SummaryStats data={data} zone={zone} />
        </motion.div>

        {/* Chart */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass rounded-2xl px-5 py-5 mb-6"
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="font-mono text-[9px] tracking-widest mb-0.5" style={{ color: '#3a6a8a' }}>
                AI FORECAST vs ACTUAL OUTCOME
              </div>
              <div className="font-display text-xl tracking-wide" style={{ color: ZONE_COLORS[zone] }}>
                {zone}
              </div>
            </div>
            <div
              className="font-mono text-[9px] px-3 py-1.5 rounded-full"
              style={{ background: 'rgba(0,204,255,0.06)', border: '1px solid rgba(0,204,255,0.15)', color: '#3a6a8a' }}
            >
              XGBoost · ROS + Optuna · F2-Optimised
            </div>
          </div>

          {data.length > 0 ? (
            <HistoricalChart data={data} zone={zone} />
          ) : (
            <div className="h-52 flex items-center justify-center font-mono text-xs" style={{ color: '#1e4060' }}>
              {loading ? 'Loading historical data…' : 'No data in range'}
            </div>
          )}
        </motion.div>

        {/* Comparison table */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="glass rounded-2xl px-5 py-5"
        >
          <div className="mb-4">
            <div className="font-mono text-[9px] tracking-widest mb-0.5" style={{ color: '#3a6a8a' }}>
              NOTABLE EVENTS — PREDICTED VS ACTUAL
            </div>
            <div className="font-display text-xl tracking-wide" style={{ color: '#b8d4e8' }}>
              EVENT LOG
            </div>
          </div>
          <ComparisonTable data={data} zone={zone} />
        </motion.div>

        {/* Footer note */}
        <div className="text-center py-6 font-mono text-[10px]" style={{ color: '#1e4060' }}>
          Historical data sourced from Open-Meteo Archive API · 2020–2026 ·
          Actual outcome derived from river_discharge {">"} 1.0 m³/s compound condition
        </div>
      </div>
    </div>
  )
}
