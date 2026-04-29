import { Canvas, useFrame } from '@react-three/fiber'
import { Stars, OrbitControls, Html } from '@react-three/drei'
import { useRef, useMemo, useEffect, Suspense } from 'react'
import * as THREE from 'three'
import { useForecastStore } from '../store/forecastStore.js'
import { BAKU_POINTS } from '../data/bakuPoints.js'

// ── Geographic projection ─────────────────────────────────────────────────────
// Real Baku bounds from GADM shapefile (notebook cell 6)
const LON_MIN = 49.2919, LON_MAX = 50.6078
const LAT_MIN = 39.665,  LAT_MAX = 40.5929
const SCENE_W = 16, SCENE_H = 11
const ELV_SCALE = 0.008   // 1 m elevation → 0.008 Three.js units  (300 m peak ≈ 2.4 u)
const TILE_W    = 0.27
const TILE_D    = 0.185

function projectGeo(lon, lat) {
  const x = ((lon - LON_MIN) / (LON_MAX - LON_MIN) - 0.5) * SCENE_W
  const z = -((lat - LAT_MIN) / (LAT_MAX - LAT_MIN) - 0.5) * SCENE_H
  return [x, z]
}

// ── Zone config — positions are real K-Means centroids (notebook cell 15) ────
// Y = zone mean_elevation × ELV_SCALE  (High 172.8 m, Moderate 69.5 m, Low ≈ 0)
const ZONE_CFG = {
  'High Relief':     { pos: [-6, 0, -7.5], baseColor: '#00e87a', radius: 0.55, label: 'Upland Zone' },
  'Moderate Relief': { pos: [ -1, 0, -7.5], baseColor: '#ffaa00', radius: 0.65, label: 'Mid-Slope Zone' },
  'Low Relief':      { pos: [ 4, 0, -7.5], baseColor: '#ff3344', radius: 0.80, label: 'Coastal Zone' },
}

// Zone index in BAKU_POINTS: 0 = Low Relief, 1 = Moderate Relief, 2 = High Relief
const ZONE_STYLES = [
  { color: '#c72233', emissive: '#ff3344', ei: 0.18 },   // Low
  { color: '#c28000', emissive: '#ffaa00', ei: 0.14 },   // Moderate
  { color: '#00b85e', emissive: '#00e87a', ei: 0.12 },   // High
]

// ── ZoneTiles — one InstancedMesh per relief zone ────────────────────────────
function ZoneTiles({ points, style }) {
  const meshRef = useRef()
  const dummy   = useMemo(() => new THREE.Object3D(), [])

  useEffect(() => {
    const mesh = meshRef.current
    if (!mesh || !points.length) return
    points.forEach(([x, h, z], i) => {
      dummy.position.set(x, h / 2, z)
      dummy.scale.set(TILE_W, h, TILE_D)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)
    })
    mesh.instanceMatrix.needsUpdate = true
  }, [points, dummy])

  if (!points.length) return null

  return (
    <instancedMesh ref={meshRef} args={[null, null, points.length]} castShadow receiveShadow>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial
        color={style.color}
        emissive={style.emissive}
        emissiveIntensity={style.ei}
        roughness={0.62}
        metalness={0.22}
      />
    </instancedMesh>
  )
}

// ── BakuMap — real SRTM tiles coloured by K-Means zone ───────────────────────
function BakuMap() {
  const zoneGroups = useMemo(() => {
    const groups = [[], [], []]
    for (const [lon, lat, elev, zone] of BAKU_POINTS) {
      const [x, z] = projectGeo(lon, lat)
      const h = Math.max(0.08, elev * ELV_SCALE)
      groups[zone].push([x, h, z])
    }
    return groups
  }, [])

  return (
    <>
      {zoneGroups.map((pts, zi) => (
        <ZoneTiles key={zi} points={pts} style={ZONE_STYLES[zi]} />
      ))}

      {/* Caspian Sea — east of the land boundary */}
      <CaspianSea />
    </>
  )
}

// ── Caspian Sea ───────────────────────────────────────────────────────────────
function CaspianSea() {
  const ref = useRef()
  useFrame(({ clock }) => {
    if (ref.current) ref.current.material.opacity = 0.65 + Math.sin(clock.elapsedTime * 0.35) * 0.04
  })
  return (
    <mesh ref={ref} position={[7, -0.04, -0.5]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[10, 13]} />
      <meshStandardMaterial color="#001529" transparent opacity={0.7} roughness={0.04} metalness={0.65} />
    </mesh>
  )
}

