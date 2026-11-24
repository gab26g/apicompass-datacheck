'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const http = require('node:http');
const { SseObserver, createTelemetry, install, MAX_FRAME } = require('../scripts/question-telemetry.cjs');

class Response extends EventEmitter {
  constructor(type = 'text/event-stream', status = 200) {
    super(); this.statusCode = status; this.headers = { 'content-type': type }; this.chunks = [];
  }
  setHeader(name, value) { this.headers[name.toLowerCase()] = value; }
  getHeader(name) { return this.headers[name.toLowerCase()]; }
  write(chunk, encoding, callback) {
    this.chunks.push(Buffer.isBuffer(chunk) ? chunk.toString() : chunk);
    if (typeof encoding === 'function') encoding();
    if (typeof callback === 'function') callback();
    return false; // Backpressure must pass through unchanged.
  }
  end(chunk, encoding, callback) {
    if (chunk != null && typeof chunk !== 'function') this.chunks.push(Buffer.isBuffer(chunk) ? chunk.toString() : chunk);
    this.emit('finish');
    if (typeof chunk === 'function') chunk();
    if (typeof encoding === 'function') encoding();
    if (typeof callback === 'function') callback();
    this.emit('close'); return this;
  }
}

function request(method = 'POST', url = '/api/agents/chat') {
  const req = new EventEmitter(); req.method = method; req.url = url;
  // Any prompt or credential inspection is a test failure.
  for (const field of ['body', 'headers', 'rawHeaders']) {
    Object.defineProperty(req, field, { get() { throw new Error('private request field accessed'); } });
  }
  return req;
}

function harness(options = {}) {
  const events = [];
  const telemetry = createTelemetry({ emit: event => events.push(event), ...options });
  return { telemetry, events, attach(req = request(), res = new Response()) {
    telemetry.observe(req, res); return { req, res };
  } };
}

const final = (extra = {}) => 'event: message\ndata: ' + JSON.stringify({
  final: true, responseMessage: { messageId: 'internal-id', content: [{ type: 'text', text: 'An answer é' }], ...extra },
}) + '\n\n';

test('pinned UI saved-agent admission path links to its final stream', () => {
  const h = harness();
  const start = h.attach(request('POST', '/api/agents/chat/agents'), new Response('application/json'));
  start.res.end(JSON.stringify({ status: 'started', streamId: 'saved-agent-stream', generationCreatedAt: 123 }));
  const stream = h.attach(request('GET', '/api/agents/chat/stream/saved-agent-stream?generationCreatedAt=123&generationProtocolVersion=2'));
  stream.res.end(final());
  assert.equal(h.events.length, 1);
  assert.equal(h.events[0].reason, 'success');
  h.telemetry.close();
});

test('HTTP 200 provider error is failed even if followed by a final answer', () => {
  const h = harness(); const { res } = h.attach();
  res.write('event: error\ndata: {"error":"PRIVATE_PROVIDER_MESSAGE"}\n\n');
  res.end(final());
  assert.equal(h.events.length, 1);
  assert.equal(h.events[0].outcome, 'failed');
  assert.equal(h.events[0].reason, 'provider_error');
  assert.equal(h.events[0].http_status, 200);
  assert.doesNotMatch(JSON.stringify(h.events), /PRIVATE_PROVIDER_MESSAGE|internal-id|An answer/);
});

test('final answer emits exactly one bounded allowlisted event and preserves callbacks/backpressure', () => {
  let now = 0; const h = harness({ now: () => now, wall: () => 1700000000000 });
  const { res } = h.attach(); let callbacks = 0;
  assert.equal(res.write('event: message\ndata: {"delta":"PRIVATE_TEXT"}\n\n', () => callbacks++), false);
  now = 20.125;
  const payload = final();
  assert.equal(res.end(payload, () => callbacks++), res);
  assert.equal(callbacks, 2);
  assert.equal(res.chunks[1], payload);
  assert.equal(h.events.length, 1);
  const event = h.events[0];
  assert.deepEqual(Object.keys(event).sort(), ['event', 'schema_version', 'app_version', 'librechat_version',
    'request_id', 'outcome', 'reason', 'http_status', 'duration_ms', 'timestamp'].sort());
  assert.equal(event.event, 'question_attempt'); assert.equal(event.outcome, 'succeeded');
  assert.equal(event.duration_ms, 20.125); assert.equal(event.timestamp, '2023-11-14T22:13:20.000Z');
  assert.match(event.request_id, /^[0-9a-f-]{36}$/);
  assert.ok(Buffer.byteLength(JSON.stringify(event)) < 1024);
  assert.doesNotMatch(JSON.stringify(event), /PRIVATE_TEXT/);
});

