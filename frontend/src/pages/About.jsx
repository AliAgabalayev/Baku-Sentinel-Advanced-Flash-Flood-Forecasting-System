import { motion } from 'framer-motion'

const TEAM = [
  {
    name: 'Ali Agabalazade',
    role: 'Lead ML / Data Engineer',
    icon: '⚙️',
    tasks: ['XGBoost model', '30-day forecast pipeline', 'Sampling strategy', 'Optuna optimisation'],
    color: '#00ccff',
  },
  {
    name: 'Nigar Rustamova',
    role: 'Data Analyst · Geospatial',
    icon: '🗺️',
    tasks: ['Zone topology (GADM)', 'Silver/Gold ETL pipeline', 'Feature engineering', 'Model training & merge'],
    color: '#00e87a',
  },
  {
    name: 'Nazrin Mammadzadeh',
    role: 'Project Manager · Docs',
    icon: '📋',
    tasks: ['README & documentation', 'Labelling strategy', 'Criteria updates', 'Project coordination'],
    color: '#9966ff',
  },
  {
    name: 'Isgandar Panahov',
    role: 'Presentation · UI Engineer',
    icon: '🖥️',
    tasks: ['Demo UI design & build', 'API integration layer', 'Data visualisation', 'Public-facing presentation'],
    color: '#ffaa00',
    highlight: true,
  },
]

const PIPELINE_STEPS = [
  {
    num: '01',
    icon: '📡',
    title: 'Live Data Ingestion',
    body: 'Every 6 hours, Baku Sentinel pulls weather and river discharge readings from the Open-Meteo API. Temperature, humidity, rain, soil moisture, and evapotranspiration are all collected across three terrain zones.',
    color: '#00ccff',
  },
  {
    num: '02',
    icon: '🧪',
    title: 'Feature Engineering',
    body: '37 predictive signals are computed — including rolling rainfall totals, soil saturation indices, and terrain cascade multipliers that model how water flows downhill from the highlands to the coastal core.',
    color: '#00e87a',
  },
  {
    num: '03',
    icon: '🤖',
    title: 'AI Risk Prediction',
    body: 'An XGBoost model — trained on 6 years of data with isotonic probability calibration — outputs a risk score for each zone every 6 hours. It is optimised to catch floods early, even at the cost of occasional false alarms.',
    color: '#9966ff',
  },
  {
    num: '04',
    icon: '🚨',
    title: 'Zone-Specific Alerts',
    body: 'Instead of a blanket city-wide warning, Sentinel issues targeted alerts per neighbourhood. The Coastal Zone (Sabail, Binəqədi) has a 6× higher baseline risk than the Upland Plateau — one alert does not fit all.',
    color: '#ffaa00',
  },
]

const TECH_STACK = [
  { name: 'XGBoost', category: 'ML Model',     icon: '🌲', desc: 'Gradient boosted trees with isotonic calibration' },
  { name: 'DuckDB',  category: 'Data Layer',    icon: '🦆', desc: 'In-process analytics DB for Bronze/Silver/Gold pipeline' },
  { name: 'Open-Meteo', category: 'Data Source', icon: '🌐', desc: 'Free weather & flood API — no key required' },
  { name: 'Optuna',  category: 'Optimisation',  icon: '🔬', desc: 'TPE hyperparameter search · 60 trials, TimeSeriesSplit' },
  { name: 'GADM',    category: 'Geospatial',    icon: '🗺️', desc: 'Terrain zone boundaries for Baku micro-zones' },
  { name: 'SRTM DEM', category: 'Elevation',    icon: '⛰️', desc: 'Digital elevation model for terrain cascade modelling' },
  { name: 'React',   category: 'Frontend',      icon: '⚛️', desc: 'Component-based UI with Zustand state management' },
  { name: 'Three.js', category: '3D Scene',     icon: '🌍', desc: 'WebGL 3D map with voxel-style risk columns' },
]

