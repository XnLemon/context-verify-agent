import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, FileText, RefreshCw } from 'lucide-react';
import { motion } from 'motion/react';

import { getWorkbenchContracts } from '@/src/lib/api';
import { cn } from '@/src/lib/utils';
import type { Contract, ContractStatus } from '@/src/types';

const PAGE_SIZE = 8;

export default function ContractLibrary({
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

  const loadContracts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getWorkbenchContracts(searchQuery);
      setContracts(response.items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : '加载合同库失败。');
    } finally {
      setLoading(false);
    }
  }, [searchQuery]);

  useEffect(() => {
    void loadContracts();
  }, [loadContracts]);

  useEffect(() => {
    setPage(1);
  }, [searchQuery]);

  const total = contracts.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  const pagedContracts = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return contracts.slice(start, start + PAGE_SIZE);
  }, [contracts, page]);

  const pageNumbers = useMemo(() => {
    const pages: number[] = [];
    const start = Math.max(1, page - 2);
    const end = Math.min(totalPages, start + 4);
    for (let index = start; index <= end; index += 1) {
      pages.push(index);
    }
    return pages;
  }, [page, totalPages]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">合同库</h1>
          <p className="text-sm text-slate-500 mt-1">分页展示当前已上传及历史合同，支持快速进入校审页面。</p>
        </div>
        <button
          type="button"
          onClick={() => void loadContracts()}
          disabled={loading}
          className="px-4 py-2 rounded-lg border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 flex items-center gap-2 disabled:opacity-50"
        >
          <RefreshCw size={16} className={cn(loading && 'animate-spin')} />
          刷新
        </button>
      </div>

      <div className="bg-surface rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between text-sm">
          <p className="text-slate-600">
            共 <span className="font-semibold text-slate-900">{total}</span> 份合同
          </p>
          <p className="text-slate-500">
            第 <span className="font-semibold text-slate-900">{page}</span> / {totalPages} 页
          </p>
        </div>

        {error ? (
          <div className="px-6 py-10 text-sm text-red-600 bg-red-50 border-t border-red-100">{error}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-subtle">
                  <th className="px-6 py-4 text-xs font-semibold text-text-muted uppercase tracking-wider">合同名称</th>
                  <th className="px-6 py-4 text-xs font-semibold text-text-muted uppercase tracking-wider">类型</th>
                  <th className="px-6 py-4 text-xs font-semibold text-text-muted uppercase tracking-wider">状态</th>
                  <th className="px-6 py-4 text-xs font-semibold text-text-muted uppercase tracking-wider">提交人</th>
                  <th className="px-6 py-4 text-xs font-semibold text-text-muted uppercase tracking-wider">更新时间</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-light">
                {loading ? (
                  <LoadingRow />
                ) : pagedContracts.length === 0 ? (
                  <EmptyRow />
                ) : (
                  pagedContracts.map((contract, index) => (
                    <motion.tr
                      key={contract.id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.03 }}
                      className="hover:bg-slate-50 transition-colors cursor-pointer"
                      onClick={() => onReviewContract(contract.id)}
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600 shrink-0">
                            <FileText size={18} />
                          </div>
                          <div>
                            <p className="font-medium text-slate-900">{contract.title}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">{contract.type}</td>
                      <td className="px-6 py-4">
                        <StatusBadge status={contract.status} />
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">{contract.author}</td>
                      <td className="px-6 py-4 text-sm text-slate-500">{contract.updatedAt}</td>
                    </motion.tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        <div className="px-6 py-4 border-t border-border bg-surface-subtle flex items-center justify-between">
          <p className="text-xs text-text-muted">
            当前显示 {(page - 1) * PAGE_SIZE + (pagedContracts.length ? 1 : 0)} - {(page - 1) * PAGE_SIZE + pagedContracts.length}
          </p>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              disabled={page <= 1}
              className="h-8 w-8 rounded-md border border-slate-200 bg-surface text-text-muted hover:bg-surface-subtle disabled:opacity-40"
            >
              <ChevronLeft size={16} className="mx-auto" />
            </button>
            {pageNumbers.map((pageNumber) => (
              <button
                key={pageNumber}
                type="button"
                onClick={() => setPage(pageNumber)}
                className={cn(
                  'h-8 min-w-8 px-2 rounded-md border text-sm',
                  page === pageNumber
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-surface text-slate-600 border-slate-200 hover:bg-slate-100',
                )}
              >
                {pageNumber}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={page >= totalPages}
              className="h-8 w-8 rounded-md border border-slate-200 bg-surface text-text-muted hover:bg-surface-subtle disabled:opacity-40"
            >
              <ChevronRight size={16} className="mx-auto" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: ContractStatus }) {
  const config = {
    pending: { label: '待处理', className: 'bg-slate-100 text-slate-600' },
    reviewing: { label: '审核中', className: 'bg-blue-100 text-blue-600' },
    approved: { label: '已通过', className: 'bg-emerald-100 text-emerald-600' },
    rejected: { label: '已驳回', className: 'bg-red-100 text-red-600' },
  };

  const { label, className } = config[status];
  return <span className={cn('px-2.5 py-1 rounded-full text-xs font-bold', className)}>{label}</span>;
}

function LoadingRow() {
  return (
    <tr>
      <td colSpan={5} className="px-6 py-10 text-center text-sm text-slate-500">
        正在加载合同库...
      </td>
    </tr>
  );
}

function EmptyRow() {
  return (
    <tr>
      <td colSpan={5} className="px-6 py-10 text-center text-sm text-slate-500">
        当前没有合同数据。
      </td>
    </tr>
  );
}
