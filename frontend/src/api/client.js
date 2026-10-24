// Same-origin by default (Vite proxy in dev, nginx in Docker, rewrites on Vercel).
const BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function get(path, params, signal) {
  const query = params
    ? '?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== '')).toString()
    : '';
  let response;
  try {
    response = await fetch(`${BASE}/api${path}${query}`, { signal });
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    throw new ApiError('Could not reach the server. Check your connection and try again.', 0);
  }
  if (!response.ok) {
    let detail = `Request failed (HTTP ${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d) => d.msg).join('; ');
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, response.status);
  }
  return response.json();
}

export const api = {
  meta: (signal) => get('/meta', null, signal),
  generation: ({ start, end, horizon }, signal) => get('/generation', { start, end, horizon }, signal),
  horizonCurve: ({ start, end, step }, signal) => get('/accuracy/horizons', { start, end, step }, signal),
  dayAhead: ({ date, gate }, signal) => get('/day-ahead', { date, gate }, signal),
  dailyAccuracy: ({ gate }, signal) => get('/accuracy/daily', { gate }, signal),
};
