import { titleMatchesQuery } from "./titleSearch.js";

function fold(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase();
}

export function matchingWorks(submission, query = "", type = "") {
  const artistName = submission.artist?.artist_name || submission.artist_name || "";
  const words = fold(query).trim().split(/\s+/).filter(Boolean);
  const works = submission.works?.length ? submission.works : [submission];
  return works.filter((work) => {
    if (type && (work.submission_type || "uncategorized") !== type) return false;
    const haystack = fold(`${artistName} ${work.title || ""} ${work.description || ""}`);
    return words.every((word) => haystack.includes(word) || titleMatchesQuery(work.title, word));
  });
}

export function searchSubmissionsByKeyword(submissions, query) {
  if (!query.trim()) return submissions;
  return submissions.filter((submission) => matchingWorks(submission, query).length > 0);
}

export function sortSubmissions(submissions, order) {
  const sorted = [...submissions];
  const compareArtist = (a, b) => (a.artist?.artist_name || a.artist_name || "").localeCompare(b.artist?.artist_name || b.artist_name || "", undefined, { sensitivity: "base" });
  const compareDate = (a, b) => Date.parse(a.created_at || 0) - Date.parse(b.created_at || 0);
  sorted.sort((a, b) => {
    const result = order === "artist_asc" ? compareArtist(a, b)
      : order === "artist_desc" ? -compareArtist(a, b)
        : order === "date_asc" ? compareDate(a, b)
          : -compareDate(a, b);
    return result || a.id - b.id;
  });
  return sorted;
}
