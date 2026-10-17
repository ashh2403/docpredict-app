export type Theme = "light" | "dark" | "system";
export type Priority = "low" | "medium" | "high";

export interface User {
  id: number;
  email: string;
  full_name: string;
  theme: Theme;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Keyword {
  term: string;
  score: number;
  count: number;
}

export interface CategoryScore {
  category: string;
  label: string;
  score: number;
}

export interface TermWeight {
  term: string;
  weight: number;
}

export interface Evidence {
  sentence: string;
  terms: string[];
  strength: number;
  share: number;
}

export interface Explanation {
  supporting_terms: TermWeight[];
  opposing_terms: TermWeight[];
  runner_up: string;
  evidence: Evidence[];
  vocabulary_coverage: number;
  method: string;
}

export interface ExtractedFields {
  emails?: string[];
  phone_numbers?: string[];
  dates?: string[];
  amounts?: string[];
  percentages?: string[];
  reference_numbers?: string[];
  key_values?: { label: string; value: string }[];
}

export interface AnalysisSummary {
  id: number;
  filename: string;
  file_type: string;
  file_size: number;
  word_count: number;
  category: string;
  category_label: string;
  confidence: number;
  is_uncertain: boolean;
  priority: Priority;
  bookmarked: boolean;
  summary: string;
  keywords: Keyword[];
  created_at: string;
}

export interface AnalysisDetail extends AnalysisSummary {
  page_count: number | null;
  char_count: number;
  uncertainty_reasons: string[];
  top_predictions: CategoryScore[];
  explanation: Explanation;
  extracted_fields: ExtractedFields;
  priority_reasons: string[];
  model_version: string;
  processing_ms: number;
}

export interface AnalysisPage {
  items: AnalysisSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface Stats {
  total: number;
  bookmarked: number;
  uncertain: number;
  average_confidence: number | null;
  by_category: { category: string; label: string; count: number }[];
  by_priority: Record<Priority, number>;
  per_day: { date: string; count: number }[];
}

export interface EvaluationSet {
  n: number;
  accuracy: number;
  macro_f1: number;
  per_class: Record<string, { precision: number; recall: number; "f1-score": number; support: number }>;
  confusion_matrix: { labels: string[]; matrix: number[][] };
  calibration: { ece: number; bins: { range: [number, number]; count: number; accuracy: number; mean_score: number }[] };
  uncertainty_policy: { coverage: number; accuracy_on_confident: number | null; flagged_uncertain: number };
}

export interface ModelInfo {
  model_version: string;
  trained_at: string;
  algorithm: string;
  hyperparameters: Record<string, number>;
  categories: { category: string; label: string }[];
  dataset: { type: string; description: string; n_total: number; n_train: number; n_test: number };
  evaluation: Partial<Record<"heldout_synthetic" | "handwritten_dev" | "handwritten_blind", EvaluationSet>>;
  uncertainty_policy: { description: string; min_top_score: number; min_margin: number; min_words: number; min_vocabulary_coverage: number };
  caveats: string[];
  supported_file_types: string[];
  max_upload_mb: number;
}

export interface HistoryQuery {
  q?: string;
  category?: string;
  priority?: Priority | "";
  bookmarked?: boolean;
  uncertain?: boolean;
  sort?: "newest" | "oldest" | "confidence" | "name";
  page?: number;
  page_size?: number;
}
