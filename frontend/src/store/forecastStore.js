import { create } from 'zustand'
import { api } from '../api/client.js'

/**
 * Central state store for Baku Sentinel.
 *
 * forecast:       Full 30-day forecast array (all zones, all 6h slots)
 * slotIndex:      Current time slot offset from [0] (driven by timeline slider)
 * currentSlot:    The 3-zone snapshot at the current slotIndex
 * status:         Overall city status derived from worst zone
 * loading/error:  Async state
 */
export const useForecastStore = create((set, get) => ({
  forecast: [],
  slotIndex: 0,
  currentSlot: [],
  overallStatus: { label: 'LOADING', level: 'LOW', color: '#3a6a8a' },
  loading: true,
  error: null,

  loadForecast: async () => {
    set({ loading: true, error: null })
    try {
      const data = await api.getForecast()
      set({ forecast: data, loading: false })
      get().updateSlot(0)
    } catch (err) {
      set({ loading: false, error: err.message })
    }
  },

  setSlotIndex: (index) => {
    set({ slotIndex: index })
    get().updateSlot(index)
  },

  updateSlot: (index) => {
    const { forecast } = get()
    if (!forecast.length) return

    // Each "slot" is one 6h timestamp containing 3 zone rows
    // Slots are ordered: all 3 zones for time[0], then time[1], etc.
    const slotOffset = index * 3
    const currentSlot = forecast.slice(slotOffset, slotOffset + 3)

    const overallStatus = deriveOverallStatus(currentSlot)
    set({ currentSlot, overallStatus })
  },

  // Convenience selector: get data for a specific zone at the current slot
  getZoneData: (zoneName) => {
    const { currentSlot } = get()
    return currentSlot.find(z => z.zone === zoneName) ?? null
  },

  // Get time series for a specific zone (all slots)
  getZoneTimeSeries: (zoneName) => {
    return get().forecast.filter(f => f.zone === zoneName)
  },
}))

function deriveOverallStatus(slot) {
  if (!slot.length) return { label: 'UNKNOWN', level: 'LOW', color: '#3a6a8a' }

  const hasHigh   = slot.some(z => z.risk_level === 'HIGH')
  const medCount  = slot.filter(z => z.risk_level === 'MEDIUM').length

  if (hasHigh)      return { label: 'FLOOD ALERT',        level: 'HIGH',   color: '#ff3344' }
  if (medCount >= 2) return { label: 'CITY-WIDE ADVISORY', level: 'MEDIUM', color: '#ffaa00' }
  if (medCount === 1) return { label: 'LOCAL WATCH',        level: 'MEDIUM', color: '#ffaa00' }
  return               { label: 'ALL CLEAR',               level: 'LOW',    color: '#00e87a' }
}
