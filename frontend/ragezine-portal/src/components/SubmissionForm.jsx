import { useEffect, useRef, useState } from "react";

import CountrySelect from "./CountrySelect";
import FormField from "./FormField";
import LanguageSelect, { MAX_LANGUAGES } from "./LanguageSelect";
import { createSubmissionBatch } from "../services/submissionService";
import { isLikelyEmail, sanitizeCountryCode, sanitizeMultiline, sanitizeSingleLine } from "../utils/sanitize";

const GIB = 1024 ** 3;
const MAX_FILE_BYTES = 5 * GIB;
const MAX_TOTAL_BYTES = 10 * GIB;
const MAX_WORKS = 10;
const MAX_TEXT = 10;
const MAX_VISUAL_VIDEO = 50;
const MAX_OTHER_LINKS = 20;
const MAX_PRONOUNS = 10;
const MAX_FILES = 60;
const DRAFT_KEY = "ragezine-submission-draft-v1";

const TYPES = [
  ["poetry", "Poetry"],
  ["visual_art", "Visual art"],
  ["short_form_writing", "Short form writing"],
  ["long_form_writing", "Long form writing"],
  ["other", "Other"],
];
const PRONOUN_SUGGESTIONS = [
  ["she/her", "She / Her"], ["he/him", "He / Him"],
  ["they/them", "They / Them"], ["she/they", "She / They"],
  ["he/they", "He / They"], ["xe/xem", "Xe / Xem"],
  ["ze/zir", "Ze / Zir"], ["Any pronouns", "Any pronouns"],
  ["Prefer not to say", "Prefer not to say"],
];

const emptyArtist = {
  artist_name: "", pronouns: [], email: "", country_origin: [],
  countries_residence: [], short_bio: "", socials: [],
  message_to_editors: "", submitted_before: "", featured_before: "",
};

function newWork(key) {
  return {
    key, submission_type: "", title: "", description: "", year: "",
    language: ["English"], published_elsewhere: "", published_where: "",
    anything_else: "", textFiles: [], visualFiles: [], videoFiles: [],
    namedLinks: [], linkName: "", linkUrl: "",
  };
}

function readDraft() {
  try {
    const saved = JSON.parse(window.sessionStorage.getItem(DRAFT_KEY));
    if (!saved?.artist || !Array.isArray(saved.works) || !saved.works.length) return null;
    if (!Array.isArray(saved.artist.pronouns) || !Array.isArray(saved.artist.socials)
      || !Array.isArray(saved.artist.country_origin) || !Array.isArray(saved.artist.countries_residence)) return null;
    if (saved.works.some((work) => !Number.isInteger(work.key) || !Array.isArray(work.namedLinks))) return null;
    return saved;
  } catch {
    return null;
  }
}

function hasDraftContent(artist, works, pronounInput, socialInput) {
  return Boolean(
    artist.artist_name || artist.email || artist.short_bio || artist.message_to_editors ||
    artist.pronouns.length || artist.socials.length || artist.country_origin.length ||
    artist.countries_residence.length || artist.submitted_before || artist.featured_before ||
    pronounInput || socialInput || works.some((work) =>
      work.title || work.description || work.submission_type || work.year || work.anything_else ||
      work.namedLinks.length || work.linkName || work.linkUrl || work.textFiles.length ||
      work.visualFiles.length || work.videoFiles.length
    )
  );
}

function invalid(message, id) {
  return { message, id };
}

function addUnique(items, input) {
  const value = sanitizeSingleLine(input);
  if (!value || items.some((item) => item.toLowerCase() === value.toLowerCase())) return items;
  return [...items, value];
}

function collectedLinks(work) {
  const links = [...work.namedLinks];
  if (work.linkName.trim() && work.linkUrl.trim()) {
    links.push({ name: sanitizeSingleLine(work.linkName), url: work.linkUrl.trim() });
  }
  return links;
}

