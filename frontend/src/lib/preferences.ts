import type { FontScale, ThemePreference } from '@/src/types';

export function resolveTheme(preference: ThemePreference): 'light' | 'dark' {
  if (preference === 'light' || preference === 'dark') {
    return preference;
  }
  if (typeof window === 'undefined') {
    return 'light';
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function applyThemePreference(preference: ThemePreference) {
  const root = document.documentElement;
  root.dataset.theme = resolveTheme(preference);
}

export function applyFontScale(fontScale: FontScale) {
  const root = document.documentElement;
  root.dataset.fontScale = fontScale;
}
