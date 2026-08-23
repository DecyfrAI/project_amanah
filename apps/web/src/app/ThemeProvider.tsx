import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'amanah.theme';

/**
 * Light is the default, everywhere, including the public routes.
 *
 * Light is a teal ground. A dark system preference does not switch the product
 * over on its own. `tokens.css` only applies its dark set when `data-theme` is
 * absent, so writing the attribute is what pins this. `index.html` writes it
 * before first paint to avoid a flash; this provider owns it from mount onward.
 */
const DEFAULT_THEME: Theme = 'light';

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function readStoredTheme(): Theme {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'dark' ? 'dark' : DEFAULT_THEME;
  } catch {
    // Storage throws in a locked-down browser profile. A theme preference is
    // not worth failing a render over.
    return DEFAULT_THEME;
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(readStoredTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // A preference that cannot be remembered still applies for this visit.
    }
  }, [theme]);

  const toggleTheme = useCallback((): void => {
    setTheme((current) => (current === 'dark' ? 'light' : 'dark'));
  }, []);

  const value = useMemo<ThemeContextValue>(() => ({ theme, toggleTheme }), [theme, toggleTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

/**
 * Single source of truth for the theme.
 *
 * Context rather than a hook with local state, because two independent copies
 * would disagree the moment one of them toggled, and the attribute on `<html>`
 * would follow whichever rendered last.
 */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (context === null) {
    throw new Error('useTheme must be used inside ThemeProvider');
  }
  return context;
}
