import assert from "node:assert/strict";
import test from "node:test";

import { searchSubmissionsByTitle } from "./titleSearch.js";

const submissions = [
  { id: 1, title: "Moonlight Garden" },
  { id: 2, title: "Blue House" },
  { id: 3, title: "MOONLIGHT" },
  { id: 4, title: "Garden of Stars" },
  { id: 5, title: "Mañana" },
];

test("empty search leaves the dashboard order unchanged", () => {
  assert.equal(searchSubmissionsByTitle(submissions, "  "), submissions);
});

test("exact titles rank before prefixes and other matches", () => {
  assert.deepEqual(
    searchSubmissionsByTitle(submissions, "moonlight").map(({ id }) => id),
    [3, 1],
  );
});

test("search matches title words without regard to case or accents", () => {
  assert.deepEqual(searchSubmissionsByTitle(submissions, "garDEN").map(({ id }) => id), [4, 1]);
  assert.deepEqual(searchSubmissionsByTitle(submissions, "manana").map(({ id }) => id), [5]);
});

test("search includes close spelling matches for each title word", () => {
  assert.deepEqual(searchSubmissionsByTitle(submissions, "blue hose").map(({ id }) => id), [2]);
  assert.deepEqual(searchSubmissionsByTitle(submissions, "moomlight").map(({ id }) => id), [1, 3]);
});

test("short queries do not return unrelated fuzzy matches", () => {
  assert.deepEqual(searchSubmissionsByTitle(submissions, "b").map(({ id }) => id), [2]);
  assert.deepEqual(searchSubmissionsByTitle(submissions, "sunset"), []);
});
