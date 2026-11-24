#!/usr/bin/env node
/* ─── the sign-in survives closing the tab, and an old tab's sign-in carries over ───────────────────
 *   RUN:  node tests/session_storage_test.js
 *
 * EXECUTING, not source-shaped: it lifts the real session functions out of template.html and runs them
 * against fake localStorage / sessionStorage, so what passes here is the code the page runs.
 *
 * Why: up to v1.003 the session lived in sessionStorage, so closing the tab signed you out. Sky agreed
 * (2026-11-23) that store computers are private and a sign-in may last as long as the token does. A
 * manager who signed in under v1.003 and still has that tab open must stay signed in after the update,
 * and sign-out must leave nothing behind in either place.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const src = fs.readFileSync(path.join(__dirname, '..', 'template.html'), 'utf8');
const lines = src.split('\n');
const start = lines.findIndex(l => l.startsWith('const SESSION_KEY='));
const end = lines.findIndex(l => l.startsWith('function clearSession('));
if (start < 0 || end < 0 || end < start) { console.log('  FAIL  could not find the session functions in template.html'); process.exit(1); }
/* everything from SESSION_KEY through clearSession — the STORES/EDIT_ROLES consts in between are harmless */
const code = lines.slice(start, end + 1).join('\n');

function fakeStore(throws) {
  const m = new Map();
  return {
    getItem(k) { if (throws) throw new Error('blocked'); return m.has(k) ? m.get(k) : null; },
    setItem(k, v) { if (throws) throw new Error('blocked'); m.set(k, String(v)); },
    removeItem(k) { if (throws) throw new Error('blocked'); m.delete(k); },
    _m: m,
  };
}
function load(opts) {
  opts = opts || {};
  const ctx = { localStorage: fakeStore(opts.localThrows), sessionStorage: fakeStore(false), Date, JSON, Number, isFinite, isNaN };
  vm.createContext(ctx);
  vm.runInContext(code + '\n;this.api={getSession,setSession,clearSession,SESSION_KEY};', ctx);
  return ctx;
}

let pass = 0, fail = 0;
const ok = (c, l) => { if (c) { pass++; console.log('  PASS  ' + l); } else { fail++; console.log('  FAIL  ' + l); } };
console.log('display shop sign-in storage\n');

const KEY = 'displayshop_session';
const future = Date.now() + 30 * 864e5;
const live = JSON.stringify({ token: 't1', expiresAt: future });

{ const c = load(); c.api.setSession({ token: 't1', expiresAt: future });
  ok(c.localStorage._m.has(KEY), 'a new sign-in is saved to localStorage');
  ok(!c.sessionStorage._m.has(KEY), 'and not to sessionStorage');
  ok(c.api.getSession() && c.api.getSession().token === 't1', 'and is read back'); }

{ const c = load(); c.sessionStorage._m.set(KEY, live);
  const s = c.api.getSession();
  ok(s && s.token === 't1', 'a v1.003 sign-in still in sessionStorage is honored');
  ok(c.localStorage._m.get(KEY) === live, 'it is copied into localStorage');
  ok(!c.sessionStorage._m.has(KEY), 'and the old sessionStorage copy is removed'); }

{ const c = load(); c.localStorage._m.set(KEY, live); c.sessionStorage._m.set(KEY, JSON.stringify({ token: 'old', expiresAt: future }));
  ok(c.api.getSession().token === 't1', 'localStorage wins when both hold one'); }

{ const c = load(); c.localStorage._m.set(KEY, live); c.sessionStorage._m.set(KEY, live);
  c.api.clearSession();
  ok(!c.localStorage._m.has(KEY) && !c.sessionStorage._m.has(KEY), 'sign-out clears both');
  ok(c.api.getSession() === null, 'and nothing reads back'); }

{ const c = load(); c.localStorage._m.set(KEY, JSON.stringify({ token: 't1', expiresAt: Date.now() - 1000 }));
  ok(c.api.getSession() === null, 'an expired token (epoch ms) is refused'); }

{ const c = load(); c.localStorage._m.set(KEY, JSON.stringify({ token: 't1', expiresAt: new Date(Date.now() - 1000).toISOString() }));
  ok(c.api.getSession() === null, 'an expired token (ISO date) is refused'); }

{ const c = load(); c.localStorage._m.set(KEY, JSON.stringify({ token: 't1', expiresAt: new Date(future).toISOString() }));
  ok(c.api.getSession() && c.api.getSession().token === 't1', 'an unexpired ISO expiry is accepted'); }

{ const c = load(); c.localStorage._m.set(KEY, '{not json');
  ok(c.api.getSession() === null, 'a corrupt stored value reads as signed out, not a crash'); }

{ const c = load({ localThrows: true }); let threw = false;
  try { c.api.setSession({ token: 't1' }); c.api.getSession(); c.api.clearSession(); } catch (e) { threw = true; }
  ok(!threw, 'blocked localStorage (private window) never throws'); }

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
