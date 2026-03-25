import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import FormField from "../components/FormField";
import { getCsrfCookie, getSession, loginUser } from "../services/authService";
import { sanitizeUsername } from "../utils/sanitize";

import "../styles/nav.css";
import "../styles/description.css";
import "../styles/form.css";
import "../styles/login.css";

export default function LoginPage() {
  const [form, setForm] = useState({ username: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [popup, setPopup] = useState({
    open: false,
    kind: "error",
    title: "",
    messages: [],
  });
  const navigate = useNavigate();

  useEffect(() => {
    async function bootstrap() {
      try {
        await getCsrfCookie();
        const session = await getSession();
        if (session?.authenticated) {
          navigate("/dashboard", { replace: true });
          return;
        }
      } catch {
        // Anonymous user is expected here.
      } finally {
        setCheckingSession(false);
      }
    }

    bootstrap();
  }, [navigate]);

  function update(key, value) {
    setForm((prev) => ({ ...prev, [key]: key === "username" ? sanitizeUsername(value) : value }));
  }

  function openPopup(kind, title, messages) {
    setPopup({
      open: true,
      kind,
      title,
      messages: Array.isArray(messages) ? messages : [messages],
    });
  }

  function closePopup() {
    setPopup((prev) => ({ ...prev, open: false }));
  }

  async function onSubmit(event) {
    event.preventDefault();

    if (!form.username.trim() || !form.password) {
      openPopup("error", "Login error", "Username and password are required.");
      return;
    }

    setLoading(true);

    try {
      await loginUser({
        username: sanitizeUsername(form.username),
        password: form.password,
      });
      navigate("/dashboard", { replace: true });
    } catch (error) {
      const message =
        error?.response?.data?.message ||
        error?.message ||
        "Login failed.";
      openPopup("error", "Login error", message);
    } finally {
      setLoading(false);
    }
  }

  if (checkingSession) {
    return (
      <div className="portal-page login-page">
        <section className="login-stage" id="home">
          <div className="login-shell login-shell-loading">
            <div className="login-copy">
              <h1>Admin Login</h1>
              <p>Checking session...</p>
            </div>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="portal-page login-page">
      <nav>
        <ul>
          <li><Link to="/">submissions</Link></li>
        </ul>
      </nav>

      <section className="login-stage" id="submit">
        <div className="login-shell">
          <div className="login-copy">
            <h2>Login</h2>
            <p>
              This page is rendered entirely in the frontend and authenticates against
              Django session auth.
            </p>
          </div>

          <div className="portal-form-wrap login-form-wrap">
            <form className="portal-form" onSubmit={onSubmit}>
              <div className="portal-grid">
                <FormField label="Username">
                  <input className="portal-input" autoComplete="username" value={form.username} onChange={(e) => update("username", e.target.value)} onBlur={(e) => update("username", e.target.value)} />
                </FormField>

                <FormField label="Password">
                  <input className="portal-input" type="password" autoComplete="current-password" value={form.password} onChange={(e) => update("password", e.target.value)} />
                </FormField>
              </div>

              <div className="portal-actions">
                <button className="portal-btn" type="submit" disabled={loading}>
                  {loading ? "signing in..." : "sign in"}
                </button>
              </div>
            </form>
          </div>
        </div>
      </section>

      {popup.open && (
        <div className="portal-modal-backdrop" onClick={closePopup}>
          <div
            className={`portal-modal portal-modal-${popup.kind}`}
            role="dialog"
            aria-modal="true"
            aria-labelledby="login-modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button type="button" className="portal-modal-close" onClick={closePopup} aria-label="Close message">
              x
            </button>

            <h3 id="login-modal-title">{popup.title}</h3>

            <div className="portal-modal-body">
              {popup.messages.map((message, index) => (
                <p key={`${message}-${index}`}>{message}</p>
              ))}
            </div>

            <button type="button" className="portal-btn" onClick={closePopup}>
              close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
