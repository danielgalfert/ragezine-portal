import SubmissionForm from "../components/SubmissionForm";

import "../styles/description.css";
import "../styles/form.css";

export default function SubmissionPage() {
  return (
    <div className="portal-page">
      <section className="hero" id="home">
        <div className="hero-panel">
          <div className="hero-copy">
            <h1 className="hero-title" aria-label="RAGE ZINE">
              <span className="hero-wordmark" aria-hidden="true">
                <span className="hero-wordmark-rage">
                  <span className="hero-letter-heavy">R</span>
                  <span className="hero-letter-regular">A</span>
                  <span className="hero-letter-heavy">G</span>
                  <span className="hero-letter-heavy">E</span>
                </span>
                <span className="hero-wordmark-zine">
                  <span className="hero-letter-light">Z</span>
                  <span className="hero-letter-heavy hero-letter-pair">IN</span>
                  <span className="hero-letter-light">E</span>
                </span>
              </span>
            </h1>
            <p className="hero-subtitle">SUBMISSION PORTAL</p>
            <div className="hero-description">
              <p>RAGE Zine is a global multidisciplinary print and digital zine &amp; platform exploring the theme of feminist rage.</p>
              <p>We are looking for submissions of all kinds of writing, art &amp; content about feminist rage or showcasing feminist rage. Multidisciplinarity is a core value for us, so we welcome submissions covering a range of topics and disciplines, including politics, literature, art, gender, LGBTQIA+ rights, global health, science, education, psychology, sexuality, visual culture and more. We also publish a range of forms and mediums, including but not limited to articles, poems, photography, painting, comics, collage, film stills and digital art.</p>
              <p>We particularly encourage submissions to go beyond the obvious scope of theme and are particularly keen on experimental, bold and fresh feminist submissions.</p>
              <p>We are primarily looking for finalised submissions, but do not hesitate to get in touch if you have an idea and would like some feedback or support creating your submission. We also reach out to select creators for commissioned contributions and/or interviews.</p>
              <p>Please note that we are a fully not-for-profit and volunteer driven platform and this is an unpaid opportunity.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="submit" id="submit">
        <div className="submit-shell">
          <div className="submit-intro">
            <h2>Submit Here</h2>
            <div className="submission-content">
              <div className="guideline-card">
                <p><span className="sub">Language:</span><br />English is preferred, but we occasionally accept submissions in other languages, if you are happy for the submission to be accompanied by an English translation. Our team can help with translations in numerous languages.</p>
              </div>
              <div className="guideline-card">
                <p><span className="sub">Format:</span><br />Text: Word, Google Doc or PDF (max. 1500 words)<br />Visual: TIFF at 300 dpi, PNG, or link<br />Video: MP4, MOV, or WebM, or link<br />We recommend up to 5 visual and video files or links in total.</p>
              </div>
              <div className="guideline-card">
                <p><span className="sub">Filename:</span><br />Artist-Name_Submission-Title</p>
              </div>
            </div>
          </div>
          <div className="portal-form-wrap"><SubmissionForm /></div>
        </div>
      </section>
    </div>
  );
}
