import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { downloadSubmissionArchive, downloadWorkArchive } from "../services/downloadService";
import { deleteSubmission, getSubmissions } from "../services/submissionService";
import { matchingWorks, searchSubmissionsByKeyword, sortSubmissions } from "../utils/submissionSearch";

const PAGE_SIZE = 20;

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

function getOriginLabel(submission) {
  const origins = submission.artist?.country_origin_names || submission.country_origin_names || [];
  return origins.length ? origins.join(", ") : submission.country_origin_name || "Unknown";
}

function getResidenceLabel(submission) {
  const residences = submission.artist?.countries_residence_names || submission.countries_residence_names || [];
  return residences.length ? residences.join(", ") : "Unknown";
}

function SubmissionGroup({ submission, works, onDelete, deletingId, canDeleteSubmissions }) {
  const artistName = submission.artist?.artist_name || submission.artist_name;
  const counts = submission.vote_counts || {};

  return (
    <article className="dashboard-artist-group">
      <header className="dashboard-artist-header">
        <div className="dashboard-artist-info">
          <div className="dashboard-artist-heading">
            <h3>{artistName}</h3>
            <span>#{submission.id}</span>
          </div>
          <p className="dashboard-artist-meta">
            <span>{submission.artist?.email || submission.email || "No email"}</span>
            <span><strong>Origin:</strong> {getOriginLabel(submission)}</span>
            <span><strong>Residence:</strong> {getResidenceLabel(submission)}</span>
          </p>
          {submission.tags?.length > 0 && (
            <div className="dashboard-tag-list" aria-label="Tags">
              {submission.tags.map((tag) => <span key={tag.id}>{tag.name}</span>)}
            </div>
          )}
        </div>
        <div className="dashboard-artist-summary">
          <span>submitted {formatDate(submission.created_at)}</span>
          <div className="dashboard-row-votes" aria-label={`Votes: ${counts.yes || 0} yes, ${counts.no || 0} no, ${counts.see_comment || 0} see comment`}>
            <span>Yes {counts.yes || 0}</span>
            <span>No {counts.no || 0}</span>
            <span>See comment {counts.see_comment || 0}</span>
          </div>
        </div>
        <div className="dashboard-row-action">
          <Link className="smallBtn dashboard-details-button" to={`/dashboard/submissions/${submission.id}`} aria-label={`View details for submission ${submission.id}`}>details</Link>
          {canDeleteSubmissions && <button
            type="button"
            className="smallBtn dashboard-delete-button"
            onClick={() => onDelete(submission)}
            disabled={deletingId === submission.id}
            aria-label={`Delete submission ${submission.id}`}
          >
            {deletingId === submission.id ? "deleting..." : "delete"}
          </button>}
        </div>
      </header>
      <div className="dashboard-block-list" aria-label={`Pieces by ${artistName}`}>
        {works.map((work, index) => (
          <div className="dashboard-block-row" key={work.id || `legacy-${submission.id}-${index}`}>
            <strong className="dashboard-block-title">{work.title}</strong>
            {work.description && <p className="dashboard-block-description">{work.description}</p>}
            <span className="dashboard-block-type">{(work.submission_type || "uncategorized").replaceAll("_", " ")}</span>
            <button
              type="button"
              className="smallBtn dashboard-block-download"
              onClick={() => work.id ? downloadWorkArchive(work.id) : downloadSubmissionArchive(submission.id)}
              aria-label={`Download ${work.title} by ${artistName}`}
            >
              ↓
            </button>
          </div>
        ))}
      </div>
    </article>
  );
}