test('a 200 delta or final marker without a final response message never becomes success', () => {
  for (const payload of ['event: message\ndata: {"delta":"hello"}\n\n',
    'event: message\ndata: {"final":true}\n\n', 'event: message\ndata: {"text":"final:true"}\n\n']) {
    const h = harness(); h.attach().res.end(payload);
    assert.equal(h.events[0].reason, 'missing_final'); assert.equal(h.events[0].outcome, 'failed');
  }
});

test('callback-only end overload leaves the observed final answer successful', () => {
  const h = harness(); const { res } = h.attach(); let called = false;
  res.write(final()); res.end(() => { called = true; });
  assert.equal(called, true); assert.equal(h.events[0].outcome, 'succeeded');
});

test('unfinished and error-marked final response messages fail', () => {
  for (const [extra, reason] of [[{ unfinished: true }, 'unfinished'], [{ error: true }, 'provider_error']]) {
    const h = harness(); h.attach().res.end(final(extra));
    assert.equal(h.events[0].reason, reason); assert.equal(h.events[0].outcome, 'failed');
  }
});

test('supported text-value content shape counts as a final answer, tool-only content does not', () => {
  const h = harness(); h.attach().res.end(final({ content: [{ type: 'text', text: { value: 'answer' } }] }));
  assert.equal(h.events[0].outcome, 'succeeded');
  const other = harness(); other.attach().res.end(final({ content: [{ type: 'tool_call', text: 'not an answer' }] }));
  assert.equal(other.events[0].outcome, 'failed');
});

test('disconnect and aborted request are counted once, including after late final writes', () => {
  for (const event of ['close', 'aborted']) {
    const h = harness(); const { req, res } = h.attach();
    (event === 'close' ? res : req).emit(event); res.end(final());
    assert.equal(h.events.length, 1); assert.equal(h.events[0].outcome, 'aborted');
  }
});

test('two-stage source protocol correlates POST admission to generation-scoped SSE without counting admission as success', () => {
  let now = 5; const h = harness({ now: () => now });
  h.attach(request(), new Response('application/json')).res.end(JSON.stringify({
    status: 'started', streamId: 'private-stream-id', generationCreatedAt: 123,
  }));
  assert.equal(h.events.length, 0); assert.equal(h.telemetry.pendingCount(), 1);
  now = 100;
  h.attach(request('GET', '/api/agents/chat/stream/private-stream-id?generationCreatedAt=123')).res.end(final());
  assert.equal(h.events.length, 1); assert.equal(h.events[0].duration_ms, 95);
  assert.equal(h.events[0].outcome, 'succeeded');
  assert.doesNotMatch(JSON.stringify(h.events), /private-stream-id/);
  assert.equal(h.telemetry.pendingCount(), 0);
  h.attach(request('GET', '/api/agents/chat/stream/private-stream-id?generationCreatedAt=123')).res.end(final());
  assert.equal(h.events.length, 1); // Replayed/reconnected stream cannot double count.
});

test('known two-stage stream error under HTTP 200 is a failed question', () => {
  const h = harness();
  h.attach(request(), new Response('application/json')).res.end('{"status":"started","streamId":"s1","generationCreatedAt":1}');
  h.attach(request('GET', '/api/agents/chat/stream/s1?generationCreatedAt=1')).res.end('event: error\ndata: {"error":"do not log me"}\n\n');
  assert.equal(h.events.length, 1); assert.equal(h.events[0].reason, 'provider_error');
});

