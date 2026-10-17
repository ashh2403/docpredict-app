import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Bookmark,
  BookmarkCheck,
  CalendarClock,
  FileQuestion,
  FileText,
  Flag,
  Hash,
  Info,
  Lightbulb,
  ListTree,
  Loader2,
  Quote,
  ScrollText,
  Tags,
  Timer,
  Trash2,
  Type,
} from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { AnalysisDetail, ExtractedFields } from "../lib/types";
import { formatBytes, formatDateTime, formatPercent, scoreBand } from "../lib/format";
import { highlightTerms } from "../lib/highlight";
import { useToast } from "../context/ToastContext";
import {
  ConfidenceGauge,
  ConfirmDialog,
  Disclaimer,
  EmptyState,
  ErrorAlert,
  PriorityBadge,
  Spinner,
  UncertainBadge,
} from "../components/ui";

const FIELD_LABELS: Record<string, string> = {
  dates: "Dates",
  amounts: "Amounts",
  reference_numbers: "Reference numbers",
  emails: "Email addresses",
  phone_numbers: "Phone numbers",
  percentages: "Percentages",
};

function FieldsCard({ fields }: { fields: ExtractedFields }) {
  const lists = Object.entries(FIELD_LABELS).filter(([k]) => (fields[k as keyof ExtractedFields] as string[] | undefined)?.length);
  const kv = fields.key_values ?? [];
  return (
    <div className="card">
      <div className="card-header">
        <h2>
          <ListTree aria-hidden /> Extracted details
        </h2>
      </div>
      <div className="card-body">
        {lists.length === 0 && kv.length === 0 ? (
          <p className="muted small">No dates, amounts, contact details or labelled fields were found in this document.</p>
        ) : (
          <dl className="kv">
            {kv.map((item) => (
              <div key={`kv-${item.label}`} style={{ display: "contents" }}>
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
            {lists.map(([key, label]) => (
              <div key={key} style={{ display: "contents" }}>
                <dt>{label}</dt>
                <dd>{(fields[key as keyof ExtractedFields] as string[]).join(", ")}</dd>
              </div>
            ))}
          </dl>
        )}
        <p className="hint" style={{ marginTop: 14 }}>
          Found with text patterns; verify important values against the original document.
        </p>
      </div>
    </div>
  );
}

export default function Result() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { notify } = useToast();
  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [error, setError] = useState<{ status: number; message: string } | null>(null);
  const [bookmarkBusy, setBookmarkBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const numericId = Number(id);
    if (!Number.isInteger(numericId) || numericId <= 0) {
      setError({ status: 404, message: "Analysis not found." });
      return;
    }
    let cancelled = false;
    api
      .getAnalysis(numericId)
      .then((a) => !cancelled && setAnalysis(a))
      .catch((e) => !cancelled && setError({ status: e instanceof ApiError ? e.status : 0, message: e.message }));
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    if (error.status === 404)
      return (
        <div className="card">
          <EmptyState
            icon={FileQuestion}
            title="Analysis not found"
            action={
              <Link to="/history" className="btn btn-primary">
                Back to history
              </Link>
            }
          >
            It may have been deleted, or it belongs to a different account.
          </EmptyState>
        </div>
      );
    return <ErrorAlert>{error.message}</ErrorAlert>;
  }
  if (!analysis) return <Spinner label="Loading analysis" />;

  const a = analysis;
  const expl = a.explanation;
  const runnerUp = a.top_predictions[1];

  const toggleBookmark = async () => {
    setBookmarkBusy(true);
    try {
      const updated = await api.setBookmark(a.id, !a.bookmarked);
      setAnalysis(updated);
      notify(updated.bookmarked ? "Added to bookmarks." : "Removed from bookmarks.");
    } catch (e) {
      notify(e instanceof ApiError ? e.message : "Could not update bookmark.", "error");
    } finally {
      setBookmarkBusy(false);
    }
  };

  const doDelete = async () => {
    setDeleting(true);
    try {
      await api.deleteAnalysis(a.id);
      notify("Analysis deleted.");
      navigate("/history", { replace: true });
    } catch (e) {
      setDeleting(false);
      setConfirmDelete(false);
      notify(e instanceof ApiError ? e.message : "Could not delete analysis.", "error");
    }
  };

  return (
    <>
      <div className="row" style={{ marginBottom: 16, justifyContent: "space-between" }}>
        <Link to="/history" className="btn btn-ghost btn-sm">
          <ArrowLeft aria-hidden /> History
        </Link>
        <div className="row">
          <button className="btn btn-secondary btn-sm" onClick={toggleBookmark} disabled={bookmarkBusy} aria-pressed={a.bookmarked}>
            {bookmarkBusy ? <Loader2 className="spin" aria-hidden /> : a.bookmarked ? <BookmarkCheck aria-hidden color="var(--primary)" /> : <Bookmark aria-hidden />}
            {a.bookmarked ? "Bookmarked" : "Bookmark"}
          </button>
          <button className="btn btn-danger-ghost btn-sm" onClick={() => setConfirmDelete(true)}>
            <Trash2 aria-hidden /> Delete
          </button>
        </div>
      </div>

      <div className="stack">
        <section className="card result-hero">
          <div>
            <span className="eyebrow">{a.is_uncertain ? "Best guess (uncertain)" : "Predicted document type"}</span>
            <h1>{a.category_label}</h1>
            <div className="row" style={{ marginTop: 12 }}>
              {a.is_uncertain ? <UncertainBadge /> : <span className="badge badge-purple">{scoreBand(a.confidence, false)}</span>}
              <PriorityBadge priority={a.priority} />
            </div>
            <div className="result-meta">
              <span title="File name">
                <FileText aria-hidden /> {a.filename}
              </span>
              <span>
                <Type aria-hidden /> {a.file_type.toUpperCase()} · {formatBytes(a.file_size)}
                {a.page_count ? ` · ${a.page_count} page${a.page_count > 1 ? "s" : ""}` : ""}
              </span>
              <span>
                <Hash aria-hidden /> {a.word_count.toLocaleString()} words
              </span>
              <span>
                <CalendarClock aria-hidden /> {formatDateTime(a.created_at)}
              </span>
              <span title="Server processing time">
                <Timer aria-hidden /> {a.processing_ms} ms
              </span>
            </div>
          </div>
          <ConfidenceGauge value={a.confidence} uncertain={a.is_uncertain} />
        </section>

        {a.is_uncertain && (
          <div className="alert alert-warning" role="status">
            <AlertTriangle aria-hidden />
            <div>
              <strong>This result is uncertain.</strong> The model's best guess is shown, but it did not meet the
              confidence policy:
              <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                {a.uncertainty_reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
        {!a.is_uncertain && a.uncertainty_reasons.length > 0 && (
          <div className="alert alert-info">
            <Info aria-hidden />
            <div>{a.uncertainty_reasons.join(" ")}</div>
          </div>
        )}

        <div className="grid grid-main">
          <div className="stack">
            <div className="card">
              <div className="card-header">
                <h2>
                  <ScrollText aria-hidden /> Summary
                </h2>
                <span className="badge badge-neutral">Extractive</span>
              </div>
              <div className="card-body">
                {a.summary ? <p className="summary-text">{a.summary}</p> : <p className="muted">No summary could be produced.</p>}
                <p className="hint" style={{ marginTop: 12 }}>
                  Made of the document's own most representative sentences. No text was generated or rewritten.
                </p>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h2>
                  <Lightbulb aria-hidden /> Why this prediction
                </h2>
              </div>
              <div className="card-body stack" style={{ gap: 22 }}>
                <div>
                  <h3>Evidence from the document</h3>
                  <p className="hint" style={{ margin: "4px 0 12px" }}>
                    Sentences containing the terms that contributed most to "{a.category_label}".
                  </p>
                  {expl.evidence.length === 0 ? (
                    <p className="muted small">No sentence contained a term the model associates with this category.</p>
                  ) : (
                    <div className="evidence">
                      {expl.evidence.map((ev, i) => (
                        <div className="evidence-item" key={i}>
                          <blockquote>
                            <Quote size={14} aria-hidden style={{ color: "var(--text-muted)", marginRight: 6, verticalAlign: "-2px" }} />
                            {highlightTerms(ev.sentence, ev.terms)}
                          </blockquote>
                          <div className="foot">
                            <span className="mini-bar" aria-hidden>
                              <span style={{ width: `${Math.round(ev.share * 100)}%` }} />
                            </span>
                            <span>{formatPercent(ev.share)} of sentence-level evidence</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <h3>Terms supporting {a.category_label}</h3>
                  <div className="chips" style={{ marginTop: 10 }}>
                    {expl.supporting_terms.length === 0 && <span className="muted small">None found.</span>}
                    {expl.supporting_terms.map((t) => (
                      <span className="chip" key={t.term} title={`Contribution ${t.weight.toFixed(3)}`}>
                        {t.term}
                        <span className="w">+{t.weight.toFixed(2)}</span>
                      </span>
                    ))}
                  </div>
                </div>

                {expl.opposing_terms.length > 0 && (
                  <div>
                    <h3>Terms pointing towards {expl.runner_up}</h3>
                    <p className="hint" style={{ margin: "4px 0 10px" }}>
                      The runner-up category{runnerUp ? ` scored ${formatPercent(runnerUp.score, runnerUp.score < 0.1 ? 1 : 0)}` : ""}. These terms favoured it over the
                      prediction.
                    </p>
                    <div className="chips">
                      {expl.opposing_terms.map((t) => (
                        <span className="chip neg" key={t.term}>
                          {t.term}
                          <span className="w">{t.weight.toFixed(2)}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <p className="hint">
                  <strong>Method:</strong> {expl.method} {formatPercent(expl.vocabulary_coverage)} of this document's content words
                  were seen during training.
                </p>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h2>
                  <Tags aria-hidden /> Keywords
                </h2>
              </div>
              <div className="card-body">
                <div className="chips">
                  {a.keywords.length === 0 && <span className="muted small">No keywords found.</span>}
                  {a.keywords.map((k) => (
                    <span className="chip" key={k.term} title={`Appears ${k.count} time${k.count > 1 ? "s" : ""}`}>
                      {k.term}
                      <span className="w">×{k.count}</span>
                    </span>
                  ))}
                </div>
                <p className="hint" style={{ marginTop: 12 }}>
                  Ranked by how often a term appears here relative to how common it is across the model's training documents.
                </p>
              </div>
            </div>
          </div>

          <div className="stack">
            <div className="card">
              <div className="card-header">
                <h2>
                  <BarChart3 aria-hidden /> Category scores
                </h2>
              </div>
              <div className="card-body">
                {a.top_predictions.map((p, i) => (
                  <div className={`score-row${i === 0 ? " top" : ""}`} key={p.category}>
                    <span className="name" title={p.label}>
                      {p.label}
                    </span>
                    <span className="score-bar" aria-hidden>
                      <span style={{ width: `${p.score * 100}%` }} />
                    </span>
                    <span className="val">{formatPercent(p.score, p.score < 0.1 ? 1 : 0)}</span>
                  </div>
                ))}
                <p className="hint" style={{ marginTop: 14 }}>
                  Scores from the classifier sum to 100% across the eight known categories. They are model scores, not
                  guaranteed probabilities. See <Link to="/model">Model &amp; accuracy</Link> for how they compared with
                  real outcomes in testing.
                </p>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h2>
                  <Flag aria-hidden /> Attention level
                </h2>
                <PriorityBadge priority={a.priority} />
              </div>
              <div className="card-body">
                <ul className="list-plain">
                  {a.priority_reasons.map((r) => (
                    <li key={r}>
                      <Info aria-hidden /> {r}
                    </li>
                  ))}
                </ul>
                <p className="hint" style={{ marginTop: 12 }}>
                  A simple rule-based check for deadlines and urgent wording. It is separate from the model score and
                  does not measure importance or risk.
                </p>
              </div>
            </div>

            <FieldsCard fields={a.extracted_fields} />

            <div className="card">
              <div className="card-header">
                <h2>
                  <Info aria-hidden /> Analysis details
                </h2>
              </div>
              <div className="card-body">
                <dl className="kv">
                  <dt>Model</dt>
                  <dd className="mono">{a.model_version}</dd>
                  <dt>Characters</dt>
                  <dd>{a.char_count.toLocaleString()}</dd>
                  <dt>Vocabulary seen</dt>
                  <dd>{formatPercent(expl.vocabulary_coverage)}</dd>
                  <dt>Stored</dt>
                  <dd>Results metadata only. The file and full text were deleted after processing.</dd>
                </dl>
              </div>
            </div>
            <Disclaimer />
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete this analysis?"
        message={`The saved result for "${a.filename}" will be permanently removed. This cannot be undone.`}
        confirmLabel="Delete analysis"
        busy={deleting}
        onConfirm={doDelete}
        onCancel={() => setConfirmDelete(false)}
      />
    </>
  );
}
