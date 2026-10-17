export const SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".txt"];
export const MAX_UPLOAD_MB = 10;

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatPercent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function relativeTime(iso: string, now: Date = new Date()): string {
  const diff = (now.getTime() - new Date(iso).getTime()) / 1000;
  if (diff < 45) return "just now";
  if (diff < 3600) return `${Math.round(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)} h ago`;
  if (diff < 86400 * 7) return `${Math.round(diff / 86400)} d ago`;
  return formatDate(iso);
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

/** Plain-language band for a model score. These are descriptive bands, not probabilities. */
export function scoreBand(score: number, uncertain: boolean): string {
  if (uncertain) return "Uncertain";
  if (score >= 0.85) return "Strong match";
  if (score >= 0.65) return "Good match";
  return "Moderate match";
}

export function validateFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!SUPPORTED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return "Unsupported file type. Please choose a PDF, DOCX or TXT file.";
  }
  if (file.size === 0) return "This file is empty.";
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `This file is larger than ${MAX_UPLOAD_MB} MB.`;
  return null;
}

export function passwordScore(pw: string): number {
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Za-z]/.test(pw) && /\d/.test(pw)) score++;
  if (pw.length >= 12) score++;
  if (/[^A-Za-z0-9]/.test(pw) && /[A-Z]/.test(pw)) score++;
  return Math.min(score, 4);
}

export function passwordProblem(pw: string): string | null {
  if (pw.length < 8) return "Use at least 8 characters.";
  if (new TextEncoder().encode(pw).length > 72) return "Use at most 72 bytes.";
  if (!/[A-Za-z]/.test(pw) || !/\d/.test(pw)) return "Include at least one letter and one number.";
  return null;
}

export const CATEGORY_COLORS: Record<string, string> = {
  invoice: "var(--chart-1)",
  contract: "var(--chart-2)",
  resume: "var(--chart-3)",
  medical_report: "var(--chart-4)",
  financial_report: "var(--chart-5)",
  research_paper: "var(--chart-6)",
  meeting_minutes: "var(--chart-7)",
  legal_notice: "var(--chart-8)",
};
