import client from "../api/client";
import { getCsrfCookie } from "./authService";

export async function createSubmission(payload, onUploadProgress) {
  const response = await client.post("/submissions/", payload, {
    timeout: 0,
    onUploadProgress,
  });
  return response.data;
}

export async function getSubmissions() {
  const response = await client.get("/submissions/");
  return response.data;
}

export async function getSubmissionById(id) {
  const response = await client.get(`/submissions/${id}/`);
  return response.data;
}

export async function getSubmissionVotes(id) {
  const response = await client.get(`/submissions/${id}/votes/`);
  return response.data;
}

export async function saveSubmissionVote(id, choice) {
  await getCsrfCookie();
  const response = await client.post(`/submissions/${id}/votes/`, { choice });
  return response.data;
}

export async function clearSubmissionVote(id) {
  await getCsrfCookie();
  const response = await client.delete(`/submissions/${id}/votes/`);
  return response.data;
}

export async function getSubmissionComments(id) {
  const response = await client.get(`/submissions/${id}/comments/`);
  return response.data;
}

export async function addSubmissionComment(id, body) {
  await getCsrfCookie();
  const response = await client.post(`/submissions/${id}/comments/`, { body });
  return response.data;
}

export function getSubmissionPreviewUrl(path) {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  const apiBase = new URL(client.defaults.baseURL, window.location.href);
  return new URL(path, apiBase).toString();
}

export async function getSubmissionPreviewText(path) {
  const response = await client.get(getSubmissionPreviewUrl(path), { responseType: "text" });
  return response.data;
}

export async function getVideoStreamAccess(documentId) {
  const response = await client.get(`/previews/documents/${documentId}/video-access/`);
  return response.data;
}

export async function deleteSubmission(id) {
  await client.delete(`/submissions/${id}/`);
}
