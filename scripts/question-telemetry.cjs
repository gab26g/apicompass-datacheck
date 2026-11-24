'use strict';
// Optional --require preload for the pinned LibreChat HTTP server. No dependencies.
const http = require('node:http');
const { randomUUID } = require('node:crypto');
const { StringDecoder } = require('node:string_decoder');
const { performance } = require('node:perf_hooks');

const MAX_FRAME = 65536;
const MAX_START = 8192;
const SAFE_ID = /^[A-Za-z0-9_-]{1,128}$/;
const INSTALL_KEY = Symbol.for('apicompass.questionTelemetry.installed');

function route(method, rawUrl) {
  if (typeof rawUrl !== 'string' || rawUrl.length > 2048) return null;
  let url;
  try { url = new URL(rawUrl, 'http://private.invalid'); } catch { return null; }
  // Pinned createPayload appends /agents for saved-agent browser submissions.
  if (method === 'POST' && /^\/api\/agents\/chat(?:\/agents)?\/?$/.test(url.pathname)) return { type: 'start' };
  // The deployed feature is the saved DataCheck agent, not ephemeral endpoints,
  // resume, abort, OpenAI compatibility, background jobs or model-only chat.
  const match = method === 'GET' && url.pathname.match(/^\/api\/agents\/chat\/stream\/([A-Za-z0-9_-]{1,128})$/);
  if (!match) return null;
  const epoch = url.searchParams.get('generationCreatedAt');
  if (!epoch || !/^\d{1,16}$/.test(epoch) || !Number.isSafeInteger(Number(epoch))) return null;
  return { type: 'stream', key: match[1] + ':' + Number(epoch) };
}

function hasAnswer(message) {
  const text = value => typeof value === 'string' ? value :
    value && typeof value.value === 'string' ? value.value : '';
  return (typeof message.text === 'string' && message.text.trim().length > 0) ||
    (Array.isArray(message.content) && message.content.some(part =>
      part && part.type === 'text' && text(part.text).trim().length > 0));
}

class SseObserver {
  constructor() {
    this.decoder = new StringDecoder('utf8');
    this.line = ''; this.data = []; this.size = 0; this.event = '';
    this.overflow = false; this.invalid = false; this.final = false; this.error = false; this.unfinished = false;
  }
  frame() {
    if (this.overflow) this.invalid = true;
    else if (this.data.length) {
      try {
        const value = JSON.parse(this.data.join('\n'));
        if (this.event === 'error' || (value && (value.error || value.responseMessage?.error))) this.error = true;
        if (value && value.final === true) {
          if (value.reconcile === true || value.responseMessage?.unfinished === true) this.unfinished = true;
          else if (value.responseMessage && typeof value.responseMessage === 'object' && hasAnswer(value.responseMessage)) this.final = true;
        }
      } catch { this.invalid = true; }
    } else if (this.event === 'error') this.error = true;
    this.line = ''; this.data = []; this.size = 0; this.event = ''; this.overflow = false;
  }
  consume(chunk, encoding) {
    if (chunk == null) return;
    const bytes = typeof chunk === 'string' ? Buffer.from(chunk, typeof encoding === 'string' ? encoding : 'utf8') : chunk;
    const decoded = this.decoder.write(bytes);
    for (const char of decoded) {
      if (char === '\n') {
        const line = this.line.endsWith('\r') ? this.line.slice(0, -1) : this.line;
        if (!this.overflow) {
          if (line === '') { this.frame(); continue; }
          if (line.startsWith('event:')) this.event = line.slice(6).replace(/^ /, '');
          if (line.startsWith('data:')) this.data.push(line.slice(5).replace(/^ /, ''));
        } else if (line === '') { this.frame(); continue; }
        this.line = '';
      } else {
        this.size += Buffer.byteLength(char, 'utf8');
        if (this.size > MAX_FRAME) { this.overflow = true; this.invalid = true; }
        // Preserve blank-line framing even when a giant frame is discarded.
        if (!this.overflow) this.line += char;
        else if (char !== '\r') this.line = '!';
      }
    }
  }
  result() {
    if (this.error) return 'provider_error';
    if (this.invalid || this.line || this.data.length || this.overflow || this.decoder.lastNeed) return 'uninspectable_stream';
    if (this.unfinished) return 'unfinished';
    return this.final ? 'success' : 'missing_final';
  }
}

