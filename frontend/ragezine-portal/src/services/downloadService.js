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

export function triggerBlobDownload(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export async function downloadCompleteArchive() {
  const response = await client.get("/downloads/complete/", {
    responseType: "blob",
  });

  return buildDownloadPayload(response);
}

export async function downloadExcelReview() {
  const response = await client.get("/downloads/excel/", {
    responseType: "blob",
  });

  return buildDownloadPayload(response, "submissions.xlsx");
}

export async function downloadSubmissionArchive(submissionId) {
  const response = await client.get(`/downloads/submissions/${submissionId}/`, {
    responseType: "blob",
  });

  return buildDownloadPayload(response, `submission-${submissionId}.zip`);
}