const MODEL_METRICS = [
  { label: 'AUC-PR',     value: '98.2%', desc: 'Precision-Recall area', color: '#00e87a' },
  { label: 'AUC-ROC',    value: '99.7%', desc: 'Discrimination ability', color: '#00ccff' },
  { label: 'F1 Score',   value: '79.0%', desc: 'Balanced precision/recall', color: '#9966ff' },
  { label: 'CV Folds',   value: '5×TSS', desc: 'TimeSeriesSplit validation', color: '#ffaa00' },
  { label: 'Train Rows', value: '22K',   desc: '6 years of 6-hourly data', color: '#00ccff' },
  { label: 'Features',   value: '37',    desc: 'Engineered signal columns', color: '#00e87a' },
]

function fadeIn(delay = 0) {
  return {
    initial: { opacity: 0, y: 20 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true },
    transition: { duration: 0.4, delay },
  }
}

// ── Section Title ──────────────────────────────────────────────────────────────
function SectionTitle({ tag, title, subtitle }) {
  return (
    <div className="mb-10">
      <div className="font-mono text-xs tracking-widest mb-1" style={{ color: '#3a6a8a' }}>{tag}</div>
      <h2 className="font-display text-4xl tracking-widest leading-none" style={{ color: '#e8f4ff' }}>{title}</h2>
      {subtitle && <p className="font-ui text-sm mt-2 max-w-xl" style={{ color: '#3a6a8a' }}>{subtitle}</p>}
    </div>
  )
}

