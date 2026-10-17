import { lazy, Suspense } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { FileQuestion } from "lucide-react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { ToastProvider } from "./context/ToastContext";
import AppLayout from "./components/AppLayout";
import { PublicOnly, RequireAuth } from "./components/RouteGuards";
import { EmptyState, Spinner } from "./components/ui";
import Landing from "./pages/Landing";
import { LoginPage, RegisterPage } from "./pages/AuthPages";

// Authenticated pages are split out so the public pages do not download the charting library.
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Analyze = lazy(() => import("./pages/Analyze"));
const Result = lazy(() => import("./pages/Result"));
const History = lazy(() => import("./pages/History"));
const Settings = lazy(() => import("./pages/Settings"));
const ModelInfo = lazy(() => import("./pages/ModelInfo"));

function NotFound() {
  const { status } = useAuth();
  return (
    <div className="center-screen">
      <EmptyState
        icon={FileQuestion}
        title="Page not found"
        action={
          <Link to={status === "authenticated" ? "/dashboard" : "/"} className="btn btn-primary">
            Go to {status === "authenticated" ? "dashboard" : "home page"}
          </Link>
        }
      >
        The page you are looking for does not exist or has moved.
      </EmptyState>
    </div>
  );
}

export function AppRoutes() {
  return (
    <Suspense fallback={<Spinner label="Loading page" />}>
      <Routes>
        <Route element={<PublicOnly />}>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>
        <Route element={<RequireAuth />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/analyze" element={<Analyze />} />
            <Route path="/analyses/:id" element={<Result />} />
            <Route path="/history" element={<History />} />
            <Route path="/model" element={<ModelInfo />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <ToastProvider>
        <AuthProvider>{children}</AuthProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Providers>
        <AppRoutes />
      </Providers>
    </BrowserRouter>
  );
}
