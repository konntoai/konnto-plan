import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useApi } from "@/lib/api";

const MeContext = createContext(null);

export function MeProvider({ children }) {
  const api = useApi();
  const [me, setMe] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await api.get("/me");
      setMe(data);
      setError(null);
      return data;
    } catch (e) {
      setError(e);
      return null;
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return <MeContext.Provider value={{ me, loading, error, refresh, setMe }}>{children}</MeContext.Provider>;
}

export function useMe() {
  const ctx = useContext(MeContext);
  if (!ctx) throw new Error("useMe must be used inside MeProvider");
  return ctx;
}
