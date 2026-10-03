import client from "../api/client";

function getFilenameFromDisposition(disposition) {
  const utf8Match = disposition?.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const quotedMatch = disposition?.match(/filename\s*=\s*"([^"]+)"/i);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }

  const bareMatch = disposition?.match(/filename\s*=\s*([^;]+)/i);
  if (bareMatch?.[1]) {
    return bareMatch[1].trim();
  }

  return "download.zip";
}

function buildDownloadPayload(response, fallbackFilename = "download.zip") {
  return {
    blob: response.data,
    filename: getFilenameFromDisposition(response.headers["content-disposition"]) || fallbackFilename,
  };
}

function startServerDownload(path) {
  const apiBase = new URL(client.defaults.baseURL, window.location.href);
  const anchor = document.createElement("a");
  anchor.href = new URL(path, apiBase).toString();
  anchor.target = "_blank";
  anchor.rel = "noopener noreferrer";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
}

export function downloadCompleteArchive() {
  startServerDownload("downloads/complete/");
}

export async function downloadExcelReview() {
  const response = await client.get("/downloads/excel/", {
    responseType: "blob",
  });

  return buildDownloadPayload(response, "submissions.xlsx");
}

export function downloadSubmissionArchive(submissionId) {
  startServerDownload(`downloads/submissions/${submissionId}/`);
}
