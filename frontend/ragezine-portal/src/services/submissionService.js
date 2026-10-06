import client from "../api/client";

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
