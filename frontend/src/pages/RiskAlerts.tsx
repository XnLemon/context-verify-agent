import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import { motion } from 'motion/react';

import { getWorkbenchContractDetail, getWorkbenchContracts } from '@/src/lib/api';
import { cn } from '@/src/lib/utils';
import type { AuditIssue, Contract, ReviewResult } from '@/src/types';

type RiskAlertRow = {
  contract: Contract;
  latestReview: ReviewResult;
  highCount: number;
  mediumCount: number;
  pendingCount: number;
};

const PAGE_SIZE = 8;

export default function RiskAlerts({
  onReviewContract,
  searchQuery,
}: {
  onReviewContract: (id: string) => void;
  searchQuery: string;
}) {
  const [rows, setRows] = useState<RiskAlertRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const loadRiskAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const contractsResponse = await getWorkbenchContracts({ search: searchQuery });
      const details = await Promise.all(
        contractsResponse.items.map(async (contract) => {
          try {
            const detail = await getWorkbenchContractDetail(contract.id);
            const latestReview = detail.latestReview;
            if (!latestReview) {
              return null;
            }

            const pendingIssues = latestReview.issues.filter((issue) => issue.status === 'pending');
            const highCount = countBySeverity(pendingIssues, 'high');
            const mediumCount = countBySeverity(pendingIssues, 'medium');
            const pendingCount = pendingIssues.length;

            if (pendingCount === 0) {
              return null;
            }

            return {
              contract,
              latestReview,
              highCount,
              mediumCount,
              pendingCount,
            } satisfies RiskAlertRow;
          } catch {
            return null;
          }
        }),
      );

      const filtered = details
        .filter((entry): entry is RiskAlertRow => entry !== null)
        .sort((left, right) => {
          if (right.highCount !== left.highCount) {
            return right.highCount - left.highCount;
          }
          if (right.mediumCount !== left.mediumCount) {
            return right.mediumCount - left.mediumCount;
          }
          return right.contract.updatedAt.localeCompare(left.contract.updatedAt);
        });

      setRows(filtered);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : '加载风险预警失败。');
    } finally {
      setLoading(false);
    }
  }, [searchQuery]);

  useEffect(() => {
    void loadRiskAlerts();
  }, [loadRiskAlerts]);

  useEffect(() => {
    setPage(1);
  }, [searchQuery]);

  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const pageItems = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return rows.slice(start, start + PAGE_SIZE);
  }, [rows, page]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">风险预警</h1>
          <p className="text-sm text-slate-500 mt-1">聚合展示待处理风险项，按风险优先级排序。</p>
        </div>
        <button
          type="button"
          onClick={() => void loadRiskAlerts()}
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
            共 <span className="font-semibold text-slate-900">{rows.length}</span> 份含风险合同
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
              <tr className="bg-surface-subtle">
                <th className="px-6 py-4 text-xs font-semibold text-text-muted uppercase tracking-wider">合同名称</th>
                <th className="px-6 py-4 text-xs font-semibold text-text-muted uppercase tracking-wider">类型</th>
                <th className="px-6 py-4 text-xs font-semibold text-text-muted uppercase tracking-wider">高风险</th>
                <th className="px-6 py-4 text-xs font-semibold text-text-muted uppercase tracking-wider">中风险</th>
                <th className="px-6 py-4 text-xs font-semibold text-text-muted uppercase tracking-wider">待处理总数</th>
                <th className="px-6 py-4 text-xs font-semibold text-text-muted uppercase tracking-wider">最近扫描</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-light">
              {loading ? (
                <LoadingRow />
              ) : pageItems.length === 0 ? (
                <EmptyRow />
              ) : (
                pageItems.map((row, index) => (
                  <motion.tr
                    key={row.contract.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.03 }}
                    className="hover:bg-slate-50 transition-colors cursor-pointer"
                    onClick={() => onReviewContract(row.contract.id)}
                  >
                    <td className="px-6 py-4 font-medium text-slate-900">{row.contract.title}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{row.contract.type}</td>
                    <td className="px-6 py-4">
                      <RiskCount count={row.highCount} tone="high" />
                    </td>
                    <td className="px-6 py-4">
                      <RiskCount count={row.mediumCount} tone="medium" />
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-700 font-medium">{row.pendingCount}</td>
                    <td className="px-6 py-4 text-sm text-slate-500">{formatDateTime(row.latestReview.generatedAt)}</td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        )}

        <div className="px-6 py-4 border-t border-border bg-surface-subtle flex items-center justify-between">
          <div className="inline-flex items-center gap-2 text-xs text-red-700 bg-red-100 px-2.5 py-1 rounded-full">
            <AlertTriangle size={12} />
            风险优先级视图
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              disabled={page <= 1}
              className="h-8 w-8 rounded-md border border-slate-200 bg-surface text-text-muted hover:bg-surface-subtle disabled:opacity-40"
            >
              <ChevronLeft size={16} className="mx-auto" />
            </button>
            <span className="px-2 text-sm text-text-muted">{page}</span>
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

function RiskCount({ count, tone }: { count: number; tone: 'high' | 'medium' }) {
  return (
    <span
      className={cn(
        'inline-flex min-w-9 justify-center px-2 py-1 rounded-full text-xs font-bold',
        tone === 'high' ? 'bg-red-100 text-red-600' : 'bg-amber-100 text-amber-600',
      )}
    >
      {count}
    </span>
  );
}

function countBySeverity(issues: AuditIssue[], severity: 'high' | 'medium') {
  return issues.filter((issue) => issue.severity === severity).length;
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString([], {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function LoadingRow() {
  return (
    <tr>
      <td colSpan={6} className="px-6 py-10 text-center text-sm text-slate-500">
        正在加载风险预警数据...
      </td>
    </tr>
  );
}

function EmptyRow() {
  return (
    <tr>
      <td colSpan={6} className="px-6 py-10 text-center text-sm text-slate-500">
        当前没有待处理风险。
      </td>
    </tr>
  );
}
