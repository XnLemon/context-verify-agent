import { Bell, Menu, Search } from 'lucide-react';
import Avatar from '@/src/components/ui/Avatar';
import { cn } from '@/src/lib/utils';
import type { UserMember } from '@/src/types';

interface HeaderProps {
  currentUser: UserMember;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onToggleSidebar: () => void;
  onProfileClick: () => void;
  sidebarExpanded?: boolean;
}

export default function Header({
  currentUser,
  searchQuery,
  onSearchChange,
  onToggleSidebar,
  onProfileClick,
  sidebarExpanded,
}: HeaderProps) {
  return (
    <header className="h-16 bg-surface border-b border-border-light flex items-center gap-4 px-5 shrink-0">
      <button
        type="button"
        onClick={onToggleSidebar}
        aria-label={sidebarExpanded ? '收起侧边栏' : '展开侧边栏'}
        aria-expanded={sidebarExpanded}
        aria-controls="sidebar"
        className="w-9 h-9 rounded-md flex items-center justify-center text-text-muted hover:bg-surface-subtle hover:text-text-primary transition-colors"
      >
        <Menu size={20} />
      </button>

      <div className="relative flex-1 max-w-sm">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="搜索合同、类型或提交人..."
          aria-label="搜索合同"
          className="w-full pl-9 pr-4 h-9 bg-surface-subtle border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all"
        />
      </div>

      <div className="ml-auto flex items-center gap-2">
        <button type="button" aria-label="通知" className="relative w-9 h-9 rounded-md flex items-center justify-center text-text-muted hover:bg-surface-subtle hover:text-text-primary transition-colors">
          <Bell size={18} />
          <span className="absolute top-2 right-2 w-2 h-2 bg-danger rounded-full border-2 border-surface" />
        </button>

        <div className="h-6 w-px bg-border mx-1" />

        <button
          onClick={onProfileClick}
          className="flex items-center gap-2.5 pl-2 pr-1.5 py-1 rounded-md hover:bg-surface-subtle transition-colors"
        >
          <div className="text-right hidden sm:block">
            <p className="text-sm font-medium text-text-primary leading-tight">{currentUser.displayName}</p>
            <p className="text-xs text-text-muted">
              {currentUser.role === 'admin' ? '管理员' : '员工'}
            </p>
          </div>
          <Avatar
            src={currentUser.avatarUrl}
            name={currentUser.displayName}
            size="sm"
          />
        </button>
      </div>
    </header>
  );
}
