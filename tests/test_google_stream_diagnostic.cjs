'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { classifyTrailingStream } = require('../scripts/google_stream_diagnostic.cjs');

test('identifies a complete data frame without returning its contents', () => {
  const value = 'data: {"candidates":[{"text":"invented confidential marker"}]}';
  const result = classifyTrailingStream(value);
  assert.equal(result.starts_data, true);
  assert.equal(result.data_colon_space, true);
  assert.equal(result.json_parseable, true);
  assert.doesNotMatch(JSON.stringify(result), /confidential|candidates|text/);
});

test('distinguishes a legal data colon without the legacy mandatory space', () => {
  const result = classifyTrailingStream('data:{"ok":true}\n\n');
  assert.equal(result.starts_data, true);
  assert.equal(result.data_colon_space, false);
  assert.equal(result.json_parseable, true);
  assert.equal(result.has_double_newline, true);
});

test('identifies heartbeat comments preceding data without exposing either', () => {
  const result = classifyTrailingStream(': heartbeat\n\ndata: {"private":"never print"}\n\n');
  assert.equal(result.starts_comment, true);
  assert.equal(result.json_parseable, false);
  assert.doesNotMatch(JSON.stringify(result), /heartbeat|private|never/);
});

test('extracts only a bounded numeric provider error code from JSON', () => {
  const result = classifyTrailingStream('{"error":{"code":503,"message":"private error detail"}}');
  assert.equal(result.starts_json_object, true);
  assert.equal(result.error_code, 503);
  assert.doesNotMatch(JSON.stringify(result), /detail|message/);
  assert.equal(classifyTrailingStream('{"error":{"code":"secret"}}').error_code, undefined);
});

test('recognizes incomplete JSON and does not treat EOF as a complete event', () => {
  assert.equal(classifyTrailingStream('data: {"candidates":[').json_parseable, false);
  assert.equal(classifyTrailingStream('[{"ok":true}]').starts_json_array, true);
});

test('bounds diagnostic parsing and handles invalid input without masking the original failure', () => {
  const result = classifyTrailingStream('x'.repeat(65537));
  assert.equal(result.truncated_for_inspection, true);
  assert.equal(result.json_parseable, false);
  assert.equal(result.trailing_length, 65537);
  assert.equal(classifyTrailingStream(null).trailing_length, 0);
});

test('preserves leading framing signals separately from trimmed classification', () => {
  const result = classifyTrailingStream('\ufeffdata: {"ok":true}');
  assert.equal(result.leading_bom, true);
  assert.equal(result.leading_whitespace, true);
  assert.equal(result.starts_data, true);
});
