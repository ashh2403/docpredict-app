import { Link } from "react-router-dom";
import {
  ArrowRight,
  BrainCircuit,
  FileSearch,
  Gauge,
  HardDrive,
  ListChecks,
  ScanText,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Logo } from "../components/ui";

const FEATURES = [
  { icon: ScanText, title: "Real text extraction", text: "Reads the actual text of PDF, Word and plain-text files. Scanned images are rejected rather than guessed." },
  { icon: BrainCircuit, title: "Local ML classifier", text: "A trained scikit-learn model sorts documents into eight types, entirely on your own machine." },
  { icon: FileSearch, title: "Evidence, not magic", text: "See which words and sentences pushed the prediction, and which category came a close second." },
  { icon: Gauge, title: "Honest uncertainty", text: "Low-scoring, ambiguous or out-of-scope documents are clearly flagged as Uncertain." },
  { icon: ListChecks, title: "Summaries & key fields", text: "Extractive summaries, keywords, dates, amounts and reference numbers taken from the document itself." },
  { icon: HardDrive, title: "Private by default", text: "Files are deleted right after analysis. Only the result metadata is saved, and you can delete it any time." },
];

export default function Landing() {
  return (
    <div className="landing">
      <header className="landing-nav">
        <Logo />
        <div className="row">
          <Link to="/login" className="btn btn-ghost">
            Sign in
          </Link>
          <Link to="/register" className="btn btn-navy">
            Create account
          </Link>
        </div>
      </header>

      <section className="hero">
        <div>
          <span className="kicker">
            <Sparkles aria-hidden /> Document intelligence that shows its work
          </span>
          <h1>
            Understand any document <em>in seconds</em>, with evidence you can check.
          </h1>
          <p className="lead">
            Upload a PDF, Word or text file. DocPredict identifies the document type, summarises it, pulls out key
            details and explains exactly why it reached its conclusion.
          </p>
          <div className="cta">
            <Link to="/register" className="btn btn-primary btn-lg">
              Get started free <ArrowRight aria-hidden />
            </Link>
            <Link to="/login" className="btn btn-secondary btn-lg">
              I have an account
            </Link>
          </div>
        </div>

        <div className="hero-visual" aria-label="Illustration of an analysis result">
          <div className="preview-card">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <span className="preview-label">How a result is presented</span>
              <span className="badge badge-purple">Invoice</span>
            </div>
            <h3 style={{ marginTop: 10 }}>Predicted category with model score</h3>
            <p className="muted small" style={{ marginTop: 4 }}>
              Every category's score is shown, so close calls are visible.
            </p>
            <div style={{ marginTop: 14 }}>
              {[
                ["Top category", 0.9],
                ["Runner-up", 0.06],
                ["Others", 0.04],
              ].map(([name, v]) => (
                <div className="score-row" key={name as string} style={{ gridTemplateColumns: "100px 1fr" }}>
                  <span className="name" style={{ color: "#3c4370" }}>
                    {name}
                  </span>
                  <span className="score-bar" style={{ background: "#f0eefb" }}>
                    <span style={{ width: `${(v as number) * 100}%`, background: "#6a59ee" }} />
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="preview-card">
            <span className="preview-label">Evidence from the document</span>
            <p style={{ marginTop: 8, fontSize: "0.9rem", color: "#121842" }}>
              Sentences containing the strongest signals are highlighted, such as{" "}
              <mark style={{ background: "#d8d1ff", borderRadius: 4, padding: "0 3px" }}>total amount due</mark>.
            </p>
            <div className="row" style={{ marginTop: 12 }}>
              <span className="badge badge-medium">Rule-based attention level</span>
              <span className="badge badge-uncertain">Uncertain flag when unsure</span>
            </div>
          </div>
        </div>
      </section>

      <section className="how">
        <div className="how-inner">
          <h2>Built for clarity, not hype</h2>
          <p>Everything DocPredict shows is computed from your document by local code you can inspect.</p>
          <div className="grid grid-3">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <div className="card feature" key={title}>
                <span className="stat-icon">
                  <Icon aria-hidden />
                </span>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="landing-foot">
        <span className="row">
          <ShieldCheck size={16} aria-hidden /> Results are illustrative and are not legal, medical or financial advice.
        </span>
        <span>DocPredict · runs locally</span>
      </footer>
    </div>
  );
}
