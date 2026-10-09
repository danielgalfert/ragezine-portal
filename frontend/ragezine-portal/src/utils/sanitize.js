// eslint-disable-next-line no-control-regex
const CONTROL_CHARS_RE = /[\x00-\x1F\x7F]/g;
// eslint-disable-next-line no-control-regex
const MULTILINE_CONTROL_CHARS_RE = /[\x00-\x09\x0B-\x1F\x7F]/g;
const BIDI_CONTROLS_RE = /[\u200e\u200f\u202a-\u202e\u2066-\u2069]/g;
const MULTISPACE_RE = /[ \t]+/g;
const SIMPLE_EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function sanitizeSingleLine(value) {
  return String(value ?? "")
    .normalize("NFC")
    .replace(BIDI_CONTROLS_RE, "")
    .replace(CONTROL_CHARS_RE, " ")
    .replace(MULTISPACE_RE, " ")
    .trim();
}

export function sanitizeMultiline(value) {
  return String(value ?? "")
    .normalize("NFC")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(BIDI_CONTROLS_RE, "")
    .replace(MULTILINE_CONTROL_CHARS_RE, " ")
    .split("\n")
    .map((line) => line.replace(MULTISPACE_RE, " ").trim())
    .filter(Boolean)
    .join("\n")
    .trim();
}

export function sanitizeCountryCode(value) {
  return sanitizeSingleLine(value).toUpperCase();
}

export function sanitizeUsername(value) {
  return sanitizeSingleLine(value);
}

export function isLikelyEmail(value) {
  return SIMPLE_EMAIL_RE.test(sanitizeSingleLine(value).toLowerCase());
}
