import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowUpRight,
  Download,
  FileText,
  Filter,
  MoreVertical,
  Plus,
  ShieldCheck,
  Upload,
  X,
} from 'lucide-react';
import { motion } from 'motion/react';

import { getWorkbenchContracts, getWorkbenchSummary, importWorkbenchContract } from '@/src/lib/api';
import { canUploadOrEditContract } from '@/src/lib/permissions';
import { cn } from '@/src/lib/utils';
import type { Contract, ContractStatus, SummaryStats, UserMember } from '@/src/types';

const EMPTY_SUMMARY: SummaryStats = {
  pendingCount: 0,
  complianceRate: 0,
  highRiskCount: 0,
  averageReviewDurationHours: 0,
  totalContracts: 0,
};

const MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024;
const ACCEPTED_FILE_EXTENSIONS = ['.txt', '.docx', '.pdf'];

export default function Dashboard({
  currentUser,
  onReviewContract,
  searchQuery,
}: {
  currentUser: UserMember;
  onReviewContract: (id: string) => void;
  searchQuery: string;
}) {
  const [summary, setSummary] = useState<SummaryStats>(EMPTY_SUMMARY);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const canUpload = canUploadOrEditContract(currentUser);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryResponse, contractsResponse] = await Promise.all([
        getWorkbenchSummary(),
        getWorkbenchContracts(searchQuery),
      ]);
      setSummary(summaryResponse);
      setContracts(contractsResponse.items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : '加载合同工作台失败。');
    } finally {
      setLoading(false);
    }
  }, [searchQuery]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  function openUploadModal() {
    if (!canUpload) {
      return;
    }
    setUploadError(null);
    setUploadSuccess(null);
    setSelectedFile(null);
    setIsUploadModalOpen(true);
  }

  function closeUploadModal() {
    if (isUploading) {
      return;
    }
    setIsUploadModalOpen(false);
    setUploadError(null);
    setUploadSuccess(null);
    setSelectedFile(null);
  }

  function handlePickFile() {
    fileInputRef.current?.click();
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setUploadError(null);
    setUploadSuccess(null);
    setSelectedFile(file);
  }

  function validateUploadFile(file: File | null): string | null {
    if (!file) {
      return '请先选择要上传的合同文件。';
    }
    const lowerName = file.name.toLowerCase();
    const hasValidExtension = ACCEPTED_FILE_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
    if (!hasValidExtension) {
      return '仅支持上传 .txt / .docx / .pdf 文件。';
    }
    if (file.size <= 0) {
      return '上传文件不能为空。';
    }
    if (file.size > MAX_UPLOAD_SIZE_BYTES) {
      return '上传文件过大，请控制在 5MB 以内。';
    }
    return null;
  }

  async function handleUploadContract() {
    if (isUploading) {
      return;
    }

    const validationError = validateUploadFile(selectedFile);
    if (validationError) {
      setUploadError(validationError);
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const response = await importWorkbenchContract(selectedFile as File, {
        author: currentUser.display_name,
      });
      setUploadSuccess('上传成功，正在进入校审页面...');
      await loadData();
      setIsUploadModalOpen(false);
      onReviewContract(response.contract.id);
    } catch (uploadFailure) {
      setUploadError(uploadFailure instanceof Error ? uploadFailure.message : '上传失败，请稍后重试。');
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex items-end justify-between gap-4">
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">{`欢迎回来，${currentUser.display_name}`}</h1>
          <p className="text-slate-500 mt-1">
            当前共有 <span className="font-bold text-slate-900">{summary.totalContracts}</span> 份合同，其中
            <span className="text-red-500 font-bold"> {summary.highRiskCount} </span> 项高风险待处理。
          </p>
        </motion.div>

        {canUpload ? (
          <motion.button
            type="button"
            onClick={openUploadModal}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl font-bold flex items-center gap-2 transition-all shadow-lg shadow-blue-600/25"
          >
            <Plus size={20} />
            <span>新建校审任务</span>
          </motion.button>
        ) : (
          <div className="text-xs text-slate-500 rounded-xl border border-slate-200 bg-white px-3 py-2">
            当前账号仅可进行最终审批
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="待校审"
          value={summary.pendingCount.toString()}
          caption={`${summary.totalContracts} 份合同总数`}
          icon={<FileText className="text-blue-600" />}
          tone="blue"
        />
        <StatCard
          title="合规率"
          value={`${summary.complianceRate.toFixed(1)}%`}
          caption="基于已生成的审查结果"
          icon={<ShieldCheck className="text-emerald-600" />}
          tone="emerald"
        />
        <StatCard
          title="高风险项"
          value={summary.highRiskCount.toString()}
          caption="仍处于待处理状态"
          icon={<AlertTriangle className="text-amber-600" />}
          tone="amber"
        />
        <StatCard
          title="平均耗时"
          value={`${summary.averageReviewDurationHours.toFixed(1)}h`}
          caption="从创建到最近一次审查"
          icon={<ArrowUpRight className="text-violet-600" />}
          tone="violet"
        />
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-lg font-bold">近期合同任务</h2>
          <div className="flex items-center gap-3">
            <button className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-lg border border-slate-200 transition-colors">
              <Filter size={16} />
              筛选
            </button>
            <button className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-lg border border-slate-200 transition-colors">
              <Download size={16} />
              导出
            </button>
          </div>
        </div>

        {error ? (
          <div className="px-6 py-10 text-sm text-red-600 bg-red-50 border-t border-red-100">{error}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/50">
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">合同名称</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">类型</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">状态</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">提交人</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">更新时间</th>
                  <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <LoadingRow />
                ) : contracts.length === 0 ? (
                  <EmptyRow />
                ) : (
                  contracts.map((contract, index) => (
                    <motion.tr
                      key={contract.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                      onClick={() => onReviewContract(contract.id)}
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600 shrink-0">
                            <FileText size={20} />
                          </div>
                          <span className="font-medium text-slate-900 group-hover:text-blue-600 transition-colors">
                            {contract.title}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-slate-600">{contract.type}</span>
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge status={contract.status} />
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 rounded-full bg-slate-200 overflow-hidden">
                            <img src={`https://picsum.photos/seed/${contract.author}/40/40`} alt="" referrerPolicy="no-referrer" />
                          </div>
                          <span className="text-sm text-slate-600">{contract.author}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-500">{contract.updatedAt}</td>
                      <td className="px-6 py-4 text-right">
                        <button className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-all">
                          <MoreVertical size={18} />
                        </button>
                      </td>
                    </motion.tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        <div className="p-4 bg-slate-50/50 border-t border-slate-100 flex items-center justify-between">
          <p className="text-sm text-slate-500">当前显示 {contracts.length} 份合同</p>
          <div className="text-xs text-slate-400">点击任意合同进入校审工作台</div>
        </div>
      </div>

      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/45 backdrop-blur-[1px] flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-white rounded-2xl border border-slate-200 shadow-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900">上传合同</h3>
              <button
                type="button"
                onClick={closeUploadModal}
                disabled={isUploading}
                className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 disabled:opacity-50"
              >
                <X size={18} />
              </button>
            </div>

            <div className="px-6 py-5 space-y-4">
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_FILE_EXTENSIONS.join(',')}
                className="hidden"
                onChange={handleFileChange}
              />
              <button
                type="button"
                onClick={handlePickFile}
                disabled={isUploading}
                className="w-full border border-dashed border-slate-300 rounded-xl p-6 text-left hover:border-blue-400 hover:bg-blue-50/30 transition-colors disabled:opacity-50"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center">
                    <Upload size={18} />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">选择合同文件</p>
                    <p className="text-xs text-slate-500 mt-1">支持 .txt / .docx / .pdf，最大 5MB</p>
                  </div>
                </div>
              </button>

              <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                <p className="text-slate-500">提交人</p>
                <p className="text-slate-900 font-medium">{currentUser.display_name}</p>
              </div>

              <div className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                {selectedFile ? (
                  <div className="space-y-1">
                    <p className="font-medium text-slate-900">{selectedFile.name}</p>
                    <p className="text-xs text-slate-500">{(selectedFile.size / 1024).toFixed(1)} KB</p>
                  </div>
                ) : (
                  <p className="text-slate-500">尚未选择文件</p>
                )}
              </div>

              {uploadError && <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">{uploadError}</div>}
              {uploadSuccess && (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                  {uploadSuccess}
                </div>
              )}
            </div>

            <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={closeUploadModal}
                disabled={isUploading}
                className="px-4 py-2 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 disabled:opacity-50"
              >
                取消
              </button>
              <button
                type="button"
                onClick={() => void handleUploadContract()}
                disabled={isUploading}
                className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {isUploading ? '上传中...' : '上传并开始校审'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  title,
  value,
  caption,
  icon,
  tone,
}: {
  title: string;
  value: string;
  caption: string;
  icon: React.ReactNode;
  tone: 'blue' | 'emerald' | 'amber' | 'violet';
}) {
  const toneClassNames = {
    blue: 'bg-blue-50 text-blue-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    violet: 'bg-violet-50 text-violet-600',
  };

  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className={cn('p-2.5 rounded-xl', toneClassNames[tone])}>{icon}</div>
      </div>
      <div className="mt-4">
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <h3 className="text-2xl font-bold text-slate-900 mt-1">{value}</h3>
        <p className="text-xs text-slate-400 mt-2">{caption}</p>
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
      <td colSpan={6} className="px-6 py-10 text-center text-sm text-slate-500">
        正在加载合同列表...
      </td>
    </tr>
  );
}

function EmptyRow() {
  return (
    <tr>
      <td colSpan={6} className="px-6 py-10 text-center text-sm text-slate-500">
        当前没有符合条件的合同。
      </td>
    </tr>
  );
}
