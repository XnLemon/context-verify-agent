import React, { useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  ArrowUp,
  Check,
  CheckCircle2,
  History,
  Info,
  MessageSquare,
  Paperclip,
  Save,
  Send,
  ShieldAlert,
  X,
  Zap,
} from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';

import {
  finalizeWorkbenchContract,
  getWorkbenchContractDetail,
  getWorkbenchHistory,
  redraftWorkbenchContract,
  scanWorkbenchContract,
  updateWorkbenchContractContent,
  sendWorkbenchChatMessage,
  updateWorkbenchIssueStatus,
} from '@/src/lib/api';
import { canFinalizeContract, canUploadOrEditContract } from '@/src/lib/permissions';
import { cn } from '@/src/lib/utils';
import type {
  AuditIssue,
  AuditIssueStatus,
  ChatMessage,
  Contract,
  ContractStatus,
  HistoryItem,
  ReviewResult,
  UserMember,
} from '@/src/types';

export default function Review({
  currentUser,
  contractId,
  onBack,
}: {
  currentUser: UserMember;
  contractId: string | null;
  onBack: () => void;
}) {
  const [activeTab, setActiveTab] = useState<'ai' | 'chat' | 'history'>('ai');
  const [contract, setContract] = useState<Contract | null>(null);
  const [latestReview, setLatestReview] = useState<ReviewResult | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAiScanning, setIsAiScanning] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [pendingIssueId, setPendingIssueId] = useState<string | null>(null);
  const [isApplyingIssueAction, setIsApplyingIssueAction] = useState(false);
  const [autoScanAttempted, setAutoScanAttempted] = useState(false);
  const [isEditingContent, setIsEditingContent] = useState(false);
  const [draftContent, setDraftContent] = useState('');
  const [isSavingContent, setIsSavingContent] = useState(false);
  const [isFinalizing, setIsFinalizing] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const canEditContract = canUploadOrEditContract(currentUser);
  const canFinalize = canFinalizeContract(currentUser);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  useEffect(() => {
    if (!contractId) {
      return;
    }

    let cancelled = false;

    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const [detail, history] = await Promise.all([
          getWorkbenchContractDetail(contractId),
          getWorkbenchHistory(contractId),
        ]);
        if (cancelled) {
          return;
        }
        setContract(detail.contract);
        setLatestReview(detail.latestReview);
        setChatMessages(detail.chatMessages);
        setHistoryItems(history);
        setAutoScanAttempted(false);
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : '加载合同详情失败。');
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadData();

    return () => {
      cancelled = true;
    };
  }, [contractId]);

  useEffect(() => {
    if (!contractId || !contract || latestReview || autoScanAttempted || loading) {
      return;
    }
    setAutoScanAttempted(true);
    void handleAiScan();
  }, [autoScanAttempted, contract, contractId, latestReview, loading]);

  async function refreshHistory(currentContractId: string) {
    try {
      const nextHistory = await getWorkbenchHistory(currentContractId);
      setHistoryItems(nextHistory);
    } catch {
      // Ignore secondary refresh errors to keep the main workflow responsive.
    }
  }

  async function handleAiScan() {
    if (!contractId) {
      return;
    }

    setIsAiScanning(true);
    setError(null);
    try {
      const response = await scanWorkbenchContract(contractId);
      setContract(response.contract);
      setLatestReview(response.latestReview);
      await refreshHistory(contractId);
    } catch (scanError) {
      setError(scanError instanceof Error ? scanError.message : '执行 AI 扫描失败。');
    } finally {
      setIsAiScanning(false);
    }
  }

  async function handleIssueStatus(issueId: string, status: AuditIssueStatus) {
    if (!contractId) {
      return;
    }

    setPendingIssueId(issueId);
    setIsApplyingIssueAction(true);
    setError(null);
    try {
      const nextReview = await updateWorkbenchIssueStatus(contractId, issueId, status, false);
      let reviewAfterDecision = nextReview;

      if (status === 'accepted') {
        try {
          const redraft = await redraftWorkbenchContract(contractId);
          reviewAfterDecision = redraft.latestReview;
          setContract(redraft.contract);
        } catch (redraftError) {
          const redraftMessage = redraftError instanceof Error ? redraftError.message : 'Accepted, but auto-redraft failed.';
          setError('Accepted, but auto-redraft failed: ' + redraftMessage);
        }
      }

      setLatestReview(reviewAfterDecision);
      const detail = await getWorkbenchContractDetail(contractId);
      setContract(detail.contract);
      await refreshHistory(contractId);
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Failed to update issue status.');
    } finally {
      setPendingIssueId(null);
      setIsApplyingIssueAction(false);
    }
  }

  async function handleSendMessage() {
    if (!contractId || !inputMessage.trim()) {
      return;
    }

    setIsSending(true);
    setError(null);
    try {
      const response = await sendWorkbenchChatMessage(contractId, inputMessage.trim());
      setInputMessage('');
      setChatMessages(response.messages);
      if (response.latestReview) {
        setLatestReview(response.latestReview);
      }
      const detail = await getWorkbenchContractDetail(contractId);
      setContract(detail.contract);
      await refreshHistory(contractId);
    } catch (chatError) {
      setError(chatError instanceof Error ? chatError.message : '发送消息失败。');
    } finally {
      setIsSending(false);
    }
  }


  function handleStartEdit() {
    if (!contract) {
      return;
    }
    setDraftContent(contract.content);
    setIsEditingContent(true);
  }

  function handleCancelEdit() {
    if (!contract) {
      setIsEditingContent(false);
      return;
    }
    setDraftContent(contract.content);
    setIsEditingContent(false);
  }

  async function handleSaveContent() {
    if (!contractId) {
      return;
    }
    if (!draftContent.trim()) {
      setError('合同正文不能为空。');
      return;
    }

    setIsSavingContent(true);
    setError(null);
    try {
      const result = await updateWorkbenchContractContent(contractId, draftContent);
      setContract(result.contract);
      setLatestReview(null);
      setIsEditingContent(false);
      await refreshHistory(contractId);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : '保存合同正文失败。');
    } finally {
      setIsSavingContent(false);
    }
  }

  async function handleFinalize(status: Extract<ContractStatus, 'approved' | 'rejected'>) {
    if (!contractId || !canFinalize) {
      return;
    }

    setIsFinalizing(true);
    setError(null);
    try {
      const result = await finalizeWorkbenchContract(contractId, status);
      setContract(result.contract);
      await refreshHistory(contractId);
    } catch (finalizeError) {
      setError(finalizeError instanceof Error ? finalizeError.message : '最终审批失败。');
    } finally {
      setIsFinalizing(false);
    }
  }
  const issues = latestReview?.issues ?? [];
  const pendingIssues = issues.filter((issue) => issue.status === 'pending');

  if (!contractId) {
    return <EmptyState onBack={onBack} message="请先从工作台选择一份合同。" />;
  }

  if (loading) {
    return <EmptyState onBack={onBack} message="正在加载合同详情..." />;
  }

  if (!contract) {
    return <EmptyState onBack={onBack} message={error ?? '未找到该合同。'} />;
  }

  return (
    <div className="h-full flex flex-col bg-slate-50">
      <div className="h-14 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 transition-colors">
            <ArrowLeft size={20} />
          </button>
          <div className="h-6 w-px bg-slate-200" />
          <h2 className="font-bold text-slate-900">{contract.title}</h2>
          <span className={cn('px-2 py-0.5 text-xs font-bold rounded', statusPillClassName(contract.status))}>
            {statusLabel(contract.status)}
          </span>
        </div>

        <div className="flex items-center gap-3">
          {canEditContract && (
            !isEditingContent ? (
              <button
                onClick={handleStartEdit}
                className="px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                编辑正文
              </button>
            ) : (
              <>
                <button
                  onClick={handleCancelEdit}
                  disabled={isSavingContent}
                  className="px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-60"
                >
                  取消编辑
                </button>
                <button
                  onClick={() => void handleSaveContent()}
                  disabled={isSavingContent}
                  className="px-4 py-1.5 text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 rounded-lg transition-colors disabled:opacity-60"
                >
                  {isSavingContent ? '保存中...' : '保存正文'}
                </button>
              </>
            )
          )}
          <button
            onClick={() => setActiveTab('history')}
            className="flex items-center gap-2 px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <History size={18} />
            操作历史
          </button>
          <button
            onClick={() => void handleAiScan()}
            disabled={isAiScanning || isEditingContent || isSavingContent}
            className="flex items-center gap-2 px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-60"
          >
            <Save size={18} />
            {isAiScanning ? '扫描中...' : '重新扫描'}
          </button>
          {canFinalize ? (
            <>
              <button
                onClick={() => void handleFinalize('approved')}
                disabled={isFinalizing || isEditingContent || isSavingContent}
                className="flex items-center gap-2 px-4 py-1.5 text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 rounded-lg transition-colors shadow-sm shadow-emerald-600/10 disabled:opacity-60"
              >
                <CheckCircle2 size={18} />
                {isFinalizing ? '提交中...' : '最终通过'}
              </button>
              <button
                onClick={() => void handleFinalize('rejected')}
                disabled={isFinalizing || isEditingContent || isSavingContent}
                className="flex items-center gap-2 px-4 py-1.5 text-sm font-medium bg-red-600 text-white hover:bg-red-700 rounded-lg transition-colors shadow-sm shadow-red-600/10 disabled:opacity-60"
              >
                <X size={18} />
                驳回
              </button>
            </>
          ) : (
            <button
              className="flex items-center gap-2 px-4 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-lg transition-colors shadow-sm shadow-blue-600/10 opacity-90"
              disabled
            >
              <Send size={18} />
              等待经理/审核审批
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-auto p-8 flex justify-center">
          <div className="w-full max-w-4xl bg-white shadow-xl shadow-slate-200/50 border border-slate-200 rounded-lg h-[min(100vh-9rem,960px)] min-h-[560px] p-8 md:p-12 font-serif leading-relaxed text-slate-800">
            {error && <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}
                        {isEditingContent ? (
              <div className="h-full flex flex-col gap-3">
                <div className="text-xs text-slate-500">你可以手动编辑合同正文，保存后会同步到系统并记录操作历史。</div>
                <textarea
                  value={draftContent}
                  onChange={(event) => setDraftContent(event.target.value)}
                  className="flex-1 w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm leading-7 font-mono resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>
            ) : (
              <DocumentContent content={contract.content} />
            )}
          </div>
        </div>

        <aside className="w-[420px] bg-white border-l border-slate-200 flex flex-col shrink-0">
          <div className="flex border-b border-slate-100 shrink-0">
            <TabButton active={activeTab === 'ai'} onClick={() => setActiveTab('ai')} icon={<Zap size={16} />} label="智能扫描" />
            <TabButton
              active={activeTab === 'chat'}
              onClick={() => setActiveTab('chat')}
              icon={<MessageSquare size={16} />}
              label="深度对话"
            />
            <TabButton
              active={activeTab === 'history'}
              onClick={() => setActiveTab('history')}
              icon={<History size={16} />}
              label="操作历史"
            />
          </div>

          <div className="flex-1 overflow-hidden flex flex-col">
            {activeTab === 'ai' && (
              <div className="flex-1 overflow-auto p-6 space-y-6">
                <div className="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-2xl p-6 text-white shadow-lg shadow-blue-600/20">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Zap size={20} fill="currentColor" />
                      <span className="font-bold">AI 实时监控</span>
                    </div>
                    <button
                      onClick={() => void handleAiScan()}
                      disabled={isAiScanning || isEditingContent || isSavingContent}
                      className="rounded-lg bg-white/15 px-3 py-1 text-[11px] font-bold hover:bg-white/20 disabled:opacity-60"
                    >
                      {isAiScanning ? '扫描中' : '重新扫描'}
                    </button>
                  </div>
                  <p className="text-sm text-blue-100 mb-6">
                    当前识别到 {pendingIssues.length} 个待处理风险点。你可以直接处理建议，或切换到对话页继续追问。
                  </p>
                  <div className="grid grid-cols-3 gap-2">
                    <StatBox
                      label="高风险"
                      value={pendingIssues.filter((issue) => issue.severity === 'high').length.toString()}
                      color="bg-red-400/20 text-red-200"
                    />
                    <StatBox
                      label="中风险"
                      value={pendingIssues.filter((issue) => issue.severity === 'medium').length.toString()}
                      color="bg-amber-400/20 text-amber-200"
                    />
                    <StatBox
                      label="建议"
                      value={pendingIssues.filter((issue) => issue.severity === 'low' || issue.severity === 'info').length.toString()}
                      color="bg-blue-400/20 text-blue-200"
                    />
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between px-1">
                    <h3 className="font-bold text-slate-900 flex items-center gap-2">
                      风险清单
                      <span className="bg-slate-100 text-slate-600 text-xs px-2 py-0.5 rounded-full">{pendingIssues.length}</span>
                    </h3>
                    {latestReview && <span className="text-xs text-slate-400">最近扫描：{formatDateTime(latestReview.generatedAt)}</span>}
                  </div>

                  <AnimatePresence mode="popLayout">
                    {pendingIssues.map((issue, index) => (
                      <motion.div
                        key={issue.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        transition={{ delay: index * 0.08 }}
                        className="group bg-white border border-slate-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-md transition-all"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <SeverityIcon severity={issue.severity} />
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                              {issueTypeLabel(issue.type)}
                            </span>
                          </div>
                          <span className="text-[10px] font-medium text-slate-400">{issue.location ?? '全文'}</span>
                        </div>
                        <h4 className="font-bold text-slate-900 mb-1">{issue.message}</h4>
                        <p className="text-sm text-slate-600 leading-relaxed mb-4">{issue.suggestion}</p>
                        <div className="flex gap-2">
                          <button
                            onClick={() => void handleIssueStatus(issue.id, 'accepted')}
                            disabled={isApplyingIssueAction || pendingIssueId !== null}
                            className="flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-blue-50 text-blue-600 hover:bg-blue-600 hover:text-white rounded-lg text-xs font-bold transition-all disabled:opacity-60"
                          >
                            <Check size={14} />
                            采纳建议
                          </button>
                          <button
                            onClick={() => void handleIssueStatus(issue.id, 'rejected')}
                            disabled={isApplyingIssueAction || pendingIssueId !== null}
                            className="flex-1 flex items-center justify-center gap-1.5 py-1.5 bg-slate-50 text-slate-500 hover:bg-red-50 hover:text-red-600 rounded-lg text-xs font-bold transition-all disabled:opacity-60"
                          >
                            <X size={14} />
                            忽略
                          </button>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>

                  {pendingIssues.length === 0 && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-12 px-6">
                      <div className="w-16 h-16 bg-emerald-50 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4">
                        <CheckCircle2 size={32} />
                      </div>
                      <h4 className="font-bold text-slate-900 mb-1">当前没有待处理风险</h4>
                      <p className="text-sm text-slate-500">你可以继续深度对话，或者重新发起一次合同扫描。</p>
                      <button onClick={() => setActiveTab('chat')} className="mt-4 text-blue-600 font-bold text-sm hover:underline">
                        进入深度对话
                      </button>
                    </motion.div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'chat' && (
              <div className="flex-1 flex flex-col overflow-hidden bg-slate-50/50">
                <div className="flex-1 overflow-auto p-6 space-y-6">
                  {chatMessages.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-500">
                      还没有对话记录，可以直接向 AI 追问合同风险、法条依据或修改建议。
                    </div>
                  ) : (
                    chatMessages.map((msg) => (
                      <div
                        key={msg.id}
                        className={cn(
                          'flex flex-col max-w-[85%]',
                          msg.role === 'user' ? 'ml-auto items-end' : 'items-start',
                        )}
                      >
                        <div
                          className={cn(
                            'p-4 rounded-2xl text-sm leading-relaxed shadow-sm whitespace-pre-wrap',
                            msg.role === 'user'
                              ? 'bg-blue-600 text-white rounded-tr-none'
                              : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none',
                          )}
                        >
                          {msg.content}
                        </div>
                        <span className="text-[10px] text-slate-400 mt-1 px-1">{msg.timestamp}</span>
                      </div>
                    ))
                  )}
                  <div ref={chatEndRef} />
                </div>

                <div className="p-4 bg-white border-t border-slate-200">
                  <div className="flex items-center gap-2 mb-3 overflow-x-auto pb-1 no-scrollbar">
                    <button
                      onClick={() => setInputMessage('请结合当前合同，给我争议解决条款的修改建议。')}
                      className="whitespace-nowrap text-xs font-bold text-slate-500 hover:text-blue-600 px-2 py-1 bg-slate-100 rounded-lg"
                    >
                      争议解决建议
                    </button>
                    <button
                      onClick={() => setInputMessage('请解释当前主体信息相关的合规风险。')}
                      className="whitespace-nowrap text-xs font-bold text-slate-500 hover:text-blue-600 px-2 py-1 bg-slate-100 rounded-lg"
                    >
                      主体合规风险
                    </button>
                    <button
                      onClick={() => setInputMessage('请告诉我付款条款应该怎么改更稳妥。')}
                      className="whitespace-nowrap text-xs font-bold text-slate-500 hover:text-blue-600 px-2 py-1 bg-slate-100 rounded-lg"
                    >
                      付款条款优化
                    </button>
                  </div>
                  <div className="relative">
                    <textarea
                      value={inputMessage}
                      onChange={(event) => setInputMessage(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' && !event.shiftKey) {
                          event.preventDefault();
                          void handleSendMessage();
                        }
                      }}
                      placeholder="向 AI 提问关于合同的任何问题..."
                      className="w-full pl-4 pr-12 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 resize-none min-h-[100px]"
                    />
                    <div className="absolute right-3 bottom-3 flex items-center gap-2">
                      <button className="p-1.5 text-slate-400 hover:text-slate-600">
                        <Paperclip size={18} />
                      </button>
                      <button
                        onClick={() => void handleSendMessage()}
                        disabled={!inputMessage.trim() || isSending}
                        className="p-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                      >
                        <ArrowUp size={18} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'history' && (
              <div className="flex-1 overflow-auto p-6 space-y-4">
                {historyItems.length === 0 ? (
                  <div className="flex flex-col items-center justify-center text-slate-400 py-12">
                    <History size={48} className="mb-4 opacity-20" />
                    <p className="text-sm">暂无操作历史</p>
                  </div>
                ) : (
                  historyItems.map((item) => (
                    <div key={item.id} className="rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <h4 className="text-sm font-bold text-slate-900">{item.title}</h4>
                        <span className="text-[11px] text-slate-400">{formatDateTime(item.createdAt)}</span>
                      </div>
                      <p className="mt-2 text-sm text-slate-600">{item.description}</p>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function DocumentContent({ content }: { content: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 900, height: 700 });
  const [page, setPage] = useState(1);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) {
      return;
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }
      const next = {
        width: Math.max(320, Math.floor(entry.contentRect.width)),
        height: Math.max(320, Math.floor(entry.contentRect.height)),
      };
      setSize((prev) => (prev.width === next.width && prev.height === next.height ? prev : next));
    });

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const pages = React.useMemo(() => {
    const lines = content.split('\n');
    const charsPerLine = Math.max(18, Math.floor((size.width - 48) / 10));
    const pageCapacity = Math.max(16, Math.floor((size.height - 96) / 28));

    const blocks: Array<{ kind: 'title' | 'clause' | 'paragraph' | 'spacer'; text: string; lines: number }> = [];

    lines.forEach((line, index) => {
      const trimmed = line.trim();
      if (!trimmed) {
        blocks.push({ kind: 'spacer', text: '', lines: 1 });
        return;
      }

      if (index === 0) {
        const lineCount = Math.max(2, Math.ceil(trimmed.length / charsPerLine) + 1);
        blocks.push({ kind: 'title', text: trimmed, lines: lineCount });
        return;
      }

      if (/^第[一二三四五六七八九十百零]+条/.test(trimmed)) {
        const lineCount = Math.max(2, Math.ceil(trimmed.length / charsPerLine) + 1);
        blocks.push({ kind: 'clause', text: trimmed, lines: lineCount });
        return;
      }

      const lineCount = Math.max(1, Math.ceil(trimmed.length / charsPerLine));
      blocks.push({ kind: 'paragraph', text: trimmed, lines: lineCount + 1 });
    });

    const pageBlocks: typeof blocks[] = [];
    let current: typeof blocks = [];
    let currentLines = 0;

    const pushCurrent = () => {
      if (current.length > 0) {
        pageBlocks.push(current);
      }
      current = [];
      currentLines = 0;
    };

    for (const block of blocks) {
      if (block.lines > pageCapacity) {
        if (current.length > 0) {
          pushCurrent();
        }
        if (block.kind !== 'paragraph') {
          pageBlocks.push([block]);
          continue;
        }

        const maxChars = Math.max(charsPerLine * Math.max(6, pageCapacity - 2), 200);
        for (let i = 0; i < block.text.length; i += maxChars) {
          const chunk = block.text.slice(i, i + maxChars);
          const chunkLines = Math.max(2, Math.ceil(chunk.length / charsPerLine) + 1);
          pageBlocks.push([{ kind: 'paragraph', text: chunk, lines: chunkLines }]);
        }
        continue;
      }

      if (currentLines + block.lines > pageCapacity && current.length > 0) {
        pushCurrent();
      }

      current.push(block);
      currentLines += block.lines;
    }

    if (current.length > 0) {
      pageBlocks.push(current);
    }

    return pageBlocks.length > 0 ? pageBlocks : [[{ kind: 'paragraph', text: '', lines: 1 }]];
  }, [content, size.height, size.width]);

  useEffect(() => {
    setPage(1);
  }, [content]);

  useEffect(() => {
    setPage((prev) => Math.min(prev, pages.length));
  }, [pages.length]);

  const currentPage = pages[Math.max(0, page - 1)] ?? [];

  return (
    <div ref={containerRef} className="h-full flex flex-col">
      <div className="flex-1 overflow-hidden">
        <div className="h-full whitespace-pre-wrap overflow-hidden">
          {currentPage.map((block, index) => {
            if (block.kind === 'spacer') {
              return <div key={index} className="h-4" />;
            }
            if (block.kind === 'title') {
              return (
                <h1 key={index} className="text-3xl font-bold mb-8 text-center text-slate-900 break-words">
                  {block.text}
                </h1>
              );
            }
            if (block.kind === 'clause') {
              return (
                <h2 key={index} className="text-xl font-bold mt-8 mb-4 text-slate-900 break-words">
                  {block.text}
                </h2>
              );
            }
            return (
              <p key={index} className="mb-4 break-words">
                {block.text}
              </p>
            );
          })}
        </div>
      </div>

      <div className="mt-6 border-t border-slate-200 pt-3 flex items-center justify-between text-sm text-slate-500">
        <button
          onClick={() => setPage((prev) => Math.max(1, prev - 1))}
          disabled={page <= 1}
          className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Prev
        </button>
        <span>
          Page {page} / {pages.length}
        </span>
        <button
          onClick={() => setPage((prev) => Math.min(pages.length, prev + 1))}
          disabled={page >= pages.length}
          className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Next
        </button>
      </div>
    </div>
  );
}

function EmptyState({ onBack, message }: { onBack: () => void; message: string }) {
  return (
    <div className="h-full flex items-center justify-center bg-slate-50">
      <div className="max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm text-center">
        <p className="text-sm text-slate-600">{message}</p>
        <button
          onClick={onBack}
          className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          返回工作台
        </button>
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex-1 flex flex-col items-center justify-center gap-1 py-4 text-[10px] font-bold transition-all border-b-2',
        active ? 'text-blue-600 border-blue-600 bg-blue-50/30' : 'text-slate-400 border-transparent hover:text-slate-600 hover:bg-slate-50',
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function StatBox({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className={cn('p-2 rounded-xl text-center', color)}>
      <p className="text-[10px] font-bold opacity-80">{label}</p>
      <p className="text-lg font-black leading-none mt-1">{value}</p>
    </div>
  );
}

function SeverityIcon({ severity }: { severity: AuditIssue['severity'] }) {
  if (severity === 'high') {
    return <ShieldAlert size={14} className="text-red-500" />;
  }
  if (severity === 'medium') {
    return <AlertCircle size={14} className="text-amber-500" />;
  }
  if (severity === 'low') {
    return <Info size={14} className="text-blue-500" />;
  }
  return <Info size={14} className="text-slate-400" />;
}

function issueTypeLabel(type: AuditIssue['type']) {
  if (type === 'risk') {
    return '法律风险';
  }
  if (type === 'compliance') {
    return '合规问题';
  }
  return '修改建议';
}

function statusLabel(status: ContractStatus) {
  const labels = {
    pending: '待处理',
    reviewing: '审核中',
    approved: '已通过',
    rejected: '已驳回',
  };
  return labels[status];
}

function statusPillClassName(status: ContractStatus) {
  const classNames = {
    pending: 'bg-slate-100 text-slate-600',
    reviewing: 'bg-blue-50 text-blue-600',
    approved: 'bg-emerald-50 text-emerald-600',
    rejected: 'bg-red-50 text-red-600',
  };
  return classNames[status];
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











