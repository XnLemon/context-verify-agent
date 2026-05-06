import { useEditor, EditorContent } from '@tiptap/react';
import { StarterKit } from '@tiptap/starter-kit';
import { Table } from '@tiptap/extension-table';
import { TableRow } from '@tiptap/extension-table-row';
import { TableCell } from '@tiptap/extension-table-cell';
import { TableHeader } from '@tiptap/extension-table-header';
import { Underline } from '@tiptap/extension-underline';
import { Placeholder } from '@tiptap/extension-placeholder';

import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  Heading1,
  Heading2,
  List,
  ListOrdered,
  Table as TableIcon,
  Undo,
  Redo,
} from 'lucide-react';
import { cn } from '@/src/lib/utils';

interface RichTextEditorProps {
  content: string;
  onChange: (html: string) => void;
  placeholder?: string;
}

export default function RichTextEditor({ content, onChange, placeholder }: RichTextEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
      }),
      Table.configure({ resizable: true }),
      TableRow,
      TableCell,
      TableHeader,
      Underline,
      Placeholder.configure({
        placeholder: placeholder ?? '请输入合同正文...',
      }),
    ],
    content,
    onUpdate: ({ editor: ed }) => {
      onChange(ed.getHTML());
    },
    immediatelyRender: true,
  });

  if (!editor) {
    return <div className="h-64 rounded-lg border border-slate-200 bg-surface animate-pulse" />;
  }

  return (
    <div className="h-full flex flex-col tiptap-editor">
      <Toolbar editor={editor} />
      <EditorContent editor={editor} className="flex-1 overflow-auto p-4 outline-none" />
    </div>
  );
}

function Toolbar({ editor }: { editor: NonNullable<ReturnType<typeof useEditor>> }) {
  if (!editor) {
    return null;
  }

  return (
    <div className="flex items-center gap-1 px-3 py-2 border-b border-slate-200 bg-surface rounded-t-lg flex-wrap shrink-0">
      <ToolbarButton
        icon={<Undo size={16} />}
        onClick={() => editor.chain().focus().undo().run()}
        disabled={!editor.can().undo()}
        label="撤销"
      />
      <ToolbarButton
        icon={<Redo size={16} />}
        onClick={() => editor.chain().focus().redo().run()}
        disabled={!editor.can().redo()}
        label="重做"
      />
      <div className="w-px h-5 bg-slate-200 mx-1" />
      <ToolbarButton
        icon={<Heading1 size={16} />}
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
        active={editor.isActive('heading', { level: 1 })}
        label="标题 1"
      />
      <ToolbarButton
        icon={<Heading2 size={16} />}
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        active={editor.isActive('heading', { level: 2 })}
        label="标题 2"
      />
      <ToolbarButton
        icon={<Heading2 size={16} className="text-lg" />}
        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        active={editor.isActive('heading', { level: 3 })}
        label="标题 3"
      />
      <div className="w-px h-5 bg-slate-200 mx-1" />
      <ToolbarButton
        icon={<Bold size={16} />}
        onClick={() => editor.chain().focus().toggleBold().run()}
        active={editor.isActive('bold')}
        label="加粗"
      />
      <ToolbarButton
        icon={<Italic size={16} />}
        onClick={() => editor.chain().focus().toggleItalic().run()}
        active={editor.isActive('italic')}
        label="斜体"
      />
      <ToolbarButton
        icon={<UnderlineIcon size={16} />}
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        active={editor.isActive('underline')}
        label="下划线"
      />
      <div className="w-px h-5 bg-slate-200 mx-1" />
      <ToolbarButton
        icon={<List size={16} />}
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        active={editor.isActive('bulletList')}
        label="无序列表"
      />
      <ToolbarButton
        icon={<ListOrdered size={16} />}
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        active={editor.isActive('orderedList')}
        label="有序列表"
      />
      <div className="w-px h-5 bg-slate-200 mx-1" />
      <ToolbarButton
        icon={<TableIcon size={16} />}
        onClick={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}
        active={editor.isActive('table')}
        label="插入表格"
      />
    </div>
  );
}

function ToolbarButton({
  icon,
  onClick,
  active,
  disabled,
  label,
}: {
  icon: React.ReactNode;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      className={cn(
        'p-1.5 rounded-md transition-colors',
        active
          ? 'bg-blue-100 text-blue-700'
          : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700',
        disabled && 'opacity-30 cursor-not-allowed',
      )}
    >
      {icon}
    </button>
  );
}
