import { useCallback } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth, useClerk } from "@clerk/react";
import { APP_TOKEN_KEY, getAppToken } from "@/lib/api";
import { FullPageLoader } from "@/components/common";

export function useSession() {
  const { isLoaded, isSignedIn } = useAuth();
  const clerk = useClerk();
  const appToken = getAppToken();
  const signOut = useCallback(async () => {
    if (getAppToken()) {
      localStorage.removeItem(APP_TOKEN_KEY);
      window.location.href = "/";
      return;
    }
    await clerk.signOut({ redirectUrl: "/" });
  }, [clerk]);
  return {
    isLoaded: Boolean(appToken) || isLoaded,
    isSignedIn: Boolean(appToken) || Boolean(isSignedIn),
    viaWhatsApp: Boolean(appToken),
    signOut,
  };
}

export function RequireAuth({ children }) {
  const { isLoaded, isSignedIn } = useSession();
  const location = useLocation();
  if (!isLoaded) return <FullPageLoader label="Opening KONNTO…" />;
  if (!isSignedIn) return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />;
  return children;
}
