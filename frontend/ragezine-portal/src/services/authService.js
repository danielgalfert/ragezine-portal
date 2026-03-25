import client from "../api/client";

let csrfRequest = null;

export async function getCsrfCookie() {
  if (!csrfRequest) {
    csrfRequest = client.get("/auth/csrf/");
  }

  try {
    const response = await csrfRequest;
    return response.data;
  } finally {
    csrfRequest = null;
  }
}

export async function loginUser(payload) {
  await getCsrfCookie();
  const response = await client.post("/auth/login/", payload);
  return response.data;
}

export async function logoutUser() {
  await getCsrfCookie();
  const response = await client.post("/auth/logout/");
  return response.data;
}

export async function getSession() {
  const response = await client.get("/auth/session/");
  return response.data;
}
