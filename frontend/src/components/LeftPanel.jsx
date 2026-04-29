import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { useForecastStore } from '../store/forecastStore.js'
import { format, addHours, parseISO } from 'date-fns'

// Baku districts mapped to terrain zones
const DISTRICTS = [
  { name: 'Sabail',      zone: 'Low Relief',      emoji: '🏙️', desc: 'Old City & Seafront' },
  { name: 'Binəqədi',   zone: 'Low Relief',      emoji: '⚓', desc: 'Port District' },
  { name: 'Suraxanı',   zone: 'Low Relief',      emoji: '🌊', desc: 'East Coastal' },
  { name: 'Yasamal',    zone: 'Moderate Relief',  emoji: '🏘️', desc: 'Mid-City Residential' },
  { name: 'Nəsimi',     zone: 'Moderate Relief',  emoji: '🕌', desc: 'Historic Centre' },
  { name: 'Xətai',      zone: 'Moderate Relief',  emoji: '🌳', desc: 'Eastern Quarter' },
  { name: 'Nərimanov',  zone: 'High Relief',      emoji: '🏔️', desc: 'Northern Heights' },
  { name: 'Sabunçu',    zone: 'High Relief',      emoji: '⛰️', desc: 'Plateau District' },
  { name: 'Abşeron',    zone: 'High Relief',      emoji: '🌿', desc: 'Outer Highlands' },
]

const RISK_DISPLAY = {
  HIGH:   { label: 'Flood Risk',    bg: 'rgba(255,51,68,0.15)',   border: 'rgba(255,51,68,0.4)',   text: '#ff3344', dot: '#ff3344' },
  MEDIUM: { label: 'Puddles',       bg: 'rgba(255,170,0,0.12)',   border: 'rgba(255,170,0,0.35)',  text: '#ffaa00', dot: '#ffaa00' },
  LOW:    { label: 'All Clear',     bg: 'rgba(0,232,122,0.08)',   border: 'rgba(0,232,122,0.25)',  text: '#00e87a', dot: '#00e87a' },
}

const STATUS_CFG = {
  HIGH:   { glow: 'status-red',   ring: '#ff3344' },
  MEDIUM: { glow: 'status-amber', ring: '#ffaa00' },
  LOW:    { glow: 'status-green', ring: '#00e87a' },
}

function StatusBadge({ status }) {
  const cfg = STATUS_CFG[status.level] ?? STATUS_CFG.LOW

  return (
    <div className="text-center py-5 px-4">
      {/* Outer ring */}
      <div
        className="relative w-32 h-32 mx-auto rounded-full flex items-center justify-center"
        style={{
          border: `2px solid ${cfg.ring}22`,
          background: `radial-gradient(circle, ${cfg.ring}12 0%, transparent 70%)`,
        }}
      >
        {/* Inner ring */}
        <div
          className={`w-24 h-24 rounded-full flex items-center justify-center ${cfg.glow}`}
          style={{
            border: `2px solid ${cfg.ring}`,
            background: `radial-gradient(circle, ${cfg.ring}20 0%, ${cfg.ring}06 60%, transparent 100%)`,
          }}
        >
          {/* Status icon */}
          <div style={{ fontSize: '2.5rem', lineHeight: 1 }}>
            {status.level === 'HIGH' ? '🚨' : status.level === 'MEDIUM' ? '⚠️' : '✅'}
          </div>
        </div>

        {/* Rotating ring */}
        <div
          className="absolute inset-0 rounded-full animate-spin-slow"
          style={{
            border: `1px dashed ${cfg.ring}30`,
          }}
        />
      </div>

      <div
        className="font-display text-3xl tracking-widest mt-3 leading-none"
        style={{ color: cfg.ring, textShadow: `0 0 20px ${cfg.ring}80` }}
      >
        {status.label}
      </div>
      <div className="font-ui text-xs mt-1 tracking-wider" style={{ color: '#3a6a8a' }}>
        CITY-WIDE STATUS
      </div>
    </div>
  )
}

function DistrictRow({ district, riskLevel, score, index }) {
  const risk = RISK_DISPLAY[riskLevel] ?? RISK_DISPLAY.LOW

  return (
    <motion.div
      className="flex items-center gap-3 px-3 py-2 rounded-lg"
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04, duration: 0.25 }}
      style={{
        background: risk.bg,
        border: `1px solid ${risk.border}`,
        marginBottom: '4px',
      }}
    >
      <span style={{ fontSize: '1rem', lineHeight: 1 }}>{district.emoji}</span>
      <div className="flex-1 min-w-0">
        <div className="font-ui text-xs font-semibold leading-tight truncate" style={{ color: '#b8d4e8' }}>
          {district.name}
        </div>
        <div className="font-mono text-[9px] leading-tight truncate" style={{ color: '#3a6a8a' }}>
          {district.desc}
        </div>
      </div>

      {/* Risk badge */}
      <div className="flex items-center gap-1.5 shrink-0">
        <div
          className="w-1.5 h-1.5 rounded-full"
          style={{
            background: risk.dot,
            boxShadow: `0 0 6px ${risk.dot}`,
            animation: riskLevel === 'HIGH' ? 'breathe 1s ease-in-out infinite' : undefined,
          }}
        />
        <span className="font-mono text-[10px] font-bold" style={{ color: risk.text }}>
          {risk.label}
        </span>
      </div>
    </motion.div>
  )
}

