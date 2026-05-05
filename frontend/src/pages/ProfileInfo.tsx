import { useMemo, useState } from 'react';

import { buildApiAssetUrl, fetchProfile, saveProfile, uploadAvatar } from '@/src/lib/profileApi';
import type { UserMember } from '@/src/types';

interface ProfileInfoProps {
  currentUser: UserMember;
  onUserUpdated: (member: UserMember) => void;
}

const ACCEPTED_AVATAR_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp'];

export default function ProfileInfo({ currentUser, onUserUpdated }: ProfileInfoProps) {
  const [displayName, setDisplayName] = useState(currentUser.displayName);
  const [loadingName, setLoadingName] = useState(false);
  const [loadingAvatar, setLoadingAvatar] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const avatarSrc = useMemo(() => {
    return (
      buildApiAssetUrl(currentUser.avatarUrl) ??
      `https://picsum.photos/seed/${currentUser.username}/120/120`
    );
  }, [currentUser.avatarUrl, currentUser.username]);

  async function refreshProfile() {
    try {
      const member = await fetchProfile();
      setDisplayName(member.displayName);
      onUserUpdated(member);
    } catch {
      // Keep existing UI state on refresh failure.
    }
  }

  async function handleSaveDisplayName() {
    setLoadingName(true);
    setError(null);
    setMessage(null);
    try {
      const member = await saveProfile({ displayName });
      onUserUpdated(member);
      setMessage('昵称已更新');
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新昵称失败');
    } finally {
      setLoadingName(false);
    }
  }

  async function handleAvatarChange(file: File | null) {
    if (!file) {
      return;
    }
    const lowerName = file.name.toLowerCase();
    if (!ACCEPTED_AVATAR_EXTENSIONS.some((ext) => lowerName.endsWith(ext))) {
      setError('头像仅支持 jpg/jpeg/png/webp 格式');
      return;
    }

    setLoadingAvatar(true);
    setError(null);
    setMessage(null);
    try {
      const response = await uploadAvatar(file);
      onUserUpdated(response.member);
      setMessage('头像已更新');
    } catch (err) {
      setError(err instanceof Error ? err.message : '上传头像失败');
    } finally {
      setLoadingAvatar(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">个人信息设置</h1>
        <p className="mt-1 text-sm text-slate-500">修改昵称与头像，保存后会同步到当前账号。</p>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-surface p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">头像</h2>
        <div className="flex items-center gap-4">
          <img src={avatarSrc} alt="avatar" className="h-20 w-20 rounded-full border border-slate-200 object-cover" />
          <label className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 cursor-pointer">
            {loadingAvatar ? '上传中...' : '上传新头像'}
            <input
              type="file"
              accept=".jpg,.jpeg,.png,.webp"
              className="hidden"
              disabled={loadingAvatar}
              onChange={(event) => void handleAvatarChange(event.target.files?.[0] ?? null)}
            />
          </label>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-surface p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">昵称</h2>
        <input
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
          placeholder="请输入昵称"
        />
        <div className="flex items-center gap-3">
          <button
            type="button"
            disabled={loadingName}
            onClick={() => void handleSaveDisplayName()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {loadingName ? '保存中...' : '保存昵称'}
          </button>
          <button
            type="button"
            disabled={loadingName || loadingAvatar}
            onClick={() => void refreshProfile()}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            重新加载
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-surface p-6 space-y-2">
        <h2 className="text-lg font-semibold text-slate-900">登录信息</h2>
        <p className="text-sm text-slate-600">用户名：{currentUser.username}</p>
        <p className="text-sm text-slate-600">最近登录：{currentUser.lastLoginAt ?? '暂无记录'}</p>
      </section>

      {message && <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</div>}
      {error && <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
    </div>
  );
}
