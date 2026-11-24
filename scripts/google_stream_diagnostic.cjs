'use strict';
// One-off debugging helper: fixed metadata only, never response content or keys.
// This classifies an incomplete provider stream; it never repairs/accepts it.
function classifyTrailingStream(value) {
  const raw = typeof value === 'string' ? value : '';
  const bounded = raw.slice(0, 65536);
  const trimmed = bounded.trim();
  const result = {
    trailing_length: raw.length,
    truncated_for_inspection: raw.length > 65536,
    leading_bom: raw.charCodeAt(0) === 0xfeff,
    leading_whitespace: bounded !== bounded.trimStart(),
    starts_data: trimmed.startsWith('data:'),
    data_colon_space: trimmed.startsWith('data: '),
    starts_comment: trimmed.startsWith(':'),
    starts_json_array: trimmed.startsWith('['),
    starts_json_object: trimmed.startsWith('{'),
    has_double_newline: /\n\n|\r\r|\r\n\r\n/.test(bounded),
    json_parseable: false,
  };
  if (result.truncated_for_inspection) return result;
  try {
    const candidate = result.starts_data ? trimmed.slice(5).trim() : trimmed;
    const parsed = JSON.parse(candidate);
    result.json_parseable = true;
    const code = parsed && typeof parsed === 'object' && parsed.error?.code;
    if (Number.isInteger(code) && code >= 100 && code <= 599) result.error_code = code;
  } catch { /* No parse exception, response value or arbitrary string is returned. */ }
  return result;
}
module.exports = { classifyTrailingStream };
