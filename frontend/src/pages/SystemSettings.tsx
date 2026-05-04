import { useState } from 'react';

import { fetchSystemSettings, saveSystemSettings } from '@/src/lib/systemSettingsApi';
import type { FontScale, ThemePreference, UserMember } from '@/src/types';

interface SystemSettingsProps {
  currentUser: UserMember;
  onUserUpdated: (member: UserMember) => void;
}

export default function SystemSettings({ currentUser, onUserUpdated }: SystemSettingsProps) {
  const [themePreference, setThemePreference] = useState<ThemePreference>(currentUser.themePreference ?? 'system');
  const [fontScale, setFontScale] = useState<FontScale>(currentUser.fontScale ?? 'medium');
  const [notifyEnabled, setNotifyEnabled] = useState<boolean>(currentUser.notifyEnabled ?? true);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      const member = await fetchSystemSettings();
      setThemePreference(member.themePreference);
      setFontScale(member.fontScale);
      setNotifyEnabled(member.notifyEnabled);
      onUserUpdated(member);
    } catch {
      // Ignore refresh failure and keep existing state.
    }
  }

  async function handleSave() {
    setLoading(true);
    setMessage(null);
    setError(null);
    try {
      const member = await saveSystemSettings({
        themePreference,
        fontScale,
        notifyEnabled,
      });
      onUserUpdated(member);
      setMessage('系统设置已保存');
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">系统设置</h1>
        <p className="mt-1 text-sm text-slate-500">管理应用偏好，不影响个人资料信息。</p>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">主题模式</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {([
            ['light', '亮色'],
            ['dark', '暗色'],
            ['system', '跟随系统'],
          ] as const).map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => setThemePreference(value)}
              className={`rounded-xl border px-4 py-3 text-sm font-medium transition ${
                themePreference === value
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">字体大小</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {([
            ['small', '小'],
            ['medium', '中'],
            ['large', '大'],
          ] as const).map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => setFontScale(value)}
              className={`rounded-xl border px-4 py-3 text-sm font-medium transition ${
                fontScale === value
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">通知偏好</h2>
        <label className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3">
          <span className="text-sm text-slate-700">开启消息提醒</span>
          <input
            type="checkbox"
            checked={notifyEnabled}
            onChange={(event) => setNotifyEnabled(event.target.checked)}
            className="h-4 w-4 accent-blue-600"
          />
        </label>
      </section>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => void handleSave()}
          disabled={loading}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {loading ? '保存中...' : '保存设置'}
        </button>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
        >
          重新加载
        </button>
      </div>

      {message && <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</div>}
      {error && <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
    </div>
  );
}
