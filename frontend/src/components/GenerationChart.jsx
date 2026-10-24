import { useMemo } from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { formatDateTime, formatDayLabel, formatMW, formatSignedMW, formatTime } from '../lib/format.js';

const HOUR = 3_600_000;

function GenerationTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="tip">
      <div className="tip__title">{formatDateTime(d.iso)}</div>
      <div className="tip__row">
        <span>Actual</span>
        <span>{formatMW(d.actual)}</span>
      </div>
      <div className="tip__row">
        <span>Forecast</span>
        <span>{formatMW(d.forecast)}</span>
      </div>
      {d.forecast != null && d.actual != null && (
        <div className="tip__row">
          <span>Error</span>
          <span>{formatSignedMW(d.forecast - d.actual)}</span>
        </div>
      )}
      {d.band && (
        <div className="tip__row">
          <span>P10–P90</span>
          <span>
            {Math.round(d.band[0]).toLocaleString('en-GB')}–{Math.round(d.band[1]).toLocaleString('en-GB')}
          </span>
        </div>
      )}
      {d.publish && (
        <div className="tip__meta">
          Forecast issued {formatDateTime(d.publish)} ({d.horizon}h ahead)
        </div>
      )}
    </div>
  );
}

/**
 * Actual (half-hourly) vs selected forecast (hourly) with an optional
 * empirical P10–P90 band around the forecast.
 */
export default function GenerationChart({ points, showBand = true, height = 380, markTime }) {
  const data = useMemo(
    () =>
      points.map((p) => ({
        t: Date.parse(p.time),
        iso: p.time,
        actual: p.actual,
        forecast: p.forecast,
        band: p.bandLow != null && p.bandHigh != null ? [p.bandLow, p.bandHigh] : null,
        publish: p.forecastPublishTime,
        horizon: p.horizonHours,
      })),
    [points],
  );

  if (!data.length) return null;
  const span = data[data.length - 1].t - data[0].t;
  const multiDay = span > 36 * HOUR;
  const tickEvery = span > 10 * 24 * HOUR ? 48 : span > 4 * 24 * HOUR ? 24 : span > 36 * HOUR ? 12 : 6;
  const first = Math.ceil(data[0].t / (tickEvery * HOUR)) * tickEvery * HOUR;
  const ticks = [];
  for (let t = first; t <= data[data.length - 1].t; t += tickEvery * HOUR) ticks.push(t);

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 4 }}>
          <CartesianGrid stroke="var(--rule)" strokeDasharray="2 4" vertical={false} />
          <XAxis
            dataKey="t"
            type="number"
            scale="time"
            domain={['dataMin', 'dataMax']}
            ticks={ticks}
            tickFormatter={(t) => (multiDay ? formatDayLabel(t) : formatTime(new Date(t).toISOString()))}
            tick={{ fill: 'var(--ink-3)', fontSize: 12 }}
            stroke="var(--rule-strong)"
          />
          <YAxis
            width={56}
            tickFormatter={(v) => `${+(v / 1000).toFixed(1)} GW`}
            tick={{ fill: 'var(--ink-3)', fontSize: 12 }}
            stroke="var(--rule-strong)"
          />
          <Tooltip content={<GenerationTooltip />} />
          {showBand && (
            <Area
              dataKey="band"
              stroke="none"
              fill="var(--forecast-soft)"
              connectNulls
              isAnimationActive={false}
              activeDot={false}
            />
          )}
          <Line
            dataKey="actual"
            stroke="var(--actual)"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
            name="Actual"
          />
          <Line
            dataKey="forecast"
            stroke="var(--forecast)"
            strokeWidth={2}
            dot={false}
            connectNulls
            isAnimationActive={false}
            name="Forecast"
          />
          {markTime && <ReferenceLine x={Date.parse(markTime)} stroke="var(--short)" strokeDasharray="4 3" />}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function GenerationLegend({ showBand = true }) {
  return (
    <div className="legend" aria-hidden="true">
      <span>
        <i className="swatch" style={{ background: 'var(--actual)' }} /> Actual
      </span>
      <span>
        <i className="swatch" style={{ background: 'var(--forecast)' }} /> Forecast
      </span>
      {showBand && (
        <span>
          <i className="swatch swatch--band" /> Likely range (P10–P90)
        </span>
      )}
    </div>
  );
}
