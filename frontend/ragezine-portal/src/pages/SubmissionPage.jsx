import React, { useMemo, useRef, useState } from "react";

import CountrySelect from "../components/CountrySelect";
import FormField from "../components/FormField";
import PronounSelect from "../components/PronounSelect";
import { createSubmission } from "../services/submissionService";
import {
  isLikelyEmail,
  sanitizeCountryCode,
  sanitizeMultiline,
  sanitizeSingleLine,
} from "../utils/sanitize";

import "../styles/nav.css";
import "../styles/description.css";
import "../styles/form.css";

const MAX_VISUALS = 5;
const MAX_WORDS_TEXT = 1500;
const SUBMISSION_TYPE_OPTIONS = [
  { value: "poetry", label: "Poetry" },
  { value: "visual_art", label: "Visual art" },
  { value: "short_form_writing", label: "Short form writing" },
  { value: "long_form_writing", label: "Long form writing" },
  { value: "other", label: "Other" },
];

const initialForm = {
  title: "",
  year: "",
  description: "",
  submission_type: "",
  artist_name: "",
  pronouns: "",
  short_bio: "",
  socials: [],
  email: "",
  country_origin: "",
  countries_residence: [],
  language: "English",
  allow_translation: false,
};

function countWords(s) {
  const t = (s || "").trim();
  return t ? t.split(/\s+/).length : 0;
}