export default function DashboardSubmissionsList({ canDeleteSubmissions = false }) {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [deletingId, setDeletingId] = useState(null);
  const [page, setPage] = useState(1);
  const [keywordQuery, setKeywordQuery] = useState("");
  const [sortCategory, setSortCategory] = useState("date");
  const [sortDirection, setSortDirection] = useState("desc");
  const [selectedTagId, setSelectedTagId] = useState("");
  const [selectedType, setSelectedType] = useState("");

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

  const searchMatches = useMemo(() => {
    const tagged = selectedTagId
      ? submissions.filter((submission) => submission.tags?.some((tag) => String(tag.id) === selectedTagId))
      : submissions;
    return searchSubmissionsByKeyword(tagged, keywordQuery);
  }, [submissions, keywordQuery, selectedTagId]);

  const filteredSubmissions = useMemo(
    () => sortSubmissions(selectedType
      ? searchMatches.filter((submission) => matchingWorks(submission, keywordQuery, selectedType).length > 0)
      : searchMatches, `${sortCategory}_${sortDirection}`),
    [searchMatches, selectedType, sortCategory, sortDirection, keywordQuery],
  );

  const summary = useMemo(() => {
    const byType = searchMatches.reduce((acc, submission) => {
      matchingWorks(submission, keywordQuery).forEach((work) => {
        const key = work.submission_type || "uncategorized";
        acc[key] = (acc[key] || 0) + 1;
      });
      return acc;
    }, {});

    const typeOrder = ["poetry", "visual_art", "short_form_writing", "long_form_writing", "other", "uncategorized"];
    return [...new Set(submissions.flatMap((submission) => (submission.works?.length ? submission.works : [submission]).map((work) => work.submission_type || "uncategorized")))]
      .sort((a, b) => typeOrder.indexOf(a) - typeOrder.indexOf(b))
      .map((type) => ({
        type,
        label: type.replaceAll("_", " "),
        count: byType[type] || 0,
      }));
  }, [submissions, searchMatches, keywordQuery]);

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

  function handleKeywordQueryChange(event) {
    setKeywordQuery(event.target.value);
    setPage(1);
  }

  async function handleSubmissionDelete(submission) {
    if (!window.confirm(`Delete submission #${submission.id} by ${submission.artist?.artist_name || submission.artist_name}? This also removes its uploaded files.`)) {
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
            <label htmlFor="dashboard-keyword-search">search artist, title, or description</label>
            <div className="dashboard-search-controls">
              <input
                id="dashboard-keyword-search"
                type="search"
                value={keywordQuery}
                onChange={handleKeywordQueryChange}
                placeholder="Search artist names, titles, or descriptions"
                autoComplete="off"
              />
              {keywordQuery && (
                <button
                  type="button"
                  className="smallBtn"
                  onClick={() => {
                    setKeywordQuery("");
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
          <div className="dashboard-order-controls">
            <div className="dashboard-sort-filter">
              <label htmlFor="dashboard-sort-category">order by</label>
              <select id="dashboard-sort-category" value={sortCategory} onChange={(event) => { setSortCategory(event.target.value); setPage(1); }}>
                <option value="date">submission date</option>
                <option value="artist">artist name</option>
              </select>
            </div>
            <div className="dashboard-direction-filter">
              <label htmlFor="dashboard-sort-direction">direction</label>
              <select id="dashboard-sort-direction" value={sortDirection} onChange={(event) => { setSortDirection(event.target.value); setPage(1); }}>
                <option value="desc">{sortCategory === "date" ? "newest first" : "Z to A"}</option>
                <option value="asc">{sortCategory === "date" ? "oldest first" : "A to Z"}</option>
              </select>
            </div>
          </div>
        </div>
        <div className="dashboard-header">
          <div className="dashboard-summary">
            <div className="dashboard-summary-card">
              <span className="dashboard-summary-label">{keywordQuery.trim() || selectedTagId ? "results" : "total"}</span>
              <strong>{searchMatches.length}</strong>
            </div>
            {summary.map((item) => (
              <button
                key={item.type}
                type="button"
                className={`dashboard-summary-card dashboard-summary-button${selectedType === item.type ? " is-active" : ""}`}
                aria-pressed={selectedType === item.type}
                onClick={() => {
                  setSelectedType((current) => current === item.type ? "" : item.type);
                  setPage(1);
                }}
              >
                <span className="dashboard-summary-label">{item.label}</span>
                <strong>{item.count}</strong>
              </button>
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
                {(keywordQuery.trim() || selectedTagId || selectedType) && ` results (${submissions.length} total)`}
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
              {visibleSubmissions.map((submission) => (
                <SubmissionGroup
                  key={submission.id}
                  submission={submission}
                  works={matchingWorks(submission, keywordQuery, selectedType)}
                  onDelete={handleSubmissionDelete}
                  deletingId={deletingId}
                  canDeleteSubmissions={canDeleteSubmissions}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
