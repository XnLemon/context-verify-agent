import { useCallback, useEffect, useState } from 'react';
import { X } from 'lucide-react';

import { createTag, deleteTag, listTags, updateTag } from '@/src/lib/api';
import Spinner from '@/src/components/ui/Spinner';
import type { TemplateTag } from '@/src/types';

const TAG_COLORS = [
  { value: '#2563eb', label: '蓝色' },
  { value: '#059669', label: '绿色' },
  { value: '#d97706', label: '橙色' },
  { value: '#dc2626', label: '红色' },
  { value: '#7c3aed', label: '紫色' },
  { value: '#0891b2', label: '青色' },
  { value: '#db2777', label: '粉色' },
  { value: '#4f46e5', label: '靛蓝' },
];

export default function TemplateTagManager({ canEdit = false }: { canEdit?: boolean }) {
  const [tags, setTags] = useState<TemplateTag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState('');
  const [newColor, setNewColor] = useState('#2563eb');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [editColor, setEditColor] = useState('');

  const loadTags = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setTags(await listTags());
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载标签失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTags();
  }, [loadTags]);

  async function handleCreate() {
    if (!newName.trim()) {
      return;
    }
    setError(null);
    try {
      const tag = await createTag(newName.trim(), newColor);
      setTags((prev) => [...prev, tag]);
      setNewName('');
      setNewColor('#2563eb');
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建标签失败');
    }
  }

  async function handleUpdate(id: number) {
    if (!editName.trim()) {
      return;
    }
    setError(null);
    try {
      const updated = await updateTag(id, editName.trim(), editColor);
      setTags((prev) => prev.map((t) => (t.id === id ? updated : t)));
      setEditingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新标签失败');
    }
  }

  async function handleDelete(id: number) {
    setError(null);
    try {
      await deleteTag(id);
      setTags((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除标签失败');
    }
  }

  function startEdit(tag: TemplateTag) {
    setEditingId(tag.id);
    setEditName(tag.name);
    setEditColor(tag.color);
  }

  function cancelEdit() {
    setEditingId(null);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Spinner size="md" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <div
            key={tag.id}
            className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium"
            style={{
              backgroundColor: `${tag.color}18`,
              borderColor: `${tag.color}30`,
              color: tag.color,
            }}
          >
            <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: tag.color }} />
            {editingId === tag.id ? (
              <input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onBlur={() => void handleUpdate(tag.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') void handleUpdate(tag.id);
                  if (e.key === 'Escape') cancelEdit();
                }}
                className="w-20 bg-transparent border-b border-current outline-none text-xs"
                autoFocus
              />
            ) : (
              <span className={canEdit ? 'cursor-pointer hover:opacity-80' : ''} onClick={() => canEdit && startEdit(tag)}>
                {tag.name}
              </span>
            )}
            {canEdit && editingId !== tag.id && (
              <button
                type="button"
                onClick={() => void handleDelete(tag.id)}
                className="opacity-50 hover:opacity-100 transition-opacity ml-0.5"
                title="删除标签"
              >
                <X size={12} />
              </button>
            )}
          </div>
        ))}
        {!loading && tags.length === 0 && (
          <p className="text-xs text-text-muted py-1">暂无标签</p>
        )}
      </div>

      {canEdit && (
        <div className="flex items-center gap-2 pt-1">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="新建标签名称..."
            className="flex-1 h-8 px-2.5 text-xs rounded-md border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
            onKeyDown={(e) => { if (e.key === 'Enter') void handleCreate(); }}
          />
          <input
            type="color"
            value={newColor}
            onChange={(e) => setNewColor(e.target.value)}
            className="w-7 h-7 rounded-md border border-border cursor-pointer p-0.5"
            title="选择颜色"
          />
          <button
            type="button"
            onClick={() => void handleCreate()}
            disabled={!newName.trim()}
            className="h-7 px-2.5 rounded-md bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors shrink-0"
          >
            添加
          </button>
        </div>
      )}
    </div>
  );
}
