import { useRef, useCallback, useMemo } from 'react'
import { format, addHours, parseISO } from 'date-fns'
import { useForecastStore } from '../store/forecastStore.js'

const TOTAL_SLOTS = 120 // 30 days × 4 slots/day

export default function TimelineSlider() {
  const slotIndex = useForecastStore(s => s.slotIndex)
  const forecast  = useForecastStore(s => s.forecast)
  const setSlot   = useForecastStore(s => s.setSlotIndex)
  const loading   = useForecastStore(s => s.loading)

  const progress = ((slotIndex / (TOTAL_SLOTS - 1)) * 100).toFixed(1)

  const handleChange = useCallback(
    (e) => setSlot(parseInt(e.target.value, 10)),
    [setSlot]
  )

  // Current time label from forecast data
  const currentTime = useMemo(() => {
    if (!forecast.length) return '—'
    const row = forecast[slotIndex * 3]
    if (!row) return '—'
    try {
      return format(parseISO(row.time), 'EEE, MMM d · HH:mm')
    } catch {
      return '—'
    }
  }, [forecast, slotIndex])

  // Build tick marks for notable events in the forecast
  const eventTicks = useMemo(() => {
    if (!forecast.length) return []
    const ticks = []
    const seen  = new Set()
    forecast
      .filter(f => f.zone === 'Low Relief')
      .forEach((f, i) => {
        const key = `${i}`
        if (seen.has(key)) return
        if (f.risk_level === 'HIGH') {
          seen.add(key)
          ticks.push({ slot: i, level: 'HIGH', color: '#ff3344' })
        } else if (f.risk_level === 'MEDIUM' && !ticks.some(t => Math.abs(t.slot - i) < 2)) {
          seen.add(key)
          ticks.push({ slot: i, level: 'MEDIUM', color: '#ffaa00' })
        }
      })
    return ticks.slice(0, 12) // Cap number of ticks for clarity
  }, [forecast])

  if (loading) {
    return (
      <div
        className="glass rounded-2xl px-6 py-4"
        style={{ borderColor: 'rgba(0,204,255,0.08)' }}
      >
        <div className="font-mono text-xs text-center" style={{ color: '#3a6a8a' }}>
          INITIALISING TIMELINE…
        </div>
      </div>
    )
  }

  return (
    <div className="glass rounded-2xl px-6 py-4 animate-rise" style={{ animationDelay: '0.2s' }}>
      <div className="flex items-center justify-between mb-3">
        {/* Left: time display */}
        <div>
          <div className="font-mono text-[9px] tracking-widest mb-0.5" style={{ color: '#3a6a8a' }}>
            VIEWING FORECAST FOR
          </div>
          <div className="font-display text-lg tracking-wide leading-none" style={{ color: '#00ccff' }}>
            {currentTime}
          </div>
        </div>

        {/* Center: slot info */}
        <div className="text-center">
          <div className="font-mono text-[9px]" style={{ color: '#3a6a8a' }}>
            SLOT {slotIndex + 1} / {TOTAL_SLOTS}
          </div>
          <div className="font-mono text-[9px]" style={{ color: '#1e4060' }}>
            {slotIndex === 0 ? 'NOW' : slotIndex < 60 ? `+${(slotIndex * 6)}h` : `DAY ${Math.floor(slotIndex / 4) + 1}`}
          </div>
        </div>

        {/* Right: horizon labels */}
        <div className="text-right">
          <div className="font-mono text-[9px] mb-0.5" style={{ color: '#3a6a8a' }}>
            {slotIndex < 60 ? '15-DAY LIVE FORECAST' : '30-DAY CLIMATOLOGICAL'}
          </div>
          <div className="font-mono text-[9px]" style={{ color: '#1e4060' }}>
            {slotIndex < 60 ? 'Open-Meteo API' : 'Seasonal Extension Model'}
          </div>
        </div>
      </div>

      {/* Tick marks for events */}
      <div className="relative mb-2">
        <div className="relative h-3">
          {/* Midpoint marker (15-day boundary) */}
          <div
            className="absolute top-0 bottom-0 w-px"
            style={{
              left: '50%',
              background: 'rgba(0,204,255,0.2)',
              transform: 'translateX(-50%)',
            }}
          />
          <div
            className="absolute font-mono text-[8px]"
            style={{ left: '50%', transform: 'translateX(-50%)', top: '1px', color: '#1e4060' }}
          >
            DAY 15
          </div>

          {/* Event ticks */}
          {eventTicks.map((tick, i) => (
            <div
              key={i}
              className="absolute top-0 bottom-0 w-0.5 rounded-full cursor-pointer"
              style={{
                left: `${(tick.slot / (TOTAL_SLOTS - 1)) * 100}%`,
                background: tick.color,
                boxShadow: `0 0 4px ${tick.color}`,
                opacity: 0.7,
              }}
              title={`${tick.level} risk at slot ${tick.slot}`}
              onClick={() => setSlot(tick.slot)}
            />
          ))}
        </div>
      </div>

      {/* Slider */}
      <div className="relative">
        <input
          type="range"
          className="sentinel-slider"
          min={0}
          max={TOTAL_SLOTS - 1}
          value={slotIndex}
          onChange={handleChange}
          style={{ '--progress': `${progress}%` }}
        />
      </div>

      {/* Axis labels */}
      <div className="flex justify-between mt-1.5">
        <span className="font-mono text-[9px]" style={{ color: '#3a6a8a' }}>NOW</span>
        <span className="font-mono text-[9px]" style={{ color: '#3a6a8a' }}>+7 DAYS</span>
        <span className="font-mono text-[9px]" style={{ color: '#3a6a8a' }}>+15 DAYS</span>
        <span className="font-mono text-[9px]" style={{ color: '#3a6a8a' }}>+22 DAYS</span>
        <span className="font-mono text-[9px]" style={{ color: '#3a6a8a' }}>+30 DAYS</span>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-2.5 pt-2.5" style={{ borderTop: '1px solid rgba(0,204,255,0.06)' }}>
        {[
          { color: '#ff3344', label: 'Flood Alert' },
          { color: '#ffaa00', label: 'Watch' },
          { color: '#3a6a8a', label: 'All Clear' },
          { color: 'rgba(0,204,255,0.3)', label: 'Day 15 Boundary' },
        ].map(item => (
          <div key={item.label} className="flex items-center gap-1.5">
            <div
              className="w-2 h-2 rounded-full"
              style={{ background: item.color, boxShadow: `0 0 4px ${item.color}` }}
            />
            <span className="font-mono text-[9px]" style={{ color: '#3a6a8a' }}>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
