import { FormEvent, useState } from 'react';
import { login } from '@/src/lib/api';
import { saveAuthSession } from '@/src/lib/auth';
import type { UserMember } from '@/src/types';

interface LoginPageProps {
  onLoginSuccess: (member: UserMember) => void;
}

export default function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await login(username, password);
      saveAuthSession(response);
      onLoginSuccess(response.member);
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: 'var(--app-bg)' }}>
      {/* Top brand bar */}
      <div className="bg-gradient-to-r from-brand-700 to-brand-600 px-10 py-3.5 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center text-white font-bold text-sm">
          S
        </div>
        <span className="text-white font-semibold text-base">SmartAudit</span>
      </div>

      {/* Center content */}
      <div className="flex-1 flex items-center justify-center px-6 relative">
        {/* Grid background */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              'linear-gradient(rgba(37,99,235,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(37,99,235,0.5) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />

        <div className="flex items-center gap-20 relative z-10">
          {/* Brand text */}
          <div className="hidden lg:block max-w-xs">
            <h2 className="text-3xl font-bold text-text-primary leading-tight mb-3">
              智能合同<br />
              <span className="text-brand-600">校审管理平台</span>
            </h2>
            <p className="text-sm text-text-secondary leading-relaxed">
              基于 AI 的智能合同审核系统，支持风险识别、条款比对、版本追踪，让合同管理更高效、更安全。
            </p>
          </div>

          {/* Login card */}
          <div className="w-full max-w-sm bg-surface rounded-xl shadow-card border border-border-light p-8">
            <h3 className="text-xl font-semibold text-text-primary mb-1">登录</h3>
            <p className="text-sm text-text-muted mb-6">登录后将自动识别成员类型并应用权限。</p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">用户名</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="请输入用户名"
                  className="w-full px-3.5 py-2.5 rounded-md border border-border text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">密码</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="请输入密码"
                  className="w-full px-3.5 py-2.5 rounded-md border border-border text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all"
                  required
                />
              </div>

              {error && <p className="text-sm text-danger">{error}</p>}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-md bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 disabled:opacity-50 transition-all"
              >
                {loading ? '登录中...' : '登录'}
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="bg-sidebar px-10 py-3 flex items-center justify-between">
        <span className="text-xs text-text-muted">© 2026 SmartAudit. All rights reserved.</span>
      </div>
    </div>
  );
}
