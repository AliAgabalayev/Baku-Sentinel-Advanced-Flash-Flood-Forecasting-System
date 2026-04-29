/**
 * API Client for Baku Sentinel
 *
 * Toggle USE_MOCK = false and point BASE_URL at your FastAPI server to go live.
 * All API calls match the shape of /api/forecast, /api/historical, /api/status.
 */

import axios from 'axios'

const BASE_URL = '/api'

// ── Mock Data Generator ───────────────────────────────────────────────────────

const ZONES = ['High Relief', 'Moderate Relief', 'Low Relief']

// Zone risk multipliers: Low Relief (coastal) = highest risk
const ZONE_MULT = {
  'High Relief': 0.38,
  'Moderate Relief': 0.72,
  'Low Relief': 1.45,
}

function rng(min, max) {
  return min + Math.random() * (max - min)
}

/**
 * Generates a 30-day, 6-hourly forecast with a simulated rain event in days 6–10.
 */
export function generateMockForecast(offsetDays = 0) {
  const data = []
  const base = new Date()
  base.setMinutes(0, 0, 0)
  // Round to nearest 6h slot
  base.setHours(Math.floor(base.getHours() / 6) * 6, 0, 0, 0)

  for (let day = 0; day < 30; day++) {
    for (let slot = 0; slot < 4; slot++) {
      const t = new Date(base)
      t.setDate(t.getDate() + day + offsetDays)
      t.setHours(slot * 6, 0, 0, 0)

      const rainEvent = day >= 6 && day <= 10
      const peakDay   = day === 8 || day === 9

      const basePrecip = peakDay
        ? rng(4, 14)
        : rainEvent
          ? rng(0, 6)
          : rng(0, 0.5)

      const baseHumid = rainEvent ? rng(75, 96) : rng(48, 72)

      ZONES.forEach((zone) => {
        const mult = ZONE_MULT[zone]

        let baseRisk = peakDay
          ? rng(0.28, 0.58)
          : rainEvent
            ? rng(0.1, 0.32)
            : rng(0, 0.09)

        const riskScore = Math.min(0.98, baseRisk * mult)
        const riskLevel = riskScore >= 0.6 ? 'HIGH' : riskScore >= 0.3 ? 'MEDIUM' : 'LOW'

        data.push({
          zone,
          time: t.toISOString(),
          temperature_2m: rng(10, 22) + (slot === 2 ? 4 : 0),
          relative_humidity_2m: Math.min(99, baseHumid),
          precipitation: Math.max(0, basePrecip * (riskScore > 0.1 ? rng(0.5, 1.5) : rng(0, 0.2))),
          wind_speed_10m: rng(6, 34),
          soil_moisture_0_to_7cm: Math.min(0.45, rng(0.09, 0.18) + (rainEvent ? 0.07 : 0)),
          soil_moisture_7_to_28cm: Math.min(0.48, rng(0.19, 0.28) + (rainEvent ? 0.06 : 0)),
          et0_fao_evapotranspiration: rng(0, 2.5),
          river_discharge: riskScore > 0.55 ? rng(1.0, 3.5) : rng(0, 0.8),
          risk_score: riskScore,
          flood_pred: riskScore >= 0.763 ? 1 : 0,
          risk_level: riskLevel,
        })
      })
    }
  }

  return data
}

/**
 * Generates historical data for the archive view.
 * Creates realistic past rain events with known outcomes.
 */
export function generateHistoricalMock(startDate, endDate) {
  const start = new Date(startDate)
  const end   = new Date(endDate)
  const data  = []

  const dayCount = Math.ceil((end - start) / 86400000)

  // Seed a few notable events
  const events = [
    { day: Math.floor(dayCount * 0.15), label: 'Heavy Autumn Rain' },
    { day: Math.floor(dayCount * 0.45), label: 'Coastal Storm' },
    { day: Math.floor(dayCount * 0.72), label: 'Spring Melt' },
  ]

  for (let d = 0; d < dayCount; d++) {
    for (let slot = 0; slot < 4; slot++) {
      const t = new Date(start)
      t.setDate(t.getDate() + d)
      t.setHours(slot * 6, 0, 0, 0)

      const nearEvent = events.find(e => Math.abs(e.day - d) <= 3)
      const peakEvent = events.find(e => Math.abs(e.day - d) <= 1)

      ZONES.forEach((zone) => {
        const mult = ZONE_MULT[zone]
        let baseRisk = peakEvent ? rng(0.25, 0.55) : nearEvent ? rng(0.1, 0.28) : rng(0, 0.08)
        const predicted_score = Math.min(0.98, baseRisk * mult)
        // Actual outcome has some noise vs. prediction
        const actual_score = Math.min(0.98, predicted_score * rng(0.75, 1.25))

        data.push({
          zone,
          time: t.toISOString(),
          precipitation: peakEvent ? rng(3, 16) : nearEvent ? rng(0, 5) : rng(0, 0.3),
          predicted_score,
          actual_score,
          predicted_level: predicted_score >= 0.6 ? 'HIGH' : predicted_score >= 0.3 ? 'MEDIUM' : 'LOW',
          actual_level:    actual_score    >= 0.6 ? 'HIGH' : actual_score    >= 0.3 ? 'MEDIUM' : 'LOW',
          event_label:     peakEvent?.label ?? null,
        })
      })
    }
  }

  return data
}

// ── API Client ────────────────────────────────────────────────────────────────

// Set to false and ensure your FastAPI backend is running on :8000 to go live
const USE_MOCK = true

function delay(ms) {
  return new Promise(r => setTimeout(r, ms))
}

export const api = {
  async getForecast() {
    if (USE_MOCK) {
      await delay(700)
      return generateMockForecast()
    }
    const res = await axios.get(`${BASE_URL}/forecast`)
    return res.data
  },

  async getHistorical(startDate, endDate) {
    if (USE_MOCK) {
      await delay(500)
      return generateHistoricalMock(startDate, endDate)
    }
    const res = await axios.get(`${BASE_URL}/historical`, {
      params: { start: startDate, end: endDate },
    })
    return res.data
  },

  async getModelMetrics() {
    if (USE_MOCK) {
      return {
        auc_roc: 0.9966,
        auc_pr: 0.9823,
        f1_score: 0.7899,
        threshold: 0.7634,
        n_train: 22098,
        cv_auc_pr_mean: 0.9973,
        cv_auc_pr_std: 0.0023,
      }
    }
    const res = await axios.get(`${BASE_URL}/metrics`)
    return res.data
  },
}
