import test from 'node:test';
import assert from 'node:assert/strict';

import {
  addDays,
  formatGWh,
  formatSignedMW,
  londonLocalToUtcIso,
  utcIsoToLondonLocal,
} from './format.js';

test('UK winter time equals UTC', () => {
  assert.equal(londonLocalToUtcIso('2026-01-15T09:30'), '2026-01-15T09:30:00Z');
  assert.equal(utcIsoToLondonLocal('2026-01-15T09:30:00Z'), '2026-01-15T09:30');
});

test('UK summer time is UTC+1', () => {
  assert.equal(londonLocalToUtcIso('2026-07-15T09:30'), '2026-07-15T08:30:00Z');
  assert.equal(utcIsoToLondonLocal('2026-07-15T08:30:00Z'), '2026-07-15T09:30');
});

test('addDays crosses month boundaries', () => {
  assert.equal(addDays('2026-01-31', 1), '2026-02-01');
  assert.equal(addDays('2026-01-01', -1), '2025-12-31');
});

test('number formatting', () => {
  assert.equal(formatGWh(280272), '280.3 GWh');
  assert.equal(formatSignedMW(-1500), '−1,500 MW');
  assert.equal(formatSignedMW(null), '—');
});