function NextEventBanner({ forecast }) {
  const nextHighSlot = useMemo(() => {
    return forecast.find(f => f.zone === 'Low Relief' && f.risk_level !== 'LOW')
  }, [forecast])

  if (!nextHighSlot) return null

  const when = nextHighSlot.time ? format(parseISO(nextHighSlot.time), 'EEE MMM d, HH:mm') : '—'
  const isHigh = nextHighSlot.risk_level === 'HIGH'

  return (
    <div
      className="mx-3 mb-3 px-3 py-2.5 rounded-lg"
      style={{
        background: isHigh ? 'rgba(255,51,68,0.08)' : 'rgba(255,170,0,0.08)',
        border: `1px solid ${isHigh ? 'rgba(255,51,68,0.25)' : 'rgba(255,170,0,0.25)'}`,
      }}
    >
      <div className="font-mono text-[9px] tracking-widest mb-1" style={{ color: '#3a6a8a' }}>
        NEXT ALERT WINDOW
      </div>
      <div className="font-ui text-xs font-semibold" style={{ color: isHigh ? '#ff3344' : '#ffaa00' }}>
        {isHigh ? '🚨' : '⚠️'} {when}
      </div>
      <div className="font-mono text-[9px] mt-0.5" style={{ color: '#3a6a8a' }}>
        Coastal zones at {nextHighSlot.risk_level} risk · {(nextHighSlot.risk_score * 100).toFixed(0)}% probability
      </div>
    </div>
  )
}

export default function LeftPanel() {
  const overallStatus = useForecastStore(s => s.overallStatus)
  const currentSlot   = useForecastStore(s => s.currentSlot)
  const forecast      = useForecastStore(s => s.forecast)
  const loading       = useForecastStore(s => s.loading)

  // Map zone risk levels to districts
  const districtsWithRisk = useMemo(() => {
    return DISTRICTS.map(d => {
      const zoneRow = currentSlot.find(z => z.zone === d.zone)
      return {
        ...d,
        riskLevel: zoneRow?.risk_level ?? 'LOW',
        score:     zoneRow?.risk_score ?? 0,
      }
    }).sort((a, b) => {
      const order = { HIGH: 0, MEDIUM: 1, LOW: 2 }
      return order[a.riskLevel] - order[b.riskLevel]
    })
  }, [currentSlot])

  return (
    <div
      className="glass h-full rounded-2xl flex flex-col overflow-hidden scan-overlay animate-rise"
      style={{ animationDelay: '0.1s' }}
    >
      {/* Header */}
      <div
        className="px-4 py-3 flex items-center gap-2"
        style={{ borderBottom: '1px solid rgba(0,204,255,0.08)' }}
      >
        <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#00ccff', boxShadow: '0 0 6px #00ccff' }} />
        <span className="font-display tracking-widest text-sm" style={{ color: '#00ccff' }}>
          CITY WATCH
        </span>
        <div
          className="ml-auto font-mono text-[9px] tracking-wider"
          style={{ color: '#3a6a8a' }}
        >
          {loading ? 'LOADING…' : 'LIVE'}
        </div>
      </div>

      {/* Status badge */}
      <StatusBadge status={overallStatus} />

      {/* Divider */}
      <div className="mx-4 mb-3" style={{ height: '1px', background: 'linear-gradient(90deg, transparent, rgba(0,204,255,0.15), transparent)' }} />

      {/* Districts header */}
      <div className="px-4 mb-2">
        <div className="font-mono text-[9px] tracking-widest" style={{ color: '#3a6a8a' }}>
          NEIGHBORHOOD WATCH — 9 DISTRICTS
        </div>
      </div>

      {/* District list */}
      <div className="flex-1 overflow-y-auto px-3 pb-2" style={{ scrollbarWidth: 'thin' }}>
        {districtsWithRisk.map((d, i) => (
          <DistrictRow key={d.name} district={d} riskLevel={d.riskLevel} score={d.score} index={i} />
        ))}
      </div>

      {/* Next event */}
      <div style={{ borderTop: '1px solid rgba(0,204,255,0.08)' }} className="pt-2">
        <NextEventBanner forecast={forecast} />
      </div>

      {/* Footer note */}
      <div className="px-4 pb-3 text-center">
        <div className="font-ui text-[9px]" style={{ color: '#1e4060' }}>
          Risk zones derived from GADM terrain topology · Updated every 6 hours
        </div>
      </div>
    </div>
  )
}
