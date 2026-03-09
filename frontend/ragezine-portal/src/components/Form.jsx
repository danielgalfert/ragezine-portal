import React, { useMemo, useState } from "react";
import CountrySelect from "./CountrySelect";
import PronounSelect from "./PronounSelect";
import { createSubmission } from "../services/submissionService";

import "../styles/nav.css";
import "../styles/description.css";
import "../styles/form.css";

const MAX_VISUALS = 5;
const MAX_WORDS_TEXT = 1500;

const initialForm = {
  title: "",
  year: "",
  description: "",
  artist_name: "",
  pronouns: "",
  short_bio: "",
  socials: "",
  countries_origin: "",
  countries_residence: "",
  language: "English",
  allow_translation: false,
};

function countWords(s) {
  const t = (s || "").trim();
  return t ? t.split(/\s+/).length : 0;
}

export default function Form() {
  const [form, setForm] = useState(initialForm);
  const [textFile, setTextFile] = useState(null);
  const [visualFiles, setVisualFiles] = useState([]);
  const [error, setError] = useState("");
  const [ok, setOk] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const bioWords = useMemo(() => countWords(form.short_bio), [form.short_bio]);

  function update(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function onPickVisuals(fileList) {
    const picked = Array.from(fileList || []);
    setVisualFiles((prev) => [...prev, ...picked].slice(0, MAX_VISUALS));
  }

  function removeVisual(idx) {
    setVisualFiles((prev) => prev.filter((_, i) => i !== idx));
  }

  function clearAll() {
    setForm(initialForm);
    setTextFile(null);
    setVisualFiles([]);
    setError("");
  }

  function buildSubmissionFormData() {
    const fd = new FormData();

    Object.entries(form).forEach(([key, value]) => {
      if (typeof value === "boolean") {
        fd.append(key, value ? "1" : "0");
      } else {
        fd.append(key, value);
      }
    });

    if (textFile) {
      fd.append("text_file", textFile);
    }

    visualFiles.forEach((file) => {
      fd.append("visual_files", file);
    });

    return fd;
  }

  function validateForm() {
    if (!form.title.trim()) return "Please provide a title of your work(s).";
    if (!form.artist_name.trim()) return "Please provide an artist name.";
    if (!form.pronouns.trim()) return "Please provide pronouns (or write N/A).";
    if (!form.short_bio.trim()) return "Please provide a short bio (2–3 sentences).";
    if (!form.countries_origin.trim()) return "Please provide countries of origin.";
    if (!form.countries_residence.trim()) return "Please provide countries of residence.";
    if (visualFiles.length > MAX_VISUALS) return `Too many visuals. Max ${MAX_VISUALS}.`;

    return "";
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setOk(false);

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);

    try {
      const payload = buildSubmissionFormData();
      await createSubmission(payload);
      setOk(true);
      clearAll();
    } catch (err) {
      setError(err?.response?.data?.message || err?.message || "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <nav>
        <ul>
          <li><a href="#about">about</a></li>
          <li><a href="#submit">submit</a></li>
          <li><a href="#events">events</a></li>
          <li><a href="#contact">contact</a></li>
        </ul>

        <div className="buttons">
          <button className="menu-button" type="button">stockists</button>
          <button className="menu-button" type="button">read</button>
        </div>
      </nav>

      <section className="submit" id="submit">
        <h2>SUBMIT</h2>

        <div className="submission-content" style={{ width: "100%" }}>
          <p>
            <span className="sub">Language:</span><br />
            English is preferred, but we occasionally accept submissions in other languages, if you are happy for the piece to be accompanied by an English translation. Our team can help with translations in numerous languages.
          </p>

          <p>
            <span className="sub">Format:</span><br />
            Text: Word or Google Docs (max. {MAX_WORDS_TEXT} words)<br />
            Visuals: TIFF &amp; 300 dpi (max. {MAX_VISUALS} individual pieces or groups of work)
          </p>

          <p>
            <span className="sub">File Name(s):</span><br />
            <span style={{ fontFamily: "NewEdge666Slanted, sans-serif" }}>
              Artist-Name_Artwork-Title
            </span>
          </p>
        </div>

        {error && <div className="portal-error">{error}</div>}
        {ok && <div className="portal-ok">Submitted ✅</div>}

        <form className="portal-form" onSubmit={onSubmit}>
          <div className="portal-grid">
            <Field label="Title of your work(s) *">
              <input
                className="portal-input"
                value={form.title}
                onChange={(e) => update("title", e.target.value)}
              />
            </Field>

            <Field label="Year (if relevant)">
              <input
                className="portal-input"
                value={form.year}
                onChange={(e) => update("year", e.target.value)}
              />
            </Field>

            <Field label="Artist name *">
              <input
                className="portal-input"
                value={form.artist_name}
                onChange={(e) => update("artist_name", e.target.value)}
              />
            </Field>

            <Field label="Pronouns *">
              <PronounSelect
                value={form.pronouns}
                onChange={(pronoun) => update("pronouns", pronoun)}
              />
            </Field>

            <Field label="Country of origin *">
              <CountrySelect
                value={form.countries_origin}
                onChange={(countryCode) => update("countries_origin", countryCode)}
              />
            </Field>

            <Field label="Countries of origin *">
              <CountrySelect
                value={form.countries_origin}
                onChange={(countries) => update("countries_origin", countries)}
                isMulti
              />
            </Field>
          </div>

          <div style={{ height: 14 }} />

          <Field label="Description of work(s), including materials if relevant">
            <textarea
              className="portal-textarea"
              value={form.description}
              onChange={(e) => update("description", e.target.value)}
            />
          </Field>

          <Field label="Short bio (2–3 sentences) *">
            <textarea
              className="portal-textarea"
              value={form.short_bio}
              onChange={(e) => update("short_bio", e.target.value)}
            />
            <div className="portal-help">
              Keep it short and sweet — 2–3 sentences.
              {bioWords > 0 && ` (${bioWords} words)`}
            </div>
          </Field>

          <div className="portal-grid">
            <Field label="Socials and/or website (if relevant)">
              <input
                className="portal-input"
                value={form.socials}
                onChange={(e) => update("socials", e.target.value)}
                placeholder="@… / https://…"
              />
            </Field>

            <Field label="Language">
              <input
                className="portal-input"
                value={form.language}
                onChange={(e) => update("language", e.target.value)}
              />
              <label className="portal-help translation-option">
                <input
                  className="portal-checkbox"
                  type="checkbox"
                  checked={form.allow_translation}
                  onChange={(e) => update("allow_translation", e.target.checked)}
                />
                <span>I’m happy for the piece to be accompanied by an English translation.</span>
              </label>
            </Field>
          </div>

          <hr className="hr" />

          <Field label="Text upload (Word / Google Docs export)">
            <input
              className="portal-file"
              type="file"
              accept=".doc,.docx,.pdf"
              onChange={(e) => setTextFile(e.target.files?.[0] || null)}
            />
            <div className="portal-help">
              Max {MAX_WORDS_TEXT} words (we’ll enforce on the backend later).
            </div>
          </Field>

          <Field label={`Visuals upload (TIFF, 300 dpi) — up to ${MAX_VISUALS} files`}>
            <input
              className="portal-file"
              type="file"
              accept=".tif,.tiff,image/tiff"
              multiple
              onChange={(e) => onPickVisuals(e.target.files)}
            />

            {visualFiles.length > 0 && (
              <ul className="portal-filelist">
                {visualFiles.map((file, idx) => (
                  <li key={`${file.name}-${idx}`}>
                    {file.name}
                    <button
                      type="button"
                      className="smallBtn"
                      onClick={() => removeVisual(idx)}
                    >
                      remove
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Field>

          <div className="portal-actions">
            <button className="portal-btn" type="submit" disabled={submitting}>
              {submitting ? "submitting…" : "submit"}
            </button>

            <button
              className="portal-btn"
              type="button"
              onClick={clearAll}
              disabled={submitting}
            >
              clear
            </button>
          </div>

          <div style={{ marginTop: 18 }} className="portal-help">
            Filename reminder: <span className="code">Artist-Name_Artwork-Title</span>
          </div>
        </form>

      </section>
    </>
  );
}

function Field({ label, children }) {
  return (
    <div className="portal-field">
      <div className="portal-label">{label}</div>
      {children}
    </div>
  );
}