import BakuScene from '../components/BakuScene.jsx'
import LeftPanel from '../components/LeftPanel.jsx'
import RightPanel from '../components/RightPanel.jsx'
import TimelineSlider from '../components/TimelineSlider.jsx'
import { useForecastStore } from '../store/forecastStore.js'

export default function Dashboard() {
  const overallStatus = useForecastStore(s => s.overallStatus)

  const alertBorder = {
    HIGH:   'rgba(255,51,68,0.35)',
    MEDIUM: 'rgba(255,170,0,0.25)',
    LOW:    'transparent',
  }[overallStatus.level] ?? 'transparent'

  return (
    <div className="relative w-full h-full overflow-hidden">

      {/* ── 3D Scene fills the full viewport ───────────────────────────────── */}
      <BakuScene />

      {/* ── Vignette overlay (darkens edges so panels pop) ──────────────────── */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `
            radial-gradient(ellipse 60% 50% at 50% 50%, transparent 30%, rgba(2,13,26,0.55) 100%),
            linear-gradient(to bottom, rgba(2,13,26,0.5) 0%, transparent 12%, transparent 80%, rgba(2,13,26,0.7) 100%)
          `,
        }}
      />

      {/* ── HIGH alert pulsing border ──────────────────────────────────────── */}
      {overallStatus.level === 'HIGH' && (
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            border: `2px solid ${alertBorder}`,
            animation: 'pulse-glow-red 1.2s ease-in-out infinite',
            borderRadius: 0,
            zIndex: 10,
          }}
        />
      )}

      {/* ── Floating UI panels ────────────────────────────────────────────── */}
      <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 20 }}>

        {/* Left panel */}
        <div
          className="absolute top-4 bottom-24 pointer-events-auto"
          style={{ left: '16px', width: '320px' }}
        >
          <LeftPanel />
        </div>

        {/* Right panel */}
        <div
          className="absolute top-4 bottom-24 pointer-events-auto"
          style={{ right: '16px', width: '320px' }}
        >
          <RightPanel />
        </div>

        {/* Bottom timeline slider */}
        <div
          className="absolute pointer-events-auto"
          style={{ bottom: '12px', left: '352px', right: '352px' }}
        >
          <TimelineSlider />
        </div>

        {/* Centre top — location badge */}
        <div
          className="absolute top-4 left-1/2 -translate-x-1/2 pointer-events-none"
          style={{ zIndex: 30 }}
        >
          <div
            className="glass rounded-full px-5 py-2 flex items-center gap-3"
            style={{ border: '1px solid rgba(0,204,255,0.15)' }}
          >
            <div
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: '#00ccff', boxShadow: '0 0 8px #00ccff', animation: 'breathe 1.5s ease-in-out infinite' }}
            />
            <span className="font-display tracking-widest text-sm" style={{ color: '#00ccff' }}>
              ABSHERON PENINSULA
            </span>
            <span className="font-mono text-[10px]" style={{ color: '#3a6a8a' }}>
              40.41°N · 49.87°E
            </span>
          </div>
        </div>

        {/* Scale legend - bottom centre */}
        <div
          className="absolute pointer-events-none flex items-center gap-4"
          style={{ bottom: '128px', left: '50%', transform: 'translateX(-50%)' }}
        >
          {[
            { color: '#00e87a', label: 'Upland · Low Risk' },
            { color: '#ffaa00', label: 'Mid-slope · Moderate' },
            { color: '#ff3344', label: 'Coastal · High Risk' },
          ].map(item => (
            <div key={item.label} className="flex items-center gap-1.5">
              <div
                className="w-2.5 h-2.5 rounded-sm"
                style={{ background: item.color, boxShadow: `0 0 6px ${item.color}` }}
              />
              <span className="font-mono text-[9px]" style={{ color: '#3a6a8a' }}>{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
