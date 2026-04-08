import { useEffect, useState } from 'react';

import { getEmployees } from '@/src/lib/api';
import type { UserMember } from '@/src/types';

export default function Employees() {
  const [employees, setEmployees] = useState<UserMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const response = await getEmployees();
        setEmployees(response.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取员工失败');
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, []);

  if (loading) {
    return <div className="p-8 text-sm text-slate-500">加载员工列表中...</div>;
  }

  if (error) {
    return <div className="p-8 text-sm text-red-600">{error}</div>;
  }

  return (
    <div className="p-8">
      <h2 className="text-xl font-semibold text-slate-900">员工列表</h2>
      <p className="mt-1 text-sm text-slate-500">仅管理员可查看和维护员工账号。</p>

      <div className="mt-6 overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">用户名</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">姓名</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">成员类型</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">最近登录</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {employees.map((item) => (
              <tr key={item.id}>
                <td className="px-4 py-3 text-sm text-slate-700">{item.username}</td>
                <td className="px-4 py-3 text-sm text-slate-700">{item.display_name}</td>
                <td className="px-4 py-3 text-sm text-slate-700">{item.member_type}</td>
                <td className="px-4 py-3 text-sm text-slate-700">{item.last_login_at ? new Date(item.last_login_at).toLocaleString() : '未登录'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
