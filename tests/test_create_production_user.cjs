'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { installGuards } = require('../scripts/create_production_user.cjs');

function fixture({ count = 0, hidden = ['synthetic-password', 'synthetic-password'], valid = true } = {}) {
  const calls = { visible: [], hidden: [], register: [] };
  const helpers = {
    askQuestion: async query => { calls.visible.push(query); return 'private-nonsecret-input'; },
    askSilentQuestion: async query => { calls.hidden.push(query); return hidden.shift(); },
  };
  const User = { countDocuments: async () => count };
  const auth = { registerUser: async (...args) => { calls.register.push(args); return { status: 200 }; } };
  installGuards({ helpers, User, auth, registerSchema: { safeParse: () => ({ success: valid }) } });
  return { calls, helpers, auth };
}

test('password and confirmation use hidden helper only, ordinary account questions stay visible', async () => {
  const h = fixture();
  await h.helpers.askQuestion('Email:');
  assert.equal(await h.helpers.askQuestion('Password: (leave blank, to generate one)'), 'synthetic-password');
  assert.equal(h.calls.hidden.length, 2);
  assert.deepEqual(h.calls.visible, ['Email:']);
  assert.doesNotMatch(JSON.stringify(h.calls), /synthetic-password/);
});

test('blank, short, oversized and mismatching passwords cannot reach upstream generation path', async () => {
  for (const hidden of [[''], ['short'], ['x'.repeat(129)], ['synthetic-password', 'different-password']]) {
    const h = fixture({ hidden });
    await assert.rejects(h.helpers.askQuestion('Password:'), /Password|Passwords/);
    assert.equal(h.calls.visible.length, 0); assert.equal(h.calls.register.length, 0);
  }
});

test('existing database is refused before any private identity or password prompt', async () => {
  const h = fixture({ count: 1 });
  await assert.rejects(h.helpers.askQuestion('Email:'), /already has a user/);
  assert.equal(h.calls.visible.length, 0); assert.equal(h.calls.hidden.length, 0);
});

test('invalid input is rejected without invoking the upstream password-logging validation path', async () => {
  const h = fixture({ valid: false });
  const result = await h.auth.registerUser({ password: 'synthetic-password' }, {});
  assert.equal(result.status, 400); assert.equal(h.calls.register.length, 0);
  assert.doesNotMatch(JSON.stringify(result), /synthetic-password/);
});

test('registration rechecks fresh state and forces verified email without sending messages', async () => {
  const h = fixture();
  await h.auth.registerUser({ password: 'synthetic-password' }, { emailVerified: false });
  assert.equal(h.calls.register.length, 1); assert.equal(h.calls.register[0][1].emailVerified, true);
  const existing = fixture({ count: 1 });
  assert.equal((await existing.auth.registerUser({}, {})).status, 409);
  assert.equal(existing.calls.register.length, 0);
});
