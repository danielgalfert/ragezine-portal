import assert from "node:assert/strict";
import test from "node:test";

import { matchingWorks, searchSubmissionsByKeyword, sortSubmissions } from "./submissionSearch.js";

const submissions = [
  { id: 1, title: "First poem", description: "An archive of feminist anger", artist_name: "Zoë", created_at: "2026-01-01T00:00:00Z", documents: [{ original_filename: "draft.pdf" }] },
  { id: 2, title: "Second piece", artist_name: "Ada", created_at: "2026-02-01T00:00:00Z", staff_search_text: "Discuss blue canvas", links: [{ url: "https://example.com/work" }] },
];

test("keyword search checks artist names, piece titles, and descriptions", () => {
  assert.deepEqual(searchSubmissionsByKeyword(submissions, "draft"), []);
  assert.deepEqual(searchSubmissionsByKeyword(submissions, "blue canvas"), []);
  assert.deepEqual(searchSubmissionsByKeyword(submissions, "example.com"), []);
  assert.deepEqual(searchSubmissionsByKeyword(submissions, "zoe poem").map((item) => item.id), [1]);
  assert.deepEqual(searchSubmissionsByKeyword(submissions, "feminist anger").map((item) => item.id), [1]);
  assert.deepEqual(searchSubmissionsByKeyword(submissions, "second").map((item) => item.id), [2]);
});

test("keyword and type filters show only matching piece rows", () => {
  const grouped = {
    id: 3,
    artist: { artist_name: "Nora Hassan" },
    works: [
      { title: "Dust Practice", submission_type: "poetry" },
      { title: "River Pattern", description: "A painted landscape", submission_type: "visual_art" },
    ],
  };
  assert.deepEqual(matchingWorks(grouped, "Nora", "poetry").map((work) => work.title), ["Dust Practice"]);
  assert.deepEqual(matchingWorks(grouped, "River", "visual_art").map((work) => work.title), ["River Pattern"]);
  assert.deepEqual(matchingWorks(grouped, "River", "poetry"), []);
  assert.deepEqual(matchingWorks(grouped, "painted", "visual_art").map((work) => work.title), ["River Pattern"]);
});

test("dashboard search includes close title spellings without matching unrelated short words", () => {
  const grouped = {
    id: 3,
    artist: { artist_name: "Nora Hassan" },
    works: [
      { title: "Moonlight Garden", submission_type: "poetry" },
      { title: "River Pattern", submission_type: "visual_art" },
    ],
  };
  assert.deepEqual(searchSubmissionsByKeyword([grouped], "moomlight").map((item) => item.id), [3]);
  assert.deepEqual(matchingWorks(grouped, "moomlight", "poetry").map((work) => work.title), ["Moonlight Garden"]);
  assert.deepEqual(matchingWorks(grouped, "moomlight", "visual_art"), []);
  assert.deepEqual(searchSubmissionsByKeyword([grouped], "sunset"), []);
  assert.deepEqual(searchSubmissionsByKeyword([grouped], "x"), []);
});

test("sort supports both directions for date and artist", () => {
  assert.deepEqual(sortSubmissions(submissions, "date_desc").map((item) => item.id), [2, 1]);
  assert.deepEqual(sortSubmissions(submissions, "date_asc").map((item) => item.id), [1, 2]);
  assert.deepEqual(sortSubmissions(submissions, "artist_asc").map((item) => item.id), [2, 1]);
  assert.deepEqual(sortSubmissions(submissions, "artist_desc").map((item) => item.id), [1, 2]);
});

test("work dates do not change submission date order", () => {
  const withLaterWork = [
    { ...submissions[0], works: [{ created_at: "2026-03-01T00:00:00Z" }] },
    submissions[1],
  ];
  assert.deepEqual(sortSubmissions(withLaterWork, "date_desc").map((item) => item.id), [2, 1]);
});
