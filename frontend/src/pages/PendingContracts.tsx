import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Clock3, RefreshCw } from 'lucide-react';
import { motion } from 'motion/react';

import { getWorkbenchContracts } from '@/src/lib/api';
import { cn } from '@/src/lib/utils';
import type { Contract } from '@/src/types';

const PAGE_SIZE = 8;

export default function PendingContracts({
  onReviewContract,
  searchQuery,
}: {
  onReviewContract: (id: string) => void;
  searchQuery: string;
}) {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const loadPendingContracts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getWorkbenchContracts({ search: searchQuery, status: 'pending' });
      setContracts(response.items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : '加载待处理列表失败。');
    } finally {
      setLoading(false);
    }
  }, [searchQuery]);

  useEffect(() => {
    void loadPendingContracts();
  }, [loadPendingContracts]);

  useEffect(() => {
    setPage(1);
  }, [searchQuery]);

  const totalPages = Math.max(1, Math.ceil(contracts.length / PAGE_SIZE));
  const pageItems = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return contracts.slice(start, start + PAGE_SIZE);
  }, [contracts, page]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">待处理</h1>
          <p className="text-sm text-slate-500 mt-1">展示当前等待校审处理的合同。</p>
        </div>
        <button
          type="button"
          onClick={() => void loadPendingContracts()}
          disabled={loading}
          className="px-4 py-2 rounded-lg border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 flex items-center gap-2 disabled:opacity-50"
        >
          <RefreshCw size={16} className={cn(loading && 'animate-spin')} />
          刷新
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between text-sm">
          <p className="text-slate-600">
            共 <span className="font-semibold text-slate-900">{contracts.length}</span> 份待处理合同
          </p>
          <p className="text-slate-500">
            第 <span className="font-semibold text-slate-900">{page}</span> / {totalPages} 页
          </p>
        </div>

        {error ? (
          <div className="px-6 py-10 text-sm text-red-600 bg-red-50 border-t border-red-100">{error}</div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/50">
                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">合同名称</th>
                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">类型</th>
                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">提交人</th>
                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">更新时间</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <LoadingRow />
              ) : pageItems.length === 0 ? (
                <EmptyRow />
              ) : (
                pageItems.map((contract, index) => (
                  <motion.tr
                    key={contract.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.03 }}
                    className="hover:bg-slate-50 transition-colors cursor-pointer"
                    onClick={() => onReviewContract(contract.id)}
                  >
                    <td className="px-6 py-4 font-medium text-slate-900">{contract.title}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{contract.type}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{contract.author}</td>
                    <td className="px-6 py-4 text-sm text-slate-500">{contract.updatedAt}</td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        )}

        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/70 flex items-center justify-between">
          <div className="inline-flex items-center gap-2 text-xs text-amber-700 bg-amber-100 px-2.5 py-1 rounded-full">
            <Clock3 size={12} />
            处理中队列
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              disabled={page <= 1}
              className="h-8 w-8 rounded-md border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 disabled:opacity-40"
            >
              <ChevronLeft size={16} className="mx-auto" />
            </button>
            <span className="px-2 text-sm text-slate-500">{page}</span>
            <button
              type="button"
              onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={page >= totalPages}
              className="h-8 w-8 rounded-md border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 disabled:opacity-40"
            >
              <ChevronRight size={16} className="mx-auto" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function LoadingRow() {
  return (
    <tr>
      <td colSpan={4} className="px-6 py-10 text-center text-sm text-slate-500">
        正在加载待处理合同...
      </td>
    </tr>
  );
}

function EmptyRow() {
  return (
    <tr>
      <td colSpan={4} className="px-6 py-10 text-center text-sm text-slate-500">
        当前没有待处理合同。
      </td>
    </tr>
  );
}