test('rejected matching GET close/abort cannot cancel the pending question before legitimate SSE succeeds', () => {
  for (const signal of ['close', 'aborted']) {
    for (const [status, type] of [[403, 'application/json'], [200, 'application/json'], [401, 'text/event-stream']]) {
      const h = harness();
      h.attach(request(), new Response('application/json')).res.end(
        '{"status":"started","streamId":"s1","generationCreatedAt":1}');
      const rejected = h.attach(request('GET', '/api/agents/chat/stream/s1?generationCreatedAt=1'),
        new Response(type, status));
      (signal === 'close' ? rejected.res : rejected.req).emit(signal);
      assert.equal(h.events.length, 0, `${status} ${type} ${signal}`);
      assert.equal(h.telemetry.pendingCount(), 1);
      h.attach(request('GET', '/api/agents/chat/stream/s1?generationCreatedAt=1')).res.end(final());
      assert.equal(h.events.length, 1);
      assert.equal(h.events[0].outcome, 'succeeded');
    }
  }
});

test('SSE JSON and UTF-8 chunk boundaries preserve typed outcome; CRLF framing works', () => {
  const bytes = Buffer.from(final().replaceAll('\n', '\r\n'));
  for (let split = 1; split < bytes.length; split++) {
    const parser = new SseObserver(); parser.consume(bytes.subarray(0, split)); parser.consume(bytes.subarray(split));
    assert.equal(parser.result(), 'success', 'split ' + split);
  }
  const parser = new SseObserver();
  for (const byte of bytes) parser.consume(Buffer.from([byte]));
  assert.equal(parser.result(), 'success');
});

test('giant/malformed/truncated frames fail closed with bounded parser state', () => {
  for (const payload of ['data: {broken}\n\n', 'data: ' + 'x'.repeat(MAX_FRAME * 3) + '\n\n' + final(),
    final() + 'data: {"error":', final() + '\ud800']) {
    const parser = new SseObserver(); parser.consume(payload);
    assert.equal(parser.result(), 'uninspectable_stream');
    assert.ok(parser.line.length <= MAX_FRAME);
    assert.ok(parser.data.join('').length <= MAX_FRAME);
  }
});

test('nonchat, control, model-only and uncorrelated stream requests emit no questions', () => {
  const h = harness();
  for (const [method, url] of [['GET', '/health'], ['GET', '/api/agents/chat'],
    ['POST', '/api/agents/chat/abort'], ['POST', '/api/agents/chat/resume'], ['POST', '/api/ask/google'],
    ['GET', '/api/agents/chat/stream/unknown?generationCreatedAt=1']]) {
    h.attach(request(method, url)).res.end(final());
  }
  assert.equal(h.events.length, 0); assert.equal(h.telemetry.pendingCount(), 0);
});

test('HTTP rejections fail safely; URL values, application-version injection and arbitrary error bodies never escape', () => {
  const h = harness({ appVersion: 'PRIVATE_VERSION\nSECRET' });
  h.attach(request('POST', '/api/agents/chat?token=PRIVATE_QUERY'), new Response('application/json', 500))
    .res.end('{"error":"PRIVATE_PROVIDER_KEY"}');
  const output = JSON.stringify(h.events);
  assert.equal(h.events[0].reason, 'http_error');
  assert.equal(h.events[0].app_version, 'apicompass-runtime-v2');
  assert.doesNotMatch(output, /PRIVATE_|SECRET|token/);
});

test('unobserved questions time out and capacity is bounded', async () => {
  const h = harness({ timeoutMs: 10, maxPending: 1 });
  const accepted = () => h.attach(request(), new Response('application/json')).res.end(
    '{"status":"started","streamId":"s1","generationCreatedAt":1}');
  accepted(); accepted();
  assert.equal(h.events[0].reason, 'capacity_exceeded'); assert.equal(h.telemetry.pendingCount(), 1);
  await new Promise(resolve => setTimeout(resolve, 25));
  assert.equal(h.events[1].reason, 'observation_timeout'); assert.equal(h.telemetry.pendingCount(), 0);
});

test('preload install observes the real public HTTP request event before the application listener', () => {
  const events = []; const telemetry = install({ emit: event => events.push(event) });
  const server = http.createServer((_req, res) => res.end(final()));
  server.emit('request', request(), new Response());
  assert.equal(events.length, 1); assert.equal(events[0].outcome, 'succeeded');
  assert.equal(install(), telemetry); telemetry.close();
});

function promptRequest() {
  const req = new EventEmitter(); req.method = 'POST'; req.url = '/api/agents/chat/agents';
  for (const field of ['headers', 'rawHeaders']) {
    Object.defineProperty(req, field, { get() { throw new Error('credentials accessed'); } });
  }
  return req;
}

