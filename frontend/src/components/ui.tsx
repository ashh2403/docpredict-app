import { useEffect, useRef, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  FileScan,
  FileText,
  FileType2,
  Flag,
  HelpCircle,
  Loader2,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";
import type { Priority } from "../lib/types";
import { formatPercent } from "../lib/format";

export function Logo({ to = "/" }: { to?: string }) {
  return (
    <Link to={to} className="brand" aria-label="DocPredict home">
      <span className="brand-mark">
        <FileScan aria-hidden />
      </span>
      <span className="brand-name">
        Doc<span>Predict</span>
      </span>
    </Link>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="center-screen" role="status">
      <Loader2 className="loader spin" aria-hidden />
      <span className="sr-only">{label}</span>
    </div>
  );
}

export function FileTypeIcon({ type }: { type: string }) {
  const Icon = type === "pdf" ? FileType2 : FileText;
  return (
    <span className="file-icon" aria-hidden>
      <Icon />
    </span>
  );
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  const label = { high: "High attention", medium: "Medium attention", low: "Low attention" }[priority];
  return (
    <span className={`badge badge-${priority}`} title="Rule-based attention level (not a model output)">
      <Flag aria-hidden />
      {label}
    </span>
  );
}

export function UncertainBadge() {
  return (
    <span className="badge badge-uncertain" title="The prediction did not meet the confidence policy">
      <HelpCircle aria-hidden />
      Uncertain
    </span>
  );
}

export function CategoryBadge({ label, uncertain }: { label: string; uncertain?: boolean }) {
  return (
    <span className={`badge ${uncertain ? "badge-neutral" : "badge-purple"}`}>
      {uncertain ? `Possibly ${label}` : label}
    </span>
  );
}

export function ScoreBar({ value }: { value: number }) {
  return (
    <span className="score-bar" aria-hidden>
      <span style={{ width: `${Math.round(value * 100)}%` }} />
    </span>
  );
}

export function ConfidenceGauge({ value, uncertain }: { value: number; uncertain: boolean }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const color = uncertain ? "var(--warning)" : "var(--primary)";
  return (
    <div className="gauge" role="img" aria-label={`Model score ${formatPercent(value)}${uncertain ? ", uncertain" : ""}`}>
      <svg viewBox="0 0 120 120">
        <circle className="gauge-track" cx="60" cy="60" r={r} fill="none" strokeWidth="10" />
        <circle
          className="gauge-fill"
          cx="60"
          cy="60"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - value)}
        />
      </svg>
      <div className="gauge-label">
        <div>
          <strong>{formatPercent(value)}</strong>
          <span>Model score</span>
        </div>
      </div>
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  children,
  action,
}: {
  icon: LucideIcon;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Icon aria-hidden />
      </span>
      <h2>{title}</h2>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

export function ErrorAlert({ children }: { children: ReactNode }) {
  return (
    <div className="alert alert-error" role="alert">
      <AlertTriangle aria-hidden />
      <div>{children}</div>
    </div>
  );
}

export function Disclaimer() {
  return (
    <p className="disclaimer">
      <ShieldAlert aria-hidden />
      <span>
        DocPredict results are automated, illustrative estimates from a model trained on synthetic examples. The
        model score is not a guaranteed probability, and the attention level is a simple wording-based rule. Nothing
        here is legal, medical or financial advice; consult a qualified professional before acting on a document.
      </span>
    </p>
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  danger = true,
  busy = false,
  onConfirm,
  onCancel,
  children,
}: {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  children?: ReactNode;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    cancelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && !busy && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, busy, onCancel]);

  if (!open) return null;
  return (
    <div className="dialog-backdrop" onMouseDown={(e) => e.target === e.currentTarget && !busy && onCancel()}>
      <div className="dialog" role="alertdialog" aria-modal="true" aria-labelledby="dialog-title">
        <h2 id="dialog-title">
          {danger && <AlertTriangle size={20} color="var(--danger)" aria-hidden />}
          {title}
        </h2>
        <p>{message}</p>
        {children}
        <div className="form-actions">
          <button ref={cancelRef} className="btn btn-secondary" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button className={`btn ${danger ? "btn-danger" : "btn-primary"}`} onClick={onConfirm} disabled={busy}>
            {busy && <Loader2 className="spin" aria-hidden />}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
