'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { bind, OPERATIONS } = require('../scripts/bind_production_action.cjs');
const root = path.resolve(__dirname, '..');
const rawSpec = fs.readFileSync(path.join(root, 'actions/datacheck.production.openapi.json'), 'utf8');
test('authenticated transport supplies a compatible identified client and preserves authorization', async () => {
  let sent;
  const context = vm.createContext({ require, module: { exports: {} }, Buffer, AbortSignal,
    fetch: async (url, options) => { sent = { url, ...options }; return { ok: true, body: [Buffer.from('{}')] }; } });
  vm.runInContext(fs.readFileSync(path.join(root, 'scripts/bind_production_action.cjs'), 'utf8'), context);
  await context.httpRequest('GET', '/api/agents/agent_test/expanded', undefined, 'synthetic-session');
  assert.match(sent.headers['User-Agent'] || '', /^Mozilla\/5\.0 .*APICompassSetup\/1\.0$/);
  assert.equal(sent.headers.Authorization, 'Bearer synthetic-session');
  assert.equal(sent.redirect, 'error');
  assert.equal(sent.url, 'http://127.0.0.1:3080/api/agents/agent_test/expanded');
});
const input = { agentId: 'agent_test', email: 'synthetic@example.invalid', password: 'synthetic-password', apiKey: 'x'.repeat(32), rawSpec, instructions: 'Synthetic instructions' };
const provider = {
  AuthTypeEnum: { ServiceHttp: 'service_http' }, AuthorizationTypeEnum: { Bearer: 'bearer' }, actionDelimiter: '_action_',
  validateAndParseOpenAPISpec: raw => ({ status: true, serverUrl: 'http://datacheck:8000', spec: JSON.parse(raw) }),
  openapiToFunction: spec => ({ functionSignatures: Object.values(spec.paths).map(methods => ({ toObjectTool: () => ({ type: 'function', function: { name: methods.get.operationId } }) })) }),
};
function harness(overrides = {}) {
  const calls = []; let saved = false;
  const agent = () => ({ id: input.agentId, author: 'owner', name: 'DataCheck', provider: 'google', model: 'gemini-3.5-flash-lite', instructions: input.instructions, actions: saved ? ['action'] : [], tools: saved ? OPERATIONS.map(name => name + '_action_datacheck') : [], ...overrides });
  const action = () => ({ agent_id: input.agentId, user: 'owner', metadata: { domain: 'http://datacheck', raw_spec: rawSpec, auth: { type: 'service_http', authorization_type: 'bearer' } } });
  return { calls, request: async (method, url, body) => {
    calls.push({ method, url });
    if (url === '/api/auth/login') return { token: 'synthetic-session', user: { id: 'owner' } };
    if (url.endsWith('/expanded')) return agent();
    if (url === '/api/agents/actions') return saved ? [action()] : [];
    assert.equal(method, 'POST'); assert.equal(body.metadata.api_key, input.apiKey);
    saved = true; return [agent(), action()];
  } };
}
test('binds exactly four operations through authenticated supported API', async () => {
  const h = harness(); const result = await bind(input, { provider, request: h.request });
  assert.equal(result.action_count, 1); assert.equal(h.calls.filter(c => c.method === 'POST').length, 2);
});
for (const override of [{ author: 'other' }, { isPublic: true }, { actions: ['existing'] }, { tools: ['existing'] }, { instructions: 'different' }, { model: 'other' }]) {
  test('refuses unsafe or already configured agent ' + Object.keys(override)[0], async () => {
    const h = harness(override); await assert.rejects(bind(input, { provider, request: h.request }));
    assert.equal(h.calls.filter(c => c.url.startsWith('/api/agents/actions/') && c.method === 'POST').length, 0);
  });
}
test('contract uses the upstream converter and documented API/auth fields', () => {
  const read = name => fs.readFileSync(path.join(root, 'upstream/LibreChat', name), 'utf8');
  const ui = read('client/src/components/SidePanel/Agents/ActionsInput.tsx');
  assert.match(ui, /openapiToFunction\(validationResult.spec\)/);
  assert.match(ui, /functionSignatures.map\(\(f\) => f.toObjectTool\(\)\)/);
  assert.match(ui, /metadata.domain = `\$\{parsedUrl.protocol\}\/\/\$\{parsedUrl.hostname\}`/);
  assert.match(read('api/server/routes/agents/v1.js'), /router.use\('\/actions'/);
  assert.match(read('api/server/routes/agents/actions.js'), /router.post\(\s*'\/:agent_id'/);
  assert.match(read('api/server/controllers/auth/LoginController.js'), /send\(\{ token, user \}\)/);
  assert.match(read('packages/data-provider/src/types/agents.ts'), /Bearer = 'bearer'/);
});
test('invalid operation set fails before any login or write', async () => {
  const h = harness(); const spec = JSON.parse(rawSpec); delete spec.paths['/datasets'];
  await assert.rejects(bind({ ...input, rawSpec: JSON.stringify(spec) }, { provider, request: h.request }));
  assert.equal(h.calls.length, 0);
});
test('failed login stops before agent reads and writes', async () => {
  let count = 0;
  await assert.rejects(bind(input, { provider, request: async () => { count++; return { twoFAPending: true }; } }));
  assert.equal(count, 1);
});
test('readback failure never reports successful binding', async () => {
  const h = harness(); let reads = 0;
  const request = async (...args) => {
    const value = await h.request(...args);
    if (args[1].endsWith('/expanded') && ++reads === 2) value.tools = ['unexpected'];
    return value;
  };
  await assert.rejects(bind(input, { provider, request }));
});
test('raw request exceptions become fixed login stage without response data', async () => {
  await assert.rejects(bind(input, { provider, request: async () => { throw new Error('PRIVATE_RAW_RESPONSE'); } }), error => {
    assert.equal(error.code, 'login_request'); assert.equal(error.message, 'login_request');
    assert.equal(JSON.stringify(error).includes('PRIVATE_RAW_RESPONSE'), false); return true;
  });
});
test('unexpected provider converter becomes fixed spec stage before login', async () => {
  let requests = 0;
  await assert.rejects(bind(input, { provider: { ...provider, openapiToFunction: () => { throw new Error('PRIVATE_RAW_SPEC'); } },
    request: async () => { requests++; } }), error => error.code === 'spec_conversion' && !error.message.includes('PRIVATE'));
  assert.equal(requests, 0);
});
test('owner mismatch reports precondition stage without weakening ownership', async () => {
  const h = harness({ author: 'another-owner' });
  await assert.rejects(bind(input, { provider, request: h.request }), error => error.code === 'agent_preconditions');
});
