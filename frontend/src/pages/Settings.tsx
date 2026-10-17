import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Database, KeyRound, Loader2, LogOut, Monitor, Moon, Palette, ShieldAlert, Sun, Trash2, UserRound } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { useToast } from "../context/ToastContext";
import { api, ApiError } from "../lib/api";
import type { Theme } from "../lib/types";
import { formatDate, initials, passwordProblem } from "../lib/format";
import { ConfirmDialog, ErrorAlert } from "../components/ui";

const THEMES: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

function ProfileSection() {
  const { user, setUser } = useAuth();
  const { notify } = useToast();
  const [name, setName] = useState(user?.full_name ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dirty = name.trim() !== user?.full_name;

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return setError("Name cannot be empty.");
    setBusy(true);
    setError(null);
    try {
      const updated = await api.updateProfile({ full_name: name.trim() });
      setUser(updated);
      setName(updated.full_name);
      notify("Profile updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update profile.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card" id="profile">
      <div className="card-header">
        <div>
          <h2>
            <UserRound aria-hidden /> Profile
          </h2>
          <p className="section-desc">Your name as shown in DocPredict.</p>
        </div>
      </div>
      <form className="card-body" onSubmit={save}>
        <div className="row" style={{ marginBottom: 20 }}>
          <span className="avatar" style={{ width: 52, height: 52, fontSize: "1.05rem" }} aria-hidden>
            {initials(user?.full_name ?? "")}
          </span>
          <div>
            <strong>{user?.full_name}</strong>
            <div className="small muted">Member since {user ? formatDate(user.created_at) : ""}</div>
          </div>
        </div>
        {error && (
          <div style={{ marginBottom: 16 }}>
            <ErrorAlert>{error}</ErrorAlert>
          </div>
        )}
        <div className="grid grid-2" style={{ gap: 16 }}>
          <div className="field">
            <label className="label" htmlFor="full_name">
              Full name
            </label>
            <input id="full_name" className="input" value={name} onChange={(e) => setName(e.target.value)} maxLength={100} autoComplete="name" />
          </div>
          <div className="field" style={{ marginTop: 0 }}>
            <label className="label" htmlFor="email_ro">
              Email
            </label>
            <input id="email_ro" className="input" value={user?.email ?? ""} disabled readOnly />
            <span className="hint">Email is used to sign in and cannot be changed.</span>
          </div>
        </div>
        <div className="form-actions">
          <button className="btn btn-secondary" type="button" disabled={!dirty || busy} onClick={() => setName(user?.full_name ?? "")}>
            Reset
          </button>
          <button className="btn btn-primary" disabled={!dirty || busy}>
            {busy && <Loader2 className="spin" aria-hidden />} Save changes
          </button>
        </div>
      </form>
    </section>
  );
}

function AppearanceSection() {
  const { setUser } = useAuth();
  const { theme, setTheme } = useTheme();
  const { notify } = useToast();
  const [saving, setSaving] = useState<Theme | null>(null);

  const choose = async (value: Theme) => {
    const previous = theme;
    setTheme(value);
    setSaving(value);
    try {
      setUser(await api.updateProfile({ theme: value }));
      notify(`Theme set to ${value}.`);
    } catch (err) {
      setTheme(previous);
      notify(err instanceof ApiError ? err.message : "Could not save theme.", "error");
    } finally {
      setSaving(null);
    }
  };

  return (
    <section className="card" id="appearance">
      <div className="card-header">
        <div>
          <h2>
            <Palette aria-hidden /> Appearance
          </h2>
          <p className="section-desc">Saved to your profile and applied whenever you sign in.</p>
        </div>
      </div>
      <div className="card-body">
        <div className="segmented" role="group" aria-label="Theme">
          {THEMES.map(({ value, label, icon: Icon }) => (
            <button key={value} type="button" aria-pressed={theme === value} onClick={() => choose(value)} disabled={saving !== null}>
              {saving === value ? <Loader2 className="spin" aria-hidden /> : <Icon aria-hidden />}
              {label}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

function PasswordSection() {
  const { notify } = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const problem = passwordProblem(next);
    if (problem) return setError(problem);
    if (next !== confirm) return setError("New passwords do not match.");
    setBusy(true);
    try {
      await api.changePassword(current, next);
      setCurrent("");
      setNext("");
      setConfirm("");
      notify("Password updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not change password.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card" id="security">
      <div className="card-header">
        <div>
          <h2>
            <KeyRound aria-hidden /> Password
          </h2>
          <p className="section-desc">Use at least 8 characters with a letter and a number.</p>
        </div>
      </div>
      <form className="card-body" onSubmit={submit}>
        {error && (
          <div style={{ marginBottom: 16 }}>
            <ErrorAlert>{error}</ErrorAlert>
          </div>
        )}
        <div className="field">
          <label className="label" htmlFor="current_password">
            Current password
          </label>
          <input id="current_password" className="input" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" />
        </div>
        <div className="grid grid-2" style={{ gap: 16, marginTop: 16 }}>
          <div className="field">
            <label className="label" htmlFor="new_password">
              New password
            </label>
            <input id="new_password" className="input" type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" />
          </div>
          <div className="field" style={{ marginTop: 0 }}>
            <label className="label" htmlFor="confirm_password">
              Confirm new password
            </label>
            <input id="confirm_password" className="input" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
          </div>
        </div>
        <div className="form-actions">
          <button className="btn btn-primary" disabled={busy || !current || !next || !confirm}>
            {busy && <Loader2 className="spin" aria-hidden />} Update password
          </button>
        </div>
      </form>
    </section>
  );
}

function DataSection() {
  const { notify } = useToast();
  const { clearSession } = useAuth();
  const navigate = useNavigate();
  const [confirmAll, setConfirmAll] = useState(false);
  const [confirmAccount, setConfirmAccount] = useState(false);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [dialogError, setDialogError] = useState<string | null>(null);

  const deleteAll = async () => {
    setBusy(true);
    try {
      const res = await api.deleteAllAnalyses();
      notify(res.detail);
      setConfirmAll(false);
    } catch (err) {
      notify(err instanceof ApiError ? err.message : "Could not delete analyses.", "error");
    } finally {
      setBusy(false);
    }
  };

  const deleteAccount = async () => {
    setBusy(true);
    setDialogError(null);
    try {
      await api.deleteAccount(password);
      clearSession();
      notify("Your account and all saved analyses were deleted.", "info");
      navigate("/", { replace: true });
    } catch (err) {
      setDialogError(err instanceof ApiError ? err.message : "Could not delete account.");
      setBusy(false);
    }
  };

  return (
    <section className="card danger-zone" id="data">
      <div className="card-header">
        <div>
          <h2>
            <Database aria-hidden /> Data &amp; privacy
          </h2>
          <p className="section-desc">What DocPredict keeps, and how to remove it.</p>
        </div>
      </div>
      <div className="card-body stack" style={{ gap: 18 }}>
        <div className="alert alert-info">
          <ShieldAlert aria-hidden />
          <div>
            <strong>Not stored:</strong> your original files and their full extracted text. Files are deleted from the
            server's temporary folder as soon as processing ends, including when it fails.
            <br />
            <strong>Stored per analysis:</strong> file name, type and size, word count, predicted type and scores,
            uncertainty reasons, extractive summary, keywords, detected fields (dates, amounts, reference numbers,
            emails, phone numbers), evidence sentences, attention level, bookmark flag and timestamp. Summaries,
            evidence and detected fields are short excerpts of your document.
          </div>
        </div>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <h3>Delete all saved analyses</h3>
            <p className="section-desc">Your account stays active.</p>
          </div>
          <button className="btn btn-danger-ghost" onClick={() => setConfirmAll(true)}>
            <Trash2 aria-hidden /> Delete all analyses
          </button>
        </div>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <h3>Delete account</h3>
            <p className="section-desc">Permanently removes your account and every saved analysis.</p>
          </div>
          <button className="btn btn-danger" onClick={() => setConfirmAccount(true)}>
            <Trash2 aria-hidden /> Delete account
          </button>
        </div>
      </div>

      <ConfirmDialog
        open={confirmAll}
        title="Delete all analyses?"
        message="Every saved analysis in your history will be permanently removed. This cannot be undone."
        confirmLabel="Delete all"
        busy={busy}
        onConfirm={deleteAll}
        onCancel={() => setConfirmAll(false)}
      />
      <ConfirmDialog
        open={confirmAccount}
        title="Delete your account?"
        message="Your account and all saved analyses will be permanently deleted. Enter your password to confirm."
        confirmLabel="Delete account"
        busy={busy}
        onConfirm={deleteAccount}
        onCancel={() => {
          setConfirmAccount(false);
          setPassword("");
          setDialogError(null);
        }}
      >
        <div className="field" style={{ marginTop: 16 }}>
          <label className="label" htmlFor="delete_password">
            Password
          </label>
          <input id="delete_password" className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          {dialogError && <span className="field-error">{dialogError}</span>}
        </div>
      </ConfirmDialog>
    </section>
  );
}

export default function Settings() {
  const { logout } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();
  const signOut = async () => {
    await logout();
    notify("You have been signed out.", "info");
    navigate("/login", { replace: true });
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <p>Manage your profile, appearance, password and data.</p>
        </div>
        <div className="page-actions">
          <button className="btn btn-secondary" onClick={signOut}>
            <LogOut aria-hidden /> Sign out
          </button>
        </div>
      </div>
      <div className="settings-grid">
        <nav className="settings-nav" aria-label="Settings sections">
          <a href="#profile">
            <UserRound aria-hidden /> Profile
          </a>
          <a href="#appearance">
            <Palette aria-hidden /> Appearance
          </a>
          <a href="#security">
            <KeyRound aria-hidden /> Password
          </a>
          <a href="#data">
            <Database aria-hidden /> Data &amp; privacy
          </a>
        </nav>
        <div className="stack">
          <ProfileSection />
          <AppearanceSection />
          <PasswordSection />
          <DataSection />
        </div>
      </div>
    </>
  );
}
