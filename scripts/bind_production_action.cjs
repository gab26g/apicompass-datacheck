'use strict';
// Runs inside the pinned chat image; only supported HTTP APIs, no database access.
const fs = require('node:fs');
const OPERATIONS = ['get_dataset_issues', 'get_dataset_profile', 'list_datasets', 'list_validation_rules'];
class BindingError extends Error {}
async function stage(code, work) {
  try { return await work(); } catch { const error = new BindingError(code); error.code = code; throw error; }
}
const requireSafe = condition => { if (!condition) throw new BindingError('Production action setup stopped; inspect the documented preconditions privately.'); };

function validateSpec(raw, provider) {
  const result = provider.validateAndParseOpenAPISpec(raw);
  requireSafe(result.status && result.serverUrl === 'http://datacheck:8000');
  const { functionSignatures } = provider.openapiToFunction(result.spec);
  const functions = functionSignatures.map(f => f.toObjectTool());
  requireSafe(functions.length === 4 && JSON.stringify(functions.map(f => f.function.name).sort()) === JSON.stringify(OPERATIONS));
  requireSafe(Object.values(result.spec.paths).every(methods => Object.keys(methods).every(method => method === 'get')));
  return functions;
}

async function bind(input, { provider, request }) {
  requireSafe(input && /^[A-Za-z0-9_-]{1,128}$/.test(input.agentId) &&
    typeof input.email === 'string' && input.email.length <= 254 &&
    typeof input.password === 'string' && input.password.length > 0 && input.password.length <= 128 &&
    typeof input.apiKey === 'string' && /^[!-~]{32,4096}$/.test(input.apiKey) &&
    typeof input.instructions === 'string' && input.instructions.length > 0 && input.instructions.length < 32768);
  const functions = await stage('spec_conversion', () => validateSpec(input.rawSpec, provider));
  const login = await stage('login_request', () => request('POST', '/api/auth/login', { email: input.email, password: input.password }));
  await stage('login_contract', () => requireSafe(typeof login.token === 'string' && typeof login.user?.id === 'string'));
  const token = login.token;
  const path = '/api/agents/' + input.agentId;
  const checkAgent = agent => {
    requireSafe(agent?.id === input.agentId && agent.author === login.user.id && agent.name === 'DataCheck' &&
      agent.provider === 'google' && agent.model === 'gemini-3.5-flash-lite' &&
      typeof agent.instructions === 'string' &&
      agent.instructions.replace(/\r\n/g, '\n').trim() === input.instructions.replace(/\r\n/g, '\n').trim() && !agent.isPublic);
    return agent;
  };
  const expanded = await stage('agent_request', () => request('GET', path + '/expanded', undefined, token));
  const agent = await stage('agent_preconditions', () => checkAgent(expanded));
  const all = await stage('actions_request', () => request('GET', '/api/agents/actions', undefined, token));
  requireSafe(Array.isArray(all) && all.length <= 100);
  const owned = all.filter(action => action.agent_id === input.agentId);
  // Never replace credentials or overwrite an existing action on rerun.
  await stage('action_already_present', () => requireSafe(owned.length === 0 && (agent.actions || []).length === 0 && (agent.tools || []).length === 0));
  const response = await stage('action_save', () => request('POST', '/api/agents/actions/' + input.agentId, {
    functions, metadata: { raw_spec: input.rawSpec, domain: 'http://datacheck', api_key: input.apiKey,
      auth: { type: provider.AuthTypeEnum.ServiceHttp, authorization_type: provider.AuthorizationTypeEnum.Bearer } },
  }, token));
  requireSafe(Array.isArray(response) && response.length === 2);
  const finalAgent = await stage('agent_readback', async () => checkAgent(await request('GET', path + '/expanded', undefined, token)));
  const finalActions = await stage('actions_readback_request', () => request('GET', '/api/agents/actions', undefined, token));
  requireSafe(Array.isArray(finalActions) && finalActions.length <= 100);
  const bound = finalActions.filter(action => action.agent_id === input.agentId);
  await stage('action_readback_contract', () => requireSafe(bound.length === 1 && bound[0].user === login.user.id &&
    bound[0].metadata?.domain === 'http://datacheck' && bound[0].metadata.raw_spec === input.rawSpec &&
    bound[0].metadata.auth?.type === provider.AuthTypeEnum.ServiceHttp &&
    bound[0].metadata.auth?.authorization_type === provider.AuthorizationTypeEnum.Bearer &&
    finalAgent.actions?.length === 1 && finalAgent.tools?.length === 4 &&
    JSON.stringify([...finalAgent.tools].sort()) ===
      JSON.stringify(OPERATIONS.map(operation => operation + provider.actionDelimiter + 'datacheck').sort())));
  return { status: 'verified', agent_id: input.agentId, action_count: 1, operation_count: 4 };
}

async function httpRequest(method, path, body, token) {
  requireSafe(path.startsWith('/api/') && !path.includes('..'));
  const response = await fetch('http://127.0.0.1:3080' + path, {
    method, redirect: 'error', signal: AbortSignal.timeout(15000),
    // Pinned LibreChat agent routes require a browser-compatible user agent.
    headers: { 'Content-Type': 'application/json',
      'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 APICompassSetup/1.0',
      ...(token ? { Authorization: 'Bearer ' + token } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  requireSafe(response.ok);
  const chunks = []; let total = 0;
  for await (const chunk of response.body) {
    total += chunk.length;
    if (total > 1024 * 1024) requireSafe(false);
    chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

async function main() {
  // Avoid upstream parser/module diagnostics echoing supplied values.
  for (const name of ['log', 'error', 'warn', 'info', 'debug']) console[name] = () => {};
  try {
    const checkOnly = process.argv.length === 3 && process.argv[2] === '--check-spec';
    requireSafe((process.argv.length === 2 || checkOnly) && !process.stdin.isTTY);
    const stat = fs.fstatSync(0);
    requireSafe(!stat.isFile()); // Credentials arrive through an anonymous pipe only.
    const chunks = []; let total = 0;
    for await (const chunk of process.stdin) { total += chunk.length; requireSafe(total <= 65536); chunks.push(chunk); }
    const input = JSON.parse(Buffer.concat(chunks).toString('utf8'));
    const provider = await stage('provider_load', () => require('/app/node_modules/librechat-data-provider'));
    if (checkOnly) {
      const functions = await stage('spec_conversion', () => validateSpec(input.rawSpec, provider));
      process.stdout.write(JSON.stringify({ status: 'spec_valid', operation_count: functions.length }) + '\n');
      return;
    }
    const result = await bind(input, { provider, request: httpRequest });
    process.stdout.write(JSON.stringify(result) + '\n');
  } catch (error) {
    const stages = new Set(['provider_load', 'spec_conversion', 'login_request', 'login_contract', 'agent_request',
      'agent_preconditions', 'actions_request', 'action_already_present', 'action_save', 'agent_readback',
      'actions_readback_request', 'action_readback_contract']);
    process.stderr.write(JSON.stringify({ status: 'failed', stage: stages.has(error?.code) ? error.code : 'input_or_contract' }) + '\n');
    process.exitCode = 1;
  }
}
module.exports = { bind, validateSpec, BindingError, OPERATIONS };
if (require.main === module) main();
