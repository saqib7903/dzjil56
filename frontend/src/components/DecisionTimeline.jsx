import { formatDateTime, formatTime } from '../lib/format.js';

const HOUR = 3_600_000;

/**
 * Two-day strip: trading day (D-1) and delivery day (D). Shows every forecast
 * run, the gate closure and which run the desk actually had in hand.
 */
export default function DecisionTimeline({ deliveryDate, gateUtc, gateLocal, usedRun, runs, dayStartUtc }) {
  const origin = Date.parse(dayStartUtc) - 24 * HOUR;
  const span = 48 * HOUR;
  const pos = (iso) => `${Math.min(100, Math.max(0, ((Date.parse(iso) - origin) / span) * 100))}%`;
  const gate = Date.parse(gateUtc);

  const runClass = (iso) => {
    if (iso === usedRun) return 'timeline__run timeline__run--used';
    return Date.parse(iso) <= gate ? 'timeline__run timeline__run--before' : 'timeline__run timeline__run--after';
  };

  const tickLabels = ['00:00', '06:00', '12:00', '18:00', '00:00', '06:00', '12:00', '18:00', '24:00'];

  return (
    <section className="card timeline" aria-label="Decision timeline">
      <p className="timeline__sentence">
        To trade delivery on <strong>{deliveryDate}</strong>, the desk bids before the{' '}
        <strong className="mono">{gateLocal}</strong> gate the day before. The latest forecast in hand then was
        the run issued at <strong className="mono">{usedRun ? formatTime(usedRun) : '—'}</strong>
        {usedRun ? ` (${formatDateTime(usedRun)})` : ''}.
      </p>
      <div className="timeline__track">
        <div className="timeline__days">
          <div className="timeline__day timeline__day--trade">
            <span className="timeline__daylabel">Trading day (D-1)</span>
          </div>
          <div className="timeline__day timeline__day--delivery">
            <span className="timeline__daylabel">Delivery day (D)</span>
          </div>
        </div>
        {runs.map((iso) => (
          <span
            key={iso}
            className={runClass(iso)}
            style={{ left: pos(iso) }}
            title={`Forecast run ${formatDateTime(iso)}${Date.parse(iso) > gate ? ' — after gate closure' : ''}`}
          />
        ))}
        <span className="timeline__gate" style={{ left: pos(gateUtc) }} />
        <span className="timeline__gate-label" style={{ left: pos(gateUtc) }}>
          gate {gateLocal}
        </span>
      </div>
      <div className="timeline__ticks" aria-hidden="true">
        {tickLabels.map((t, i) => (
          <span key={i}>{t}</span>
        ))}
      </div>
      <div className="timeline__key">
        <span>
          <i className="timeline__run timeline__run--used" /> Forecast used for the decision
        </span>
        <span>
          <i className="timeline__run timeline__run--before" /> Earlier runs
        </span>
        <span>
          <i className="timeline__run timeline__run--after" /> Issued after gate (too late to trade on)
        </span>
      </div>
    </section>
  );
}