// Conservative whole-question omission: no partially redacted text can imply full
// capture. This heuristic is not a guarantee of PII detection; fictional data only.
const MAX_QUESTION = 500;
const UNSAFE_QUESTION = /[\x00-\x1f\x7f-\x9f\u200b-\u200f\u2028-\u202e\u2060-\u206f\ufeff\ud800-\udfff]|[^\s@]+@[^\s@]+|\b[a-z][a-z0-9+.-]*:\/\/|www\.|\bbearer\s+\S+|\b(?:password|passwd|secret|token|api[_-]?key|authorization|cookie)["']?\s*[:=]|\b(?:AIza|sk-|AKIA|ASIA)[A-Za-z0-9_-]*|-----BEGIN[^\r\n]*PRIVATE KEY-----|[A-Za-z0-9_+\/=.-]{32,}|\+?\d[\d ().-]{5,}\d/iu;

function captureQuestion(req) {
  try {
    // Body parser and pinned client use req.body.text; do not inspect other
    // body fields, request streams, authentication headers or cookies.
    const text = req.body?.text;
    if (typeof text !== 'string' || !text.trim()) return { question_status: 'omitted_missing' };
    // String.length first bounds work even on the server's 3 MB parsed input.
    if (text.length > MAX_QUESTION * 2 || [...text].length > MAX_QUESTION) {
      return { question_status: 'omitted_over_limit' };
    }
    if (UNSAFE_QUESTION.test(text)) return { question_status: 'redacted' };
    return { question: text.trim(), question_status: 'captured' };
  } catch { return { question_status: 'omitted_unavailable' }; }
}

function createTelemetry(options = {}) {
  const emit = options.emit || (event => process.stdout.write(JSON.stringify(event) + '\n'));
  const now = options.now || (() => performance.now());
  const wall = options.wall || Date.now;
  const timeoutMs = options.timeoutMs || 300000;
  const maxPending = options.maxPending || 128;
  const configuredVersion = options.appVersion || process.env.APICOMPASS_VERSION || '';
  const appVersion = /^[A-Za-z0-9._-]{1,64}$/.test(configuredVersion) ? configuredVersion : 'apicompass-runtime-v2';
  const logQuestions = options.logQuestions === undefined ? process.env.APICOMPASS_LOG_QUESTIONS === '1' : options.logQuestions === true;
  const pending = new Map();
  const active = new Set();

  function complete(attempt, outcome, status) {
    if (attempt.done) return;
    attempt.done = true;
    clearTimeout(attempt.timer);
    active.delete(attempt);
    if (attempt.key && pending.get(attempt.key) === attempt) pending.delete(attempt.key);
    const elapsed = now() - attempt.start;
    const duration = Number.isFinite(elapsed) ? Math.min(300000, Math.max(0, Math.round(elapsed * 1000) / 1000)) : 300000;
    const state = outcome === 'success' ? 'succeeded' : ['aborted', 'disconnected'].includes(outcome) ? 'aborted' : 'failed';
    // The dedicated host shipper publishes AnswerSuccess/AnswerFailure metrics.
    // Emission here is not evidence of delivery to CloudWatch.
    const event = {
      event: 'question_attempt', schema_version: 1, app_version: appVersion,
      librechat_version: '0.8.8', request_id: attempt.id,
      outcome: state, reason: outcome,
      http_status: Number.isInteger(status) && status >= 0 && status <= 599 ? status : 0,
      duration_ms: duration, timestamp: new Date(wall()).toISOString(),
      ...(logQuestions ? attempt.question : {}),
    };
    try { emit(event); } catch { /* Telemetry must never break the chat stream. */ }
  }

  function begin() {
    if (active.size >= maxPending) complete(active.values().next().value, 'capacity_exceeded', 0);
    const attempt = { id: randomUUID(), start: now(), done: false,
      question: logQuestions ? { question_status: 'omitted_unavailable' } : undefined };
    active.add(attempt);
    attempt.timer = setTimeout(() => complete(attempt, 'observation_timeout', 0), timeoutMs);
    attempt.timer.unref?.();
    return attempt;
  }

  function observe(req, res) {
    const matched = route(req.method, req.url);
    if (!matched) return;
    const attempt = matched.type === 'start' ? begin() : pending.get(matched.key);
    if (!attempt || attempt.done) return;
    // Generated locally; no client-controlled ID or auth header is read.
    if (matched.type === 'start' && !res.headersSent) res.setHeader('X-APICompass-Question-ID', attempt.id);
    let startBody = '', startSize = 0, startOverflow = false;
    let stream = new SseObserver();
    let finished = false;
    const acceptedStream = () => res.statusCode === 200 &&
      String(res.getHeader('content-type') || '').toLowerCase().startsWith('text/event-stream');
    const canAbortAttempt = () => matched.type === 'start' || acceptedStream();
    function consume(chunk, encoding) {
      try {
        if (chunk == null || typeof chunk === 'function' || attempt.done || finished) return;
        const type = String(res.getHeader('content-type') || '').toLowerCase();
        const contentEncoding = String(res.getHeader('content-encoding') || 'identity').toLowerCase();
        if (contentEncoding !== 'identity') { stream.invalid = true; return; }
        if (type.startsWith('text/event-stream')) { stream.consume(chunk, encoding); return; }
        if (matched.type === 'start') {
          const bytes = typeof chunk === 'string' ? Buffer.from(chunk, typeof encoding === 'string' ? encoding : 'utf8') : chunk;
          startSize += bytes.length;
          if (startSize > MAX_START) { startOverflow = true; startBody = ''; }
          else if (!startOverflow) startBody += bytes.toString('utf8');
        }
      } catch { stream.invalid = true; }
    }
    const write = res.write;
    const end = res.end;
    res.write = function (chunk, encoding) { consume(chunk, encoding); return Reflect.apply(write, this, arguments); };
    res.end = function (chunk, encoding) { consume(chunk, encoding); return Reflect.apply(end, this, arguments); };
    res.once('finish', () => {
      finished = true;
      if (attempt.done) return;
      if (logQuestions && matched.type === 'start') attempt.question = captureQuestion(req);
      const status = res.statusCode;
      const isSse = String(res.getHeader('content-type') || '').toLowerCase().startsWith('text/event-stream');
      if (matched.type === 'stream') {
        // A rejected subscription must not let another client cancel the real
        // question. Its unresolved attempt will time out conservatively.
        if (!acceptedStream()) return;
        complete(attempt, stream.result(), status);
      } else if (status >= 400) complete(attempt, 'http_error', status);
      else if (isSse) complete(attempt, stream.result(), status);
      else {
        try {
          const value = startOverflow ? null : JSON.parse(startBody);
          if (!value || value.status !== 'started' || typeof value.streamId !== 'string' || !SAFE_ID.test(value.streamId) ||
              !Number.isSafeInteger(value.generationCreatedAt) || value.generationCreatedAt < 0) {
            complete(attempt, 'invalid_start_response', status); return;
          }
          const key = value.streamId + ':' + value.generationCreatedAt;
          if (pending.has(key)) { complete(attempt, 'duplicate_start', status); return; }
          attempt.key = key;
          pending.set(key, attempt);
        } catch { complete(attempt, 'invalid_start_response', status); }
      }
      startBody = ''; stream = null;
    });
    res.once('close', () => {
      if (!finished && canAbortAttempt()) complete(attempt, 'disconnected', res.statusCode);
    });
    req.once('aborted', () => {
      if (canAbortAttempt()) complete(attempt, 'aborted', res.statusCode);
    });
  }
  return { observe, close: () => {
    for (const attempt of Array.from(active)) complete(attempt, 'shutdown', 0);
  }, pendingCount: () => active.size };
}

function install(options) {
  if (http.Server.prototype[INSTALL_KEY]) return http.Server.prototype[INSTALL_KEY];
  const telemetry = createTelemetry(options);
  const original = http.Server.prototype.emit;
  http.Server.prototype.emit = function (name, ...args) {
    if (name === 'request') {
      try { telemetry.observe(args[0], args[1]); } catch { /* Preserve HTTP behavior. */ }
    }
    return Reflect.apply(original, this, [name, ...args]);
  };
  http.Server.prototype[INSTALL_KEY] = telemetry;
  return telemetry;
}

module.exports = { SseObserver, createTelemetry, install, route, MAX_FRAME };
if (process.env.APICOMPASS_QUESTION_TELEMETRY === '1') install();
