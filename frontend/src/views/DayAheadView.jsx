import { api } from '../api/client.js';
import DecisionTimeline from '../components/DecisionTimeline.jsx';
import GenerationChart, { GenerationLegend } from '../components/GenerationChart.jsx';
import { StatGrid, StatTile } from '../components/StatTile.jsx';
import { ErrorState, Loading } from '../components/Status.jsx';
import { useApi } from '../hooks/useApi.js';
import { addDays, formatDeliveryDate, formatGWh, formatMW, formatSignedGWh, formatSignedMW } from '../lib/format.js';

export default function DayAheadView({ meta, date, onDateChange, gate, onGateChange }) {
  const { data, error, loading } = useApi((signal) => api.dayAhead({ date, gate }, signal), [date, gate], {
    delay: 120,
  });

  const first = meta.firstDeliveryDate;
  const last = meta.lastDeliveryDate;
  const e = data?.energy;
  const buffer = e && e.forecastMwh != null && e.firmWindP10Mwh != null ? e.forecastMwh - e.firmWindP10Mwh : null;

  return (
    <>
      <header className="view-intro">
        <h2>How much wind can we count on tomorrow?</h2>
        <p>
          Pick a delivery day. You see the forecast that was available at the day-ahead auction gate, the range
          January's errors say to expect, and what the wind actually did.
        </p>
      </header>

      <div className="toolbar">
        <label className="field">
          <span>Delivery day</span>
          <div className="stepper">
            <button
              type="button"
              className="btn"
              aria-label="Previous day"
              disabled={date <= first}
              onClick={() => onDateChange(addDays(date, -1))}
            >
              ‹
            </button>
            <input
              className="input"
              type="date"
              min={first}
              max={last}
              value={date}
              onChange={(ev) => ev.target.value && onDateChange(ev.target.value)}
            />
            <button
              type="button"
              className="btn"
              aria-label="Next day"
              disabled={date >= last}
              onClick={() => onDateChange(addDays(date, 1))}
            >
              ›
            </button>
          </div>
        </label>
        <label className="field">
          <span>Gate closure on D-1 (UK time)</span>
          <input
            className="input"
            type="time"
            step={600}
            value={gate}
            onChange={(ev) => ev.target.value && onGateChange(ev.target.value)}
          />
        </label>
        <div className="field">
          <span>Auction</span>
          <div className="chip-row">
            {[
              ['09:50', 'N2EX day-ahead'],
              ['15:30', 'Afternoon'],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                className="chip"
                aria-pressed={gate === value}
                onClick={() => onGateChange(value)}
              >
                {label} · {value}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && !data && <ErrorState error={error} />}
      {!data && !error && <Loading />}

      {data && (
        <div className={loading ? 'is-loading' : undefined}>
          {error && <ErrorState error={error} />}
          <DecisionTimeline
            deliveryDate={formatDeliveryDate(data.deliveryDate)}
            gateUtc={data.gateClosureUtc}
            gateLocal={data.gateClosureLocal}
            usedRun={data.forecastPublishTime}
            runs={data.forecastRuns}
            dayStartUtc={data.points[0].time}
          />

          <StatGrid>
            <StatTile
              tone="forecast"
              label="Forecast wind at gate"
              value={formatGWh(e.forecastMwh)}
              note={`Average ${formatMW(e.forecastMwh != null ? e.forecastMwh / e.hours : null)}`}
            />
            <StatTile
              label="Wind you can count on (P10)"
              value={formatGWh(e.firmWindP10Mwh)}
              note={`Outturn met this on 9 in 10 of the ${e.daysInSample} days analysed`}
            />
            <StatTile
              tone="short"
              label="Cover to hold for wind risk"
              value={formatGWh(buffer)}
              note="Forecast minus the P10 level"
            />
            <StatTile
              tone="actual"
              label="Actual wind outturn"
              value={formatGWh(e.actualMwh)}
              note={
                e.errorMwh == null
                  ? 'No outturn yet'
                  : `Forecast was ${formatSignedGWh(e.errorMwh)} ${e.errorMwh > 0 ? 'too high' : 'too low'}`
              }
            />
          </StatGrid>

          <section className="card">
            <div className="card__head">
              <h3 className="card__title">Half-hourly wind, delivery day</h3>
              <GenerationLegend />
            </div>
            <GenerationChart points={data.points} />
            <p className="card__note">
              Mean absolute error {formatMW(data.summary.mae)} · bias {formatSignedMW(data.summary.bias)} · range
              from {data.band.sampleSize.toLocaleString('en-GB')} January periods traded at the same gate.
            </p>
          </section>
        </div>
      )}
    </>
  );
}
