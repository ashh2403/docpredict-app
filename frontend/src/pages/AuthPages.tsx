import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { CheckCircle2, Eye, EyeOff, Loader2, Lock, Mail, User as UserIcon } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { ApiError } from "../lib/api";
import { passwordProblem, passwordScore } from "../lib/format";
import { ErrorAlert, Logo } from "../components/ui";

function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="auth">
      <aside className="auth-aside">
        <Logo />
        <div style={{ position: "relative", zIndex: 1 }}>
          <h2>Document analysis you can actually explain.</h2>
          <p>Classify, summarise and extract key details from your documents, with the evidence behind every result.</p>
          <ul className="auth-points">
            <li>
              <CheckCircle2 aria-hidden /> Processed locally. Nothing is sent to third-party AI services.
            </li>
            <li>
              <CheckCircle2 aria-hidden /> Uploaded files are deleted immediately after analysis.
            </li>
            <li>
              <CheckCircle2 aria-hidden /> Uncertain results are labelled as uncertain.
            </li>
          </ul>
        </div>
        <p className="small" style={{ color: "#8d91bd", position: "relative", zIndex: 1 }}>
          Illustrative tool: not legal, medical or financial advice.
        </p>
      </aside>
      <main className="auth-main">
        <div className="auth-card">
          <div className="auth-mobile-brand">
            <Logo />
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}

function PasswordInput({
  id,
  value,
  onChange,
  autoComplete,
  invalid,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete: string;
  invalid?: boolean;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="input-icon">
      <Lock aria-hidden />
      <input
        id={id}
        className="input"
        type={show ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
        required
        aria-invalid={invalid || undefined}
        style={{ paddingRight: 48 }}
      />
      <button
        type="button"
        className="icon-btn input-action"
        onClick={() => setShow((s) => !s)}
        aria-label={show ? "Hide password" : "Show password"}
      >
        {show ? <EyeOff /> : <Eye />}
      </button>
    </div>
  );
}

export function LoginPage() {
  const { login, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email.trim(), password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from !== "/login" ? from : "/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign-in failed. Please try again.");
      setBusy(false);
    }
  };

  return (
    <AuthLayout>
      <h1>Welcome back</h1>
      <p>Sign in to analyse documents and review your history.</p>
      {sessionExpired && !error && (
        <div className="alert alert-info" style={{ marginBottom: 18 }}>
          Your session ended. Please sign in again.
        </div>
      )}
      <form onSubmit={submit} noValidate>
        {error && (
          <div style={{ marginBottom: 18 }}>
            <ErrorAlert>{error}</ErrorAlert>
          </div>
        )}
        <div className="field">
          <label className="label" htmlFor="email">
            Email
          </label>
          <div className="input-icon">
            <Mail aria-hidden />
            <input
              id="email"
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="you@company.com"
              required
            />
          </div>
        </div>
        <div className="field">
          <label className="label" htmlFor="password">
            Password
          </label>
          <PasswordInput id="password" value={password} onChange={setPassword} autoComplete="current-password" />
        </div>
        <button className="btn btn-primary btn-lg btn-block" style={{ marginTop: 24 }} disabled={busy || !email || !password}>
          {busy && <Loader2 className="spin" aria-hidden />}
          Sign in
        </button>
      </form>
      <p className="auth-switch">
        New to DocPredict? <Link to="/register">Create an account</Link>
      </p>
    </AuthLayout>
  );
}

export function RegisterPage() {
  const { register } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [touched, setTouched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const pwProblem = passwordProblem(password);
  const mismatch = confirm.length > 0 && confirm !== password;
  const score = password ? Math.max(1, passwordScore(password)) : 0;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    setError(null);
    if (!name.trim()) return setError("Please enter your name.");
    if (pwProblem) return setError(pwProblem);
    if (confirm !== password) return setError("Passwords do not match.");
    setBusy(true);
    try {
      await register(email.trim(), name.trim(), password);
      notify("Account created. Welcome to DocPredict!");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed. Please try again.");
      setBusy(false);
    }
  };

  return (
    <AuthLayout>
      <h1>Create your account</h1>
      <p>Start analysing documents in under a minute.</p>
      <form onSubmit={submit} noValidate>
        {error && (
          <div style={{ marginBottom: 18 }}>
            <ErrorAlert>{error}</ErrorAlert>
          </div>
        )}
        <div className="field">
          <label className="label" htmlFor="name">
            Full name
          </label>
          <div className="input-icon">
            <UserIcon aria-hidden />
            <input
              id="name"
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
              maxLength={100}
              placeholder="Jane Doe"
              required
            />
          </div>
        </div>
        <div className="field">
          <label className="label" htmlFor="email">
            Email
          </label>
          <div className="input-icon">
            <Mail aria-hidden />
            <input
              id="email"
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="you@company.com"
              required
            />
          </div>
        </div>
        <div className="field">
          <label className="label" htmlFor="password">
            Password
          </label>
          <PasswordInput
            id="password"
            value={password}
            onChange={setPassword}
            autoComplete="new-password"
            invalid={touched && !!pwProblem}
          />
          <div className="pw-meter" data-score={score} aria-hidden>
            <span />
            <span />
            <span />
            <span />
          </div>
          <span className="hint">At least 8 characters, including a letter and a number.</span>
        </div>
        <div className="field">
          <label className="label" htmlFor="confirm">
            Confirm password
          </label>
          <PasswordInput id="confirm" value={confirm} onChange={setConfirm} autoComplete="new-password" invalid={mismatch} />
          {mismatch && <span className="field-error">Passwords do not match.</span>}
        </div>
        <button
          className="btn btn-primary btn-lg btn-block"
          style={{ marginTop: 24 }}
          disabled={busy || !name || !email || !password || !confirm}
        >
          {busy && <Loader2 className="spin" aria-hidden />}
          Create account
        </button>
      </form>
      <p className="auth-switch">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </AuthLayout>
  );
}