function errorMessages(value, prefix = "") {
  if (typeof value === "string") return [prefix ? `${prefix}: ${value}` : value];
  if (Array.isArray(value)) return value.flatMap((item) => errorMessages(item, prefix));
  if (value && typeof value === "object") {
    return Object.entries(value).flatMap(([key, item]) => errorMessages(item, key === "non_field_errors" ? prefix : key));
  }
  return [String(value || "Submission failed.")];
}

function UploadBox({ label, format, accept, files, onPick, onRemove, onClear, id }) {
  const fileInputRef = useRef(null);
  const dragDepth = useRef(0);
  const [isDragging, setIsDragging] = useState(false);
  const [fileError, setFileError] = useState("");
  const acceptedExtensions = accept.toLowerCase().split(",").map((extension) => extension.trim());

  function addFiles(selectedFiles) {
    const accepted = selectedFiles.filter((file) =>
      acceptedExtensions.some((extension) => file.name.toLowerCase().endsWith(extension)));
    setFileError(accepted.length === selectedFiles.length
      ? ""
      : "Some files were not added. Check the formats shown above.");
    if (accepted.length) onPick(accepted);
  }

  function hasDraggedFiles(event) {
    return Array.from(event.dataTransfer?.types || []).includes("Files");
  }

  return (
    <div
      className={`portal-upload-box${isDragging ? " portal-upload-box--dragging" : ""}`}
      onDragEnter={(event) => {
        if (!hasDraggedFiles(event)) return;
        event.preventDefault();
        dragDepth.current += 1;
        setIsDragging(true);
      }}
      onDragOver={(event) => {
        if (!hasDraggedFiles(event)) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "copy";
      }}
      onDragLeave={(event) => {
        if (dragDepth.current === 0) return;
        event.preventDefault();
        dragDepth.current = Math.max(0, dragDepth.current - 1);
        if (dragDepth.current === 0) setIsDragging(false);
      }}
      onDrop={(event) => {
        const droppedFiles = Array.from(event.dataTransfer?.files || []);
        if (!hasDraggedFiles(event) && !droppedFiles.length) return;
        event.preventDefault();
        dragDepth.current = 0;
        setIsDragging(false);
        if (droppedFiles.length) addFiles(droppedFiles);
      }}
    >
      <div className="portal-upload-heading">
        <span className="portal-label">{label}</span>
        <button type="button" className="smallBtn" onClick={onClear} disabled={!files.length}>clear files</button>
      </div>
      <p className="portal-help portal-upload-format">Format: {format}</p>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        multiple
        hidden
        tabIndex={-1}
        onChange={(event) => {
          addFiles(Array.from(event.target.files || []));
          event.target.value = "";
        }}
      />
      <div className="portal-drop-zone">
        <svg className="portal-drop-icon" viewBox="0 0 48 48" aria-hidden="true">
          <path d="M12 4h16l8 8v26a4 4 0 0 1-4 4H12a4 4 0 0 1-4-4V8a4 4 0 0 1 4-4Z" />
          <path d="M28 4v8h8M24 34V19m-5 5 5-5 5 5" />
        </svg>
        <span className="portal-drop-title">Drag files here</span>
        <span className="portal-drop-or">or</span>
        <button id={id} type="button" className="portal-file-picker" aria-label={`Choose ${label.toLowerCase()}`} onClick={() => fileInputRef.current?.click()}>
          choose files
        </button>
      </div>
      {fileError && <p className="portal-upload-error" role="alert">{fileError}</p>}
      {files.length > 0 && (
        <ul className="portal-filelist">
          {files.map((file, index) => (
            <li key={`${file.name}-${index}`}>
              <span>{file.name}</span>
              <button type="button" className="smallBtn" onClick={() => onRemove(index)} aria-label={`Remove ${file.name}`}>remove</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function SubmissionForm() {
  const errorRef = useRef(null);
  const [restoredDraft] = useState(readDraft);
  const [artist, setArtist] = useState(() => ({ ...emptyArtist, ...restoredDraft?.artist }));
  const [works, setWorks] = useState(() => restoredDraft?.works?.map((work) => ({
    ...newWork(work.key), ...work,
    language: Array.isArray(work.language) ? work.language : [work.language || "English"],
    textFiles: [], visualFiles: [], videoFiles: [],
  })) || [newWork(0)]);
  const nextWorkKey = useRef(restoredDraft ? Math.max(...restoredDraft.works.map((work) => work.key)) + 1 : 1);
  const [pronounInput, setPronounInput] = useState(restoredDraft?.pronounInput || "");
  const [socialInput, setSocialInput] = useState(restoredDraft?.socialInput || "");
  const [submitting, setSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [uploadPhase, setUploadPhase] = useState("uploading");
  const [formError, setFormError] = useState("");
  const [draftNotice, setDraftNotice] = useState(Boolean(restoredDraft));
  const [popup, setPopup] = useState({ open: false, kind: "success", title: "", messages: [] });

  useEffect(() => {
    try {
      if (!hasDraftContent(artist, works, pronounInput, socialInput)) {
        window.sessionStorage.removeItem(DRAFT_KEY);
        return;
      }
      window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify({
        artist,
        works: works.map((work) => ({ ...work, textFiles: [], visualFiles: [], videoFiles: [] })),
        hadFiles: Boolean(restoredDraft?.hadFiles || works.some((work) =>
          work.textFiles.length || work.visualFiles.length || work.videoFiles.length
        )),
        pronounInput,
        socialInput,
      }));
    } catch {
      // The form still works if browser storage is unavailable.
    }
  }, [artist, works, pronounInput, socialInput, restoredDraft?.hadFiles]);

  function updateArtist(field, value) {
    setFormError("");
    setArtist((current) => ({ ...current, [field]: value }));
  }

  function updateWork(key, field, value) {
    setFormError("");
    setWorks((current) => current.map((work) => work.key === key ? { ...work, [field]: value } : work));
  }

  function appendFilesToWork(key, field, files) {
    setFormError("");
    setWorks((current) => current.map((work) => work.key === key
      ? { ...work, [field]: [...work[field], ...files] }
      : work));
  }

  function removeFromWork(key, field, index) {
    setWorks((current) => current.map((work) => work.key === key
      ? { ...work, [field]: work[field].filter((_, itemIndex) => itemIndex !== index) }
      : work));
  }

  function addNamedLink(key) {
    setWorks((current) => current.map((work) => {
      if (work.key !== key || work.namedLinks.length >= MAX_OTHER_LINKS) return work;
      const name = sanitizeSingleLine(work.linkName);
      const url = work.linkUrl.trim();
      if (!name || !url) return work;
      return { ...work, namedLinks: [...work.namedLinks, { name, url }], linkName: "", linkUrl: "" };
    }));
  }

  function clearNamedLinks(key) {
    setWorks((current) => current.map((work) => work.key === key
      ? { ...work, namedLinks: [], linkName: "", linkUrl: "" }
      : work));
  }

  function addPronoun(value, clearDraft = true) {
    setArtist((current) => ({
      ...current,
      pronouns: current.pronouns.length >= MAX_PRONOUNS ? current.pronouns : addUnique(current.pronouns, value),
    }));
    if (clearDraft) setPronounInput("");
  }

  function clearAfterSuccess() {
    try { window.sessionStorage.removeItem(DRAFT_KEY); } catch { /* Storage is optional. */ }
    setArtist(emptyArtist);
    setWorks([newWork(nextWorkKey.current++)]);
    setPronounInput("");
    setSocialInput("");
    setDraftNotice(false);
  }

  function validate() {
    const pronouns = addUnique(artist.pronouns, pronounInput);
    if (sanitizeSingleLine(artist.artist_name).length < 2) return invalid("Enter artist name(s) of at least 2 characters.", "artist-name");
    if (!pronouns.length || pronouns.length > MAX_PRONOUNS) return invalid("Add your pronouns or choose a suggestion.", "pronoun-input");
    if (!isLikelyEmail(artist.email)) return invalid("Enter a valid email address.", "artist-email");
    if (!artist.country_origin.length) return invalid("Select at least one country of origin.", "artist-origin");
    if (!artist.countries_residence.length) return invalid("Select at least one country of residence.", "artist-residence");
    if (sanitizeMultiline(artist.short_bio).length < 10) return invalid("Enter a short bio of at least 10 characters.", "artist-bio");
    if (!artist.submitted_before) return invalid("Answer whether you have submitted before.", "artist-submitted-before");
    if (!artist.featured_before) return invalid("Answer whether you have been featured before.", "artist-featured-before");
    if (works.length < 1 || works.length > MAX_WORKS) return invalid(`Add 1 to ${MAX_WORKS} submissions.`, "submission-info-heading");

    let totalBytes = 0;
    let totalFiles = 0;
    for (const [index, work] of works.entries()) {
      const prefix = `Submission ${index + 1}: `;
      if (!work.submission_type) return invalid(`${prefix}choose a submission type.`, `work-${work.key}-type`);
      if (sanitizeSingleLine(work.title).length < 3) return invalid(`${prefix}enter a title of at least 3 characters.`, `work-${work.key}-title`);
      if (!Array.isArray(work.language) || !work.language.length) return invalid(`${prefix}select or enter a language.`, `work-${work.key}-language`);
      if (work.language.length > MAX_LANGUAGES) return invalid(`${prefix}select up to ${MAX_LANGUAGES} languages.`, `work-${work.key}-language`);
      if (sanitizeMultiline(work.description).length < 10) return invalid(`${prefix}enter a description of at least 10 characters.`, `work-${work.key}-description`);
      if (!work.published_elsewhere) return invalid(`${prefix}answer the publication question.`, `work-${work.key}-published`);
      if (work.published_elsewhere === "yes" && !sanitizeMultiline(work.published_where)) return invalid(`${prefix}tell us where it was published.`, `work-${work.key}-published-where`);
      const files = [...work.textFiles, ...work.visualFiles, ...work.videoFiles];
      totalFiles += files.length;
      if (Boolean(work.linkName.trim()) !== Boolean(work.linkUrl.trim())) return invalid(`${prefix}enter both a link name and URL.`, `work-${work.key}-link-name`);
      const links = collectedLinks(work);
      if (!files.length && !links.length) return invalid(`${prefix}add a file or link.`, `work-${work.key}-text-files`);
      if (work.textFiles.length > MAX_TEXT) return invalid(`${prefix}too many text files.`, `work-${work.key}-text-files`);
      if (work.visualFiles.length + work.videoFiles.length > MAX_VISUAL_VIDEO) return invalid(`${prefix}too many visual or video files.`, `work-${work.key}-visual-files`);
      if (links.length > MAX_OTHER_LINKS) return invalid(`${prefix}too many links.`, `work-${work.key}-link-name`);
      for (const link of links) {
        if (!link.name || link.name.length > 120) return invalid(`${prefix}give each link a name of at most 120 characters.`, `work-${work.key}-link-name`);
        try {
          if (new URL(link.url).protocol !== "https:") return invalid(`${prefix}use HTTPS links.`, `work-${work.key}-link-url`);
        } catch {
          return invalid(`${prefix}enter complete HTTPS links.`, `work-${work.key}-link-url`);
        }
      }
      for (const file of files) {
        if (file.size > MAX_FILE_BYTES) return invalid(`${prefix}${file.name} exceeds 5 GB.`, `work-${work.key}-text-files`);
        totalBytes += file.size;
      }
    }
    if (totalBytes > MAX_TOTAL_BYTES) return invalid("Files exceed 10 GB in total.", "submission-info-heading");
    if (totalFiles > MAX_FILES) return invalid("Add at most 60 files across all submissions.", "submission-info-heading");
    return null;
  }

  function buildPayload() {
    const data = new FormData();
    data.append("artist", JSON.stringify({
      artist_name: sanitizeSingleLine(artist.artist_name),
      pronouns: addUnique(artist.pronouns, pronounInput).join(", "),
      email: sanitizeSingleLine(artist.email).toLowerCase(),
      country_origin: artist.country_origin.map(sanitizeCountryCode),
      countries_residence: artist.countries_residence.map(sanitizeCountryCode),
      short_bio: sanitizeMultiline(artist.short_bio),
      socials: addUnique(artist.socials, socialInput).join("\n"),
      message_to_editors: sanitizeMultiline(artist.message_to_editors),
      submitted_before: artist.submitted_before === "yes",
      featured_before: artist.featured_before === "yes",
    }));
    data.append("submissions", JSON.stringify(works.map((work) => ({
      submission_type: work.submission_type,
      title: sanitizeSingleLine(work.title),
      description: sanitizeMultiline(work.description),
      year: sanitizeSingleLine(work.year),
      language: work.language.map(sanitizeSingleLine).join(", "),
      named_links: collectedLinks(work),
      published_elsewhere: work.published_elsewhere === "yes",
      published_where: work.published_elsewhere === "yes" ? sanitizeMultiline(work.published_where) : "",
      anything_else: sanitizeMultiline(work.anything_else),
    }))));
    works.forEach((work, index) => {
      work.textFiles.forEach((file) => data.append(`submission_${index}_text_files`, file));
      [...work.visualFiles, ...work.videoFiles].forEach((file) => data.append(`submission_${index}_visuals`, file));
    });
    return data;
  }

  async function submit(event) {
    event.preventDefault();
    const error = validate();
    if (error) {
      setFormError(error.message);
      const target = document.getElementById(error.id);
      target?.focus();
      target?.scrollIntoView({ block: "center" });
      return;
    }
    setFormError("");
    setSubmitting(true);
    setUploadProgress(null);
    setUploadPhase("uploading");
    try {
      await createSubmissionBatch(buildPayload(), (progress) => {
        if (progress.total) {
          const percent = Math.min(100, Math.round(progress.loaded / progress.total * 100));
          setUploadProgress(percent);
          if (percent === 100) setUploadPhase("processing");
        }
      });
      setPopup({ open: true, kind: "success", title: "Submission successful", messages: ["Your submissions have been received."] });
      clearAfterSuccess();
    } catch (err) {
      setFormError(errorMessages(err?.response?.data || err?.message).join(" "));
      window.requestAnimationFrame(() => errorRef.current?.scrollIntoView({ block: "center" }));
    } finally {
      setSubmitting(false);
      setUploadProgress(null);
    }
  }

  return (
    <>
      <form className="portal-form" onSubmit={submit} noValidate>
        {draftNotice && <div className="portal-form-notice" role="status">
          <p>{restoredDraft?.hadFiles
            ? "We restored the text from this tab. Files do not survive a reload. Check and select all files you need before you submit."
            : "We restored your draft from this tab."}</p>
          <button type="button" className="smallBtn" onClick={() => setDraftNotice(false)}>dismiss</button>
        </div>}
        {formError && <p ref={errorRef} className="portal-form-error" role="alert">{formError}</p>}
        <section className="portal-form-block" aria-labelledby="artist-info-heading">
          <div className="portal-section-heading">
            <h3 id="artist-info-heading">Artist information</h3>
            <p className="portal-section-note">Artist information applies to all submissions.</p>
          </div>
          <div className="portal-grid portal-artist-grid">
            <FormField id="artist-name" label="Artist name(s) *">
              <input className="portal-input" value={artist.artist_name} onChange={(event) => updateArtist("artist_name", event.target.value)} onBlur={(event) => updateArtist("artist_name", sanitizeSingleLine(event.target.value))} />
            </FormField>
            <FormField id="artist-email" label="Email *">
              <input className="portal-input" type="email" autoComplete="email" value={artist.email} onChange={(event) => updateArtist("email", event.target.value)} onBlur={(event) => updateArtist("email", sanitizeSingleLine(event.target.value))} />
            </FormField>
            <FormField id="artist-origin" label="Countries of origin *">
              <CountrySelect value={artist.country_origin} onChange={(countries) => updateArtist("country_origin", countries)} isMulti />
            </FormField>
            <FormField id="artist-residence" label="Countries of residence *">
              <CountrySelect value={artist.countries_residence} onChange={(countries) => updateArtist("countries_residence", countries)} isMulti />
            </FormField>
            <FormField id="artist-submitted-before" label="Have you submitted to RAGE Zine before? *">
              <select className={`portal-input${artist.submitted_before ? "" : " portal-input-placeholder"}`} value={artist.submitted_before} onChange={(event) => updateArtist("submitted_before", event.target.value)}><option value="">Choose one...</option><option value="yes">Yes</option><option value="no">No</option></select>
            </FormField>
            <FormField id="artist-featured-before" label="Have you been featured in RAGE Zine before? *">
              <select className={`portal-input${artist.featured_before ? "" : " portal-input-placeholder"}`} value={artist.featured_before} onChange={(event) => updateArtist("featured_before", event.target.value)}><option value="">Choose one...</option><option value="yes">Yes</option><option value="no">No</option></select>
            </FormField>
          </div>
          <div className="portal-grid portal-artist-identity">
            <FormField label="Pronouns *">
              <div className="portal-inline-entry portal-pronoun-entry">
                <input id="pronoun-input" className="portal-input" value={pronounInput} maxLength={40} placeholder="Click one of the suggestions or write your own." aria-label="Add pronouns" onChange={(event) => { setPronounInput(event.target.value); setFormError(""); }} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addPronoun(pronounInput); } }} />
                <button type="button" className="smallBtn portal-inline-btn" onClick={() => addPronoun(pronounInput)}>add</button>
              </div>
              <div className="portal-help portal-pronoun-suggestions-label">Suggestions:</div>
              <div className="portal-pronoun-suggestions" role="group" aria-label="Suggested pronouns">
                {PRONOUN_SUGGESTIONS.filter(([value]) => !artist.pronouns.some((item) => item.toLowerCase() === value.toLowerCase())).map(([value, label]) => (
                  <button key={value} type="button" className="portal-pronoun-suggestion" onClick={() => addPronoun(value, false)}>{label}</button>
                ))}
              </div>
              {artist.pronouns.length > 0 && (
                <ul className="portal-pill-list">
                  {artist.pronouns.map((value, index) => <li key={`${value}-${index}`}><span>{value}</span><button type="button" className="portal-remove-inline" onClick={() => updateArtist("pronouns", artist.pronouns.filter((_, itemIndex) => itemIndex !== index))} aria-label={`Remove ${value}`}>x</button></li>)}
                </ul>
              )}
            </FormField>
            <FormField label="Socials and/or website (if relevant)">
              <div className="portal-inline-entry">
                <input className="portal-input" value={socialInput} placeholder="@name / https://..." onChange={(event) => setSocialInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); updateArtist("socials", addUnique(artist.socials, socialInput)); setSocialInput(""); } }} />
                <button type="button" className="smallBtn portal-inline-btn" onClick={() => { updateArtist("socials", addUnique(artist.socials, socialInput)); setSocialInput(""); }}>add</button>
              </div>
              {artist.socials.length > 0 && <ul className="portal-pill-list">{artist.socials.map((value, index) => <li key={`${value}-${index}`}><span>{value}</span><button type="button" className="portal-remove-inline" onClick={() => updateArtist("socials", artist.socials.filter((_, itemIndex) => itemIndex !== index))} aria-label={`Remove ${value}`}>x</button></li>)}</ul>}
            </FormField>
          </div>
          <div className="portal-grid portal-artist-notes">
            <FormField id="artist-bio" label="Short bio (2-3 sentences) *">
              <textarea className="portal-textarea" value={artist.short_bio} onChange={(event) => updateArtist("short_bio", event.target.value)} onBlur={(event) => updateArtist("short_bio", sanitizeMultiline(event.target.value))} />
            </FormField>
            <FormField label="Message to the editors (optional)">
              <textarea className="portal-textarea" value={artist.message_to_editors} onChange={(event) => updateArtist("message_to_editors", event.target.value)} onBlur={(event) => updateArtist("message_to_editors", sanitizeMultiline(event.target.value))} />
            </FormField>
          </div>
        </section>

        <section className="portal-form-block" aria-labelledby="submission-info-heading">
          <h3 id="submission-info-heading">Submission information</h3>
          {works.map((work, index) => (
            <article className="portal-work-card" key={work.key}>
              <div className="portal-work-heading">
                <h4 aria-label={`Submission ${index + 1}`}>#{index + 1}</h4>
                {works.length > 1 && <button type="button" className="smallBtn portal-work-remove" aria-label={`Remove submission ${index + 1}`} onClick={() => setWorks((current) => current.filter((item) => item.key !== work.key))}><svg className="portal-work-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="M4 10h12" /></svg>remove submission</button>}
              </div>
              <div className="portal-grid portal-work-core">
                <FormField id={`work-${work.key}-type`} label="Submission type *">
                  <select className={`portal-input${work.submission_type ? "" : " portal-input-placeholder"}`} value={work.submission_type} onChange={(event) => updateWork(work.key, "submission_type", event.target.value)}><option value="">Choose one...</option>{TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
                </FormField>
                <FormField id={`work-${work.key}-title`} label="Title of your submission *">
                  <input className="portal-input" value={work.title} onChange={(event) => updateWork(work.key, "title", event.target.value)} onBlur={(event) => updateWork(work.key, "title", sanitizeSingleLine(event.target.value))} />
                </FormField>
                <FormField label="Year (if relevant)">
                  <input className="portal-input" value={work.year} onChange={(event) => updateWork(work.key, "year", event.target.value)} onBlur={(event) => updateWork(work.key, "year", sanitizeSingleLine(event.target.value))} />
                </FormField>
                <FormField id={`work-${work.key}-language`} label="Language(s) of submission *">
                  <LanguageSelect value={work.language} onChange={(language) => updateWork(work.key, "language", language)} />
                </FormField>
              </div>
              <FormField id={`work-${work.key}-description`} label="Description of your submission, including materials (if relevant) *" help="Use 10 to 10,000 characters.">
                <textarea className="portal-textarea" value={work.description} onChange={(event) => updateWork(work.key, "description", event.target.value)} onBlur={(event) => updateWork(work.key, "description", sanitizeMultiline(event.target.value))} />
              </FormField>
              <div className="portal-upload-grid">
                <div className="portal-file-upload-group">
                  <UploadBox id={`work-${work.key}-text-files`} label="Text files" format="Word or PDF; up to 1500 words." accept=".doc,.docx,.pdf" files={work.textFiles} onPick={(files) => appendFilesToWork(work.key, "textFiles", files)} onRemove={(itemIndex) => removeFromWork(work.key, "textFiles", itemIndex)} onClear={() => updateWork(work.key, "textFiles", [])} />
                  <UploadBox id={`work-${work.key}-visual-files`} label="Visual files" format="TIFF at 300 dpi, or PNG." accept=".tif,.tiff,.png" files={work.visualFiles} onPick={(files) => appendFilesToWork(work.key, "visualFiles", files)} onRemove={(itemIndex) => removeFromWork(work.key, "visualFiles", itemIndex)} onClear={() => updateWork(work.key, "visualFiles", [])} />
                  <UploadBox label="Video files" format="MP4, MOV, or WebM." accept=".mp4,.mov,.webm" files={work.videoFiles} onPick={(files) => appendFilesToWork(work.key, "videoFiles", files)} onRemove={(itemIndex) => removeFromWork(work.key, "videoFiles", itemIndex)} onClear={() => updateWork(work.key, "videoFiles", [])} />
                  <p className="portal-help portal-upload-limit">Size: up to 5 GB per file; 10 GB total for all submissions.</p>
                  <p className="portal-help portal-filename-reminder">Filename reminder: <span className="code">Artist-Name_Submission-Title</span></p>
                </div>
                <div className="portal-upload-box portal-link-box">
                  <div className="portal-upload-heading">
                    <span className="portal-label">Links</span>
                    <button type="button" className="smallBtn" disabled={!work.namedLinks.length && !work.linkName && !work.linkUrl} onClick={() => clearNamedLinks(work.key)}>clear links</button>
                  </div>
                  <p className="portal-help portal-upload-format">Please name each link.</p>
                  <p className="portal-help portal-link-access">Please make sure that the RAGE Zine team can access your links.</p>
                  <input id={`work-${work.key}-link-name`} className="portal-input" aria-label="Link name" placeholder="Link name" maxLength={120} value={work.linkName} onChange={(event) => updateWork(work.key, "linkName", event.target.value)} />
                  <input id={`work-${work.key}-link-url`} className="portal-input" type="url" inputMode="url" aria-label="Link URL" placeholder="https://..." value={work.linkUrl} onChange={(event) => updateWork(work.key, "linkUrl", event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addNamedLink(work.key); } }} />
                  <button type="button" className="smallBtn portal-link-add" disabled={!work.linkName.trim() || !work.linkUrl.trim() || work.namedLinks.length >= MAX_OTHER_LINKS} onClick={() => addNamedLink(work.key)}>add link</button>
                  {work.namedLinks.length > 0 && <ul className="portal-filelist">{work.namedLinks.map((link, linkIndex) => <li key={`${link.name}-${linkIndex}`}><span><strong>{link.name}</strong><br />{link.url}</span><button type="button" className="smallBtn" onClick={() => removeFromWork(work.key, "namedLinks", linkIndex)} aria-label={`Remove ${link.name}`}>remove</button></li>)}</ul>}
                </div>
              </div>
              <div className="portal-grid portal-work-footer">
                <div className="portal-publication-group">
                  <FormField id={`work-${work.key}-published`} label="Has this submission been published elsewhere? *">
                    <select className={`portal-input${work.published_elsewhere ? "" : " portal-input-placeholder"}`} value={work.published_elsewhere} onChange={(event) => updateWork(work.key, "published_elsewhere", event.target.value)}><option value="">Choose one...</option><option value="yes">Yes</option><option value="no">No</option></select>
                  </FormField>
                  {work.published_elsewhere === "yes" && <FormField id={`work-${work.key}-published-where`} label="If yes, where? *"><input className="portal-input" value={work.published_where} onChange={(event) => updateWork(work.key, "published_where", event.target.value)} onBlur={(event) => updateWork(work.key, "published_where", sanitizeSingleLine(event.target.value))} /></FormField>}
                  <p className="portal-help portal-restriction">RAGE Zine happily accepts submissions that have been published elsewhere, this is just for our information.</p>
                </div>
                <FormField label="Anything else we need to know?">
                  <textarea className="portal-textarea" value={work.anything_else} onChange={(event) => updateWork(work.key, "anything_else", event.target.value)} onBlur={(event) => updateWork(work.key, "anything_else", sanitizeMultiline(event.target.value))} />
                </FormField>
              </div>
            </article>
          ))}
          {works.length < MAX_WORKS && <button type="button" className="smallBtn portal-work-add" onClick={() => setWorks((current) => [...current, newWork(nextWorkKey.current++)])}><svg className="portal-work-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="M4 10h12M10 4v12" /></svg>add submission</button>}
        </section>

        <div className="portal-actions">
          <button className="portal-btn" type="submit" disabled={submitting}>
            {submitting ? uploadPhase === "processing" ? "saving submission..." : uploadProgress === null ? "submitting..." : `uploading ${uploadProgress}%...` : "submit"}
          </button>
          {submitting && uploadPhase === "processing" && <p role="status">Files uploaded. We are saving your submission. Keep this page open.</p>}
        </div>
      </form>

      {popup.open && (
        <div className="portal-modal-backdrop" onClick={() => setPopup((current) => ({ ...current, open: false }))}>
          <div className={`portal-modal portal-modal-${popup.kind}`} role="dialog" aria-modal="true" aria-labelledby="submission-modal-title" onClick={(event) => event.stopPropagation()}>
            <button type="button" className="portal-modal-close" onClick={() => setPopup((current) => ({ ...current, open: false }))} aria-label="Close message">x</button>
            <h3 id="submission-modal-title">{popup.title}</h3>
            <div className="portal-modal-body">{popup.messages.map((message, index) => <p key={`${message}-${index}`}>{message}</p>)}</div>
            <button type="button" className="portal-btn" onClick={() => setPopup((current) => ({ ...current, open: false }))}>close</button>
          </div>
        </div>
      )}
    </>
  );
}
