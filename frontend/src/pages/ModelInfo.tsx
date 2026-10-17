import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertTriangle, BrainCircuit, Database, Gauge, Grid3x3, ShieldQuestion, Target } from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { EvaluationSet, ModelInfo as ModelInfoT } from "../lib/types";
import { formatDate, formatPercent } from "../lib/format";
import { Disclaimer, ErrorAlert, Spinner } from "../components/ui";

const SETS: { key: "heldout_synthetic" | "handwritten_blind" | "handwritten_dev"; title: string; note: string }[] = [
  { key: "heldout_synthetic", title: "Held-out synthetic", note: "Same generator as the training data, so optimistic." },
  { key: "handwritten_blind", title: "Hand-written (blind)", note: "Never used for training or tuning. Very small sample." },
  { key: "handwritten_dev", title: "Hand-written (development)", note: "Influenced model development, so optimistic." },
];

const tooltipStyle = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: 10,
  color: "var(--text)",
  fontSize: 13,
};

function short(label: string): string {
  return label.replace(" / Agreement", "").replace(" / CV", "").replace(" Report", "").replace("Meeting ", "");
}

export default function ModelInfo() {
  const [info, setInfo] = useState<ModelInfoT | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .modelInfo()
      .then(setInfo)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load model information."));
  }, []);

  if (error) return <ErrorAlert>{error}</ErrorAlert>;
  if (!info) return <Spinner label="Loading model information" />;

  const labelOf = Object.fromEntries(info.categories.map((c) => [c.category, c.label]));
  const heldout = info.evaluation.heldout_synthetic as EvaluationSet | undefined;
  const blind = info.evaluation.handwritten_blind as EvaluationSet | undefined;

  const perClass = heldout
    ? Object.entries(heldout.per_class).map(([cat, m]) => ({
        name: short(labelOf[cat] ?? cat),
        "Held-out synthetic": +(m["f1-score"] * 100).toFixed(1),
        "Blind hand-written": blind ? +((blind.per_class[cat]?.["f1-score"] ?? 0) * 100).toFixed(1) : undefined,
      }))
    : [];

  const calibBySet = SETS.map((s) => ({
    title: s.title,
    points: (info.evaluation[s.key]?.calibration.bins ?? []).map((b) => ({ score: +(b.mean_score * 100).toFixed(1), accuracy: +(b.accuracy * 100).toFixed(1), n: b.count })),
  }));

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Model &amp; accuracy</h1>
          <p>
            How the classifier works, what it was trained on and how it performed in testing. These numbers come from
            the evaluation run that produced the model currently in use.
          </p>
        </div>
      </div>

      <div className="stack">
        <div className="alert alert-warning">
          <AlertTriangle aria-hidden />
          <div>
            <strong>Illustrative model.</strong> The classifier was trained on <strong>synthetic</strong> documents
            generated from templates, not on a representative real-world dataset. Accuracy on your documents is
            unknown and is likely lower than the figures below. Independent evaluation on real documents would be needed
            before relying on it.
          </div>
        </div>

        <div className="grid grid-3">
          {SETS.map(({ key, title, note }) => {
            const s = info.evaluation[key];
            if (!s) return null;
            return (
              <div className="card stat" key={key}>
                <div className="stat-top">
                  <span className="stat-label">{title}</span>
                  <span className="stat-icon">
                    <Target aria-hidden />
                  </span>
                </div>
                <div className="row" style={{ alignItems: "baseline", gap: 8 }}>
                  <span className="stat-value">{formatPercent(s.accuracy, 1)}</span>
                  <span className="muted small">accuracy · n = {s.n}</span>
                </div>
                <div className="small" style={{ color: "var(--text-2)" }}>
                  Macro F1 {formatPercent(s.macro_f1, 1)} · {formatPercent(s.uncertainty_policy.coverage)} passed the confidence policy
                  {s.uncertainty_policy.accuracy_on_confident !== null && ` (${formatPercent(s.uncertainty_policy.accuracy_on_confident, 1)} correct)`}
                </div>
                <span className="stat-foot">{note}</span>
              </div>
            );
          })}
        </div>

        <div className="grid grid-2">
          <div className="card">
            <div className="card-header">
              <h2>
                <BrainCircuit aria-hidden /> Model
              </h2>
              <span className="badge badge-neutral mono">{info.model_version}</span>
            </div>
            <div className="card-body">
              <dl className="kv">
                <dt>Algorithm</dt>
                <dd>{info.algorithm}</dd>
                <dt>Settings</dt>
                <dd>
                  {Object.entries(info.hyperparameters)
                    .map(([k, v]) => `${k} = ${v}`)
                    .join(", ")}
                </dd>
                <dt>Trained</dt>
                <dd>{info.trained_at ? formatDate(info.trained_at) : "Unknown"}</dd>
                <dt>Categories</dt>
                <dd>{info.categories.map((c) => c.label).join(", ")}</dd>
                <dt>File types</dt>
                <dd>
                  {info.supported_file_types.join(", ")} · up to {info.max_upload_mb} MB
                </dd>
              </dl>
            </div>
          </div>
          <div className="card">
            <div className="card-header">
              <h2>
                <Database aria-hidden /> Training data
              </h2>
              <span className="badge badge-uncertain">{info.dataset.type}</span>
            </div>
            <div className="card-body">
              <p style={{ color: "var(--text-2)" }}>{info.dataset.description}</p>
              <dl className="kv" style={{ marginTop: 14 }}>
                <dt>Documents</dt>
                <dd>
                  {info.dataset.n_total.toLocaleString()} ({info.dataset.n_train.toLocaleString()} training,{" "}
                  {info.dataset.n_test.toLocaleString()} held out)
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="grid grid-2">
          <div className="card">
            <div className="card-header">
              <h2>
                <Target aria-hidden /> F1 score by category
              </h2>
            </div>
            <div className="card-body" style={{ height: 320 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={perClass} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" tick={{ fill: "var(--text-muted)", fontSize: 11 }} interval={0} angle={-30} textAnchor="end" height={60} tickLine={false} axisLine={false} />
                  <YAxis domain={[0, 100]} tick={{ fill: "var(--text-muted)", fontSize: 12 }} tickLine={false} axisLine={false} unit="%" />
                  <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => `${v}%`} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="Held-out synthetic" fill="var(--chart-1)" radius={[4, 4, 0, 0]} animationDuration={600} />
                  {blind && <Bar dataKey="Blind hand-written" fill="var(--chart-2)" radius={[4, 4, 0, 0]} animationDuration={600} />}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <div>
                <h2>
                  <Gauge aria-hidden /> Score calibration
                </h2>
                <p className="section-desc">Average model score vs. how often the prediction was actually correct.</p>
              </div>
            </div>
            <div className="card-body" style={{ height: 320 }}>
              {calibBySet.every((s) => s.points.length === 0) ? (
                <p className="muted">No calibration data.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart margin={{ top: 4, right: 12, left: -18, bottom: 16 }}>
                    <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                    <XAxis type="number" dataKey="score" domain={[0, 100]} unit="%" tick={{ fill: "var(--text-muted)", fontSize: 12 }} label={{ value: "Average model score", position: "insideBottom", offset: -10, fill: "var(--text-muted)", fontSize: 12 }} />
                    <YAxis type="number" domain={[0, 100]} unit="%" tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
                    <Tooltip contentStyle={tooltipStyle} formatter={(v: number, name: string) => [`${v}%`, name]} labelFormatter={(v) => `Score ≈ ${v}%`} />
                    <Legend verticalAlign="top" height={44} wrapperStyle={{ fontSize: 12 }} />
                    <Line data={[{ score: 0, accuracy: 0 }, { score: 100, accuracy: 100 }]} dataKey="accuracy" name="Perfect calibration" stroke="var(--text-muted)" strokeDasharray="4 4" dot={false} />
                    {calibBySet.map((s, i) => (
                      <Line key={s.title} data={s.points} dataKey="accuracy" name={s.title} stroke={["var(--chart-1)", "var(--chart-2)", "var(--chart-6)"][i]} strokeWidth={2} animationDuration={600} />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2>
              <ShieldQuestion aria-hidden /> Uncertainty policy
            </h2>
          </div>
          <div className="card-body">
            <p style={{ color: "var(--text-2)" }}>{info.uncertainty_policy.description}</p>
            <h3 style={{ marginTop: 18 }}>Known limitations</h3>
            <ul className="list-plain" style={{ marginTop: 10 }}>
              {info.caveats.map((c) => (
                <li key={c}>
                  <AlertTriangle aria-hidden /> {c}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {heldout && (
          <div className="card">
            <div className="card-header">
              <div>
                <h2>
                  <Grid3x3 aria-hidden /> Confusion matrix · held-out synthetic
                </h2>
                <p className="section-desc">Rows are the true category, columns the predicted category.</p>
              </div>
            </div>
            <div className="card-body table-wrap">
              <table className="cm">
                <thead>
                  <tr>
                    <th className="rowh">True \ Predicted</th>
                    {heldout.confusion_matrix.labels.map((l) => (
                      <th key={l}>{short(labelOf[l] ?? l)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {heldout.confusion_matrix.matrix.map((row, i) => {
                    const max = Math.max(...row, 1);
                    return (
                      <tr key={i}>
                        <th className="rowh">{short(labelOf[heldout.confusion_matrix.labels[i]] ?? "")}</th>
                        {row.map((v, j) => (
                          <td
                            key={j}
                            style={{
                              background: v ? `color-mix(in srgb, ${i === j ? "var(--primary)" : "var(--danger)"} ${Math.round((v / max) * (i === j ? 30 : 45)) + 8}%, transparent)` : undefined,
                              fontWeight: i === j ? 650 : 400,
                            }}
                          >
                            {v}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <Disclaimer />
      </div>
    </>
  );
}
