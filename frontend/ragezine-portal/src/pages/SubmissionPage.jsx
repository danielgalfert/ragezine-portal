import React, { useMemo, useRef, useState } from "react";

import CountrySelect from "../components/CountrySelect";
import FormField from "../components/FormField";
import { createSubmission } from "../services/submissionService";
import {
  isLikelyEmail,
  sanitizeCountryCode,
  sanitizeMultiline,
  sanitizeSingleLine,
} from "../utils/sanitize";

import "../styles/description.css";
import "../styles/form.css";

const RECOMMENDED_VISUALS = 5;
const MAX_VISUAL_ATTACHMENTS = 50;
const MAX_TEXT_ATTACHMENTS = 10;
const MAX_WORDS_TEXT = 1500;
const MAX_PRONOUN_TAGS = 10;
const PRONOUN_SUGGESTIONS = [
  { value: "she/her", label: "She / Her" },
  { value: "he/him", label: "He / Him" },
  { value: "they/them", label: "They / Them" },
  { value: "she/they", label: "She / They" },
  { value: "he/they", label: "He / They" },
  { value: "xe/xem", label: "Xe / Xem" },
  { value: "ze/zir", label: "Ze / Zir" },
  { value: "Any pronouns", label: "Any pronouns" },
  { value: "Prefer not to say", label: "Prefer not to say" },
];
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
  pronouns: [],
  short_bio: "",
  socials: [],
  email: "",
  country_origin: "",
  countries_residence: [],
  language: "English",
};

function countWords(s) {
  const t = (s || "").trim();
  return t ? t.split(/\s+/).length : 0;
}

