import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Spinner } from "./ui";

export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <Spinner label="Restoring session" />;
  if (status === "anonymous") return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}

export function PublicOnly() {
  const { status } = useAuth();
  if (status === "loading") return <Spinner label="Restoring session" />;
  if (status === "authenticated") return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}
