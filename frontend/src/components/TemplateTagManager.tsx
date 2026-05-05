import { useState } from 'react';
import { Plus, X } from 'lucide-react';

import { createTag, deleteTag } from '@/src/lib/api';
import { cn } from '@/src/lib/utils';
import type { TemplateTag } from '@/src/types';

interface TemplateTagManagerProps {
  tags: TemplateTag[];
  selectedTagIds: number[];
  onTagSelect: (tagIds: number[]) => void;
  onTagsChanged: () => void;
  isEditor?: boolean;
}

const PRESET_COLORS = [
  '#3B82F6',
  '#10B981',
  '#F59E0B',
  '#EF4444',
  '#8B5CF6',
  '#EC4899',
  '#06B6D4',
  '#84CC16',
  '#F97316',
  '#6366F1',
];

export default function TemplateTagManager({
  tags,
  selectedTagIds,
  onTagSelect,
  onTagsChanged,
  isEditor = false,
}: TemplateTagManagerProps) {
  const [newTagName, setNewTagName] = useState('');
  const [creating, setCreating] = useState(false);
  const [creationError, setCreationError] = useState<string | null>(null);

  function handleToggle(tagId: number) {
    if (selectedTagIds.includes(tagId)) {
      onTagSelect(selectedTagIds.filter((id) => id !== tagId));
    } else {
      onTagSelect([...selectedTagIds, tagId]);
    }
  }

  async function handleCreate() {
    const name = newTagName.trim();
    if (!name || creating) {
      return;
    }
    setCreating(true);
    setCreationError(null);
    try {
      const color = PRESET_COLORS[Math.floor(Math.random() * PRESET_COLORS.length)];
      await createTag(name, color);
      setNewTagName('');
      onTagsChanged();
    } catch (err) {
      setCreationError(err instanceof Error ? err.message : '创建标签失败');
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(tagId: number) {
    if (selectedTagIds.includes(tagId)) {
      onTagSelect(selectedTagIds.filter((id) => id !== tagId));
    }
    try {
      await deleteTag(tagId);
      onTagsChanged();
    } catch (err) {
      console.error('Failed to delete tag:', err);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault();
      void handleCreate();
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <div key={tag.id} className="flex items-center">
            {isEditor ? (
              <label
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs cursor-pointer hover:opacity-80 transition-opacity select-none"
                style={{
                  backgroundColor: `${tag.color}18`,
                  color: tag.color,
                  border: `1px solid ${tag.color}30`,
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedTagIds.includes(tag.id)}
                  onChange={() => handleToggle(tag.id)}
                  className="h-3 w-3 rounded"
                />
                <span>{tag.name}</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    void handleDelete(tag.id);
                  }}
                  className="ml-0.5 rounded-full hover:bg-black/10 p-0.5"
                  title="删除标签"
                >
                  <X size={10} />
                </button>
              </label>
            ) : (
              <button
                type="button"
                onClick={() => handleToggle(tag.id)}
                className={cn(
                  'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs transition-all select-none',
                  selectedTagIds.includes(tag.id)
                    ? 'shadow-sm'
                    : 'opacity-60 hover:opacity-100',
                )}
                style={{
                  backgroundColor: `${tag.color}18`,
                  color: tag.color,
                  border: `1px solid ${tag.color}30`,
                  ...(selectedTagIds.includes(tag.id)
                    ? { boxShadow: `0 0 0 2px ${tag.color}40` }
                    : {}),
                }}
              >
                <span>{tag.name}</span>
              </button>
            )}
          </div>
        ))}
        {tags.length === 0 && (
          <span className="text-xs text-slate-400 py-1">暂无标签</span>
        )}
      </div>

      {isEditor && (
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={newTagName}
            onChange={(e) => setNewTagName(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入标签名称，回车创建..."
            className="flex-1 px-2.5 py-1.5 text-xs border border-slate-200 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 placeholder:text-slate-400"
          />
          <button
            type="button"
            onClick={() => void handleCreate()}
            disabled={creating || !newTagName.trim()}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors shrink-0"
          >
            <Plus size={12} />
            新建
          </button>
        </div>
      )}
      {creationError && <p className="text-xs text-red-500">{creationError}</p>}
    </div>
  );
}