export default function SubmissionPage() {
  const textFileInputRef = useRef(null);
  const visualFileInputRef = useRef(null);
  const videoFileInputRef = useRef(null);
  const [form, setForm] = useState(initialForm);
  const [socialInput, setSocialInput] = useState("");
  const [pronounInput, setPronounInput] = useState("");
  const [textFiles, setTextFiles] = useState([]);
  const [visualFiles, setVisualFiles] = useState([]);
  const [videoFiles, setVideoFiles] = useState([]);
  const [textLinks, setTextLinks] = useState([""]);
  const [visualLinks, setVisualLinks] = useState([""]);
  const [videoLinks, setVideoLinks] = useState([""]);
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

    if (key === "submission_type") {
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
    setVisualFiles((prev) => [...prev, ...picked].slice(0, MAX_VISUAL_ATTACHMENTS));
  }

  function removeVisual(idx) {
    setVisualFiles((prev) => prev.filter((_, i) => i !== idx));
  }

  function onPickVideos(fileList) {
    const picked = Array.from(fileList || []);
    setVideoFiles((prev) => [...prev, ...picked].slice(0, MAX_VISUAL_ATTACHMENTS));
  }

  function removeVideo(idx) {
    setVideoFiles((prev) => prev.filter((_, i) => i !== idx));
  }

  function clearAll() {
    setForm(initialForm);
    setSocialInput("");
    setPronounInput("");
    setTextFiles([]);
    setVisualFiles([]);
    setVideoFiles([]);
    setTextLinks([""]);
    setVisualLinks([""]);
    setVideoLinks([""]);
    if (textFileInputRef.current) textFileInputRef.current.value = "";
    if (visualFileInputRef.current) visualFileInputRef.current.value = "";
    if (videoFileInputRef.current) videoFileInputRef.current.value = "";
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

  function pronounTags() {
    const draft = sanitizeSingleLine(pronounInput);
    const tags = [...form.pronouns];
    if (draft && !tags.some((tag) => tag.toLowerCase() === draft.toLowerCase())) tags.push(draft);
    return tags;
  }

  function addPronounValue(rawValue) {
    const value = sanitizeSingleLine(rawValue);
    if (!value) return;
    setForm((prev) => ({
      ...prev,
      pronouns: prev.pronouns.length >= MAX_PRONOUN_TAGS || prev.pronouns.some((tag) => tag.toLowerCase() === value.toLowerCase())
        ? prev.pronouns
        : [...prev.pronouns, value],
    }));
  }

  function addPronoun() {
    addPronounValue(pronounInput);
    setPronounInput("");
  }

  function removePronoun(index) {
    setForm((prev) => ({
      ...prev,
      pronouns: prev.pronouns.filter((_, itemIndex) => itemIndex !== index),
    }));
  }

  function onPickTextFiles(fileList) {
    const picked = Array.from(fileList || []);
    setTextFiles((prev) => [...prev, ...picked]);
  }

  function removeTextFile(index) {
    setTextFiles((prev) => prev.filter((_, i) => i !== index));
  }

  function linkFields(type) {
    const links = type === "text" ? textLinks : type === "visual" ? visualLinks : videoLinks;
    const setLinks = type === "text" ? setTextLinks : type === "visual" ? setVisualLinks : setVideoLinks;
    const limit = type === "text" ? MAX_TEXT_ATTACHMENTS : MAX_VISUAL_ATTACHMENTS;
    const otherAttachmentCount = type === "text" ? textFiles.length :
      visualFiles.length + videoFiles.length + (type === "visual" ? videoLinks : visualLinks).filter((url) => url.trim()).length;
    return (
      <div className="portal-link-fields">
        {links.map((url, index) => (
          <div className="portal-inline-entry" key={`${type}-link-${index}`}>
            <input
              className="portal-input"
              type="url"
              inputMode="url"
              aria-label={`${type === "text" ? "Text" : type === "visual" ? "Visual" : "Video"} link ${index + 1}`}
              placeholder="https://..."
              value={url}
              onChange={(event) => setLinks((prev) => prev.map((item, itemIndex) => itemIndex === index ? event.target.value : item))}
            />
            {links.length > 1 && (
              <button type="button" className="smallBtn portal-inline-btn" onClick={() => setLinks((prev) => prev.filter((_, itemIndex) => itemIndex !== index))} aria-label={`Remove link ${index + 1}`}>
                remove
              </button>
            )}
          </div>
        ))}
        {links.length + otherAttachmentCount < limit && (
          <button type="button" className="smallBtn portal-add-link" onClick={() => setLinks((prev) => [...prev, ""])}>
            add another link
          </button>
        )}
      </div>
    );
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
      pronouns: pronounTags().join(", "),
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
    videoFiles.forEach((file) => {
      fd.append("visuals", file);
    });

    textLinks.map((url) => url.trim()).filter(Boolean).forEach((url) => fd.append("text_links", url));
    visualLinks.map((url) => url.trim()).filter(Boolean).forEach((url) => fd.append("visual_links", url));
    videoLinks.map((url) => url.trim()).filter(Boolean).forEach((url) => fd.append("video_links", url));

    return fd;
  }

  function validateForm() {
    if (!form.title.trim()) return "Please provide a title of your work(s).";
    if (!form.submission_type) return "Please choose a submission type.";
    if (!form.artist_name.trim()) return "Please provide an artist name.";
    if (!pronounTags().length) return "Please provide pronouns (or add 'Prefer not to say').";
    if (pronounTags().length > MAX_PRONOUN_TAGS) return `Add at most ${MAX_PRONOUN_TAGS} pronoun tags.`;
    if (!form.short_bio.trim()) return "Please provide a short bio (2-3 sentences).";
    if (!form.email.trim()) return "Please provide an email address.";
    if (!isLikelyEmail(form.email)) return "Please provide a valid email address.";
    if (!form.country_origin.trim()) return "Please provide countries of origin.";
    if (!form.countries_residence.length) return "Please provide countries of residence.";
    const links = [...textLinks, ...visualLinks, ...videoLinks].map((url) => url.trim()).filter(Boolean);
    if (links.some((url) => {
      try {
        const parsed = new URL(url);
        return parsed.protocol !== "https:" || !parsed.hostname;
      } catch {
        return true;
      }
    })) return "Use complete HTTPS links for your work.";
    if (textFiles.length + textLinks.filter((url) => url.trim()).length > MAX_TEXT_ATTACHMENTS) return `Add at most ${MAX_TEXT_ATTACHMENTS} text files or links.`;
    if (visualFiles.length + videoFiles.length + [...visualLinks, ...videoLinks].filter((url) => url.trim()).length > MAX_VISUAL_ATTACHMENTS) return `Add at most ${MAX_VISUAL_ATTACHMENTS} visual or video files or links.`;
    if (!textFiles.length && !visualFiles.length && !videoFiles.length && !links.length) return "Add at least one file or link.";

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
      <section className="hero" id="home">
        <div className="hero-panel">
          <div className="hero-copy">
            <h1 className="hero-title" aria-label="RAGE ZINE">
              <span className="hero-wordmark" aria-hidden="true">
                <span className="hero-wordmark-rage">
                  <span className="hero-letter-heavy">R</span>
                  <span className="hero-letter-regular">A</span>
                  <span className="hero-letter-heavy">G</span>
                  <span className="hero-letter-heavy">E</span>
                </span>
                <span className="hero-wordmark-zine">
                  <span className="hero-letter-light">Z</span>
                  <span className="hero-letter-heavy hero-letter-pair">IN</span>
                  <span className="hero-letter-light">E</span>
                </span>
              </span>
            </h1>
            <p className="hero-subtitle">SUBMISSION PORTAL</p>
            <div className="hero-description">
              <p>
                RAGE Zine is a global multidisciplinary print and digital zine &amp; platform exploring the theme of feminist rage.
              </p>
              <p>
                We are looking for submissions of all kinds of writing, art &amp; content about feminist rage or showcasing feminist rage. Multidisciplinarity is a core value for us, so we are looking for pieces covering a range of topics and disciplines, including politics, literature, art, gender, LGBTQIA+ rights, global health, science, education, psychology, sexuality, visual culture and more. We also publish a range of forms and mediums, including but not limited to articles, poems, photography, painting, comics, collage, film stills and digital art.
              </p>
              <p>
                We particularly encourage submissions to go beyond the obvious scope of theme and are particularly keen on experimental, bold and fresh feminist work.
              </p>
              <p>
                We are primarily looking for finalised submissions, but do not hesitate to get in touch if you have an idea and would like some feedback or support creating your piece. We also reach out to select creators for commissioned pieces and/or interviews.
              </p>
              <p>
                Please note that we are a fully not-for-profit and volunteer driven platform and this is an unpaid opportunity.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="submit" id="submit">
        <div className="submit-shell">
          <div className="submit-intro">
            <h2>Submit</h2>

            <div className="submission-content">
              <div className="guideline-card">
                <p>
                  <span className="sub">Language:</span><br />
                  English is preferred, but we occasionally accept submissions in other languages, if you are happy for the piece to be accompanied by an English translation. Our team can help with translations in numerous languages.
                </p>
              </div>

              <div className="guideline-card">
                <p>
                  <span className="sub">Format:</span><br />
                  Text: Word, Google Doc or PDF (max. {MAX_WORDS_TEXT} words)<br />
                  Visual: TIFF at 300 dpi, or link<br />
                  Video: MP4, MOV, or WebM, or link<br />
                  We recommend up to {RECOMMENDED_VISUALS} visual and video files or links in total.
                </p>
              </div>

              <div className="guideline-card">
                <p>
                  <span className="sub">Filename:</span><br />
                  Artist-Name_Artwork-Title
                </p>
              </div>
            </div>
          </div>

          <div className="portal-form-wrap">
            <form className="portal-form" onSubmit={onSubmit}>
              <div className="portal-grid">
                <FormField label="Title of your work(s) *">
                  <input className="portal-input" value={form.title} onChange={(e) => update("title", e.target.value)} onBlur={(e) => update("title", sanitizeSingleLine(e.target.value))} />
                </FormField>

                <FormField label="Year (if relevant)">
                  <input className="portal-input" value={form.year} onChange={(e) => update("year", e.target.value)} onBlur={(e) => update("year", sanitizeSingleLine(e.target.value))} />
                </FormField>

                <FormField label="Artist name *">
                  <input className="portal-input" value={form.artist_name} onChange={(e) => update("artist_name", e.target.value)} onBlur={(e) => update("artist_name", sanitizeSingleLine(e.target.value))} />
                </FormField>

                <FormField label="Email *">
                  <input
                    className="portal-input"
                    type="email"
                    autoComplete="email"
                    value={form.email}
                    onChange={(e) => update("email", e.target.value)}
                    onBlur={(e) => update("email", sanitizeSingleLine(e.target.value))}
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
                  <div className="portal-inline-entry">
                    <input
                      className="portal-input"
                      value={pronounInput}
                      onChange={(event) => setPronounInput(event.target.value)}
                      onBlur={(event) => setPronounInput(sanitizeSingleLine(event.target.value))}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          event.preventDefault();
                          addPronoun();
                        }
                      }}
                      placeholder="she/her or your own"
                      maxLength={40}
                      disabled={form.pronouns.length >= MAX_PRONOUN_TAGS}
                      aria-label="Add pronouns"
                    />
                    <button type="button" className="smallBtn portal-inline-btn" onClick={addPronoun} disabled={form.pronouns.length >= MAX_PRONOUN_TAGS}>
                      add
                    </button>
                  </div>
                  <div className="portal-help portal-pronoun-suggestions-label">Suggestions:</div>
                  <div className="portal-pronoun-suggestions" role="group" aria-label="Suggested pronouns">
                    {PRONOUN_SUGGESTIONS.filter((option) => !form.pronouns.some((tag) => tag.toLowerCase() === option.value.toLowerCase())).map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        className="portal-pronoun-suggestion"
                        onClick={() => addPronounValue(option.value)}
                        disabled={form.pronouns.length >= MAX_PRONOUN_TAGS}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                  {form.pronouns.length > 0 && (
                    <ul className="portal-pill-list">
                      {form.pronouns.map((pronoun, index) => (
                        <li key={`${pronoun}-${index}`}>
                          <span>{pronoun}</span>
                          <button type="button" className="portal-remove-inline" onClick={() => removePronoun(index)} aria-label={`Remove ${pronoun}`}>
                            x
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
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

              <div className="portal-grid portal-grid-socials">
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

                <FormField label="Language">
                  <input className="portal-input" value={form.language} onChange={(e) => update("language", e.target.value)} onBlur={(e) => update("language", sanitizeSingleLine(e.target.value))} />
                </FormField>
              </div>

              <hr className="hr" />

              <FormField label="Text upload (Word / PDF)">
                <input ref={textFileInputRef} className="portal-file" type="file" accept=".doc,.docx,.pdf,.txt,.rtf,.odt,.md,.pages" multiple onChange={(e) => onPickTextFiles(e.target.files)} />
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

              <FormField label="Text link (Google Doc or other HTTPS link)">
                {linkFields("text")}
                <div className="portal-help">Set access so the RAGE Zine team can open your work.</div>
              </FormField>

              <FormField label="Visual upload (TIFF)">
                <input ref={visualFileInputRef} className="portal-file" type="file" accept=".tif,.tiff" multiple onChange={(e) => onPickVisuals(e.target.files)} />

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

              <FormField label="Visual link">
                {linkFields("visual")}
                <div className="portal-help">Set access so the RAGE Zine team can open your work.</div>
              </FormField>

              <FormField label="Video upload (MP4 / MOV / WebM)">
                <input ref={videoFileInputRef} className="portal-file" type="file" accept=".mp4,.mov,.webm" multiple onChange={(e) => onPickVideos(e.target.files)} />

                {videoFiles.length > 0 && (
                  <ul className="portal-filelist">
                    {videoFiles.map((file, idx) => (
                      <li key={`${file.name}-${idx}`}>
                        <span>{file.name}</span>
                        <button type="button" className="smallBtn" onClick={() => removeVideo(idx)}>
                          x
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </FormField>

              <FormField label="Video link">
                {linkFields("video")}
                <div className="portal-help">Set access so the RAGE Zine team can open your work.</div>
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
