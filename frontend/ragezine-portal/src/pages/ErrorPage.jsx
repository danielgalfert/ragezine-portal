import { useEffect } from "react";
import { Link } from "react-router-dom";

import { publicSiteUrl } from "../publicSiteUrl";
import "../styles/error.css";

const ERRORS = {
  404: {
    title: "Page not found",
    message: "Check the address, or go back to the submission form.",
  },
  500: {
    title: "Something went wrong",
    message: "Reload the page. If the problem continues, try again later.",
  },
};

export default function ErrorPage({ status = 500 }) {
  const error = ERRORS[status] || ERRORS[500];

  useEffect(() => {
    document.title = `${error.title} — RAGE Zine`;
  }, [error.title]);

  return (
    <main className="portal-page error-page">
      <section className="error-stage" aria-labelledby="error-title">
        <div className="error-panel">
          <p className="error-number" aria-hidden="true">{status}</p>
          <h1 id="error-title">{error.title}</h1>
          <p>{error.message}</p>
          <div className="error-actions">
            {status === 500 && (
              <button type="button" onClick={() => window.location.reload()}>
                Reload page
              </button>
            )}
            <a href={publicSiteUrl}>Go to submission form</a>
            <Link to="/login">Staff sign in</Link>
          </div>
        </div>
      </section>
    </main>
  );
}
