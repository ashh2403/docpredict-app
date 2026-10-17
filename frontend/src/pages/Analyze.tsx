import { useEffect, useRef, useState, type DragEvent } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, Circle, FileUp, Loader2, LockKeyhole, RefreshCw, Trash2, UploadCloud, X } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { useToast } from "../context/ToastContext";
import { formatBytes, MAX_UPLOAD_MB, validateFile } from "../lib/format";
import { ErrorAlert, FileTypeIcon } from "../components/ui";

type Phase = "idle" | "uploading" | "analyzing";

const STEPS = [
  "Uploading securely",
  "Server is validating the file, extracting text, classifying and explaining",
];

export default function Analyze() {
  const navigate = useNavigate();
  const { notify } = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const step = phase === "analyzing" ? 1 : 0;

  const choose = (f: File | undefined | null) => {
    if (!f) return;
    setError(validateFile(f));
    setFile(f);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (phase !== "idle") return;
    choose(e.dataTransfer.files?.[0]);
  };

  const reset = () => {
    setFile(null);
    setError(null);
    setProgress(0);
    if (inputRef.current) inputRef.current.value = "";
  };

  const start = async () => {
    if (!file) return;
    const problem = validateFile(file);
    if (problem) return setError(problem);
    setError(null);
    setPhase("uploading");
    setProgress(0);
    abortRef.current = new AbortController();
    try {
      const result = await api.uploadDocument(
        file,
        (f) => {
          setProgress(f);
          if (f >= 1) setPhase("analyzing");
        },
        abortRef.current.signal,
      );
      notify("Analysis complete and saved to your history.");
      navigate(`/analyses/${result.id}`);
    } catch (err) {
      setPhase("idle");
      if (err instanceof ApiError && err.status === -1) return;
      setError(err instanceof ApiError ? err.message : "Analysis failed. Please try again.");
    }
  };

  const cancel = () => abortRef.current?.abort();
  const busy = phase !== "idle";
  const ext = file?.name.split(".").pop()?.toLowerCase() ?? "";

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Analyze a document</h1>
          <p>
            DocPredict extracts the text, predicts the document type with a locally trained model, and explains the
            result with evidence from the document.
          </p>
        </div>
      </div>

      <div className="grid grid-main">
        <div className="card card-pad stack">
          <div
            className={`dropzone${dragging ? " dragging" : ""}${busy ? " disabled" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              if (!busy) setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => !busy && inputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && !busy && inputRef.current?.click()}
            aria-label="Choose a document to upload"
          >
            <span className="dropzone-icon">
              <UploadCloud aria-hidden />
            </span>
            <div>
              <h2>Drop your document here</h2>
              <p className="muted" style={{ marginTop: 4 }}>
                or <span style={{ color: "var(--primary-text)", fontWeight: 600 }}>browse files</span> on your device
              </p>
            </div>
            <div className="file-types">
              <span className="badge badge-neutral">PDF</span>
              <span className="badge badge-neutral">DOCX</span>
              <span className="badge badge-neutral">TXT</span>
              <span className="badge badge-neutral">Max {MAX_UPLOAD_MB} MB</span>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
              hidden
              data-testid="file-input"
              onChange={(e) => choose(e.target.files?.[0])}
            />
          </div>

          {file && (
            <div className="file-row">
              <FileTypeIcon type={ext} />
              <div className="meta">
                <strong title={file.name}>{file.name}</strong>
                <span className="small muted">
                  {formatBytes(file.size)} · {ext.toUpperCase() || "Unknown type"}
                </span>
              </div>
              {!busy && (
                <button className="icon-btn danger" onClick={reset} aria-label="Remove file">
                  <Trash2 />
                </button>
              )}
            </div>
          )}

          {error && (
            <ErrorAlert>
              <strong>We could not analyse this file.</strong> {error}
            </ErrorAlert>
          )}

          {busy && (
            <div className="stack" style={{ gap: 14 }} aria-live="polite">
              <div className={`progress${phase === "analyzing" ? " indeterminate" : ""}`}>
                <span style={{ width: `${Math.round(progress * 100)}%` }} />
              </div>
              <div className="steps">
                {STEPS.map((label, i) => {
                  const state = i < step ? "done" : i === step ? "active" : "";
                  return (
                    <div key={label} className={`step ${state}`}>
                      {state === "done" ? <CheckCircle2 aria-hidden /> : state === "active" ? <Loader2 className="spin" aria-hidden /> : <Circle aria-hidden />}
                      {label}
                      {i === 0 && phase === "uploading" && ` (${Math.round(progress * 100)}%)`}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="row" style={{ justifyContent: "flex-end" }}>
            {busy ? (
              <button className="btn btn-secondary" onClick={cancel} disabled={phase === "analyzing"}>
                <X aria-hidden /> Cancel upload
              </button>
            ) : (
              error &&
              file && (
                <button className="btn btn-secondary" onClick={reset}>
                  <RefreshCw aria-hidden /> Choose another file
                </button>
              )
            )}
            <button className="btn btn-primary" onClick={start} disabled={!file || busy || !!validateFile(file)}>
              {busy ? <Loader2 className="spin" aria-hidden /> : <FileUp aria-hidden />}
              {busy ? "Analyzing…" : "Analyze document"}
            </button>
          </div>
        </div>

        <div className="stack">
          <div className="card card-pad">
            <h2 className="row" style={{ gap: 10 }}>
              <LockKeyhole size={18} color="var(--primary)" aria-hidden /> What happens to your file
            </h2>
            <ul className="list-plain retained" style={{ marginTop: 14 }}>
              <li>
                <CheckCircle2 aria-hidden /> The file is checked on the server (type, size, structure) and processed
                locally. Nothing is sent to third-party services.
              </li>
              <li>
                <CheckCircle2 aria-hidden /> The uploaded file and its full text are deleted as soon as the analysis
                finishes, even if it fails.
              </li>
              <li>
                <CheckCircle2 aria-hidden /> Saved: file name, size, predicted type and scores, a short extractive
                summary, keywords, detected fields (such as dates, amounts, emails) and evidence sentences.
              </li>
              <li>
                <CheckCircle2 aria-hidden /> You can delete any saved analysis, or all of them, at any time.
              </li>
            </ul>
          </div>
          <div className="card card-pad">
            <h2>Supported document types</h2>
            <p className="muted small" style={{ marginTop: 6 }}>
              The model recognises: invoices, contracts and agreements, resumes and CVs, medical reports, financial
              reports, research papers, meeting minutes and legal notices. Other documents will be flagged as
              uncertain. Scanned images without a text layer cannot be read.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
