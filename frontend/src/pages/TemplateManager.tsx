import { useCallback, useEffect, useState } from 'react';
import { FileText, Pencil, Plus, RefreshCw, Search, Trash2, X } from 'lucide-react';
import { motion } from 'motion/react';

import {
  createClause,
  createTemplate,
  deleteClause,
  deleteTemplate,
  listClauses,
  listTags,
  listTemplates,
  updateClause,
  updateTemplate,
} from '@/src/lib/api';
import { cn } from '@/src/lib/utils';
import type { ClauseResponse, TemplateResponse, TemplateTag } from '@/src/types';
import TemplateTagManager from '@/src/components/TemplateTagManager';

type TabKey = 'templates' | 'clauses';

interface EditFormState {
  name: string;
  description: string;
  content: string;
  tagIds: number[];
}

const EMPTY_FORM: EditFormState = {
  name: '',
  description: '',
  content: '',
  tagIds: [],
};

export default function TemplateManager() {
  const [activeTab, setActiveTab] = useState<TabKey>('templates');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilterTagIds, setSelectedFilterTagIds] = useState<number[]>([]);
  const [items, setItems] = useState<(TemplateResponse | ClauseResponse)[]>([]);
  const [tags, setTags] = useState<TemplateTag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Inline editor state
  const [editingId, setEditingId] = useState<string | null>(null); // null = closed, 'new' = creating, string = editing
  const [editForm, setEditForm] = useState<EditFormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [fetchedTags, fetchedItems] = await Promise.all([
        listTags(),
        activeTab === 'templates'
          ? listTemplates({
              search: searchQuery || undefined,
              tagIds: selectedFilterTagIds.length > 0 ? selectedFilterTagIds : undefined,
            })
          : listClauses({
              search: searchQuery || undefined,
              tagIds: selectedFilterTagIds.length > 0 ? selectedFilterTagIds : undefined,
            }),
      ]);
      setTags(fetchedTags);
      setItems(fetchedItems);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : '加载数据失败');
    } finally {
      setLoading(false);
    }
  }, [activeTab, searchQuery, selectedFilterTagIds]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // Reset filter and close editor when tab changes
  useEffect(() => {
    setSearchQuery('');
    setSelectedFilterTagIds([]);
    closeEditor();
  }, [activeTab]);

  function openNewEditor() {
    setEditForm(EMPTY_FORM);
    setEditingId('new');
  }

  function openEditEditor(item: TemplateResponse | ClauseResponse) {
    setEditForm({
      name: isTemplateItem(item) ? item.name : item.title,
      description: isTemplateItem(item) ? (item.description ?? '') : '',
      content: item.content,
      tagIds: item.tags.map((t) => t.id),
    });
    setEditingId(item.id);
  }

  function closeEditor() {
    setEditingId(null);
    setEditForm(EMPTY_FORM);
    setSaving(false);
  }

  function isTemplateItem(
    item: TemplateResponse | ClauseResponse,
  ): item is TemplateResponse {
    return 'name' in item;
  }

  async function handleSave() {
    if (saving) {
      return;
    }

    const nameOrTitle = editForm.name.trim();
    const content = editForm.content.trim();
    if (!nameOrTitle || !content) {
      return;
    }

    setSaving(true);
    try {
      if (activeTab === 'templates') {
        const data = {
          name: nameOrTitle,
          description: editForm.description.trim() || undefined,
          content,
          tags: editForm.tagIds,
        };
        if (editingId === 'new') {
          await createTemplate(data);
        } else if (editingId) {
          await updateTemplate(editingId, data);
        }
      } else {
        const data = {
          title: nameOrTitle,
          content,
          tags: editForm.tagIds,
        };
        if (editingId === 'new') {
          await createClause(data);
        } else if (editingId) {
          await updateClause(editingId, data);
        }
      }
      closeEditor();
      await loadData();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : '保存失败');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(item: TemplateResponse | ClauseResponse) {
    if (editingId) {
      return;
    }
    const label = isTemplateItem(item) ? item.name : item.title;
    if (!window.confirm(`确定要删除"${label}"吗？此操作不可撤销。`)) {
      return;
    }
    try {
      if (activeTab === 'templates') {
        await deleteTemplate(item.id);
      } else {
        await deleteClause(item.id);
      }
      await loadData();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : '删除失败');
    }
  }

  const hasFilter =
    searchQuery.trim().length > 0 || selectedFilterTagIds.length > 0;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">模板管理</h1>
          <p className="text-sm text-slate-500 mt-1">
            管理合同全文模板和条款片段，支持标签分类和快速检索。
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadData()}
          disabled={loading}
          className="px-4 py-2 rounded-lg border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 flex items-center gap-2 disabled:opacity-50"
        >
          <RefreshCw size={16} className={cn(loading && 'animate-spin')} />
          刷新
        </button>
      </div>

      {/* Tab Bar */}
      <div className="border-b border-slate-200">
        <div className="flex gap-6">
          <TabButton
            active={activeTab === 'templates'}
            onClick={() => setActiveTab('templates')}
          >
            全文模板
          </TabButton>
          <TabButton
            active={activeTab === 'clauses'}
            onClick={() => setActiveTab('clauses')}
          >
            条款片段
          </TabButton>
        </div>
      </div>

      {/* Search + New Button */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索名称..."
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
          />
        </div>
        <button
          type="button"
          onClick={openNewEditor}
          disabled={editingId !== null}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          <Plus size={16} />
          {activeTab === 'templates' ? '新建模板' : '新建条款'}
        </button>
      </div>

      {/* Tag Filter */}
      {tags.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs font-medium text-slate-500 mb-2">按标签筛选</p>
          <TemplateTagManager
            tags={tags}
            selectedTagIds={selectedFilterTagIds}
            onTagSelect={setSelectedFilterTagIds}
            onTagsChanged={() => void loadData()}
          />
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Inline Editor for new item */}
      {editingId === 'new' && (
        <InlineEditor
          activeTab={activeTab}
          editForm={editForm}
          onFormChange={setEditForm}
          tags={tags}
          onTagsChanged={() => void loadData()}
          onSave={() => void handleSave()}
          onCancel={closeEditor}
          saving={saving}
        />
      )}

      {/* List View */}
      <div className="space-y-3">
        {loading ? (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-10 text-center">
            <p className="text-sm text-slate-500">正在加载...</p>
          </div>
        ) : items.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-10 text-center space-y-2">
            <FileText className="mx-auto text-slate-300" size={40} />
            <p className="text-sm text-slate-500">
              {hasFilter
                ? '没有符合条件的记录。'
                : activeTab === 'templates'
                  ? '暂无模板，点击上方按钮创建。'
                  : '暂无条款，点击上方按钮创建。'}
            </p>
          </div>
        ) : (
          items.map((item, index) =>
            editingId === item.id ? (
              <InlineEditor
                key={item.id}
                activeTab={activeTab}
                editForm={editForm}
                onFormChange={setEditForm}
                tags={tags}
                onTagsChanged={() => void loadData()}
                onSave={() => void handleSave()}
                onCancel={closeEditor}
                saving={saving}
              />
            ) : (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.03 }}
              >
                <ItemCard
                  item={item}
                  activeTab={activeTab}
                  onEdit={() => openEditEditor(item)}
                  onDelete={() => void handleDelete(item)}
                  disabled={editingId !== null}
                />
              </motion.div>
            ),
          )
        )}
      </div>

      {/* Tag Management Section */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-base font-semibold text-slate-900">标签管理</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            管理所有标签，删除标签后关联关系自动解除。
          </p>
        </div>
        <div className="px-6 py-4">
          <TemplateTagManager
            tags={tags}
            selectedTagIds={[]}
            onTagSelect={() => {
              /* no-op in management mode */
            }}
            onTagsChanged={() => void loadData()}
            isEditor
          />
        </div>
      </div>
    </div>
  );
}

