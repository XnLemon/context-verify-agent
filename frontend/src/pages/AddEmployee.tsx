import { FormEvent, useState } from 'react';

import { createEmployee } from '@/src/lib/api';
import type { CreateEmployeeRequest } from '@/src/types';

const memberTypeOptions: CreateEmployeeRequest['memberType'][] = ['legal', 'procurement', 'business', 'other'];

export default function AddEmployee() {
  const [form, setForm] = useState<CreateEmployeeRequest>({
    username: '',
    password: '',
    displayName: '',
    memberType: 'legal',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      const member = await createEmployee(form);
      setSuccess(`员工 ${member.displayName} 创建成功`);
      setForm({ username: '', password: '', displayName: '', memberType: 'legal' });
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建员工失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-8">
      <h2 className="text-xl font-semibold text-slate-900">添加员工</h2>
      <p className="mt-1 text-sm text-slate-500">创建后员工可登录系统，但不具备管理员权限。</p>

      <form onSubmit={handleSubmit} className="mt-6 max-w-xl space-y-4 rounded-xl border border-slate-200 bg-white p-6">
        <div>
          <label className="mb-1 block text-sm text-slate-700">用户名</label>
          <input
            value={form.username}
            onChange={(event) => setForm((prev) => ({ ...prev, username: event.target.value }))}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
            required
          />
        </div>

        <div>
          <label className="mb-1 block text-sm text-slate-700">姓名</label>
          <input
            value={form.displayName}
            onChange={(event) => setForm((prev) => ({ ...prev, displayName: event.target.value }))}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
            required
          />
        </div>

        <div>
          <label className="mb-1 block text-sm text-slate-700">密码</label>
          <input
            type="password"
            value={form.password}
            onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
            required
            minLength={6}
          />
        </div>

        <div>
          <label className="mb-1 block text-sm text-slate-700">成员类型</label>
          <select
            value={form.memberType}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, memberType: event.target.value as CreateEmployeeRequest['memberType'] }))
            }
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
          >
            {memberTypeOptions.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {success && <p className="text-sm text-emerald-600">{success}</p>}

        <button
          type="submit"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
          disabled={submitting}
        >
          {submitting ? '创建中...' : '创建员工'}
        </button>
      </form>
    </div>
  );
}
