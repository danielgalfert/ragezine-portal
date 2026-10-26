import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getSession, logoutUser } from "../services/authService";
import {
  addSubmissionComment,
  getSubmissionById,
  getSubmissionComments,
  getSubmissionPreviewText,
  getSubmissionPreviewUrl,
} from "../services/submissionService";
import "../styles/dashboard.css";
import "../styles/nav.css";
import "../styles/description.css";
import "../styles/form.css";
import "../styles/submissionDetails.css";

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function formatFileSize(bytes) {
  if (!bytes) return "size unknown";
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KiB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MiB`;
}

function Detail({ label, value }) {
  return (
    <div className="details-field">
      <dt>{label}</dt>
      <dd>{value || "—"}</dd>
    </div>
  );
}

function Preview({ document }) {
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const url = getSubmissionPreviewUrl(document?.preview_url);

  useEffect(() => {
    if (!document || !["text", "document"].includes(document.preview_kind)) return;
    let active = true;
    getSubmissionPreviewText(document.preview_url)
      .then((content) => { if (active) setText(content); })
      .catch(() => { if (active) setError("This file could not be previewed. Download it to view it."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [document]);

  if (!document) return <p>Select a file to preview.</p>;
  if (!url || !document.preview_kind) return <p>A preview is not available for this file. Download it to view it.</p>;
  if (document.preview_kind === "pdf") return <iframe className="details-pdf" src={url} title={`Preview of ${document.original_filename}`} />;
  if (document.preview_kind === "image") return <img className="details-image" src={url} alt={`Preview of ${document.original_filename}`} />;
  if (document.preview_kind === "video") return <video className="details-video" key={url} controls preload="metadata" src={url}>Your browser cannot play this video. Download it to view it.</video>;
  if (error) return <p role="alert">{error}</p>;
  if (loading || !text) return <p>Loading preview...</p>;
  return <pre className="details-text">{text}</pre>;
}

export default function SubmissionDetailsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [checkingSession, setCheckingSession] = useState(true);
  const [submission, setSubmission] = useState(null);
  const [comments, setComments] = useState([]);
  const [selectedFileId, setSelectedFileId] = useState(null);
  const [error, setError] = useState("");
  const [commentError, setCommentError] = useState("");
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const session = await getSession();
        if (!session?.authenticated || !session?.user?.is_staff) {
          navigate("/login", { replace: true });
          return;
        }
        const [details, notes] = await Promise.all([getSubmissionById(id), getSubmissionComments(id)]);
        if (!active) return;
        setSubmission(details);
        setComments(Array.isArray(notes) ? notes : notes.results || []);
        setSelectedFileId(details.documents?.[0]?.id ?? null);
      } catch (err) {
        if (active) setError(err?.response?.status === 404 ? "Submission not found." : "Could not load this submission.");
      } finally {
        if (active) setCheckingSession(false);
      }
    }
    load();
    return () => { active = false; };
  }, [id, navigate]);

  async function onLogout() {
    try { await logoutUser(); }
    finally { navigate("/login", { replace: true }); }
  }

  async function onCommentSubmit(event) {
    event.preventDefault();
    if (!draft.trim() || saving) return;
    setSaving(true);
    setCommentError("");
    try {
      const comment = await addSubmissionComment(id, draft.trim());
      setComments((current) => [...current, comment]);
      setDraft("");
    } catch (err) {
      setCommentError(err?.response?.data?.body?.[0] || "Could not save this comment.");
    } finally {
      setSaving(false);
    }
  }

  const files = submission?.documents || [];
  const selectedFile = files.find((file) => file.id === selectedFileId) || null;

  return (
    <main>
      <div className="portal-page dashboard-page details-page">
        <nav className="details-nav">
          <ul>
            <li><Link to="/dashboard">← all submissions</Link></li>
            <li><button type="button" className="menu-button" onClick={onLogout}>log out</button></li>
          </ul>
        </nav>
        <div className="details-shell">
          {checkingSession && <p>Loading submission...</p>}
          {!checkingSession && error && <div className="details-card" role="alert"><p>{error}</p><Link to="/dashboard">Back to submissions</Link></div>}
          {!checkingSession && submission && (
            <>
              <header className="details-heading">
                <p>submission #{submission.id}</p>
                <h1>{submission.title}</h1>
                <p>by {submission.artist_name}</p>
              </header>

              <section className="details-card" aria-labelledby="details-heading">
                <h2 id="details-heading">Submission details</h2>
                <dl className="details-grid">
                  <Detail label="Artist" value={submission.artist_name} />
                  <Detail label="Pronouns" value={submission.pronouns} />
                  <Detail label="Email" value={<a href={`mailto:${submission.email}`}>{submission.email}</a>} />
                  <Detail label="Type" value={submission.submission_type?.replaceAll("_", " ")} />
                  <Detail label="Volume" value={submission.volume} />
                  <Detail label="Year" value={submission.year} />
                  <Detail label="Language" value={submission.language} />
                  <Detail label="Country of origin" value={submission.country_origin_name || submission.country_origin} />
                  <Detail label="Residence" value={submission.countries_residence_names?.join(", ")} />
                  <Detail label="Submitted" value={formatDate(submission.created_at)} />
                  <Detail label="Updated" value={formatDate(submission.updated_at)} />
                  <Detail label="Socials" value={submission.socials} />
                  <Detail label="English translation" value={submission.allow_translation ? "Allowed" : "Not allowed"} />
                  <Detail label="Description" value={submission.description} />
                  <Detail label="Short bio" value={submission.short_bio} />
                </dl>
              </section>

              <section className="details-card" aria-labelledby="files-heading">
                <h2 id="files-heading">Files ({files.length})</h2>
                {files.length === 0 ? <p>No files are attached.</p> : (
                  <div className="details-files-layout">
                    <div className="details-file-list" aria-label="Attached files">
                      {files.map((file) => (
                        <button
                          key={file.id}
                          type="button"
                          className={`details-file-button${file.id === selectedFileId ? " is-selected" : ""}`}
                          onClick={() => setSelectedFileId(file.id)}
                          aria-pressed={file.id === selectedFileId}
                        >
                          <strong>{file.original_filename || `File ${file.id}`}</strong>
                          <span>{file.document_type} · {formatFileSize(file.size)}</span>
                        </button>
                      ))}
                    </div>
                    <div className="details-preview-panel">
                      <div className="details-preview-bar">
                        <strong>{selectedFile?.original_filename || "Preview"}</strong>
                        {selectedFile && <a href={selectedFile.download_url}>Download original ↓</a>}
                      </div>
                      <div className="details-preview"><Preview key={selectedFile?.id} document={selectedFile} /></div>
                    </div>
                  </div>
                )}
              </section>

              <section className="details-card details-comments" aria-labelledby="comments-heading">
                <h2 id="comments-heading">Staff comments</h2>
                <p>Comments are visible to staff only.</p>
                <form onSubmit={onCommentSubmit}>
                  <label htmlFor="staff-comment">Add a comment</label>
                  <textarea id="staff-comment" value={draft} maxLength={4000} onChange={(event) => setDraft(event.target.value)} rows={4} required />
                  {commentError && <p role="alert" className="details-error">{commentError}</p>}
                  <button type="submit" className="smallBtn" disabled={saving || !draft.trim()}>{saving ? "saving..." : "post comment"}</button>
                </form>
                <div className="details-comment-list">
                  {comments.length === 0 && <p>No comments yet.</p>}
                  {comments.map((comment) => (
                    <article key={comment.id} className="details-comment">
                      <div><strong>{comment.author_name}</strong><time dateTime={comment.created_at}>{formatDate(comment.created_at)}</time></div>
                      <p>{comment.body}</p>
                    </article>
                  ))}
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
