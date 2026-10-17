import { Suspense, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  BrainCircuit,
  History,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Settings,
  Sun,
  UploadCloud,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { useToast } from "../context/ToastContext";
import { api } from "../lib/api";
import { initials } from "../lib/format";
import { Logo, Spinner } from "./ui";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/analyze", label: "Analyze document", icon: UploadCloud },
  { to: "/history", label: "History", icon: History },
];
const NAV_SECONDARY = [
  { to: "/model", label: "Model & accuracy", icon: BrainCircuit },
  { to: "/settings", label: "Settings", icon: Settings },
];

function titleFor(pathname: string): string {
  if (pathname.startsWith("/analyses/")) return "Analysis result";
  const all = [...NAV, ...NAV_SECONDARY];
  return all.find((n) => pathname.startsWith(n.to))?.label ?? "DocPredict";
}

export default function AppLayout() {
  const { user, logout, setUser } = useAuth();
  const { resolved, setTheme } = useTheme();
  const { notify } = useToast();
  const [navOpen, setNavOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => setNavOpen(false), [location.pathname]);
  useEffect(() => {
    document.title = `${titleFor(location.pathname)} · DocPredict`;
  }, [location.pathname]);

  const toggleTheme = async () => {
    const next = resolved === "dark" ? "light" : "dark";
    setTheme(next);
    try {
      setUser(await api.updateProfile({ theme: next }));
    } catch {
      notify("Theme changed for this browser, but could not be saved to your profile.", "error");
    }
  };

  const handleLogout = async () => {
    await logout();
    notify("You have been signed out.", "info");
    navigate("/login", { replace: true });
  };

  const renderLinks = (items: typeof NAV) =>
    items.map(({ to, label, icon: Icon }) => (
      <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "active" : undefined)}>
        <Icon aria-hidden />
        {label}
      </NavLink>
    ));

  return (
    <div className={`shell${navOpen ? " nav-open" : ""}`}>
      <aside className="sidebar" aria-label="Main navigation">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <Logo to="/dashboard" />
          {navOpen && (
            <button className="icon-btn" onClick={() => setNavOpen(false)} aria-label="Close menu">
              <X />
            </button>
          )}
        </div>
        <div className="nav-section">Workspace</div>
        <nav className="nav">{renderLinks(NAV)}</nav>
        <div className="nav-section">Account</div>
        <nav className="nav">{renderLinks(NAV_SECONDARY)}</nav>
        <div className="sidebar-footer">
          <div className="user-chip">
            <span className="avatar" aria-hidden>
              {initials(user?.full_name ?? "")}
            </span>
            <div className="who">
              <strong>{user?.full_name}</strong>
              <span>{user?.email}</span>
            </div>
            <button className="icon-btn" onClick={handleLogout} aria-label="Sign out" title="Sign out">
              <LogOut />
            </button>
          </div>
        </div>
      </aside>
      <div className="scrim" onClick={() => setNavOpen(false)} aria-hidden />

      <div className="main">
        <header className="topbar">
          <button className="icon-btn menu-btn" onClick={() => setNavOpen(true)} aria-label="Open menu">
            <Menu />
          </button>
          <div className="topbar-title">{titleFor(location.pathname)}</div>
          <div className="topbar-actions">
            <button
              className="icon-btn"
              onClick={toggleTheme}
              aria-label={resolved === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              title="Toggle theme"
            >
              {resolved === "dark" ? <Sun /> : <Moon />}
            </button>
            <NavLink to="/analyze" className="btn btn-primary btn-sm">
              <UploadCloud aria-hidden />
              <span>Upload</span>
            </NavLink>
          </div>
        </header>
        <main className="content" key={location.pathname}>
          <Suspense fallback={<Spinner label="Loading page" />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
