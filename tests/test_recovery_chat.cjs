'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { inspectAnswer, readFinal, probe } = require('../scripts/recovery_chat.cjs');
const generated = '2026-11-23T11:40:00.000Z';
const started = Date.parse(generated) - 1000;
const report = { id: 'shipments', row_count: 60, issue_count: 7, affected_row_count: 7,
  dataset_version: 'shipments-v2', ruleset_version: 'shipments-rules-v2', generated_at: generated,
  request_id: 'a0418fb3-ba8e-420c-bcc6-92c4ce6f7762', source: { storage: 's3', object_version: 'actual-version' } };
const answer = () => ({ content: [{ type: 'tool_call', tool_call: {
  name: 'get_dataset_issues_action_datacheck', output: JSON.stringify(report) } },
{ type: 'text', text: 'row_count: 60\nissue_count: 7\naffected_row_count: 7\ndataset_version: shipments-v2\nruleset_version: shipments-rules-v2\nrequest_id: ' + report.request_id }] });
test('requires a fresh S3 tool result and matching final answer', () => {
  assert.equal(inspectAnswer(answer(), started).request_id, report.request_id);
  for (const bad of [ { content: answer().content.slice(1) }, { ...answer(), error: true },
    { ...answer(), unfinished: true }, { content: [answer().content[0], { type: 'text', text: 'Everything is clean' }] } ]) {
    assert.throws(() => inspectAnswer(bad, started));
  }
  assert.throws(() => inspectAnswer(answer(), Date.parse(generated) + 1000));
});
test('accepts only a complete final SSE frame; provider errors remain failures', async () => {
  const frame = 'event: message\ndata: ' + JSON.stringify({ final: true, responseMessage: answer() }) + '\n\n';
  assert.deepEqual(await readFinal([Buffer.from(frame)]), answer());
  for (const bad of ['data: {"final":true}\n\n', frame.slice(0, -2),
    'event: error\ndata: {"error":"PRIVATE_ERROR"}\n\n' + frame]) {
    await assert.rejects(readFinal([Buffer.from(bad)]));
  }
});

test('normal authenticated recovery flow verifies restored resources before starting a fresh tool turn', async () => {
  const input = { email: 'synthetic@example.invalid', password: 'PRIVATE_PASSWORD', conversation_id: 'saved-convo', agent_id: 'agent_saved' };
  const calls = [];
  const transport = async (url, options) => {
    calls.push({ url, options });
    const path = new URL(url).pathname;
    const reply = object => ({ ok: true, body: [Buffer.from(JSON.stringify(object))] });
    if (path.endsWith('/login')) return reply({ token: 'PRIVATE_SESSION', user: { id: 'owner' } });
    if (path.includes('/convos/')) return reply({ conversationId: input.conversation_id, agent_id: input.agent_id });
    if (path.endsWith('/expanded')) return reply({ author: 'owner', name: 'DataCheck', provider: 'google',
      model: 'gemini-3.5-flash-lite', tools: [1, 2, 3, 4], actions: [1] });
    if (path.endsWith('/actions')) return reply([{ agent_id: input.agent_id, user: 'owner', metadata: { domain: 'http://datacheck' } }]);
    if (path.endsWith('/chat/agents')) return reply({ status: 'started', streamId: 'fresh-stream', generationCreatedAt: 123 });
    if (path.includes('/stream/')) {
      const message = answer(); const actual = { ...report, generated_at: new Date(Date.now() + 1000).toISOString() };
      message.content[0].tool_call.output = JSON.stringify(actual);
      return { ok: true, headers: new Headers({ 'Content-Type': 'text/event-stream' }),
        body: [Buffer.from('data: ' + JSON.stringify({ final: true, responseMessage: message }) + '\n\n')] };
    }
    return reply({});
  };
  const result = await probe(input, transport);
  assert.equal(result.tool_answer_verified, true);
  assert.doesNotMatch(JSON.stringify(result), /PRIVATE|owner|email/);
  const admitted = calls.find(c => c.url.endsWith('/chat/agents'));
  assert.equal(JSON.parse(admitted.options.body).conversationId, 'new');
  assert.equal(admitted.options.headers.Authorization, 'Bearer PRIVATE_SESSION');
  assert.match(admitted.options.headers['User-Agent'], /APICompassRecovery/);
  assert.equal(admitted.options.redirect, 'error');
});

test('failed login produces only a fixed stage and never calls restored agent routes', async () => {
  let calls = 0;
  const result = await probe({ email: 'synthetic@example.invalid', password: 'PRIVATE_PASSWORD', conversation_id: 'saved', agent_id: 'agent_saved' },
    async () => { calls++; throw Error('PRIVATE_RESPONSE'); });
  assert.deepEqual(result, { verified: false, stage: 'login', http_status: 0 }); assert.equal(calls, 1);
});
test('login rejection reports only numeric HTTP status, without reading its private body', async () => {
  const result = await probe({ email: 'synthetic@example.invalid', password: 'PRIVATE_PASSWORD', conversation_id: 'saved', agent_id: 'agent_saved' },
    async () => ({ ok: false, status: 401, get body() { throw Error('PRIVATE_BODY'); } }));
  assert.deepEqual(result, { verified: false, stage: 'login', http_status: 401 });
});