export default function About() {
  return (
    <div
      className="w-full h-full overflow-y-auto"
      style={{ background: '#020d1a' }}
    >
      {/* Background glow */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: `
            radial-gradient(ellipse 70% 50% at 50% 0%, rgba(0,80,160,0.15) 0%, transparent 60%),
            radial-gradient(ellipse 50% 40% at 80% 100%, rgba(0,40,80,0.10) 0%, transparent 60%)
          `,
        }}
      />

      <div className="relative max-w-5xl mx-auto px-6 py-12">

        {/* ── HERO ──────────────────────────────────────────────────────────── */}
        <motion.div
          className="mb-20 text-center"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Logo ring */}
          <div className="relative w-24 h-24 mx-auto mb-6">
            <div
              className="absolute inset-0 rounded-full animate-spin-slow"
              style={{ border: '1px dashed rgba(0,204,255,0.25)' }}
            />
            <div
              className="absolute inset-2 rounded-full"
              style={{ border: '2px solid rgba(0,204,255,0.4)', background: 'radial-gradient(circle, rgba(0,204,255,0.12) 0%, transparent 70%)' }}
            />
            <div className="absolute inset-0 flex items-center justify-center text-4xl">🛡️</div>
          </div>

          <div className="font-display text-6xl tracking-widest leading-none mb-2" style={{ color: '#e8f4ff' }}>
            BAKU SENTINEL
          </div>
          <div
            className="font-ui text-base tracking-widest uppercase mb-5"
            style={{ color: '#00ccff', letterSpacing: '0.3em' }}
          >
            Flash Flood Intelligence System
          </div>
          <p className="font-ui text-base max-w-2xl mx-auto leading-relaxed" style={{ color: '#3a6a8a' }}>
            Baku Sentinel was built by <strong style={{ color: '#b8d4e8' }}>Team Gale</strong> to answer a question
            that standard weather apps cannot: not just whether it will rain, but whether your neighbourhood will flood.
            Using 6 years of historical data and an AI trained specifically on Baku's topography, the system gives
            zone-specific, 30-day flood risk forecasts — in plain language, for everyday citizens.
          </p>
        </motion.div>

        {/* ── WHY IT MATTERS ────────────────────────────────────────────────── */}
        <motion.section className="mb-20" {...fadeIn(0.1)}>
          <SectionTitle
            tag="THE PROBLEM"
            title="WHY BAKU FLOODS"
            subtitle="Three compounding factors make Baku uniquely vulnerable to flash flooding."
          />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              {
                icon: '🌊',
                title: 'Coastal Lowlands',
                body: 'Large parts of the city sit at or near sea level. When it rains hard, there is simply nowhere for water to drain — gravity pulls it all toward the shore.',
                color: '#00ccff',
              },
              {
                icon: '🏗️',
                title: 'Concrete Surface',
                body: "Baku is heavily urbanised. Roads, pavements, and rooftops can't absorb rain the way soil does, so water rushes directly into streets and tunnels — sometimes within minutes.",
                color: '#ff3344',
              },
              {
                icon: '⛰️',
                title: 'Terrain Cascade',
                body: 'Elevation drops from 200 m in the west to 0 m at the coast. Rain that falls on the upland plateau flows downhill and accelerates into the lowland core, arriving long after the rain stops.',
                color: '#ffaa00',
              },
            ].map(card => (
              <motion.div
                key={card.title}
                className="glass rounded-2xl p-5"
                {...fadeIn(0.15)}
              >
                <div style={{ fontSize: '2rem', marginBottom: '12px' }}>{card.icon}</div>
                <h3 className="font-display text-xl tracking-wide mb-2" style={{ color: card.color }}>{card.title}</h3>
                <p className="font-ui text-sm leading-relaxed" style={{ color: '#3a6a8a' }}>{card.body}</p>
              </motion.div>
            ))}
          </div>
        </motion.section>

        {/* ── HOW IT WORKS ──────────────────────────────────────────────────── */}
        <motion.section className="mb-20" {...fadeIn(0.1)}>
          <SectionTitle
            tag="UNDER THE HOOD"
            title="HOW IT WORKS"
            subtitle="Four stages transform raw weather data into a forecast you can act on."
          />
          <div className="relative">
            {/* Connector line */}
            <div
              className="absolute left-8 top-8 bottom-8 w-px hidden md:block"
              style={{ background: 'linear-gradient(to bottom, rgba(0,204,255,0.3), rgba(0,204,255,0.05))' }}
            />
            <div className="flex flex-col gap-5">
              {PIPELINE_STEPS.map((step, i) => (
                <motion.div
                  key={step.num}
                  className="glass rounded-2xl px-6 py-5 flex gap-5 items-start"
                  {...fadeIn(0.05 * i)}
                >
                  <div
                    className="shrink-0 w-14 h-14 rounded-xl flex items-center justify-center text-2xl"
                    style={{ background: `${step.color}12`, border: `1px solid ${step.color}30` }}
                  >
                    {step.icon}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-baseline gap-3 mb-1">
                      <span className="font-mono text-[10px]" style={{ color: step.color }}>STEP {step.num}</span>
                      <h3 className="font-display text-xl tracking-wide" style={{ color: '#e8f4ff' }}>{step.title}</h3>
                    </div>
                    <p className="font-ui text-sm leading-relaxed" style={{ color: '#3a6a8a' }}>{step.body}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.section>

        {/* ── MODEL METRICS ─────────────────────────────────────────────────── */}
        <motion.section className="mb-20" {...fadeIn(0.1)}>
          <SectionTitle
            tag="MODEL PERFORMANCE"
            title="THE NUMBERS"
            subtitle="The AI model was rigorously validated to prioritise catching real floods over avoiding false alarms."
          />
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
            {MODEL_METRICS.map(m => (
              <motion.div
                key={m.label}
                className="glass rounded-2xl px-5 py-4 text-center"
                {...fadeIn(0.05)}
              >
                <div
                  className="font-display text-4xl leading-none mb-1"
                  style={{ color: m.color, textShadow: `0 0 20px ${m.color}60` }}
                >
                  {m.value}
                </div>
                <div className="font-ui text-xs font-semibold mb-0.5" style={{ color: '#b8d4e8' }}>{m.label}</div>
                <div className="font-mono text-[9px]" style={{ color: '#3a6a8a' }}>{m.desc}</div>
              </motion.div>
            ))}
          </div>

          <div
            className="glass rounded-2xl px-6 py-4 font-ui text-sm leading-relaxed"
            style={{ color: '#3a6a8a', borderColor: 'rgba(255,170,0,0.15)' }}
          >
            <span style={{ color: '#ffaa00' }}>⚠️ Design choice:</span> The model is deliberately biased toward{' '}
            <strong style={{ color: '#b8d4e8' }}>recall over precision</strong> using the F2-score metric.
            A missed flood is far more dangerous than a false alarm, so Sentinel prefers to warn you early even
            when conditions are borderline. The {' '}
            <strong style={{ color: '#b8d4e8' }}>1:93 class imbalance</strong> (floods are rare) was handled
            with RandomOverSampler and scale_pos_weight tuning.
          </div>
        </motion.section>

        {/* ── TECH STACK ────────────────────────────────────────────────────── */}
        <motion.section className="mb-20" {...fadeIn(0.1)}>
          <SectionTitle tag="BUILT WITH" title="TECH STACK" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {TECH_STACK.map(t => (
              <motion.div
                key={t.name}
                className="glass rounded-xl px-4 py-3"
                {...fadeIn(0.04)}
                whileHover={{ scale: 1.02, transition: { duration: 0.15 } }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span style={{ fontSize: '20px' }}>{t.icon}</span>
                  <div>
                    <div className="font-ui text-xs font-semibold" style={{ color: '#b8d4e8' }}>{t.name}</div>
                    <div className="font-mono text-[8px] tracking-wider" style={{ color: '#3a6a8a' }}>{t.category}</div>
                  </div>
                </div>
                <p className="font-ui text-[11px] leading-tight" style={{ color: '#1e4060' }}>{t.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.section>

        {/* ── TEAM ──────────────────────────────────────────────────────────── */}
        <motion.section className="mb-12" {...fadeIn(0.1)}>
          <SectionTitle
            tag="TEAM GALE"
            title="THE BUILDERS"
            subtitle="A four-person team from Ironhack — each owning a distinct layer of the system."
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {TEAM.map(member => (
              <motion.div
                key={member.name}
                className="glass rounded-2xl px-6 py-5"
                {...fadeIn(0.06)}
                style={{
                  border: member.highlight ? `1px solid ${member.color}30` : undefined,
                  background: member.highlight ? `rgba(255,170,0,0.04)` : undefined,
                }}
              >
                <div className="flex items-start gap-4">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl shrink-0"
                    style={{ background: `${member.color}12`, border: `1px solid ${member.color}25` }}
                  >
                    {member.icon}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap mb-0.5">
                      <span className="font-display text-lg tracking-wide" style={{ color: '#e8f4ff' }}>
                        {member.name}
                      </span>
                      {member.highlight && (
                        <span
                          className="font-mono text-[8px] px-2 py-0.5 rounded-full tracking-widest"
                          style={{ background: `${member.color}18`, color: member.color, border: `1px solid ${member.color}30` }}
                        >
                          THIS UI
                        </span>
                      )}
                    </div>
                    <div className="font-mono text-[10px] tracking-wide mb-3" style={{ color: member.color }}>
                      {member.role}
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {member.tasks.map(task => (
                        <span
                          key={task}
                          className="font-mono text-[9px] px-2 py-0.5 rounded-full"
                          style={{ background: `${member.color}0a`, color: '#3a6a8a', border: `1px solid ${member.color}18` }}
                        >
                          {task}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.section>

        {/* ── DATA DISCLAIMER ───────────────────────────────────────────────── */}
        <motion.div
          className="glass rounded-2xl px-6 py-5 mb-8"
          {...fadeIn(0.1)}
          style={{ borderColor: 'rgba(0,204,255,0.08)' }}
        >
          <div className="font-mono text-[9px] tracking-widest mb-2" style={{ color: '#3a6a8a' }}>DATA & DISCLAIMER</div>
          <p className="font-ui text-xs leading-relaxed" style={{ color: '#1e4060' }}>
            All weather and river discharge data is sourced from the{' '}
            <strong style={{ color: '#3a6a8a' }}>Open-Meteo API</strong> (open-source, no commercial key required).
            Terrain boundaries use <strong style={{ color: '#3a6a8a' }}>GADM administrative areas</strong> and{' '}
            <strong style={{ color: '#3a6a8a' }}>SRTM elevation data</strong>. This system is a research and educational
            prototype. Flood risk predictions should be used alongside — not as a replacement for — official civil
            protection warnings from Azerbaijan's State Hydrometeorology Service.
          </p>
        </motion.div>

        {/* Footer */}
        <div className="text-center py-4 font-mono text-[10px]" style={{ color: '#1e4060' }}>
          Baku Sentinel · Team Gale · Ironhack 2026 · Built in 5 days
          <br />
          Historical range 2020-01-01 → 2026-04-20 · 27,600 training rows · 3 terrain zones
        </div>

      </div>
    </div>
  )
}
