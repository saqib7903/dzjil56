import { useEffect, useState } from 'react';

import { api } from './api/client.js';
import { ErrorState, Loading } from './components/Status.jsx';
import { useApi } from './hooks/useApi.js';
import { formatDateTime } from './lib/format.js';
import AccuracyView from './views/AccuracyView.jsx';
import DayAheadView from './views/DayAheadView.jsx';
import ExplorerView from './views/ExplorerView.jsx';

const TABS = [
  ['day-ahead', 'Day-ahead'],
  ['explorer', 'Forecast vs actual'],
  ['accuracy', 'Accuracy'],
];

function readHash() {
  const id = window.location.hash.replace('#', '');
  return TABS.some(([t]) => t === id) ? id : 'day-ahead';
}

export default function App() {
  const [tab, setTab] = useState(readHash);
  const [date, setDate] = useState('2026-01-15');
  const [gate, setGate] = useState(null);
  const [attempt, setAttempt] = useState(0);
  const meta = useApi((signal) => api.meta(signal), [attempt]);

  useEffect(() => {
    const onHash = () => setTab(readHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  useEffect(() => {
    if (meta.data && gate == null) setGate(meta.data.defaultGateClosure);
  }, [meta.data, gate]);

  const selectTab = (id) => {
    setTab(id);
    window.history.replaceState(null, '', `#${id}`);
  };

  const openDay = (day) => {
    setDate(day);
    selectTab('day-ahead');
    window.scrollTo({ top: 0 });
  };

  return (
    <>
      <header className="masthead">
        <div className="masthead__inner">
          <div className="masthead__top">
            <div>
              <h1 className="wordmark">
                Wind<span>ward</span>
              </h1>
              <p className="masthead__tagline">GB national wind forecasts vs outturn, for day-ahead procurement</p>
            </div>
            {meta.data && (
              <span className="source-chip">
                Elexon BMRS · <b>{meta.data.dataSource === 'live' ? 'live' : 'snapshot'}</b> ·{' '}
                {meta.data.dataSource === 'live' ? 'updated' : 'taken'} {formatDateTime(meta.data.loadedAt)}
              </span>
            )}
          </div>
          <nav className="tabs" role="tablist" aria-label="Views">
            {TABS.map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="tab"
                className="tab"
                aria-selected={tab === id}
                onClick={() => selectTab(id)}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="page">
        {meta.error && <ErrorState error={meta.error} onRetry={() => setAttempt((n) => n + 1)} />}
        {!meta.data && !meta.error && <Loading label="Connecting to the data service…" />}
        {meta.data && gate && (
          <>
            {tab === 'day-ahead' && (
              <DayAheadView meta={meta.data} date={date} onDateChange={setDate} gate={gate} onGateChange={setGate} />
            )}
            {tab === 'explorer' && <ExplorerView meta={meta.data} />}
            {tab === 'accuracy' && <AccuracyView gate={gate} onOpenDay={openDay} />}
            <p className="footer">
              Data: Elexon Insights Solution — FUELHH (wind outturn, 30-min) and WINDFOR (national wind forecast,
              hourly). Delivery days {meta.data.firstDeliveryDate} to {meta.data.lastDeliveryDate}, times in UK local
              time. Forecasts more than {meta.data.maxHorizonHours} hours ahead are excluded.
            </p>
          </>
        )}
      </main>
    </>
  );
}
