// Formatting and time helpers. The GB market runs on UK local time
// (Europe/London); the API speaks UTC.

export const MARKET_TZ = 'Europe/London';

const nf0 = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1, minimumFractionDigits: 1 });

export function formatMW(value) {
  return value == null ? '—' : `${nf0.format(value)} MW`;
}

export function formatSignedMW(value) {
  if (value == null) return '—';
  const sign = value > 0 ? '+' : value < 0 ? '−' : '';
  return `${sign}${nf0.format(Math.abs(value))} MW`;
}

export function formatGWh(mwh) {
  return mwh == null ? '—' : `${nf1.format(mwh / 1000)} GWh`;
}

export function formatSignedGWh(mwh) {
  if (mwh == null) return '—';
  const sign = mwh > 0 ? '+' : mwh < 0 ? '−' : '';
  return `${sign}${nf1.format(Math.abs(mwh) / 1000)} GWh`;
}

export function formatPct(value) {
  return value == null ? '—' : `${nf1.format(value)}%`;
}

function parts(date, options) {
  return Object.fromEntries(
    new Intl.DateTimeFormat('en-GB', { timeZone: MARKET_TZ, hourCycle: 'h23', ...options })
      .formatToParts(date)
      .map((p) => [p.type, p.value]),
  );
}

/** "Thu 15 Jan, 09:30" in UK time. */
export function formatDateTime(iso) {
  if (!iso) return '—';
  const p = parts(new Date(iso), {
    weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });
  return `${p.weekday} ${p.day} ${p.month}, ${p.hour}:${p.minute}`;
}

export function formatTime(iso) {
  const p = parts(new Date(iso), { hour: '2-digit', minute: '2-digit' });
  return `${p.hour}:${p.minute}`;
}

export function formatDayLabel(isoOrMs) {
  const p = parts(new Date(isoOrMs), { day: 'numeric', month: 'short' });
  return `${p.day} ${p.month}`;
}

/** Long label for a YYYY-MM-DD delivery date. */
export function formatDeliveryDate(ymd) {
  const [y, m, d] = ymd.split('-').map(Number);
  return new Intl.DateTimeFormat('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
  }).format(new Date(Date.UTC(y, m - 1, d)));
}

/** Offset (ms) of UK local time from UTC at the given instant. */
function londonOffsetMs(utcMs) {
  const p = parts(new Date(utcMs), {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
  const asUtc = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second);
  return asUtc - utcMs;
}

/** "2026-01-15T09:30" (UK wall clock, as from <input type=datetime-local>) -> UTC ISO string. */
export function londonLocalToUtcIso(local) {
  const [date, time = '00:00'] = local.split('T');
  const [y, m, d] = date.split('-').map(Number);
  const [hh, mm] = time.split(':').map(Number);
  const guess = Date.UTC(y, m - 1, d, hh, mm);
  const utc = guess - londonOffsetMs(guess - londonOffsetMs(guess));
  return new Date(utc).toISOString().replace('.000Z', 'Z');
}

/** UTC ISO -> "YYYY-MM-DDTHH:MM" in UK wall clock time. */
export function utcIsoToLondonLocal(iso) {
  const p = parts(new Date(iso), {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  });
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
}

export function addDays(ymd, days) {
  const [y, m, d] = ymd.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
}
