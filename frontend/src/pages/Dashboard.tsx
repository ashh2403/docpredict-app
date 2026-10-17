import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  ArrowRight,
  Bookmark,
  FileStack,
  Gauge,
  HelpCircle,
  PieChart as PieIcon,
  UploadCloud,
  Flag,
  Clock,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import type { AnalysisSummary, Stats } from "../lib/types";
import { CATEGORY_COLORS, formatPercent, relativeTime } from "../lib/format";
import { CategoryBadge, EmptyState, ErrorAlert, FileTypeIcon, PriorityBadge, Spinner, UncertainBadge } from "../components/ui";

const tooltipStyle = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: 10,
  boxShadow: "var(--shadow)",
  color: "var(--text)",
  fontSize: 13,
};

function greeting(): string {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState<Stats | null>(null);
  const [recent, setRecent] = useState<AnalysisSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.stats(), api.listAnalyses({ page_size: 5 })])
      .then(([s, page]) => {
        if (cancelled) return;
        setStats(s);
        setRecent(page.items);
      })
      .catch((e) => !cancelled && setError(e instanceof ApiError ? e.message : "Could not load dashboard."));
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <ErrorAlert>{error}</ErrorAlert>;
  if (!stats) return <Spinner label="Loading dashboard" />;

  const firstName = user?.full_name.split(" ")[0] ?? "";
  const perDay = stats.per_day.map((d) => ({
    ...d,
    label: new Date(d.date + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short" }),
  }));

  return (
    <>
      <div className="page-head">
        <div>
          <h1>
            {greeting()}, {firstName}
          </h1>
          <p>Here is an overview of the documents you have analysed.</p>
        </div>
        <div className="page-actions">
          <Link to="/analyze" className="btn btn-primary">
            <UploadCloud aria-hidden /> Analyze a document
          </Link>
        </div>
      </div>

      {stats.total === 0 ? (
        <div className="card">
          <EmptyState
            icon={FileStack}
            title="No analyses yet"
            action={
              <Link to="/analyze" className="btn btn-primary">
                <UploadCloud aria-hidden /> Upload your first document
              </Link>
            }
          >
            Upload a PDF, DOCX or TXT file to see its predicted type, summary, key details and the evidence behind the
            prediction. Your statistics will appear here.
          </EmptyState>
        </div>
      ) : (
        <div className="stack">
          <div className="grid grid-4">
            <div className="card stat">
              <div className="stat-top">
                <span className="stat-label">Total analyses</span>
                <span className="stat-icon navy">
                  <FileStack aria-hidden />
                </span>
              </div>
              <span className="stat-value">{stats.total}</span>
              <span className="stat-foot">Saved in your history</span>
            </div>
            <div className="card stat">
              <div className="stat-top">
                <span className="stat-label">Average model score</span>
                <span className="stat-icon">
                  <Gauge aria-hidden />
                </span>
              </div>
              <span className="stat-value">{stats.average_confidence !== null ? formatPercent(stats.average_confidence) : "–"}</span>
              <span className="stat-foot">Top-category score, not a probability</span>
            </div>
            <div className="card stat">
              <div className="stat-top">
                <span className="stat-label">Flagged uncertain</span>
                <span className="stat-icon amber">
                  <HelpCircle aria-hidden />
                </span>
              </div>
              <span className="stat-value">{stats.uncertain}</span>
              <span className="stat-foot">Did not meet the confidence policy</span>
            </div>
            <div className="card stat">
              <div className="stat-top">
                <span className="stat-label">Bookmarked</span>
                <span className="stat-icon green">
                  <Bookmark aria-hidden />
                </span>
              </div>
              <span className="stat-value">{stats.bookmarked}</span>
              <span className="stat-foot">
                <Link to="/history?bookmarked=true">View bookmarks</Link>
              </span>
            </div>
          </div>

          <div className="grid grid-main">
            <div className="card">
              <div className="card-header">
                <h2>
                  <Activity aria-hidden /> Activity
                  <span className="card-sub">· last 14 days</span>
                </h2>
              </div>
              <div className="card-body" style={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={perDay} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                    <defs>
                      <linearGradient id="actFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.28} />
                        <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="label" tick={{ fill: "var(--text-muted)", fontSize: 12 }} tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={18} />
                    <YAxis allowDecimals={false} tick={{ fill: "var(--text-muted)", fontSize: 12 }} tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: "var(--text-muted)" }} formatter={(v: number) => [v, "Analyses"]} />
                    <Area type="monotone" dataKey="count" stroke="var(--chart-1)" strokeWidth={2.5} fill="url(#actFill)" animationDuration={600} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h2>
                  <PieIcon aria-hidden /> Document types
                </h2>
              </div>
              <div className="card-body">
                <div style={{ height: 180 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={stats.by_category} dataKey="count" nameKey="label" innerRadius={52} outerRadius={80} paddingAngle={2} stroke="none" animationDuration={600}>
                        {stats.by_category.map((c) => (
                          <Cell key={c.category} fill={CATEGORY_COLORS[c.category] ?? "var(--chart-8)"} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <ul className="list-plain" style={{ marginTop: 12 }}>
                  {stats.by_category.map((c) => (
                    <li key={c.category} style={{ alignItems: "center" }}>
                      <span className="dot" style={{ background: CATEGORY_COLORS[c.category] }} />
                      <Link to={`/history?category=${c.category}`} style={{ color: "var(--text-2)", flex: 1 }}>
                        {c.label}
                      </Link>
                      <strong style={{ fontVariantNumeric: "tabular-nums" }}>{c.count}</strong>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          <div className="grid grid-main">
            <div className="card">
              <div className="card-header">
                <h2>
                  <Clock aria-hidden /> Recent analyses
                </h2>
                <Link to="/history" className="btn btn-ghost btn-sm">
                  View all <ArrowRight aria-hidden />
                </Link>
              </div>
              <div>
                {recent.map((a) => (
                  <Link key={a.id} to={`/analyses/${a.id}`} className="recent-item">
                    <FileTypeIcon type={a.file_type} />
                    <div className="meta">
                      <strong>{a.filename}</strong>
                      <span>
                        {relativeTime(a.created_at)} · {a.word_count.toLocaleString()} words
                      </span>
                    </div>
                    {a.is_uncertain ? <UncertainBadge /> : <CategoryBadge label={a.category_label} />}
                  </Link>
                ))}
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h2>
                  <Flag aria-hidden /> Attention levels
                </h2>
              </div>
              <div className="card-body">
                {(["high", "medium", "low"] as const).map((p) => {
                  const n = stats.by_priority[p] ?? 0;
                  return (
                    <div key={p} style={{ marginBottom: 16 }}>
                      <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
                        <Link to={`/history?priority=${p}`}>
                          <PriorityBadge priority={p} />
                        </Link>
                        <strong style={{ fontVariantNumeric: "tabular-nums" }}>{n}</strong>
                      </div>
                      <span className="score-bar" style={{ display: "block", height: 8 }}>
                        <span
                          style={{
                            width: `${stats.total ? (n / stats.total) * 100 : 0}%`,
                            background: p === "high" ? "var(--danger)" : p === "medium" ? "var(--warning)" : "var(--success)",
                          }}
                        />
                      </span>
                    </div>
                  );
                })}
                <p className="hint">Attention level is a rule-based check for deadlines and urgent wording, separate from the model score.</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
