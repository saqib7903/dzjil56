import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { formatDeliveryDate, formatMW, formatSignedGWh, formatSignedMW } from '../lib/format.js';

const axisTick = { fill: 'var(--ink-3)', fontSize: 12 };
const gw = (v) => `${+(v / 1000).toFixed(1)} GW`;

function Tip({ title, rows }) {
  return (
    <div className="tip">
      <div className="tip__title">{title}</div>
      {rows.map(([label, value]) => (
        <div className="tip__row" key={label}>
          <span>{label}</span>
          <span>{value}</span>
        </div>
      ))}
    </div>
  );
}

/** MAE / P90 / bias as the minimum lead time grows. */
export function HorizonCurveChart({ points, dayAheadRange, selected, height = 300 }) {
  const data = points.filter((p) => p.count > 0);
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 18, left: 4 }}>
          <CartesianGrid stroke="var(--rule)" strokeDasharray="2 4" vertical={false} />
          {dayAheadRange && (
            <ReferenceArea
              x1={dayAheadRange[0]}
              x2={dayAheadRange[1]}
              fill="var(--short-soft)"
              stroke="none"
              label={{ value: 'Day-ahead lead times', position: 'insideTop', fill: 'var(--short)', fontSize: 12 }}
            />
          )}
          {selected != null && <ReferenceLine x={selected} stroke="var(--ink)" strokeDasharray="3 3" />}
          <XAxis
            dataKey="horizonHours"
            type="number"
            domain={[0, 48]}
            ticks={[0, 6, 12, 18, 24, 30, 36, 42, 48]}
            tick={axisTick}
            stroke="var(--rule-strong)"
            label={{ value: 'Minimum lead time (hours)', position: 'insideBottom', offset: -10, fill: 'var(--ink-3)', fontSize: 12 }}
          />
          <YAxis width={60} tickFormatter={gw} tick={axisTick} stroke="var(--rule-strong)" />
          <Tooltip
            content={({ active, payload }) =>
              active && payload?.length ? (
                <Tip
                  title={`${payload[0].payload.horizonHours}h lead time`}
                  rows={[
                    ['Mean abs error', formatMW(payload[0].payload.mae)],
                    ['P90 abs error', formatMW(payload[0].payload.p90AbsError)],
                    ['Bias', formatSignedMW(payload[0].payload.bias)],
                    ['Periods', payload[0].payload.count],
                  ]}
                />
              ) : null
            }
          />
          <Line dataKey="p90AbsError" stroke="var(--short)" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line dataKey="mae" stroke="var(--forecast)" strokeWidth={2.5} dot={false} isAnimationActive={false} />
          <Line
            dataKey="bias"
            stroke="var(--actual)"
            strokeWidth={1.5}
            strokeDasharray="5 4"
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Daily energy error (forecast − actual) for each delivery day. Click a bar to open that day. */
export function DailyScorecardChart({ days, onSelect, height = 280 }) {
  const data = days.filter((d) => d.errorMwh != null);
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 4 }}>
          <CartesianGrid stroke="var(--rule)" strokeDasharray="2 4" vertical={false} />
          <XAxis
            dataKey="deliveryDate"
            tickFormatter={(d) => String(Number(d.slice(8)))}
            interval={1}
            tick={axisTick}
            stroke="var(--rule-strong)"
          />
          <YAxis width={72} tickFormatter={(v) => `${+(v / 1000).toFixed(0)} GWh`} tick={axisTick} stroke="var(--rule-strong)" />
          <ReferenceLine y={0} stroke="var(--ink-3)" />
          <Tooltip
            cursor={{ fill: 'rgba(15,34,51,0.05)' }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <Tip
                  title={formatDeliveryDate(payload[0].payload.deliveryDate)}
                  rows={[
                    ['Forecast − actual', formatSignedGWh(payload[0].payload.errorMwh)],
                    ['Mean abs error', formatMW(payload[0].payload.mae)],
                  ]}
                />
              ) : null
            }
          />
          <Bar
            dataKey="errorMwh"
            isAnimationActive={false}
            onClick={(entry) => onSelect?.(entry.deliveryDate ?? entry.payload?.deliveryDate)}
            style={{ cursor: onSelect ? 'pointer' : 'default' }}
          >
            {data.map((d) => (
              <Cell key={d.deliveryDate} fill={d.errorMwh > 0 ? 'var(--short)' : 'var(--long)'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Mean absolute error by UK hour of day. */
export function HourlyErrorChart({ hourly, height = 220 }) {
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <BarChart data={hourly} margin={{ top: 8, right: 12, bottom: 0, left: 4 }}>
          <CartesianGrid stroke="var(--rule)" strokeDasharray="2 4" vertical={false} />
          <XAxis
            dataKey="hour"
            tickFormatter={(h) => String(h).padStart(2, '0')}
            interval={2}
            tick={axisTick}
            stroke="var(--rule-strong)"
          />
          <YAxis width={60} tickFormatter={gw} tick={axisTick} stroke="var(--rule-strong)" />
          <Tooltip
            cursor={{ fill: 'rgba(15,34,51,0.05)' }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <Tip
                  title={`${String(payload[0].payload.hour).padStart(2, '0')}:00 UK time`}
                  rows={[
                    ['Mean abs error', formatMW(payload[0].payload.mae)],
                    ['Bias', formatSignedMW(payload[0].payload.bias)],
                    ['Periods', payload[0].payload.count],
                  ]}
                />
              ) : null
            }
          />
          <Bar dataKey="mae" fill="var(--forecast)" radius={[3, 3, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
