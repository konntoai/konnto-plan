import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ClerkProvider } from "@clerk/react";
import { useTheme } from "@/context/ThemeContext";

// Brand Clerk once per theme: it styles sign-in, sign-up and the user menu.
const PALETTE = {
  dark: {
    colorPrimary: "#3D71FF",
    colorPrimaryForeground: "#ffffff",
    colorForeground: "#F1F6FD",
    colorMutedForeground: "#A2ADC3",
    colorBackground: "#0A1230",
    colorInput: "#0F162F",
    colorInputForeground: "#F1F6FD",
    colorBorder: "#1C2540",
    colorNeutral: "#F1F6FD",
    colorDanger: "#FF5A66",
  },
  light: {
    colorPrimary: "#1453FF",
    colorPrimaryForeground: "#ffffff",
    colorForeground: "#11182C",
    colorMutedForeground: "#566176",
    colorBackground: "#ffffff",
    colorInput: "#F4F6FB",
    colorInputForeground: "#11182C",
    colorBorder: "#DADFE8",
    colorNeutral: "#11182C",
    colorDanger: "#E0243A",
  },
};

const buildAppearance = (theme) => ({
  variables: {
    ...PALETTE[theme === "light" ? "light" : "dark"],
    fontFamily: "Figtree, ui-sans-serif, -apple-system, sans-serif",
    fontFamilyButtons: "Figtree, ui-sans-serif, -apple-system, sans-serif",
    borderRadius: "0.85rem",
  },
  elements: {
    cardBox: "rounded-3xl border border-[hsl(var(--glass-border))] shadow-[0_30px_80px_-30px_hsl(var(--glow-blue))]",
    headerTitle: "font-display font-extrabold tracking-tight",
    formButtonPrimary: "bg-brand-gradient shadow-[0_10px_28px_-10px_hsl(var(--glow-blue))] hover:brightness-110",
  },
});

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Starts Clerk from the backend's runtime config, so deploy's live keys need no rebuild.
// Must render inside <BrowserRouter> so Clerk navigates without reloading.
export default function ClerkAuthProvider({ children }) {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const [config, setConfig] = useState(null);
  const [unavailable, setUnavailable] = useState(false);
  const appearance = useMemo(() => buildAppearance(theme), [theme]);

  // Retries while the backend restarts (e.g. right after provisioning): the app's
  // Clerk components crash if they ever render without <ClerkProvider>.
  useEffect(() => {
    let cancelled = false;
    const load = async (attempt = 0) => {
      try {
        const cfg = await (await fetch(`${BACKEND_URL}/api/clerk/config`)).json();
        if (cfg.enabled) return cancelled || setConfig(cfg);
      } catch {}
      if (cancelled) return;
      if (attempt >= 20) return setUnavailable(true);
      setTimeout(() => load(attempt + 1), 1500);
    };
    load();
    return () => { cancelled = true; };
  }, []);

  if (unavailable) return <p style={{ padding: 24 }}>Sign-in is unavailable right now. Refresh the page to try again.</p>;
  if (!config) return null;
  return (
    <ClerkProvider
      publishableKey={config.publishable_key}
      proxyUrl={config.proxy_url || undefined}
      appearance={appearance}
      routerPush={(to) => navigate(to)}
      routerReplace={(to) => navigate(to, { replace: true })}
      signInUrl="/sign-in"
      signUpUrl="/sign-up"
      signInFallbackRedirectUrl="/"
      signUpFallbackRedirectUrl="/"
      afterSignOutUrl="/"
    >
      {children}
    </ClerkProvider>
  );
}
