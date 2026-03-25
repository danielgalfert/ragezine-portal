import client from "../api/client";

export async function createSubmission(payload) {
  const response = await client.post("/submissions/", payload);
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
