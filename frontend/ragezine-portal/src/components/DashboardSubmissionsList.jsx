import { useEffect, useMemo, useState } from "react";

import { getSubmissions } from "../services/submissionService";
import { downloadSubmissionArchive } from "../services/downloadService";

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
  const [page, setPage] = useState(1);

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

  const summary = useMemo(() => {
    const byType = submissions.reduce((acc, submission) => {
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
  }, [submissions]);

  const totalPages = Math.max(1, Math.ceil(submissions.length / PAGE_SIZE));
  const visibleSubmissions = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return submissions.slice(start, start + PAGE_SIZE);
  }, [page, submissions]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  function handleSubmissionDownload(submissionId) {
    downloadSubmissionArchive(submissionId);
  }

  return (
    <section className="dashboard-section" id="submissions-list">
      <div className="dashboard-shell">
        <div className="dashboard-header">
          <div className="dashboard-summary">
            <div className="dashboard-summary-card">
              <span className="dashboard-summary-label">total</span>
              <strong>{submissions.length}</strong>
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

        {!loading && !error && submissions.length === 0 && (
          <div className="dashboard-panel">
            <p>No submissions yet.</p>
          </div>
        )}

        {!loading && !error && submissions.length > 0 && (
          <>
            <div className="dashboard-toolbar">
              <p className="dashboard-range">
                Showing {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, submissions.length)} of {submissions.length}
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
                  <div className="dashboard-row-action">
                    <button
                      type="button"
                      className="smallBtn dashboard-download-button"
                      onClick={() => handleSubmissionDownload(submission.id)}
                      aria-label={`Download submission ${submission.id}`}
                      title={`Download submission ${submission.id}`}
                    >
                      <DownloadIcon />
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
