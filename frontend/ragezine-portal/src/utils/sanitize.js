const CONTROL_CHARS_RE = /[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g;
const MULTISPACE_RE = /[ \t]+/g;
const SIMPLE_EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function sanitizeSingleLine(value) {
  return String(value ?? "")
    .replace(CONTROL_CHARS_RE, "")
    .replace(MULTISPACE_RE, " ")
    .trim();
}

export function sanitizeMultiline(value) {
  return String(value ?? "")
    .replace(CONTROL_CHARS_RE, "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
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
