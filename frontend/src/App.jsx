import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { useEffect } from 'react'
import Dashboard from './pages/Dashboard.jsx'
import Archive from './pages/Archive.jsx'
import About from './pages/About.jsx'
import { useForecastStore } from './store/forecastStore.js'

function Navbar() {
  const location = useLocation()
  const isDashboard = location.pathname === '/'

  return (
    <nav className="absolute top-0 left-0 right-0 z-50 h-14 flex items-center px-6 gap-8"
      style={{
        background: 'rgba(2, 13, 26, 0.85)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(0,204,255,0.1)',
        boxShadow: '0 4px 24px rgba(0,0,0,0.6)',
      }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 mr-4">
        <div className="relative">
          <div
            className="w-7 h-7 rounded-full border-2 flex items-center justify-center"
            style={{ borderColor: '#00ccff', boxShadow: '0 0 12px rgba(0,204,255,0.5)' }}
          >
            <div className="w-2 h-2 rounded-full bg-cyan-DEFAULT animate-pulse" style={{ background: '#00ccff' }} />
          </div>
          <div
            className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full"
            style={{ background: '#00e87a', boxShadow: '0 0 6px #00e87a', animation: 'breathe 2s ease-in-out infinite' }}
          />
        </div>
        <div>
          <div className="font-display text-xl leading-none tracking-widest" style={{ color: '#00ccff' }}>
            BAKU SENTINEL
          </div>
          <div className="font-mono text-[9px] leading-none tracking-wider" style={{ color: '#3a6a8a' }}>
            FLOOD INTELLIGENCE SYSTEM
          </div>
        </div>
      </div>

      {/* Nav links */}
      <div className="flex items-center gap-1 ml-auto">
        {[
          { to: '/', label: 'LIVE MAP' },
          { to: '/archive', label: 'ARCHIVE' },
          { to: '/about', label: 'ABOUT' },
        ].map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `font-ui text-xs tracking-widest px-4 py-1.5 rounded transition-all duration-200 ${
                isActive
                  ? 'text-cyan-DEFAULT border border-cyan-dim bg-cyan-glow'
                  : 'text-sentinel-text-dim hover:text-sentinel-text border border-transparent hover:border-cyan-dim/30'
              }`
            }
            style={({ isActive }) => isActive ? { color: '#00ccff', background: 'rgba(0,204,255,0.08)' } : { color: '#3a6a8a' }}
          >
            {label}
          </NavLink>
        ))}
      </div>

      {/* Live indicator */}
      <div className="flex items-center gap-2 ml-4 pl-4" style={{ borderLeft: '1px solid rgba(0,204,255,0.1)' }}>
        <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#00e87a', boxShadow: '0 0 6px #00e87a', animation: 'breathe 1.5s ease-in-out infinite' }} />
        <span className="font-mono text-[10px] tracking-wider" style={{ color: '#00e87a' }}>LIVE</span>
      </div>
    </nav>
  )
}

function PageWrapper({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
      className="w-full h-full"
    >
      {children}
    </motion.div>
  )
}

function AppInner() {
  const location = useLocation()
  const loadForecast = useForecastStore(s => s.loadForecast)

  useEffect(() => {
    loadForecast()
  }, [])

  return (
    <div className="relative w-screen h-screen overflow-hidden font-ui" style={{ background: '#020d1a', color: '#b8d4e8' }}>
      <Navbar />
      <div className="pt-14 h-full">
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<PageWrapper><Dashboard /></PageWrapper>} />
            <Route path="/archive" element={<PageWrapper><Archive /></PageWrapper>} />
            <Route path="/about" element={<PageWrapper><About /></PageWrapper>} />
          </Routes>
        </AnimatePresence>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppInner />
    </BrowserRouter>
  )
}
