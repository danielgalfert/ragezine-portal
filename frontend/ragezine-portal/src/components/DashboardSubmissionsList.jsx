import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { deleteSubmission, getSubmissions } from "../services/submissionService";
import { downloadSubmissionArchive } from "../services/downloadService";
import { searchSubmissionsByTitle } from "../utils/titleSearch";

const PAGE_SIZE = 20;

function DownloadIcon() {
  return (
    <svg
      aria-hidden="true"
      className="dashboard-download-icon"
      viewBox="0 -960 960 960"
      fill="currentColor"
    >
      <path d="M480-320 280-520l56-58 104 104v-326h80v326l104-104 56 58-200 200ZM200-160q-33 0-56.5-23.5T120-240v-120h80v120h560v-120h80v120q0 33-23.5 56.5T760-160H200Z" />
    </svg>
  );
}

function formatDate(value) {
  if (!value) {
    return "Unknown";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "numeric",
    day: "numeric",
  }).format(date);
}

function getResidenceLabel(submission) {
  const residences = submission.countries_residence_names || [];
  if (!residences.length) {
    return submission.country_origin || "Unknown";
  }

  return residences.join(", ");
}

export default function DashboardSubmissionsList() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [deletingId, setDeletingId] = useState(null);
  const [page, setPage] = useState(1);
  const [titleQuery, setTitleQuery] = useState("");
  const [selectedTagId, setSelectedTagId] = useState("");

  useEffect(() => {
    let active = true;

    async function loadSubmissions() {
      try {
        const data = await getSubmissions();
        if (!active) {
          return;
        }
        setSubmissions(Array.isArray(data) ? data : data.results || []);
      } catch (err) {
        if (!active) {
          return;
        }
        setError(err?.response?.data?.detail || err?.message || "Failed to load submissions.");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadSubmissions();

    return () => {
      active = false;
    };
  }, []);

  const availableTags = useMemo(() => {
    const tags = new Map();
    submissions.forEach((submission) => {
      submission.tags?.forEach((tag) => tags.set(tag.id, tag));
    });
    return [...tags.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [submissions]);

  const filteredSubmissions = useMemo(() => {
    const tagged = selectedTagId
      ? submissions.filter((submission) => submission.tags?.some((tag) => String(tag.id) === selectedTagId))
      : submissions;
    return searchSubmissionsByTitle(tagged, titleQuery);
  }, [submissions, titleQuery, selectedTagId]);

  const summary = useMemo(() => {
    const byType = filteredSubmissions.reduce((acc, submission) => {
      const key = submission.submission_type || "other";
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});

    return Object.entries(byType)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([type, count]) => ({
        type: type.replaceAll("_", " "),
        count,
      }));
  }, [filteredSubmissions]);

  const totalPages = Math.max(1, Math.ceil(filteredSubmissions.length / PAGE_SIZE));
  const visibleSubmissions = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filteredSubmissions.slice(start, start + PAGE_SIZE);
  }, [page, filteredSubmissions]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  function handleSubmissionDownload(submissionId) {
    downloadSubmissionArchive(submissionId);
  }

  function handleTitleQueryChange(event) {
    setTitleQuery(event.target.value);
    setPage(1);
  }

  async function handleSubmissionDelete(submission) {
    if (!window.confirm(`Delete submission #${submission.id} by ${submission.artist_name}? This also removes its uploaded files.`)) {
      return;
    }

    setDeleteError("");
    setDeletingId(submission.id);
    try {
      await deleteSubmission(submission.id);
      setSubmissions((current) => current.filter((item) => item.id !== submission.id));
    } catch (err) {
      setDeleteError(err?.response?.data?.detail || err?.message || "Failed to delete submission.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="dashboard-section" id="submissions-list">
      <div className="dashboard-shell">
        <div className="dashboard-filters">
          <div className="dashboard-search">
            <label htmlFor="dashboard-title-search">search by title</label>
            <div className="dashboard-search-controls">
              <input
                id="dashboard-title-search"
                type="search"
                value={titleQuery}
                onChange={handleTitleQueryChange}
                placeholder="Find a submission title"
                autoComplete="off"
              />
              {titleQuery && (
                <button
                  type="button"
                  className="smallBtn"
                  onClick={() => {
                    setTitleQuery("");
                    setPage(1);
                  }}
                >
                  clear
                </button>
              )}
            </div>
          </div>
          <div className="dashboard-tag-filter">
            <label htmlFor="dashboard-tag-filter">filter by tag</label>
            <select
              id="dashboard-tag-filter"
              value={selectedTagId}
              onChange={(event) => {
                setSelectedTagId(event.target.value);
                setPage(1);
              }}
            >
              <option value="">all tags</option>
              {availableTags.map((tag) => <option key={tag.id} value={tag.id}>{tag.name}</option>)}
            </select>
          </div>
        </div>
        <div className="dashboard-header">
          <div className="dashboard-summary">
            <div className="dashboard-summary-card">
              <span className="dashboard-summary-label">{titleQuery.trim() || selectedTagId ? "results" : "total"}</span>
              <strong>{filteredSubmissions.length}</strong>
            </div>
            {summary.map((item) => (
              <div key={item.type} className="dashboard-summary-card">
                <span className="dashboard-summary-label">{item.type}</span>
                <strong>{item.count}</strong>
              </div>
            ))}
          </div>
        </div>

        {loading && (
          <div className="dashboard-panel">
            <p>Loading submissions...</p>
          </div>
        )}

        {!loading && error && (
          <div className="dashboard-panel dashboard-panel-error">
            <p>{error}</p>
          </div>
        )}

        {deleteError && (
          <div className="dashboard-panel dashboard-panel-error" role="alert">
            <p>{deleteError}</p>
          </div>
        )}

        {!loading && !error && submissions.length === 0 && (
          <div className="dashboard-panel">
            <p>No submissions yet.</p>
          </div>
        )}

        {!loading && !error && submissions.length > 0 && filteredSubmissions.length === 0 && (
          <div className="dashboard-panel" role="status">
            <p>No submissions match these filters.</p>
          </div>
        )}

        {!loading && !error && filteredSubmissions.length > 0 && (
          <>
            <div className="dashboard-toolbar">
              <p className="dashboard-range" role="status">
                Showing {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, filteredSubmissions.length)} of {filteredSubmissions.length}
                {(titleQuery.trim() || selectedTagId) && ` results (${submissions.length} total)`}
              </p>
              <div className="dashboard-pagination">
                <button
                  type="button"
                  className="smallBtn"
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                  disabled={page === 1}
                >
                  previous
                </button>
                <span className="dashboard-page-indicator">
                  page {page} / {totalPages}
                </span>
                <button
                  type="button"
                  className="smallBtn"
                  onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                  disabled={page === totalPages}
                >
                  next
                </button>
              </div>
            </div>

            <div className="dashboard-list">
              <div className="dashboard-list-head">
                <span>ID</span>
                <span>submission date</span>
                <span>artist</span>
                <span>title and short description</span>
                <span>type</span>
                <span>email</span>
                <span>residence</span>
                <span>votes</span>
                <span></span>
              </div>

              {visibleSubmissions.map((submission) => (
                <article key={submission.id} className="dashboard-row">
                  <div className="dashboard-row-id">{submission.id}</div>
                  <div className="dashboard-row-date">{formatDate(submission.created_at)}</div>
                  <div className="dashboard-row-artist">{submission.artist_name}</div>
                  <div className="dashboard-row-title">
                    <strong>{submission.title}</strong>
                    <p>{submission.description || submission.short_bio || "No description provided."}</p>
                    {submission.tags?.length > 0 && (
                      <div className="dashboard-tag-list" aria-label="Tags">
                        {submission.tags.map((tag) => <span key={tag.id}>{tag.name}</span>)}
                      </div>
                    )}
                    {submission.documents?.length > 0 && (
                      <div className="dashboard-document-list">
                        {submission.documents.map((document) => (
                          <a key={document.id} href={document.download_url} title={`Download ${document.original_filename}`}>
                            {document.original_filename || `Document ${document.id}`}
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="dashboard-row-type">
                    {(submission.submission_type || "other").replaceAll("_", " ")}
                  </div>
                  <div className="dashboard-row-email">{submission.email || "Missing"}</div>
                  <div className="dashboard-row-location">{getResidenceLabel(submission)}</div>
                  <div className="dashboard-row-votes" aria-label={`Votes: ${submission.vote_counts?.yes || 0} yes, ${submission.vote_counts?.no || 0} no, ${submission.vote_counts?.see_comment || 0} see comment`}>
                    <span>Yes {submission.vote_counts?.yes || 0}</span>
                    <span>No {submission.vote_counts?.no || 0}</span>
                    <span>See comment {submission.vote_counts?.see_comment || 0}</span>
                  </div>
                  <div className="dashboard-row-action">
                    <Link
                      className="smallBtn dashboard-details-button"
                      to={`/dashboard/submissions/${submission.id}`}
                      aria-label={`View details for submission ${submission.id}`}
                    >
                      details
                    </Link>
                    <button
                      type="button"
                      className="smallBtn dashboard-download-button"
                      onClick={() => handleSubmissionDownload(submission.id)}
                      aria-label={`Download submission ${submission.id}`}
                      title={`Download submission ${submission.id}`}
                    >
                      <DownloadIcon />
                    </button>
                    <button
                      type="button"
                      className="smallBtn dashboard-delete-button"
                      onClick={() => handleSubmissionDelete(submission)}
                      disabled={deletingId === submission.id}
                      aria-label={`Delete submission ${submission.id}`}
                      title={`Delete submission ${submission.id}`}
                    >
                      {deletingId === submission.id ? "deleting..." : "delete"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
