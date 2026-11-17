import { useRef, useState } from "react";

import CountrySelect from "./CountrySelect";
import FormField from "./FormField";
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

const TYPES = [
  ["poetry", "Poetry"],
  ["visual_art", "Visual art"],
  ["short_form_writing", "Short form writing"],
  ["long_form_writing", "Long form writing"],
  ["other", "Other"],
];
const LANGUAGES = ["English", "Spanish", "Danish", "French", "German", "Italian", "Portuguese", "Other"];

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
    language: "English", published_elsewhere: "", published_where: "",
    anything_else: "", textFiles: [], visualFiles: [], videoFiles: [],
    namedLinks: [], linkName: "", linkUrl: "",
  };
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

function UploadBox({ label, format, accept, files, onPick, onRemove, onClear }) {
  const fileInputRef = useRef(null);
  return (
    <div className="portal-upload-box">
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
          onPick(Array.from(event.target.files || []));
          event.target.value = "";
        }}
      />
      <button type="button" className="portal-file-picker" aria-label={`Choose ${label.toLowerCase()}`} onClick={() => fileInputRef.current?.click()}>
        choose files
      </button>
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
  const nextWorkKey = useRef(1);
  const [artist, setArtist] = useState(emptyArtist);
  const [works, setWorks] = useState([newWork(0)]);
  const [pronounInput, setPronounInput] = useState("");
  const [socialInput, setSocialInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [popup, setPopup] = useState({ open: false, kind: "success", title: "", messages: [] });

  function updateArtist(field, value) {
    setArtist((current) => ({ ...current, [field]: value }));
  }

  function updateWork(key, field, value) {
    setWorks((current) => current.map((work) => work.key === key ? { ...work, [field]: value } : work));
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
    setArtist(emptyArtist);
    setWorks([newWork(nextWorkKey.current++)]);
    setPronounInput("");
    setSocialInput("");
  }

  function validate() {
    const pronouns = addUnique(artist.pronouns, pronounInput);
    if (sanitizeSingleLine(artist.artist_name).length < 2) return "Enter artist name(s) of at least 2 characters.";
    if (!pronouns.length || pronouns.length > MAX_PRONOUNS) return "Add your pronouns or choose a suggestion.";
    if (!isLikelyEmail(artist.email)) return "Enter a valid email address.";
    if (!artist.country_origin.length || !artist.countries_residence.length) return "Select countries of origin and residence.";
    if (sanitizeMultiline(artist.short_bio).length < 10) return "Enter a short bio of at least 10 characters.";
    if (!artist.submitted_before || !artist.featured_before) return "Answer both RAGE Zine history questions.";
    if (works.length < 1 || works.length > MAX_WORKS) return `Add 1 to ${MAX_WORKS} submissions.`;

    let totalBytes = 0;
    let totalFiles = 0;
    for (const [index, work] of works.entries()) {
      const prefix = `Submission ${index + 1}: `;
      if (!work.submission_type) return `${prefix}choose a submission type.`;
      if (sanitizeSingleLine(work.title).length < 3) return `${prefix}enter a title of at least 3 characters.`;
      if (sanitizeMultiline(work.description).length < 10) return `${prefix}enter a description of at least 10 characters.`;
      if (!work.published_elsewhere) return `${prefix}answer the publication question.`;
      if (work.published_elsewhere === "yes" && !sanitizeMultiline(work.published_where)) return `${prefix}tell us where it was published.`;
      const files = [...work.textFiles, ...work.visualFiles, ...work.videoFiles];
      totalFiles += files.length;
      if (Boolean(work.linkName.trim()) !== Boolean(work.linkUrl.trim())) return `${prefix}enter both a link name and URL.`;
      const links = collectedLinks(work);
      if (!files.length && !links.length) return `${prefix}add a file or link.`;
      if (work.textFiles.length > MAX_TEXT) return `${prefix}too many text files.`;
      if (work.visualFiles.length + work.videoFiles.length > MAX_VISUAL_VIDEO) return `${prefix}too many visual or video files.`;
      if (links.length > MAX_OTHER_LINKS) return `${prefix}too many links.`;
      for (const link of links) {
        if (!link.name || link.name.length > 120) return `${prefix}give each link a name of at most 120 characters.`;
        try {
          if (new URL(link.url).protocol !== "https:") return `${prefix}use HTTPS links.`;
        } catch {
          return `${prefix}enter complete HTTPS links.`;
        }
      }
      for (const file of files) {
        if (file.size > MAX_FILE_BYTES) return `${prefix}${file.name} exceeds 5 GiB.`;
        totalBytes += file.size;
      }
    }
    if (totalBytes > MAX_TOTAL_BYTES) return "Files exceed 10 GiB in total.";
    if (totalFiles > MAX_FILES) return "Add at most 60 files across all submissions.";
    return "";
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
      language: sanitizeSingleLine(work.language),
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
      setPopup({ open: true, kind: "error", title: "Submission error", messages: [error] });
      return;
    }
    setSubmitting(true);
    setUploadProgress(null);
    try {
      await createSubmissionBatch(buildPayload(), (progress) => {
        if (progress.total) setUploadProgress(Math.min(100, Math.round(progress.loaded / progress.total * 100)));
      });
      setPopup({ open: true, kind: "success", title: "Submission successful", messages: ["Your submissions have been received."] });
      clearAfterSuccess();
    } catch (err) {
      setPopup({
        open: true, kind: "error", title: "Submission error",
        messages: errorMessages(err?.response?.data || err?.message),
      });
    } finally {
      setSubmitting(false);
      setUploadProgress(null);
    }
  }

  return (
    <>
      <form className="portal-form" onSubmit={submit}>
        <section className="portal-form-block" aria-labelledby="artist-info-heading">
          <h3 id="artist-info-heading">Artist information</h3>
          <div className="portal-grid portal-artist-grid">
            <FormField label="Artist name(s) *">
              <input className="portal-input" value={artist.artist_name} onChange={(event) => updateArtist("artist_name", event.target.value)} onBlur={(event) => updateArtist("artist_name", sanitizeSingleLine(event.target.value))} />
            </FormField>
            <FormField label="Email *">
              <input className="portal-input" type="email" autoComplete="email" value={artist.email} onChange={(event) => updateArtist("email", event.target.value)} onBlur={(event) => updateArtist("email", sanitizeSingleLine(event.target.value))} />
            </FormField>
            <FormField label="Countries of origin *">
              <CountrySelect value={artist.country_origin} onChange={(countries) => updateArtist("country_origin", countries)} isMulti />
            </FormField>
            <FormField label="Countries of residence *">
              <CountrySelect value={artist.countries_residence} onChange={(countries) => updateArtist("countries_residence", countries)} isMulti />
            </FormField>
            <FormField label="Have you submitted to RAGE Zine before? *">
              <select className="portal-input" value={artist.submitted_before} onChange={(event) => updateArtist("submitted_before", event.target.value)}><option value="">Choose one...</option><option value="yes">Yes</option><option value="no">No</option></select>
            </FormField>
            <FormField label="Have you been featured in RAGE Zine before? *">
              <select className="portal-input" value={artist.featured_before} onChange={(event) => updateArtist("featured_before", event.target.value)}><option value="">Choose one...</option><option value="yes">Yes</option><option value="no">No</option></select>
            </FormField>
          </div>
          <div className="portal-grid portal-artist-identity">
            <FormField label="Pronouns *">
              <div className="portal-inline-entry portal-pronoun-entry">
                <input className="portal-input" value={pronounInput} maxLength={40} placeholder="she/her or your own" aria-label="Add pronouns" onChange={(event) => setPronounInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addPronoun(pronounInput); } }} />
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
            <FormField label="Short bio (2-3 sentences) *">
              <textarea className="portal-textarea" value={artist.short_bio} onChange={(event) => updateArtist("short_bio", event.target.value)} onBlur={(event) => updateArtist("short_bio", sanitizeMultiline(event.target.value))} />
            </FormField>
            <FormField label="Message to the editors">
              <textarea className="portal-textarea" value={artist.message_to_editors} onChange={(event) => updateArtist("message_to_editors", event.target.value)} onBlur={(event) => updateArtist("message_to_editors", sanitizeMultiline(event.target.value))} />
            </FormField>
          </div>
        </section>

        <section className="portal-form-block" aria-labelledby="submission-info-heading">
          <h3 id="submission-info-heading">Submission information</h3>
          <p className="portal-help">Your artist information applies to all pieces.</p>
          {works.map((work, index) => (
            <article className="portal-work-card" key={work.key}>
              {works.length > 1 && <button type="button" className="portal-work-remove" aria-label={`Remove piece ${index + 1}`} onClick={() => setWorks((current) => current.filter((item) => item.key !== work.key))}>−</button>}
              <div className="portal-grid portal-work-core">
                <FormField label="Submission type *">
                  <select className="portal-input" value={work.submission_type} onChange={(event) => updateWork(work.key, "submission_type", event.target.value)}><option value="">Choose one...</option>{TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
                </FormField>
                <FormField label="Title of your work(s) *">
                  <input className="portal-input" value={work.title} onChange={(event) => updateWork(work.key, "title", event.target.value)} onBlur={(event) => updateWork(work.key, "title", sanitizeSingleLine(event.target.value))} />
                </FormField>
                <FormField label="Year (if relevant)">
                  <input className="portal-input" value={work.year} onChange={(event) => updateWork(work.key, "year", event.target.value)} onBlur={(event) => updateWork(work.key, "year", sanitizeSingleLine(event.target.value))} />
                </FormField>
                <FormField label="Language of submission">
                  <select className="portal-input" value={work.language} onChange={(event) => updateWork(work.key, "language", event.target.value)}>{LANGUAGES.map((language) => <option key={language} value={language}>{language}</option>)}</select>
                </FormField>
              </div>
              <FormField label="Description of work(s), including materials if relevant">
                <textarea className="portal-textarea" value={work.description} onChange={(event) => updateWork(work.key, "description", event.target.value)} onBlur={(event) => updateWork(work.key, "description", sanitizeMultiline(event.target.value))} />
              </FormField>
              <div className="portal-upload-grid">
                <UploadBox label="Text files" format="Word (.doc, .docx) or PDF; up to 1500 words" accept=".doc,.docx,.pdf" files={work.textFiles} onPick={(files) => updateWork(work.key, "textFiles", [...work.textFiles, ...files])} onRemove={(itemIndex) => removeFromWork(work.key, "textFiles", itemIndex)} onClear={() => updateWork(work.key, "textFiles", [])} />
                <UploadBox label="Visual files" format="TIFF (.tif, .tiff) at 300 dpi, or PNG (.png)" accept=".tif,.tiff,.png" files={work.visualFiles} onPick={(files) => updateWork(work.key, "visualFiles", [...work.visualFiles, ...files])} onRemove={(itemIndex) => removeFromWork(work.key, "visualFiles", itemIndex)} onClear={() => updateWork(work.key, "visualFiles", [])} />
                <UploadBox label="Video files" format="MP4, MOV, or WebM" accept=".mp4,.mov,.webm" files={work.videoFiles} onPick={(files) => updateWork(work.key, "videoFiles", [...work.videoFiles, ...files])} onRemove={(itemIndex) => removeFromWork(work.key, "videoFiles", itemIndex)} onClear={() => updateWork(work.key, "videoFiles", [])} />
                <div className="portal-upload-box portal-link-box">
                  <div className="portal-upload-heading">
                    <span className="portal-label">Links</span>
                    <button type="button" className="smallBtn" disabled={!work.namedLinks.length && !work.linkName && !work.linkUrl} onClick={() => clearNamedLinks(work.key)}>clear links</button>
                  </div>
                  <p className="portal-help portal-upload-format">Name each link</p>
                  <input className="portal-input" aria-label="Link name" placeholder="Link name" maxLength={120} value={work.linkName} onChange={(event) => updateWork(work.key, "linkName", event.target.value)} />
                  <input className="portal-input" type="url" inputMode="url" aria-label="Link URL" placeholder="https://..." value={work.linkUrl} onChange={(event) => updateWork(work.key, "linkUrl", event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addNamedLink(work.key); } }} />
                  <button type="button" className="smallBtn portal-link-add" disabled={!work.linkName.trim() || !work.linkUrl.trim() || work.namedLinks.length >= MAX_OTHER_LINKS} onClick={() => addNamedLink(work.key)}>add link</button>
                  {work.namedLinks.length > 0 && <ul className="portal-filelist">{work.namedLinks.map((link, linkIndex) => <li key={`${link.name}-${linkIndex}`}><span><strong>{link.name}</strong><br />{link.url}</span><button type="button" className="smallBtn" onClick={() => removeFromWork(work.key, "namedLinks", linkIndex)} aria-label={`Remove ${link.name}`}>remove</button></li>)}</ul>}
                </div>
              </div>
              <p className="portal-help portal-upload-limit">Size: up to 5 GiB per file; 10 GiB total for all pieces.</p>
              <p className="portal-help">Set access so the RAGE Zine team can open your work.</p>
              <div className="portal-grid portal-work-footer">
                <div className="portal-publication-group">
                  <FormField label="Has this piece been published elsewhere? *">
                    <select className="portal-input" value={work.published_elsewhere} onChange={(event) => updateWork(work.key, "published_elsewhere", event.target.value)}><option value="">Choose one...</option><option value="yes">Yes</option><option value="no">No</option></select>
                  </FormField>
                  {work.published_elsewhere === "yes" && <FormField label="If yes, where? *"><input className="portal-input" value={work.published_where} onChange={(event) => updateWork(work.key, "published_where", event.target.value)} onBlur={(event) => updateWork(work.key, "published_where", sanitizeSingleLine(event.target.value))} /></FormField>}
                  <p className="portal-help portal-restriction">RAGE Zine happily accepts submissions that have been published elsewhere, this is just for our information.</p>
                </div>
                <FormField label="Anything else we need to know?">
                  <textarea className="portal-textarea" value={work.anything_else} onChange={(event) => updateWork(work.key, "anything_else", event.target.value)} onBlur={(event) => updateWork(work.key, "anything_else", sanitizeMultiline(event.target.value))} />
                </FormField>
              </div>
              <p className="portal-help">Filename reminder: <span className="code">Artist-Name_Artwork-Title</span></p>
            </article>
          ))}
          {works.length < MAX_WORKS && <button type="button" className="portal-work-add" aria-label="Add another piece" onClick={() => setWorks((current) => [...current, newWork(nextWorkKey.current++)])}>+</button>}
        </section>

        <div className="portal-actions">
          <button className="portal-btn" type="submit" disabled={submitting}>
            {submitting ? uploadProgress === null ? "submitting..." : `uploading ${uploadProgress}%...` : "submit"}
          </button>
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
