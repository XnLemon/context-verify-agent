import type { AvatarUploadResponse, UpdateProfileRequest, UserMember } from '@/src/types';
import {
  buildApiAssetUrl,
  getAuthProfile,
  updateAuthProfile,
  uploadAuthProfileAvatar,
} from '@/src/lib/api';

export function fetchProfile(): Promise<UserMember> {
  return getAuthProfile();
}

export function saveProfile(payload: UpdateProfileRequest): Promise<UserMember> {
  return updateAuthProfile(payload);
}

export function uploadAvatar(file: File): Promise<AvatarUploadResponse> {
  return uploadAuthProfileAvatar(file);
}

export { buildApiAssetUrl };