export default function SubmissionPage() {
  const textFileInputRef = useRef(null);
  const visualFileInputRef = useRef(null);
  const [form, setForm] = useState(initialForm);
  const [socialInput, setSocialInput] = useState("");
  const [textFiles, setTextFiles] = useState([]);
  const [visualFiles, setVisualFiles] = useState([]);
  const [submitPopup, setSubmitPopup] = useState({
    open: false,
    kind: "success",
    title: "",
    messages: [],
  });
  const [submitting, setSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);

  const bioWords = useMemo(() => countWords(form.short_bio), [form.short_bio]);

  function update(key, value) {
    let nextValue = value;

    if (["title", "year", "artist_name", "submission_type", "pronouns", "email", "language"].includes(key)) {
      nextValue = sanitizeSingleLine(value);
    }

    if (["description", "short_bio"].includes(key)) {
      nextValue = value;
    }

    if (key === "country_origin") {
      nextValue = sanitizeCountryCode(value);
    }

    if (key === "countries_residence" && Array.isArray(value)) {
      nextValue = value.map(sanitizeCountryCode);
    }

    setForm((prev) => ({ ...prev, [key]: nextValue }));
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
    setSocialInput("");
    setTextFiles([]);
    setVisualFiles([]);
    if (textFileInputRef.current) textFileInputRef.current.value = "";
    if (visualFileInputRef.current) visualFileInputRef.current.value = "";
  }

  function openPopup(kind, title, messages) {
    setSubmitPopup({
      open: true,
      kind,
      title,
      messages: Array.isArray(messages) ? messages : [messages],
    });
  }

  function closePopup() {
    setSubmitPopup((prev) => ({ ...prev, open: false }));
  }

  function extractErrorMessages(value, parentKey = "") {
    if (!value) {
      return ["Submission failed."];
    }

    if (typeof value === "string") {
      return [parentKey ? `${parentKey}: ${value}` : value];
    }

    if (Array.isArray(value)) {
      return value.flatMap((item) => extractErrorMessages(item, parentKey));
    }

    if (typeof value === "object") {
      return Object.entries(value).flatMap(([key, nestedValue]) =>
        extractErrorMessages(nestedValue, key === "non_field_errors" ? parentKey : key)
      );
    }

    return [String(value)];
  }

  function addSocial() {
    const value = sanitizeSingleLine(socialInput);
    if (!value) return;
    setForm((prev) => ({
      ...prev,
      socials: prev.socials.includes(value) ? prev.socials : [...prev.socials, value],
    }));
    setSocialInput("");
  }

  function removeSocial(index) {
    setForm((prev) => ({
      ...prev,
      socials: prev.socials.filter((_, i) => i !== index),
    }));
  }

  function onPickTextFiles(fileList) {
    const picked = Array.from(fileList || []);
    setTextFiles((prev) => [...prev, ...picked]);
  }

  function removeTextFile(index) {
    setTextFiles((prev) => prev.filter((_, i) => i !== index));
  }

  function buildSubmissionFormData() {
    const fd = new FormData();
    const normalizedForm = {
      ...form,
      title: sanitizeSingleLine(form.title),
      year: sanitizeSingleLine(form.year),
      description: sanitizeMultiline(form.description),
      submission_type: sanitizeSingleLine(form.submission_type),
      artist_name: sanitizeSingleLine(form.artist_name),
      pronouns: sanitizeSingleLine(form.pronouns).toLowerCase(),
      short_bio: sanitizeMultiline(form.short_bio),
      socials: form.socials.map(sanitizeSingleLine).filter(Boolean),
      email: sanitizeSingleLine(form.email).toLowerCase(),
      country_origin: sanitizeCountryCode(form.country_origin),
      countries_residence: form.countries_residence.map(sanitizeCountryCode),
      language: sanitizeSingleLine(form.language),
    };

    Object.entries(normalizedForm).forEach(([key, value]) => {
      if (value === null || value === undefined || value === "") {
        return;
      }

      if (key === "socials") {
        fd.append(key, value.join("\n"));
        return;
      }

      if (Array.isArray(value)) {
        value.forEach((item) => {
          fd.append(key, item);
        });
        return;
      }

      if (typeof value === "boolean") {
        fd.append(key, value ? "true" : "false");
        return;
      }

      fd.append(key, value);
    });

    textFiles.forEach((file) => {
      fd.append("text_files", file);
    });

    visualFiles.forEach((file) => {
      fd.append("visuals", file);
    });

    return fd;
  }

  function validateForm() {
    if (!form.title.trim()) return "Please provide a title of your work(s).";
    if (!form.submission_type) return "Please choose a submission type.";
    if (!form.artist_name.trim()) return "Please provide an artist name.";
    if (!form.pronouns.trim()) return "Please provide pronouns (or write N/A).";
    if (!form.short_bio.trim()) return "Please provide a short bio (2-3 sentences).";
    if (!form.email.trim()) return "Please provide an email address.";
    if (!isLikelyEmail(form.email)) return "Please provide a valid email address.";
    if (!form.country_origin.trim()) return "Please provide countries of origin.";
    if (!form.countries_residence.length) return "Please provide countries of residence.";
    if (visualFiles.length > MAX_VISUALS) return `Too many visual or video files. Max ${MAX_VISUALS}.`;

    return "";
  }

  async function onSubmit(e) {
    e.preventDefault();

    const validationError = validateForm();
    if (validationError) {
      openPopup("error", "Submission error", validationError);
      return;
    }

    setSubmitting(true);
    setUploadProgress(null);

    try {
      const payload = buildSubmissionFormData();
      await createSubmission(payload, (event) => {
        if (event.total) {
          setUploadProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)));
        }
      });
      openPopup("success", "Submission successful", "Your submission has been received.");
      clearAll();
    } catch (err) {
      const backendData = err?.response?.data;
      const messages = backendData
        ? extractErrorMessages(backendData)
        : [err?.message || "Submission failed."];
      openPopup("error", "Submission error", messages);
    } finally {
      setSubmitting(false);
      setUploadProgress(null);
    }
  }

  return (
    <div className="portal-page">
      <nav>
        <ul>
          <li><a href="#home">home</a></li>
          <li><a href="#submit">submit</a></li>
        </ul>
      </nav>

      <section className="hero" id="home">
        <div className="hero-panel">
          <div className="hero-copy">
            <h1>Submission Portal</h1>
            <p>
              A submission portal for bold, multidisciplinary feminist work across
              writing, visuals, and hybrid forms.
            </p>
          </div>
        </div>
      </section>

      <section className="submit" id="submit">
        <div className="submit-shell">
          <div className="submit-intro">
            <h2>Submit</h2>
            <p>
              Use the form to send text, visual work, or both. The styling here now
              follows the reference site instead of the previous dark app theme.
            </p>

            <div className="submission-content">
              <div className="guideline-card">
                <p>
                  <span className="sub">Language:</span><br />
                  English is preferred, but submissions in other languages are welcome
                  if they can be accompanied by an English translation.
                </p>
              </div>

              <div className="guideline-card">
                <p>
                  <span className="sub">Format:</span><br />
                  Text: Word or Google Docs export (max. {MAX_WORDS_TEXT} words)<br />
                  Visuals: TIFF and 300 dpi; video: MP4, MOV, or WebM (max. {MAX_VISUALS} files)
                </p>
              </div>

              <div className="guideline-card">
                <p>
                  <span className="sub">Filename:</span><br />
                  <span style={{ fontFamily: "NewEdge666Slanted, sans-serif" }}>
                    Artist-Name_Artwork-Title
                  </span>
                </p>
              </div>
            </div>
          </div>

          <div className="portal-form-wrap">
            <form className="portal-form" onSubmit={onSubmit}>
              <div className="portal-grid">
                <FormField label="Title of your work(s) *">
                  <input className="portal-input" value={form.title} onChange={(e) => update("title", e.target.value)} onBlur={(e) => update("title", e.target.value)} />
                </FormField>

                <FormField label="Year (if relevant)">
                  <input className="portal-input" value={form.year} onChange={(e) => update("year", e.target.value)} onBlur={(e) => update("year", e.target.value)} />
                </FormField>

                <FormField label="Artist name *">
                  <input className="portal-input" value={form.artist_name} onChange={(e) => update("artist_name", e.target.value)} onBlur={(e) => update("artist_name", e.target.value)} />
                </FormField>

                <FormField label="Email *">
                  <input
                    className="portal-input"
                    type="email"
                    autoComplete="email"
                    value={form.email}
                    onChange={(e) => update("email", e.target.value)}
                    onBlur={(e) => update("email", e.target.value)}
                    pattern="^[^\s@]+@[^\s@]+\.[^\s@]+$"
                    required
                  />
                </FormField>

                <FormField label="Submission type *">
                  <select className="portal-input" value={form.submission_type} onChange={(e) => update("submission_type", e.target.value)}>
                    <option value="">Choose one...</option>
                    {SUBMISSION_TYPE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </FormField>

                <FormField label="Pronouns *">
                  <PronounSelect value={form.pronouns} onChange={(pronoun) => update("pronouns", pronoun)} />
                </FormField>

                <FormField label="Country of origin *">
                  <CountrySelect value={form.country_origin} onChange={(countryCode) => update("country_origin", countryCode)} />
                </FormField>

                <FormField label="Countries of residence *">
                  <CountrySelect value={form.countries_residence} onChange={(countries) => update("countries_residence", countries)} isMulti />
                </FormField>
              </div>

              <div style={{ height: 14 }} />

              <FormField label="Description of work(s), including materials if relevant">
                <textarea className="portal-textarea" value={form.description} onChange={(e) => update("description", e.target.value)} onBlur={(e) => update("description", sanitizeMultiline(e.target.value))} />
              </FormField>

              <FormField label="Short bio (2-3 sentences) *">
                <textarea className="portal-textarea" value={form.short_bio} onChange={(e) => update("short_bio", e.target.value)} onBlur={(e) => update("short_bio", sanitizeMultiline(e.target.value))} />
                <div className="portal-help">
                  Keep it short and sweet, 2-3 sentences.
                  {bioWords > 0 && ` (${bioWords} words)`}
                </div>
              </FormField>

              <div className="portal-grid">
                <FormField label="Socials and/or website (if relevant)">
                  <div className="portal-inline-entry">
                    <input
                      className="portal-input"
                      value={socialInput}
                      onChange={(e) => setSocialInput(e.target.value)}
                      onBlur={(e) => setSocialInput(sanitizeSingleLine(e.target.value))}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          addSocial();
                        }
                      }}
                      placeholder="@name / https://..."
                    />
                    <button type="button" className="smallBtn portal-inline-btn" onClick={addSocial}>
                      add
                    </button>
                  </div>

                  {form.socials.length > 0 && (
                    <ul className="portal-pill-list">
                      {form.socials.map((social, index) => (
                        <li key={`${social}-${index}`}>
                          <span>{social}</span>
                          <button type="button" className="portal-remove-inline" onClick={() => removeSocial(index)} aria-label={`Remove ${social}`}>
                            x
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </FormField>

                <FormField
                  label={
                    <>
                      Language <br />
                      &nbsp;
                    </>
                  }
                >
                  <input className="portal-input" value={form.language} onChange={(e) => update("language", e.target.value)} onBlur={(e) => update("language", e.target.value)} />
                  <label className="portal-help translation-option">
                    <input className="portal-checkbox" type="checkbox" checked={form.allow_translation} onChange={(e) => update("allow_translation", e.target.checked)} />
                    <span>
                      I am happy for the piece to be accompanied by an English
                      translation.
                    </span>
                  </label>
                </FormField>
              </div>

              <hr className="hr" />

              <FormField label="Text upload (Word / Google Docs export)">
                <input ref={textFileInputRef} className="portal-file" type="file" accept=".doc,.docx,.pdf" multiple onChange={(e) => onPickTextFiles(e.target.files)} />
                <div className="portal-help">
                  Max {MAX_WORDS_TEXT} words.
                </div>

                {textFiles.length > 0 && (
                  <ul className="portal-filelist">
                    {textFiles.map((file, idx) => (
                      <li key={`${file.name}-${idx}`}>
                        <span>{file.name}</span>
                        <button type="button" className="smallBtn" onClick={() => removeTextFile(idx)}>
                          x
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </FormField>

              <FormField label={`Visuals or video upload - up to ${MAX_VISUALS} files`}>
                <input ref={visualFileInputRef} className="portal-file" type="file" accept=".tif,.tiff,.mp4,.mov,.webm,image/tiff,video/mp4,video/quicktime,video/webm" multiple onChange={(e) => onPickVisuals(e.target.files)} />

                {visualFiles.length > 0 && (
                  <ul className="portal-filelist">
                    {visualFiles.map((file, idx) => (
                      <li key={`${file.name}-${idx}`}>
                        <span>{file.name}</span>
                        <button type="button" className="smallBtn" onClick={() => removeVisual(idx)}>
                          x
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </FormField>

              <div style={{ marginTop: 18 }} className="portal-help">
                Filename reminder: <span className="code">Artist-Name_Artwork-Title</span>
              </div>

              <div className="portal-actions">
                <button className="portal-btn" type="submit" disabled={submitting}>
                  {submitting
                    ? uploadProgress === 100
                      ? "processing submission..."
                      : uploadProgress === null
                        ? "submitting..."
                        : `uploading ${uploadProgress}%...`
                    : "submit"}
                </button>

                <button className="portal-btn portal-btn-secondary" type="button" onClick={clearAll} disabled={submitting}>
                  clear
                </button>
              </div>
            </form>
          </div>
        </div>
      </section>

      {submitPopup.open && (
        <div className="portal-modal-backdrop" onClick={closePopup}>
          <div
            className={`portal-modal portal-modal-${submitPopup.kind}`}
            role="dialog"
            aria-modal="true"
            aria-labelledby="submission-modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button type="button" className="portal-modal-close" onClick={closePopup} aria-label="Close message">
              x
            </button>

            <h3 id="submission-modal-title">{submitPopup.title}</h3>

            <div className="portal-modal-body">
              {submitPopup.messages.map((message, index) => (
                <p key={`${message}-${index}`}>{message}</p>
              ))}
            </div>

            <button type="button" className="portal-btn" onClick={closePopup}>
              close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