// ─── Tab Button ──────────────────────────────────────────────────────────────

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'pb-3 text-sm font-medium border-b-2 transition-colors',
        active
          ? 'border-blue-600 text-blue-600'
          : 'border-transparent text-slate-500 hover:text-slate-700',
      )}
    >
      {children}
    </button>
  );
}

// ─── Item Card ───────────────────────────────────────────────────────────────

function ItemCard({
  item,
  activeTab,
  onEdit,
  onDelete,
  disabled,
}: {
  item: TemplateResponse | ClauseResponse;
  activeTab: TabKey;
  onEdit: () => void;
  onDelete: () => void;
  disabled: boolean;
}) {
  const isTemplate = activeTab === 'templates';
  const tmpl = isTemplate ? (item as TemplateResponse) : null;
  const title = isTemplate ? tmpl!.name : (item as ClauseResponse).title;
  const description = tmpl?.description ?? null;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3 min-w-0 flex-1">
            <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600 shrink-0 mt-0.5">
              <FileText size={18} />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="font-semibold text-slate-900 truncate">{title}</h3>
              {description && (
                <p className="text-sm text-slate-500 mt-0.5 line-clamp-2">
                  {description}
                </p>
              )}
              {item.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {item.tags.map((tag) => (
                    <span
                      key={tag.id}
                      className="inline-block px-2 py-0.5 rounded-full text-[11px]"
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
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={onEdit}
              disabled={disabled}
              className="p-2 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors disabled:opacity-40"
              title="编辑"
            >
              <Pencil size={16} />
            </button>
            <button
              type="button"
              onClick={onDelete}
              disabled={disabled}
              className="p-2 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-40"
              title="删除"
            >
              <Trash2 size={16} />
            </button>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span>
              创建人: {item.createdBy}
            </span>
            <span className="hidden sm:inline">
              {new Date(item.createdAt).toLocaleDateString('zh-CN')}
            </span>
          </div>
          <span className="text-xs text-slate-400">
            更新于 {new Date(item.updatedAt).toLocaleDateString('zh-CN')}
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Inline Editor ───────────────────────────────────────────────────────────

function InlineEditor({
  activeTab,
  editForm,
  onFormChange,
  tags,
  onTagsChanged,
  onSave,
  onCancel,
  saving,
}: {
  activeTab: TabKey;
  editForm: EditFormState;
  onFormChange: (form: EditFormState) => void;
  tags: TemplateTag[];
  onTagsChanged: () => void;
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
}) {
  const isTemplate = activeTab === 'templates';

  function updateField<K extends keyof EditFormState>(
    field: K,
    value: EditFormState[K],
  ) {
    onFormChange({ ...editForm, [field]: value });
  }

  return (
    <div className="bg-white rounded-2xl border-2 border-blue-200 shadow-lg overflow-hidden">
      <div className="px-6 py-3 bg-blue-50 border-b border-blue-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-blue-700">
          {editForm.name ? `编辑: ${editForm.name}` : isTemplate ? '新建模板' : '新建条款'}
        </h3>
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="p-1 rounded-md text-blue-400 hover:text-blue-600 hover:bg-blue-100 disabled:opacity-50"
        >
          <X size={16} />
        </button>
      </div>

      <div className="px-6 py-4 space-y-4">
        {/* Name / Title */}
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">
            {isTemplate ? '模板名称' : '条款标题'}
          </label>
          <input
            type="text"
            value={editForm.name}
            onChange={(e) => updateField('name', e.target.value)}
            placeholder={isTemplate ? '输入模板名称...' : '输入条款标题...'}
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>

        {/* Description (templates only) */}
        {isTemplate && (
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              描述
            </label>
            <textarea
              value={editForm.description}
              onChange={(e) => updateField('description', e.target.value)}
              placeholder="输入模板描述（可选）..."
              rows={2}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 resize-none"
            />
          </div>
        )}

        {/* Content */}
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">
            内容
          </label>
          <textarea
            value={editForm.content}
            onChange={(e) => updateField('content', e.target.value)}
            placeholder="输入正文内容..."
            rows={8}
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono leading-relaxed resize-y"
          />
        </div>

        {/* Tags */}
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-2">
            关联标签
          </label>
          <TemplateTagManager
            tags={tags}
            selectedTagIds={editForm.tagIds}
            onTagSelect={(tagIds) => updateField('tagIds', tagIds)}
            onTagsChanged={onTagsChanged}
            isEditor
          />
        </div>
      </div>

      <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="px-4 py-2 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 disabled:opacity-50"
        >
          取消
        </button>
        <button
          type="button"
          onClick={onSave}
          disabled={saving || !editForm.name.trim() || !editForm.content.trim()}
          className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? '保存中...' : '保存'}
        </button>
      </div>
    </div>
  );
}
