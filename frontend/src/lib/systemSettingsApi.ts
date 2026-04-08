import type { UpdateSettingsRequest, UserMember } from '@/src/types';
import { getAuthSettings, updateAuthSettings } from '@/src/lib/api';

export function fetchSystemSettings(): Promise<UserMember> {
  return getAuthSettings();
}

export function saveSystemSettings(payload: UpdateSettingsRequest): Promise<UserMember> {
  return updateAuthSettings(payload);
}
