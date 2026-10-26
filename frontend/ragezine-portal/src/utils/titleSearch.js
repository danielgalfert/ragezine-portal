function normalize(value) {
  return String(value || "")
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLocaleLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function editDistanceWithinLimit(left, right, limit) {
  if (Math.abs(left.length - right.length) > limit) {
    return limit + 1;
  }

  let previous = Array.from({ length: right.length + 1 }, (_, index) => index);

  for (let row = 1; row <= left.length; row += 1) {
    const current = [row];
    let smallest = current[0];

    for (let column = 1; column <= right.length; column += 1) {
      current[column] = Math.min(
        previous[column] + 1,
        current[column - 1] + 1,
        previous[column - 1] + (left[row - 1] === right[column - 1] ? 0 : 1),
      );
      smallest = Math.min(smallest, current[column]);
    }

    if (smallest > limit) {
      return limit + 1;
    }
    previous = current;
  }

  return previous[right.length];
}

function scoreToken(queryToken, titleToken) {
  if (titleToken === queryToken) return 0;
  if (titleToken.startsWith(queryToken)) return 1;
  if (queryToken.length >= 3 && titleToken.includes(queryToken)) return 2;

  const limit = queryToken.length >= 6 ? 2 : queryToken.length >= 3 ? 1 : 0;
  const distance = editDistanceWithinLimit(queryToken, titleToken, limit);
  return distance <= limit ? 3 + distance : null;
}

function scoreTitle(title, query) {
  const normalizedTitle = normalize(title);
  if (!normalizedTitle) return null;
  if (normalizedTitle === query) return 0;
  if (normalizedTitle.startsWith(query)) return 1;
  if (normalizedTitle.includes(query)) return 2;

  const titleTokens = normalizedTitle.split(" ");
  const queryTokens = query.split(" ");
  let score = 3;

  for (const queryToken of queryTokens) {
    const matches = titleTokens
      .map((titleToken) => scoreToken(queryToken, titleToken))
      .filter((value) => value !== null);
    if (matches.length === 0) return null;
    score += Math.min(...matches);
  }

  return score;
}

export function searchSubmissionsByTitle(submissions, input) {
  const query = normalize(input);
  if (!query) return submissions;

  return submissions
    .map((submission, index) => ({
      submission,
      index,
      score: scoreTitle(submission.title, query),
    }))
    .filter((item) => item.score !== null)
    .sort((left, right) => left.score - right.score || left.index - right.index)
    .map((item) => item.submission);
}