// ── Risk Column ───────────────────────────────────────────────────────────────
function RiskColumn({ zone, score, level, pos, baseColor, radius }) {
  const colRef  = useRef()
  const ringRef = useRef()
  const capRef  = useRef()

  const height = Math.max(0.25, score * 7)

  useFrame(({ clock }) => {
    const t = clock.elapsedTime
    if (colRef.current)  colRef.current.material.emissiveIntensity  = 0.45 + Math.sin(t * 1.8 + pos[0]) * 0.2
    if (ringRef.current) {
      ringRef.current.rotation.y  = t * 0.6
      ringRef.current.material.opacity = 0.25 + Math.sin(t * 2.5) * 0.1
    }
    if (capRef.current)  capRef.current.material.emissiveIntensity   = 0.8  + Math.sin(t * 3   + pos[2]) * 0.2
  })

  const color = new THREE.Color(baseColor)

  return (
    <group position={pos}>
      {/* Base glow disc */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <circleGeometry args={[radius * 2.2, 32]} />
        <meshBasicMaterial color={baseColor} transparent opacity={0.07} />
      </mesh>

      {/* Rotating hex ring */}
      <mesh ref={ringRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
        <ringGeometry args={[radius * 1.4, radius * 2, 6]} />
        <meshBasicMaterial color={baseColor} transparent opacity={0.3} side={THREE.DoubleSide} />
      </mesh>

      {/* Main column */}
      <mesh ref={colRef} position={[0, height / 2, 0]} castShadow>
        <boxGeometry args={[radius * 0.85, height, radius * 0.85]} />
        <meshStandardMaterial color={baseColor} emissive={baseColor} emissiveIntensity={0.5} transparent opacity={0.88} roughness={0.15} metalness={0.75} />
      </mesh>

      {/* Glowing cap */}
      <mesh ref={capRef} position={[0, height + 0.06, 0]}>
        <boxGeometry args={[radius * 1.1, 0.12, radius * 1.1]} />
        <meshStandardMaterial color={baseColor} emissive={baseColor} emissiveIntensity={1.0} />
      </mesh>

      {/* Column light source */}
      <pointLight color={baseColor} intensity={level === 'HIGH' ? 4 : level === 'MEDIUM' ? 2.5 : 1.2} distance={9} position={[0, height + 0.5, 0]} />

      {/* HTML label */}
      <Html position={[0, height + 1.8, 0]} center distanceFactor={12} occlude={false}>
        <div style={{ textAlign: 'center', pointerEvents: 'none', userSelect: 'none', animation: 'flicker 8s ease-in-out infinite' }}>
          <div style={{ fontFamily: '"Bebas Neue", sans-serif', fontSize: '13px', letterSpacing: '0.12em', color: baseColor, textShadow: `0 0 12px ${baseColor}, 0 0 24px ${baseColor}66`, whiteSpace: 'nowrap' }}>
            {zone}
          </div>
          <div style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '10px', color: '#e8f4ff', background: `${baseColor}20`, border: `1px solid ${baseColor}55`, borderRadius: '4px', padding: '2px 8px', marginTop: '3px', whiteSpace: 'nowrap' }}>
            {level} · {(score * 100).toFixed(0)}%
          </div>
        </div>
      </Html>
    </group>
  )
}

// ── Grid ──────────────────────────────────────────────────────────────────────
function SceneGrid() {
  return (
    <gridHelper args={[28, 28, 'rgba(0,204,255,0.10)', 'rgba(0,204,255,0.04)']} position={[0, 0.005, 0]} />
  )
}

// ── Loading overlay ───────────────────────────────────────────────────────────
function LoadingOverlay() {
  return (
    <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
      <div className="text-center">
        <div className="w-16 h-16 rounded-full border-2 mx-auto mb-4" style={{ borderColor: 'rgba(0,204,255,0.3)', borderTopColor: '#00ccff', animation: 'spin-slow 1s linear infinite' }} />
        <div className="font-mono text-xs tracking-widest" style={{ color: '#00ccff' }}>CALIBRATING SENSORS</div>
      </div>
    </div>
  )
}

// ── Scene Inner ───────────────────────────────────────────────────────────────
function SceneInner() {
  const forecast  = useForecastStore(s => s.forecast)
  const slotIndex = useForecastStore(s => s.slotIndex)

  const zoneData = useMemo(() => {
    if (!forecast.length) return []
    const slotOffset = slotIndex * 3
    const slot = forecast.slice(slotOffset, slotOffset + 3)
    return slot.map(row => {
      const cfg = ZONE_CFG[row.zone] ?? { pos: [0, 0, 0], baseColor: '#00ccff', radius: 0.6 }
      return {
        zone:      row.zone,
        score:     row.risk_score,
        level:     row.risk_level,
        pos:       cfg.pos,
        baseColor: cfg.baseColor,
        radius:    cfg.radius,
      }
    })
  }, [forecast, slotIndex])

  return (
    <>
      <color attach="background" args={['#020d1a']} />
      <fog attach="fog" args={['#020d1a', 30, 62]} />

      <Stars radius={90} depth={55} count={5000} factor={3.5} saturation={0} fade speed={0.25} />

      <ambientLight intensity={0.55} color="#4a8ab5" />
      <directionalLight position={[-9, 16, -6]} intensity={1.2} color="#6aaad4" castShadow />
      <directionalLight position={[8, 10, 8]}   intensity={0.4} color="#2a5a8a" />
      <hemisphereLight skyColor="#1a4a7a" groundColor="#0a1a2a" intensity={0.6} />
      <pointLight position={[0, 22, 0]} intensity={0.5} color="#0066aa" />

      <BakuMap />
      <SceneGrid />

      {zoneData.map(z => <RiskColumn key={z.zone} {...z} />)}

      <OrbitControls
        enablePan={false}
        minPolarAngle={Math.PI / 8}
        maxPolarAngle={Math.PI / 2.3}
        minDistance={9}
        maxDistance={28}
        autoRotate
        autoRotateSpeed={0.18}
        target={[-1, 0.8, -1]}
      />
    </>
  )
}

// ── Public component ──────────────────────────────────────────────────────────
export default function BakuScene() {
  const loading = useForecastStore(s => s.loading)
  return (
    <div className="absolute inset-0">
      {loading && <LoadingOverlay />}
      <Canvas camera={{ position: [4, 12, 16], fov: 40 }} shadows gl={{ antialias: true, alpha: false }} dpr={[1, 1.5]}>
        <Suspense fallback={null}>
          <SceneInner />
        </Suspense>
      </Canvas>
    </div>
  )
}
