import type { LoginResponse } from '@/src/types';

const AUTH_STORAGE_KEY = 'contract-review-auth';

export function saveAuthSession(payload: LoginResponse) {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(payload));
}

export function getAuthSession(): LoginResponse | null {
  const raw = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as LoginResponse;
    if (!parsed.token || !parsed.member) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function clearAuthSession() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

export function getAuthToken(): string | null {
  return getAuthSession()?.token ?? null;
}

export function updateAuthSessionMember(member: LoginResponse['member']) {
  const session = getAuthSession();
  if (!session) {
    return;
  }
  saveAuthSession({
    ...session,
    member,
  });
}
