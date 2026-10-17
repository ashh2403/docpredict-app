import { vi } from "vitest";
import type { AnalysisDetail, User } from "../lib/types";

export const user: User = {
  id: 1,
  email: "alice@example.com",
  full_name: "Alice Smith",
  theme: "light",
  created_at: "2025-01-01T10:00:00Z",
};

export const analysis: AnalysisDetail = {
  id: 7,
  filename: "recipe.txt",
  file_type: "txt",
  file_size: 512,
  word_count: 80,
  category: "meeting_minutes",
  category_label: "Meeting Minutes",
  confidence: 0.44,
  is_uncertain: true,
  priority: "low",
  bookmarked: false,
  summary: "Peel and slice six apples.",
  keywords: [{ term: "apples", score: 1, count: 2 }],
  created_at: "2025-03-01T09:00:00Z",
  page_count: null,
  char_count: 400,
  uncertainty_reasons: ["Top model score 44% is below the 50% threshold."],
  top_predictions: [
    { category: "meeting_minutes", label: "Meeting Minutes", score: 0.44 },
    { category: "medical_report", label: "Medical Report", score: 0.12 },
  ],
  explanation: {
    supporting_terms: [{ term: "minutes", weight: 0.31 }],
    opposing_terms: [],
    runner_up: "Medical Report",
    evidence: [{ sentence: "Bake for forty minutes until golden.", terms: ["minutes"], strength: 0.3, share: 1 }],
    vocabulary_coverage: 0.09,
    method: "Linear model attribution.",
  },
  extracted_fields: {},
  priority_reasons: ["No urgency wording or deadlines were detected."],
  model_version: "tfidf-logreg-1.0",
  processing_ms: 42,
};

type Handler = (url: string, init?: RequestInit) => { status: number; body?: unknown } | undefined;

/** Install a fetch mock that routes by "METHOD /path" and records calls. */
export function mockFetch(routes: Record<string, { status: number; body?: unknown } | Handler>) {
  const calls: { method: string; url: string; init?: RequestInit }[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    calls.push({ method, url, init });
    const path = url.split("?")[0];
    const route = routes[`${method} ${path}`];
    const result = typeof route === "function" ? route(url, init) : route;
    if (!result) return new Response(JSON.stringify({ detail: "Not mocked" }), { status: 500 });
    return new Response(result.body === undefined ? "" : JSON.stringify(result.body), { status: result.status });
  });
  vi.stubGlobal("fetch", fn);
  return { fn, calls };
}
