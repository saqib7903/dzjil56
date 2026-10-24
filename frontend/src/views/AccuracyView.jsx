import { api } from '../api/client.js';
import { DailyScorecardChart, HorizonCurveChart } from '../components/AccuracyCharts.jsx';
import { StatGrid, StatTile } from '../components/StatTile.jsx';
import { ErrorState, Loading } from '../components/Status.jsx';
import { useApi } from '../hooks/useApi.js';
import { formatDeliveryDate, formatMW, formatPct, formatSignedGWh, formatSignedMW } from '../lib/format.js';

function gateHours(gate) {
  const [h, m] = gate.split(':').map(Number);
  return h + m / 60;
}

function nearest(points, hours) {
  return points.reduce((best, p) =>
    p.count > 0 && Math.abs(p.horizonHours - hours) < Math.abs(best.horizonHours - hours) ? p : best,
  );
}

export default function AccuracyView({ gate, onOpenDay }) {
  const curve = useApi((signal) => api.horizonCurve({ step: 0.5 }, signal), []);
  const daily = useApi((signal) => api.dailyAccuracy({ gate }, signal), [gate]);

  // Lead times covered when trading a whole delivery day at this gate.
  const lo = 24 - gateHours(gate);
  const dayAheadRange = [Math.max(0, lo), Math.min(48, lo + 23.5)];

  const days = daily.data?.days.filter((d) => d.errorMwh != null) ?? [];
  const over = days.filter((d) => d.errorMwh > 0).length;
  const worst = days.reduce((w, d) => (w == null || Math.abs(d.errorMwh) > Math.abs(w.errorMwh) ? d : w), null);
  const s = daily.data?.summary;

  let growth = null;
  if (curve.data) {
    const at0 = nearest(curve.data.points, 0);
    const atFar = nearest(curve.data.points, dayAheadRange[1]);
    growth = { at0, atFar };
  }

  return (
    <>
      <header className="view-intro">
        <h2>How good are the forecasts?</h2>
        <p>
          Accuracy across every delivery period from 1 January to 1 February, measured on the forecast the desk would actually have used.
          Use these numbers to size how much cover to hold against a wind shortfall.
        </p>
      </header>

      {(daily.error || curve.error) && <ErrorState error={daily.error || curve.error} />}
      {(!daily.data || !curve.data) && !(daily.error || curve.error) && <Loading />}

      {daily.data && curve.data && (
        <>
          <StatGrid>
            <StatTile tone="forecast" label={`Mean absolute error at ${gate} gate`} value={formatMW(s.mae)} note={`${s.count} hourly periods`} />
            <StatTile
              tone="short"
              label="Bias (forecast − actual)"
              value={formatSignedMW(s.bias)}
              note={`Forecast too high on ${over} of ${days.length} days`}
            />
            <StatTile label="P90 absolute error" value={formatMW(s.p90AbsError)} note={`P99: ${formatMW(s.p99AbsError)}`} />
            <StatTile label="Error relative to output" value={formatPct(s.wapePct)} note="Total |error| ÷ total actual" />
          </StatGrid>

          <section className="card">
            <div className="card__head">
              <h3 className="card__title">What the numbers say</h3>
            </div>
            <ul className="findings">
              <li className="is-risk">
                The forecast available at the {gate} gate over-predicted wind on <strong>{over} of {days.length}</strong>{' '}
                delivery days, by {formatSignedMW(s.bias)} on average. Treating it as unbiased would leave the desk
                systematically short.
              </li>
              <li>
                Error grows with lead time: mean absolute error is {formatMW(growth.at0.mae)} for the freshest forecast and{' '}
                {formatMW(growth.atFar.mae)} at {growth.atFar.horizonHours}h, the longest lead time a {gate} gate implies.
              </li>
              {worst && (
                <li className="is-risk">
                  The largest miss was{' '}
                  <button type="button" className="chip" onClick={() => onOpenDay(worst.deliveryDate)}>
                    {formatDeliveryDate(worst.deliveryDate)}
                  </button>{' '}
                  at {formatSignedGWh(worst.errorMwh)} over the day.
                </li>
              )}
            </ul>
          </section>

          <section className="card">
            <div className="card__head">
              <h3 className="card__title">Error vs forecast lead time</h3>
              <div className="legend" aria-hidden="true">
                <span>
                  <i className="swatch" style={{ background: 'var(--forecast)' }} /> Mean abs error
                </span>
                <span>
                  <i className="swatch" style={{ background: 'var(--short)' }} /> P90 abs error
                </span>
                <span>
                  <i className="swatch" style={{ background: 'var(--actual)' }} /> Bias
                </span>
              </div>
            </div>
            <HorizonCurveChart points={curve.data.points} dayAheadRange={dayAheadRange} />
            <p className="card__note">All January target hours. Forecasts are issued eight times a day, so the curve steps.</p>
          </section>

          <section className="card">
            <div className="card__head">
              <h3 className="card__title">Daily energy error, forecast at {gate} gate</h3>
              <div className="legend" aria-hidden="true">
                <span>
                  <i className="swatch" style={{ background: 'var(--short)', height: 10 }} /> Over-forecast (short risk)
                </span>
                <span>
                  <i className="swatch" style={{ background: 'var(--long)', height: 10 }} /> Under-forecast
                </span>
              </div>
            </div>
            <DailyScorecardChart days={daily.data.days} onSelect={onOpenDay} />
            <p className="card__note">Click a day to open it in the day-ahead view.</p>
          </section>
        </>
      )}
    </>
  );
}
