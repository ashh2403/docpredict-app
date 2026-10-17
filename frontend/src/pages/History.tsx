import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Bookmark, BookmarkCheck, ChevronLeft, ChevronRight, FilterX, History as HistoryIcon, Search, Trash2, UploadCloud } from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { AnalysisPage, AnalysisSummary, HistoryQuery } from "../lib/types";
import { formatDate, formatPercent } from "../lib/format";
import { useToast } from "../context/ToastContext";
import {
  CategoryBadge,
  ConfirmDialog,
  EmptyState,
  ErrorAlert,
  FileTypeIcon,
  PriorityBadge,
  ScoreBar,
  UncertainBadge,
} from "../components/ui";

const CATEGORIES: [string, string][] = [
  ["invoice", "Invoice"],
  ["contract", "Contract / Agreement"],
  ["resume", "Resume / CV"],
  ["medical_report", "Medical Report"],
  ["financial_report", "Financial Report"],
  ["research_paper", "Research Paper"],
  ["meeting_minutes", "Meeting Minutes"],
  ["legal_notice", "Legal Notice"],
];
const PAGE_SIZE = 10;

export default function History() {
  const [params, setParams] = useSearchParams();
  const { notify } = useToast();
  const [data, setData] = useState<AnalysisPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState(params.get("q") ?? "");
  const [pendingDelete, setPendingDelete] = useState<AnalysisSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [busyIds, setBusyIds] = useState<Set<number>>(new Set());

  const query: HistoryQuery = useMemo(
    () => ({
      q: params.get("q") ?? undefined,
      category: params.get("category") ?? undefined,
      priority: (params.get("priority") as HistoryQuery["priority"]) ?? undefined,
      bookmarked: params.get("bookmarked") === "true" ? true : undefined,
      uncertain: params.get("uncertain") === "true" ? true : params.get("uncertain") === "false" ? false : undefined,
      sort: (params.get("sort") as HistoryQuery["sort"]) ?? "newest",
      page: Number(params.get("page") ?? 1) || 1,
      page_size: PAGE_SIZE,
    }),
    [params],
  );

  const updateParam = useCallback(
    (key: string, value: string | null) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (value === null || value === "") next.delete(key);
          else next.set(key, value);
          if (key !== "page") next.delete("page");
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  // Debounce the search box into the URL.
  useEffect(() => {
    const current = params.get("q") ?? "";
    if (search.trim() === current) return;
    const t = window.setTimeout(() => updateParam("q", search.trim()), 300);
    return () => window.clearTimeout(t);
  }, [search, params, updateParam]);

  const load = useCallback(() => {
    setLoading(true);
    api
      .listAnalyses(query)
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load history."))
      .finally(() => setLoading(false));
  }, [query]);

  useEffect(load, [load]);

  const hasFilters = ["q", "category", "priority", "bookmarked", "uncertain"].some((k) => params.get(k));
  const clearFilters = () => {
    setSearch("");
    setParams(new URLSearchParams(), { replace: true });
  };

  const setBusy = (id: number, on: boolean) =>
    setBusyIds((s) => {
      const n = new Set(s);
      if (on) n.add(id);
      else n.delete(id);
      return n;
    });

  const toggleBookmark = async (item: AnalysisSummary) => {
    setBusy(item.id, true);
    try {
      const updated = await api.setBookmark(item.id, !item.bookmarked);
      if (query.bookmarked && !updated.bookmarked) {
        load();
      } else {
        setData((d) => d && { ...d, items: d.items.map((i) => (i.id === item.id ? { ...i, bookmarked: updated.bookmarked } : i)) });
      }
      notify(updated.bookmarked ? "Added to bookmarks." : "Removed from bookmarks.");
    } catch (e) {
      notify(e instanceof ApiError ? e.message : "Could not update bookmark.", "error");
    } finally {
      setBusy(item.id, false);
    }
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await api.deleteAnalysis(pendingDelete.id);
      notify("Analysis deleted.");
      setPendingDelete(null);
      if (data && data.items.length === 1 && (query.page ?? 1) > 1) updateParam("page", String((query.page ?? 1) - 1));
      else load();
    } catch (e) {
      notify(e instanceof ApiError ? e.message : "Could not delete analysis.", "error");
    } finally {
      setDeleting(false);
    }
  };

  const page = query.page ?? 1;
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  const actions = (item: AnalysisSummary) => (
    <div className="row-actions">
      <button
        className={`icon-btn${item.bookmarked ? " active" : ""}`}
        onClick={(e) => {
          e.preventDefault();
          toggleBookmark(item);
        }}
        disabled={busyIds.has(item.id)}
        aria-label={item.bookmarked ? `Remove bookmark from ${item.filename}` : `Bookmark ${item.filename}`}
        aria-pressed={item.bookmarked}
        title={item.bookmarked ? "Remove bookmark" : "Bookmark"}
      >
        {item.bookmarked ? <BookmarkCheck /> : <Bookmark />}
      </button>
      <button
        className="icon-btn danger"
        onClick={(e) => {
          e.preventDefault();
          setPendingDelete(item);
        }}
        aria-label={`Delete ${item.filename}`}
        title="Delete"
      >
        <Trash2 />
      </button>
    </div>
  );

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Analysis history</h1>
          <p>Search, filter and revisit every document you have analysed.</p>
        </div>
        <div className="page-actions">
          <Link to="/analyze" className="btn btn-primary">
            <UploadCloud aria-hidden /> New analysis
          </Link>
        </div>
      </div>

      <div className="card">
        <div className="toolbar">
          <div className="input-icon search">
            <Search aria-hidden />
            <input
              className="input"
              type="search"
              placeholder="Search file names, summaries, keywords…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search history"
              maxLength={100}
            />
          </div>
          <select className="select" value={query.category ?? ""} onChange={(e) => updateParam("category", e.target.value)} aria-label="Filter by type">
            <option value="">All types</option>
            {CATEGORIES.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
          <select className="select" value={query.priority ?? ""} onChange={(e) => updateParam("priority", e.target.value)} aria-label="Filter by attention level">
            <option value="">Any attention</option>
            <option value="high">High attention</option>
            <option value="medium">Medium attention</option>
            <option value="low">Low attention</option>
          </select>
          <select
            className="select"
            value={params.get("bookmarked") === "true" ? "bookmarked" : params.get("uncertain") ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              setParams(
                (prev) => {
                  const next = new URLSearchParams(prev);
                  next.delete("bookmarked");
                  next.delete("uncertain");
                  next.delete("page");
                  if (v === "bookmarked") next.set("bookmarked", "true");
                  else if (v) next.set("uncertain", v);
                  return next;
                },
                { replace: true },
              );
            }}
            aria-label="Filter by status"
          >
            <option value="">All results</option>
            <option value="bookmarked">Bookmarked</option>
            <option value="true">Uncertain only</option>
            <option value="false">Confident only</option>
          </select>
          <select className="select" value={query.sort} onChange={(e) => updateParam("sort", e.target.value === "newest" ? null : e.target.value)} aria-label="Sort">
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="confidence">Highest score</option>
            <option value="name">File name A–Z</option>
          </select>
          {hasFilters && (
            <button className="btn btn-ghost btn-sm" onClick={clearFilters}>
              <FilterX aria-hidden /> Clear
            </button>
          )}
        </div>

        {error && (
          <div className="card-body">
            <ErrorAlert>{error}</ErrorAlert>
          </div>
        )}

        {!error && data && data.items.length === 0 && !loading && (
          hasFilters ? (
            <EmptyState icon={Search} title="No matching analyses" action={<button className="btn btn-secondary" onClick={clearFilters}>Clear filters</button>}>
              Try a different search term or remove some filters.
            </EmptyState>
          ) : (
            <EmptyState icon={HistoryIcon} title="Your history is empty" action={<Link to="/analyze" className="btn btn-primary"><UploadCloud aria-hidden /> Analyze a document</Link>}>
              Every document you analyse is saved here so you can come back to it.
            </EmptyState>
          )
        )}

        {!error && data && data.items.length > 0 && (
          <div style={{ opacity: loading ? 0.6 : 1, transition: "opacity 0.15s" }}>
            <div className="table-wrap responsive">
              <table className="table">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Predicted type</th>
                    <th>Model score</th>
                    <th>Attention</th>
                    <th>Date</th>
                    <th>
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <div className="doc-cell">
                          <FileTypeIcon type={item.file_type} />
                          <div style={{ minWidth: 0 }}>
                            <Link to={`/analyses/${item.id}`} title={item.filename}>
                              {item.filename}
                            </Link>
                            <span className="sub">
                              {item.file_type.toUpperCase()} · {item.word_count.toLocaleString()} words
                            </span>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div className="row" style={{ gap: 6 }}>
                          <CategoryBadge label={item.category_label} uncertain={item.is_uncertain} />
                          {item.is_uncertain && <UncertainBadge />}
                        </div>
                      </td>
                      <td>
                        <div className="conf-cell">
                          <ScoreBar value={item.confidence} />
                          <span className="v">{formatPercent(item.confidence)}</span>
                        </div>
                      </td>
                      <td>
                        <PriorityBadge priority={item.priority} />
                      </td>
                      <td className="muted" style={{ whiteSpace: "nowrap" }}>
                        {formatDate(item.created_at)}
                      </td>
                      <td>{actions(item)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mobile-list">
              {data.items.map((item) => (
                <Link key={item.id} to={`/analyses/${item.id}`} className="mobile-item">
                  <div className="top">
                    <div className="doc-cell" style={{ minWidth: 0 }}>
                      <FileTypeIcon type={item.file_type} />
                      <div style={{ minWidth: 0 }}>
                        <strong style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.filename}</strong>
                        <span className="sub">
                          {formatDate(item.created_at)} · {formatPercent(item.confidence)} score
                        </span>
                      </div>
                    </div>
                    {actions(item)}
                  </div>
                  <div className="badges">
                    <CategoryBadge label={item.category_label} uncertain={item.is_uncertain} />
                    {item.is_uncertain && <UncertainBadge />}
                    <PriorityBadge priority={item.priority} />
                  </div>
                </Link>
              ))}
            </div>

            <div className="pagination">
              <span>
                Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, data.total)} of {data.total}
              </span>
              <div className="row">
                <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => updateParam("page", String(page - 1))}>
                  <ChevronLeft aria-hidden /> Previous
                </button>
                <span>
                  Page {page} of {totalPages}
                </span>
                <button className="btn btn-secondary btn-sm" disabled={page >= totalPages} onClick={() => updateParam("page", String(page + 1))}>
                  Next <ChevronRight aria-hidden />
                </button>
              </div>
            </div>
          </div>
        )}

        {!data && loading && !error && (
          <div className="card-body stack" style={{ gap: 12 }}>
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="skeleton" style={{ height: 44 }} />
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!pendingDelete}
        title="Delete this analysis?"
        message={`The saved result for "${pendingDelete?.filename}" will be permanently removed.`}
        confirmLabel="Delete"
        busy={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  );
}
