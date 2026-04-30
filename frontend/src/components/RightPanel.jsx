import { useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, RadialBarChart, RadialBar, PolarAngleAxis,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import { useForecastStore } from '../store/forecastStore.js'

// ── Custom Tooltip ────────────────────────────────────────────────────────────
function RainTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div
      className="glass px-3 py-2 rounded-lg"
      style={{ fontSize: '11px', border: '1px solid rgba(0,204,255,0.2)' }}
    >
      <div className="font-mono" style={{ color: '#00ccff' }}>{label}</div>
      <div className="font-mono" style={{ color: '#b8d4e8' }}>
        {payload[0].value.toFixed(1)} mm
      </div>
    </div>
  )
}

// ── Section Header ────────────────────────────────────────────────────────────
function SectionHeader({ icon, title, subtitle }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span style={{ fontSize: '14px' }}>{icon}</span>
      <div>
        <div className="font-ui text-xs font-semibold tracking-wide" style={{ color: '#b8d4e8' }}>
          {title}
        </div>
        {subtitle && (
          <div className="font-mono text-[9px]" style={{ color: '#3a6a8a' }}>
            {subtitle}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Rain Intensity Chart ──────────────────────────────────────────────────────
function RainChart({ data }) {
  const chartData = useMemo(() => {
    // Show Low Relief (coastal zone) precipitation — most at-risk
    const lowRelief = data.filter(d => d.zone === 'Low Relief').slice(0, 20)
    return lowRelief.map(d => ({
      label: format(parseISO(d.time), 'MMM d HH:mm'),
      mm:    parseFloat(d.precipitation.toFixed(2)),
    }))
  }, [data])

  const maxMm = Math.max(...chartData.map(d => d.mm), 5)

  return (
    <div>
      <SectionHeader
        icon="🌧️"
        title="Rain Intensity"
        subtitle="COASTAL ZONE · NEXT 5 DAYS"
      />
      <div style={{ height: 110 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
            <defs>
              <linearGradient id="rainGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#00ccff" stopOpacity={0.5} />
                <stop offset="100%" stopColor="#00ccff" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 8, fill: '#3a6a8a', fontFamily: '"JetBrains Mono"' }}
              interval={3}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[0, maxMm + 2]}
              tick={{ fontSize: 8, fill: '#3a6a8a', fontFamily: '"JetBrains Mono"' }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<RainTooltip />} />
            <Area
              type="monotone"
              dataKey="mm"
              stroke="#00ccff"
              strokeWidth={1.5}
              fill="url(#rainGrad)"
              dot={false}
              activeDot={{ r: 3, fill: '#00ccff', stroke: 'none' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ── Soil Absorption Gauge ─────────────────────────────────────────────────────
function SoilGauge({ value }) {
  // value 0–1 (soil moisture fraction)
  const pct = Math.round(value * 100)
  const gaugeColor = pct > 70 ? '#ff3344' : pct > 45 ? '#ffaa00' : '#00e87a'

  const gaugeData = [{ name: 'soil', value: pct, fill: gaugeColor }]

  return (
    <div>
      <SectionHeader
        icon="💧"
        title="Ground Absorption"
        subtitle="HOW SATURATED IS THE SOIL?"
      />
      <div className="flex items-center gap-4">
        <div style={{ width: 100, height: 100, flexShrink: 0 }}>
          <RadialBarChart
            width={100}
            height={100}
            cx={50}
            cy={50}
            innerRadius={30}
            outerRadius={46}
            startAngle={220}
            endAngle={-40}
            data={gaugeData}
          >
            <PolarAngleAxis
              type="number"
              domain={[0, 100]}
              angleAxisId={0}
              tick={false}
            />
            <RadialBar
              background={{ fill: 'rgba(0,204,255,0.06)' }}
              dataKey="value"
              cornerRadius={4}
              angleAxisId={0}
            />
          </RadialBarChart>
          {/* Center value */}
          <div
            className="font-display text-xl text-center"
            style={{
              color: gaugeColor,
              marginTop: '-62px',
              textShadow: `0 0 12px ${gaugeColor}80`,
            }}
          >
            {pct}%
          </div>
          <div style={{ marginTop: '42px' }} />
        </div>

        <div className="flex-1 text-xs" style={{ color: '#3a6a8a' }}>
          <div
            className="font-ui text-sm font-semibold mb-1"
            style={{ color: gaugeColor }}
          >
            {pct > 70 ? 'Near Saturation' : pct > 45 ? 'Moderate' : 'Good Drainage'}
          </div>
          <div className="font-ui leading-relaxed">
            {pct > 70
              ? 'Ground is nearly full. Even light rain may cause surface runoff.'
              : pct > 45
                ? 'Soil is moist. Heavy rain could pool in low areas.'
                : 'Ground can absorb rain well. Low flood risk from soil.'}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Weather Stats ─────────────────────────────────────────────────────────────
function StatCard({ icon, value, unit, label, color = '#00ccff' }) {
  return (
    <div
      className="flex-1 rounded-xl px-3 py-2.5 text-center"
      style={{
        background: `${color}0a`,
        border: `1px solid ${color}22`,
      }}
    >
      <div style={{ fontSize: '16px', marginBottom: '2px' }}>{icon}</div>
      <div className="font-display text-lg leading-none" style={{ color }}>
        {value}<span className="text-xs">{unit}</span>
      </div>
      <div className="font-mono text-[9px] mt-1 leading-tight" style={{ color: '#3a6a8a' }}>
        {label}
      </div>
    </div>
  )
}

// ── Risk Score Bar ────────────────────────────────────────────────────────────
function RiskBar({ zone, score, level }) {
  const color = level === 'HIGH' ? '#ff3344' : level === 'MEDIUM' ? '#ffaa00' : '#00e87a'
  const pct   = Math.round(score * 100)

  return (
    <div className="mb-2">
      <div className="flex justify-between items-center mb-1">
        <span className="font-ui text-[10px]" style={{ color: '#3a6a8a' }}>{zone}</span>
        <span className="font-mono text-[10px] font-bold" style={{ color }}>{pct}%</span>
      </div>
      <div
        className="w-full rounded-full overflow-hidden"
        style={{ height: '5px', background: 'rgba(0,204,255,0.08)' }}
      >
        <motion.div
          className="h-full rounded-full"
          style={{ background: color, boxShadow: `0 0 6px ${color}80` }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}

// ── Model Confidence ──────────────────────────────────────────────────────────
function ModelBadge() {
  return (
    <div
      className="px-3 py-2.5 rounded-xl"
      style={{ background: 'rgba(0,204,255,0.05)', border: '1px solid rgba(0,204,255,0.12)' }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-[9px] tracking-widest" style={{ color: '#3a6a8a' }}>
          AI MODEL CONFIDENCE
        </span>
        <span
          className="font-mono text-[9px] px-2 py-0.5 rounded"
          style={{ background: 'rgba(0,232,122,0.12)', color: '#00e87a', border: '1px solid rgba(0,232,122,0.25)' }}
        >
          CALIBRATED
        </span>
      </div>
      <div className="flex gap-3 text-center">
        {[
          { label: 'AUC-PR',  value: '45.7%' },
          { label: 'AUC-ROC', value: '93.2%' },
          { label: 'CV Folds', value: '5×TSS' },
        ].map(m => (
          <div key={m.label} className="flex-1">
            <div className="font-display text-base leading-none" style={{ color: '#00ccff' }}>{m.value}</div>
            <div className="font-mono text-[8px] mt-0.5" style={{ color: '#3a6a8a' }}>{m.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Public Component ──────────────────────────────────────────────────────────
export default function RightPanel() {
  const currentSlot = useForecastStore(s => s.currentSlot)
  const forecast    = useForecastStore(s => s.forecast)
  const loading     = useForecastStore(s => s.loading)

  const lowZone = currentSlot.find(z => z.zone === 'Low Relief')
  const temp    = lowZone ? lowZone.temperature_2m.toFixed(0) : '—'
  const wind    = lowZone ? lowZone.wind_speed_10m.toFixed(0) : '—'
  const humid   = lowZone ? lowZone.relative_humidity_2m.toFixed(0) : '—'
  const soilVal = lowZone ? lowZone.soil_moisture_0_to_7cm : 0.15

  return (
    <div
      className="glass h-full rounded-2xl flex flex-col overflow-hidden scan-overlay animate-rise"
      style={{ animationDelay: '0.15s' }}
    >
      {/* Header */}
      <div
        className="px-4 py-3 flex items-center gap-2"
        style={{ borderBottom: '1px solid rgba(0,204,255,0.08)' }}
      >
        <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#00ccff', boxShadow: '0 0 6px #00ccff' }} />
        <span className="font-display tracking-widest text-sm" style={{ color: '#00ccff' }}>
          SENSOR FEED
        </span>
        {loading && <span className="font-mono text-[9px] ml-auto" style={{ color: '#3a6a8a' }}>LOADING…</span>}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-5">

        {/* Live conditions */}
        <div>
          <div className="font-mono text-[9px] tracking-widest mb-3" style={{ color: '#3a6a8a' }}>
            LIVE CONDITIONS · COASTAL ZONE
          </div>
          <div className="flex gap-2">
            <StatCard icon="🌡️" value={temp} unit="°C" label="TEMPERATURE" color="#00ccff" />
            <StatCard icon="💨" value={wind} unit="km/h" label="WIND SPEED"  color="#9966ff" />
            <StatCard icon="💧" value={humid} unit="%" label="HUMIDITY"    color="#00cccc" />
          </div>
        </div>

        {/* Divider */}
        <div style={{ height: '1px', background: 'linear-gradient(90deg, transparent, rgba(0,204,255,0.12), transparent)' }} />

        {/* Rain chart */}
        {forecast.length > 0 && <RainChart data={forecast} />}

        {/* Divider */}
        <div style={{ height: '1px', background: 'linear-gradient(90deg, transparent, rgba(0,204,255,0.12), transparent)' }} />

        {/* Soil gauge */}
        <SoilGauge value={soilVal} />

        {/* Divider */}
        <div style={{ height: '1px', background: 'linear-gradient(90deg, transparent, rgba(0,204,255,0.12), transparent)' }} />

        {/* Zone risk bars */}
        <div>
          <SectionHeader icon="📊" title="Zone Risk Scores" subtitle="ALL 3 TERRAIN ZONES" />
          {currentSlot.map(z => (
            <RiskBar key={z.zone} zone={z.zone} score={z.risk_score} level={z.risk_level} />
          ))}
        </div>

        {/* Model badge */}
        <ModelBadge />
      </div>
    </div>
  )
}
