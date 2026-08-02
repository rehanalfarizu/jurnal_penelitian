const trimTrailingSlash = value => String(value || '').replace(/\/+$/, '')

const readPositiveInteger = (value, fallback) => {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
}

// Local historical replay is the reproducible default.
export const TELEMETRY_API_URL = trimTrailingSlash(
  import.meta.env.VITE_TELEMETRY_API_URL || 'http://127.0.0.1:8000/api'
)

export const TELEMETRY_POLL_INTERVAL_MS = readPositiveInteger(
  import.meta.env.VITE_TELEMETRY_POLL_INTERVAL_MS,
  3500
)
