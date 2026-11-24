'use strict';
// Runs only inside the labelled assessment chat container, using normal login.
const { randomUUID } = require('node:crypto');
const { StringDecoder } = require('node:string_decoder');
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 APICompassRecovery/1.0';
const safe = condition => { if (!condition) throw new Error('verification_failed'); };
const id = value => typeof value === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(value);

function inspectAnswer(message, started) {
  safe(message && !message.error && !message.unfinished && Array.isArray(message.content));
  const tools = message.content.filter(p => p.type === 'tool_call' &&
    p.tool_call?.name === 'get_dataset_issues_action_datacheck');
  safe(tools.length === 1 && typeof tools[0].tool_call.output === 'string');
  const report = JSON.parse(tools[0].tool_call.output);
  const stamp = Date.parse(report.generated_at);
  safe(report.id === 'shipments' && report.row_count === 60 && report.issue_count === 7 &&
    report.affected_row_count === 7 && report.dataset_version === 'shipments-v2' &&
    report.ruleset_version === 'shipments-rules-v2' && report.source?.storage === 's3' &&
    typeof report.source.object_version === 'string' && !['', 'null'].includes(report.source.object_version) &&
    /^[a-f0-9-]{36}$/.test(report.request_id) && Number.isFinite(stamp) && stamp >= started);
  const text = message.content.filter(p => p.type === 'text').map(p =>
    typeof p.text === 'string' ? p.text : p.text?.value || '').join('\n').replace(/[`*]/g, '').toLowerCase();
  safe(/row[ _]*count\s*:\s*60\b/.test(text) && /issue[ _]*count\s*:\s*7\b/.test(text) &&
    /affected[ _]*row[ _]*count\s*:\s*7\b/.test(text) && text.includes(report.request_id) &&
    text.includes('shipments-v2') && text.includes('shipments-rules-v2'));
  return { row_count: 60, issue_count: 7, affected_row_count: 7, request_id: report.request_id,
    dataset_version: report.dataset_version, ruleset_version: report.ruleset_version };
}

async function readFinal(body) {
  const decoder = new StringDecoder('utf8');
  let pending = '', total = 0, frameBytes = 0, data = [], event = '', final, failed = false;
  const frame = () => {
    if (event === 'error') failed = true;
    if (data.length) {
      const value = JSON.parse(data.join('\n'));
      if (value.error || value.responseMessage?.error) failed = true;
      if (value.final === true) { safe(!value.reconcile && value.responseMessage); final = value.responseMessage; }
    }
    data = []; event = ''; frameBytes = 0;
  };
  for await (const chunk of body) {
    total += chunk.length; safe(total <= 2 * 1024**2);
    pending += decoder.write(Buffer.from(chunk));
    safe(Buffer.byteLength(pending) <= 65536);
    let end;
    while ((end = pending.indexOf('\n')) !== -1) {
      const line = pending.slice(0, end).replace(/\r$/, ''); pending = pending.slice(end + 1);
      frameBytes += Buffer.byteLength(line); safe(frameBytes <= 65536);
      if (!line) frame();
      else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''));
      else if (line.startsWith('event:')) event = line.slice(6).trim();
    }
  }
  safe(!decoder.lastNeed && !pending && !data.length && !failed && final);
  return final;
}

async function probe(input, transport = fetch) {
  let stage = 'input', token, httpStatus = 0;
  const base = 'http://127.0.0.1:3080';
  const request = async (path, method = 'GET', body) => {
    const response = await transport(base + path, { method, redirect: 'error', signal: AbortSignal.timeout(120000),
      headers: { 'Content-Type': 'application/json', 'User-Agent': UA, 'X-LibreChat-Generation-Protocol': '2',
        ...(token ? { Authorization: 'Bearer ' + token } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body) });
    httpStatus = Number.isInteger(response.status) && response.status >= 100 && response.status <= 599 ? response.status : 0;
    safe(response.ok);
    return response;
  };
  const json = async (...args) => {
    const response = await request(...args); let size = 0, chunks = [];
    for await (const chunk of response.body) { size += chunk.length; safe(size <= 1024**2); chunks.push(Buffer.from(chunk)); }
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  };
  try {
    safe(input && id(input.conversation_id) && id(input.agent_id) && typeof input.email === 'string' &&
      input.email.length <= 254 && typeof input.password === 'string' && input.password.length <= 128);
    stage = 'login'; const login = await json('/api/auth/login', 'POST', { email: input.email, password: input.password });
    stage = 'login_contract';
    safe(typeof login.token === 'string' && typeof login.user?.id === 'string'); token = login.token;
    stage = 'conversation'; const convo = await json('/api/convos/' + input.conversation_id);
    safe(convo.conversationId === input.conversation_id && convo.agent_id === input.agent_id);
    stage = 'agent'; const agent = await json('/api/agents/' + input.agent_id + '/expanded');
    safe(agent.author === login.user.id && !agent.isPublic && agent.name === 'DataCheck' &&
      agent.provider === 'google' && agent.model === 'gemini-3.5-flash-lite' && agent.tools?.length === 4 && agent.actions?.length === 1);
    stage = 'action'; const actions = await json('/api/agents/actions');
    safe(Array.isArray(actions)); const owned = actions.filter(a => a.agent_id === input.agent_id);
    safe(owned.length === 1 && owned[0].user === login.user.id && owned[0].metadata?.domain === 'http://datacheck');
    stage = 'admission'; const started = Date.now();
    const admitted = await json('/api/agents/chat/agents', 'POST', { endpoint: 'agents', agent_id: input.agent_id,
      conversationId: 'new', messageId: randomUUID(), clientRequestId: randomUUID(),
      parentMessageId: '00000000-0000-0000-0000-000000000000', isCreatedByUser: true, isTemporary: false,
      generationProtocolVersion: 2,
      text: 'Run a fresh get_dataset_issues check for shipments. In your final answer use these exact labels: row_count, issue_count, affected_row_count, dataset_version, ruleset_version, request_id. Put a colon after each label. Do not reuse earlier results.' });
    safe(admitted.status === 'started' && id(admitted.streamId) && Number.isSafeInteger(admitted.generationCreatedAt));
    stage = 'stream'; const response = await request('/api/agents/chat/stream/' + admitted.streamId +
      '?generationCreatedAt=' + admitted.generationCreatedAt + '&generationProtocolVersion=2');
    safe((response.headers.get('content-type') || '').startsWith('text/event-stream'));
    const message = await readFinal(response.body);
    stage = 'answer'; const result = inspectAnswer(message, started);
    return { login: true, conversation_present: true, action_present: true, tool_answer_verified: true, ...result };
  } catch { return { verified: false, stage, http_status: httpStatus }; }
  finally { if (token) await request('/api/auth/logout', 'POST').catch(() => {}); }
}

async function main() {
  let size = 0, chunks = [];
  try {
    safe(!process.stdin.isTTY && !require('node:fs').fstatSync(0).isFile());
    for await (const chunk of process.stdin) { size += chunk.length; safe(size <= 4096); chunks.push(chunk); }
    const result = await probe(JSON.parse(Buffer.concat(chunks).toString('utf8')));
    process.stdout.write(JSON.stringify(result) + '\n');
  } catch { process.stdout.write('{"verified":false,"stage":"input"}\n'); }
}
module.exports = { inspectAnswer, readFinal, probe, main };