test('opt-in reads parsed text only at admission finish and carries it to the final correlated event', () => {
  const h = harness({ logQuestions: true }); const req = promptRequest();
  let parsed = false, reads = 0;
  Object.defineProperty(req, 'body', { get() {
    assert.equal(parsed, true, 'must wait for body parsing'); reads++;
    return { text: 'Inspect shipments and explain all findings.', password: 'NEVER_CAPTURE' };
  } });
  const { res } = h.attach(req, new Response('application/json'));
  assert.equal(reads, 0); assert.equal(req.listenerCount('data'), 0);
  parsed = true;
  res.end('{"status":"started","streamId":"safe","generationCreatedAt":9}');
  assert.equal(h.events.length, 0); assert.equal(reads, 1);
  h.attach(request('GET', '/api/agents/chat/stream/safe?generationCreatedAt=9')).res.end(final());
  assert.equal(h.events[0].question, 'Inspect shipments and explain all findings.');
  assert.equal(h.events[0].question_status, 'captured');
  assert.doesNotMatch(JSON.stringify(h.events), /NEVER_CAPTURE/);
});

test('opt-in redacts entire suspected secrets and contact details without leaking substrings', () => {
  for (const text of ['Email student@example.invalid', 'https://user:pass@example.invalid/path',
    'Bearer short-secret', 'api_key=short-secret', 'password: short-secret',
    'AIza' + 'a'.repeat(35), 'sk-' + 'a'.repeat(20), 'AKIA' + 'A'.repeat(16),
    '-----BEGIN PRIVATE KEY-----', 'opaque ' + 'a'.repeat(32), 'Call +63 912 345 6789',
    'Inspect\u0000shipments', 'Inspect\nshipments', 'bad \ud800']) {
    const h = harness({ logQuestions: true }); const req = promptRequest(); req.body = { text };
    h.attach(req).res.end(final());
    assert.equal(h.events[0].question_status, 'redacted', text);
    assert.equal(Object.hasOwn(h.events[0], 'question'), false, text);
  }
});

test('opt-in reports missing, oversized and unreadable questions without claiming full capture', () => {
  for (const [body, status] of [[{}, 'omitted_missing'], [{ text: 5 }, 'omitted_missing'],
    [{ text: '   ' }, 'omitted_missing'], [{ text: 'x '.repeat(251) }, 'omitted_over_limit'],
    [{ text: '🙂'.repeat(501) }, 'omitted_over_limit']]) {
    const h = harness({ logQuestions: true }); const req = promptRequest(); req.body = body;
    h.attach(req).res.end(final());
    assert.equal(h.events[0].question_status, status);
    assert.equal(Object.hasOwn(h.events[0], 'question'), false);
  }
  const unreadable = harness({ logQuestions: true }); unreadable.attach().res.end(final());
  assert.equal(unreadable.events[0].question_status, 'omitted_unavailable');
  const aborted = harness({ logQuestions: true }); const req = promptRequest();
  Object.defineProperty(req, 'body', { get() { throw new Error('must not read before finish'); } });
  aborted.attach(req).req.emit('aborted');
  assert.equal(aborted.events[0].question_status, 'omitted_unavailable');
});

test('environment opt-in is explicit and a false option disables body access', () => {
  const previous = process.env.APICOMPASS_LOG_QUESTIONS;
  try {
    process.env.APICOMPASS_LOG_QUESTIONS = '1';
    const h = harness(); const req = promptRequest(); req.body = { text: 'Inspect inventory.' };
    h.attach(req).res.end(final()); assert.equal(h.events[0].question, 'Inspect inventory.');
    const off = harness({ logQuestions: false }); off.attach().res.end(final());
    assert.equal(Object.hasOwn(off.events[0], 'question_status'), false);
  } finally {
    if (previous === undefined) delete process.env.APICOMPASS_LOG_QUESTIONS;
    else process.env.APICOMPASS_LOG_QUESTIONS = previous;
  }
});

test('exactly 500 Unicode codepoints can be captured without splitting surrogate pairs', () => {
  const h = harness({ logQuestions: true }); const req = promptRequest(); req.body = { text: '🙂'.repeat(500) };
  h.attach(req).res.end(final());
  assert.equal(h.events[0].question_status, 'captured');
  assert.equal([...h.events[0].question].length, 500);
  assert.ok(Buffer.byteLength(JSON.stringify(h.events[0])) < 4096);
});
