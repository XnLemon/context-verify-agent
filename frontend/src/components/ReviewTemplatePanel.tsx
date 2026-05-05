import { useEffect, useState } from 'react';
import { ChevronDown, ChevronRight, FileText, Search } from 'lucide-react';

import { listClauses, listTemplates } from '@/src/lib/api';
import { cn } from '@/src/lib/utils';
import type { ClauseResponse, TemplateResponse } from '@/src/types';

interface ReviewTemplatePanelProps {
  onInsertContent: (content: string) => void;
}

export default function ReviewTemplatePanel({ onInsertContent }: ReviewTemplatePanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [activeSubTab, setActiveSubTab] = useState<'template' | 'clause'>('template');
  const [searchQuery, setSearchQuery] = useState('');
  const [templates, setTemplates] = useState<TemplateResponse[]>([]);
  const [clauses, setClauses] = useState<ClauseResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    setExpandedId(null);
  }, [activeSubTab]);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      setLoading(true);
      try {
        if (activeSubTab === 'template') {
          const data = await listTemplates({ search: searchQuery || undefined });
          if (!cancelled) {
            setTemplates(data);
          }
        } else {
          const data = await listClauses({ search: searchQuery || undefined });
          if (!cancelled) {
            setClauses(data);
          }
        }
      } catch {
        // Silently swallow fetch errors for this non-critical panel
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void fetchData();

    return () => {
      cancelled = true;
    };
  }, [activeSubTab, searchQuery]);

  const items: Array<TemplateResponse | ClauseResponse> = activeSubTab === 'template' ? templates : clauses;

  function getItemName(item: TemplateResponse | ClauseResponse): string {
    return activeSubTab === 'template'
      ? (item as TemplateResponse).name
      : (item as ClauseResponse).title;
  }

  function getItemTags(item: TemplateResponse | ClauseResponse) {
    return (item as TemplateResponse).tags ?? (item as ClauseResponse).tags ?? [];
  }

  return (
    <div className="border-b border-slate-200">
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors"
      >
        <span className="text-sm font-bold text-slate-800">公司模板</span>
        {collapsed ? (
          <ChevronRight size={16} className="text-slate-400" />
        ) : (
          <ChevronDown size={16} className="text-slate-400" />
        )}
      </button>

      {!collapsed && (
        <div className="px-3 pb-3 space-y-3">
          {/* Sub-tabs */}
          <div className="flex bg-slate-100 rounded-lg p-0.5">
            <button
              onClick={() => setActiveSubTab('template')}
              className={cn(
                'flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-all',
                activeSubTab === 'template'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700',
              )}
            >
              全文模板
            </button>
            <button
              onClick={() => setActiveSubTab('clause')}
              className={cn(
                'flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-all',
                activeSubTab === 'clause'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700',
              )}
            >
              条款片段
            </button>
          </div>

          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索模板..."
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 placeholder:text-slate-400"
            />
          </div>

          {/* Item list */}
          <div className="max-h-64 overflow-y-auto space-y-1">
            {loading ? (
              <div className="text-center py-4 text-xs text-slate-400">加载中...</div>
            ) : items.length === 0 ? (
              <div className="text-center py-4 text-xs text-slate-400">暂无模板</div>
            ) : (
              items.map((item) => {
                const tags = getItemTags(item);
                return (
                  <div key={item.id} className="border border-slate-200 rounded-lg overflow-hidden">
                    <button
                      onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                      className="w-full flex items-center justify-between gap-2 px-3 py-2 hover:bg-slate-50 transition-colors"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText size={14} className="text-slate-400 shrink-0" />
                        <span className="text-xs font-medium text-slate-700 truncate">
                          {getItemName(item)}
                        </span>
                      </div>
                      {tags.length > 0 && (
                        <div className="flex items-center gap-1 shrink-0">
                          {tags.slice(0, 2).map((tag) => (
                            <span
                              key={tag.id}
                              className="px-1.5 py-0.5 text-[10px] font-medium rounded"
                              style={{
                                backgroundColor: `${tag.color}18`,
                                color: tag.color,
                                border: `1px solid ${tag.color}30`,
                              }}
                            >
                              {tag.name}
                            </span>
                          ))}
                        </div>
                      )}
                    </button>

                    {expandedId === item.id && (
                      <div className="px-3 pb-3 space-y-2">
                        {/* Description (templates only) */}
                        {activeSubTab === 'template' && (item as TemplateResponse).description && (
                          <p className="text-[11px] text-slate-500 leading-relaxed">
                            {(item as TemplateResponse).description}
                          </p>
                        )}

                        {/* Content preview */}
                        <div className="text-xs text-slate-600 bg-slate-50 rounded-lg p-2.5 leading-relaxed font-mono whitespace-pre-wrap max-h-28 overflow-y-auto">
                          {item.content.length > 300
                            ? item.content.slice(0, 300) + '...'
                            : item.content}
                        </div>

                        {/* Tags (show all when expanded) */}
                        {tags.length > 2 && (
                          <div className="flex flex-wrap gap-1">
                            {tags.slice(2).map((tag) => (
                              <span
                                key={tag.id}
                                className="px-1.5 py-0.5 text-[10px] font-medium rounded"
                                style={{
                                  backgroundColor: `${tag.color}18`,
                                  color: tag.color,
                                  border: `1px solid ${tag.color}30`,
                                }}
                              >
                                {tag.name}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Insert button */}
                        <button
                          onClick={() => onInsertContent(item.content)}
                          className="w-full py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                        >
                          插入到正文
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
