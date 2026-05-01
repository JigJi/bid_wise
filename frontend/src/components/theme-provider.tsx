"use client";

import * as React from "react";

type Attribute = "class" | "data-theme";

type ThemeProviderProps = {
  attribute?: Attribute;
  defaultTheme?: "dark" | "light" | "system";
  enableSystem?: boolean;
  disableTransitionOnChange?: boolean;
  children: React.ReactNode;
};

type ThemeContextValue = {
  theme: "dark" | "light" | "system";
  resolvedTheme: "dark" | "light";
  setTheme: (t: "dark" | "light" | "system") => void;
};

const ThemeContext = React.createContext<ThemeContextValue | undefined>(
  undefined,
);

const STORAGE_KEY = "bidwise-theme";

function getSystemTheme(): "dark" | "light" {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

/**
 * Minimal in-house theme provider — avoids next-themes dependency for now.
 * Persists to localStorage, applies class to <html>, supports system mode.
 */
export function ThemeProvider({
  attribute = "class",
  defaultTheme = "dark",
  enableSystem = true,
  disableTransitionOnChange = true,
  children,
}: ThemeProviderProps) {
  const [theme, setThemeState] = React.useState<"dark" | "light" | "system">(
    defaultTheme,
  );
  const [resolved, setResolved] = React.useState<"dark" | "light">(
    defaultTheme === "system" ? "dark" : (defaultTheme as "dark" | "light"),
  );

  React.useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as
      | "dark"
      | "light"
      | "system"
      | null;
    if (stored) setThemeState(stored);
  }, []);

  React.useEffect(() => {
    const root = document.documentElement;
    const apply = (t: "dark" | "light") => {
      if (disableTransitionOnChange) {
        const css = document.createElement("style");
        css.appendChild(
          document.createTextNode(
            "*,*::before,*::after{transition:none!important}",
          ),
        );
        document.head.appendChild(css);
        // force reflow
        window.getComputedStyle(root).getPropertyValue("opacity");
        setTimeout(() => document.head.removeChild(css), 0);
      }
      if (attribute === "class") {
        root.classList.remove("dark", "light");
        root.classList.add(t);
      } else {
        root.setAttribute("data-theme", t);
      }
      setResolved(t);
    };
    if (theme === "system" && enableSystem) {
      apply(getSystemTheme());
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      const onChange = () => apply(mq.matches ? "dark" : "light");
      mq.addEventListener("change", onChange);
      return () => mq.removeEventListener("change", onChange);
    } else {
      apply(theme as "dark" | "light");
    }
  }, [theme, enableSystem, attribute, disableTransitionOnChange]);

  const setTheme = React.useCallback((t: "dark" | "light" | "system") => {
    localStorage.setItem(STORAGE_KEY, t);
    setThemeState(t);
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme: resolved, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = React.useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
