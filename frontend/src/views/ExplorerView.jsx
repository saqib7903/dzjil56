import { useState } from 'react';

import { api } from '../api/client.js';
import { HourlyErrorChart } from '../components/AccuracyCharts.jsx';
import GenerationChart, { GenerationLegend } from '../components/GenerationChart.jsx';
import { StatGrid, StatTile } from '../components/StatTile.jsx';
import { ErrorState, Loading } from '../components/Status.jsx';
import { useApi } from '../hooks/useApi.js';
import { formatMW, formatPct, formatSignedMW, londonLocalToUtcIso, utcIsoToLondonLocal } from '../lib/format.js';

const PRESETS = [
  ['Full January', '2026-01-01T00:00', '2026-02-01T00:00'],
  ['1–7 Jan', '2026-01-01T00:00', '2026-01-08T00:00'],
  ['8–14 Jan', '2026-01-08T00:00', '2026-01-15T00:00'],
  ['15–21 Jan', '2026-01-15T00:00', '2026-01-22T00:00'],
  ['22–31 Jan', '2026-01-22T00:00', '2026-02-01T00:00'],
];

export default function ExplorerView({ meta }) {
  const minLocal = utcIsoToLondonLocal(meta.windowStart);
  const maxLocal = utcIsoToLondonLocal(meta.windowEnd);
  const [start, setStart] = useState('2026-01-08T00:00');
  const [end, setEnd] = useState('2026-01-15T00:00');
  const [horizon, setHorizon] = useState(4);
  const [showBand, setShowBand] = useState(true);

  const invalid = !start || !end || start >= end ? 'Start must be before end.' : null;

  const { data, error, loading } = useApi(
    (signal) =>
      invalid
        ? Promise.reject(new Error(invalid))
        : api.generation({ start: londonLocalToUtcIso(start), end: londonLocalToUtcIso(end), horizon }, signal),
    [start, end, horizon, invalid],
    { delay: 150 },
  );

  const s = data?.summary;

  return (
    <>
      <header className="view-intro">
        <h2>Forecast vs actual at any lead time</h2>
        <p>
          For each half hour we show the latest forecast published at least the chosen number of hours before it.
          Slide the horizon to see how accuracy changes as you trade further ahead.
        </p>
      </header>

      <div className="toolbar">
        <label className="field">
          <span>Start (UK time)</span>
          <input
            className="input"
            type="datetime-local"
            min={minLocal}
            max={maxLocal}
            step={1800}
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>
        <label className="field">
          <span>End (UK time)</span>
          <input
            className="input"
            type="datetime-local"
            min={minLocal}
            max={maxLocal}
            step={1800}
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </label>
        <label className="field slider-field">
          <span>
            Forecast horizon: <output>{horizon}h</output>
          </span>
          <input
            type="range"
            min={0}
            max={meta.maxHorizonHours}
            step={0.5}
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
          />
        </label>
        <label className="toggle">
          <input type="checkbox" checked={showBand} onChange={(e) => setShowBand(e.target.checked)} />
          Show likely range
        </label>
      </div>
      <div className="chip-row" style={{ marginBottom: 16 }}>
        {PRESETS.map(([label, a, b]) => (
          <button
            key={label}
            type="button"
            className="chip"
            aria-pressed={start === a && end === b}
            onClick={() => {
              setStart(a);
              setEnd(b);
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <ErrorState error={error} />}
      {!data && !error && <Loading />}

      {data && (
        <div className={loading ? 'is-loading' : undefined}>
          <StatGrid>
            <StatTile tone="forecast" label="Mean absolute error" value={formatMW(s.mae)} note={`${s.count} matched hours`} />
            <StatTile label="RMSE" value={formatMW(s.rmse)} note="Penalises large misses" />
            <StatTile
              tone={s.bias > 0 ? 'short' : undefined}
              label="Bias (forecast − actual)"
              value={formatSignedMW(s.bias)}
              note={s.bias > 0 ? 'Forecast runs high: risk of being short' : 'Forecast runs low'}
            />
            <StatTile label="P90 absolute error" value={formatMW(s.p90AbsError)} note="9 in 10 hours miss by less" />
            <StatTile label="Error relative to output" value={formatPct(s.wapePct)} note="Total |error| ÷ total actual" />
          </StatGrid>

          <section className="card">
            <div className="card__head">
              <h3 className="card__title">Wind generation</h3>
              <GenerationLegend showBand={showBand} />
            </div>
            {data.points.some((p) => p.forecast != null) ? (
              <GenerationChart points={data.points} showBand={showBand} />
            ) : (
              <div className="status">No forecast was published that far ahead. Try a horizon below 46 hours.</div>
            )}
            {showBand && (
              <p className="card__note">
                Likely range: forecast plus the 10th–90th percentile of errors at this horizon across all of
                January ({data.band.sampleSize.toLocaleString('en-GB')} periods).
              </p>
            )}
          </section>

          <section className="card">
            <div className="card__head">
              <h3 className="card__title">Where in the day the forecast misses most</h3>
              <p className="card__note">Mean absolute error by UK hour, selected range and horizon</p>
            </div>
            <HourlyErrorChart hourly={data.hourly} />
          </section>
        </div>
      )}
    </>
  );
}
