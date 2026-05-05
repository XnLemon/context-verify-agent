import {
  LayoutDashboard, FileText, CheckCircle2, AlertCircle, Clock, LayoutTemplate,
  Users, UserPlus, Settings, LogOut, ChevronRight,
} from 'lucide-react';
import { cn } from '@/src/lib/utils';
import type { UserMember } from '@/src/types';

export type ListPage =
  | 'dashboard' | 'library' | 'reviewed' | 'alerts' | 'pending' | 'templates'
  | 'employees' | 'add-employee' | 'system-settings' | 'profile-info';

interface NavItem {
  key: ListPage;
  icon: React.ReactNode;
  label: string;
}

interface SidebarProps {
  currentUser: UserMember;
  currentPage: ListPage;
  expanded: boolean;
  onNavigate: (page: ListPage) => void;
  onLogout: () => void;
}

const mainNav: NavItem[] = [
  { key: 'dashboard', icon: <LayoutDashboard size={20} />, label: '工作台' },
  { key: 'library', icon: <FileText size={20} />, label: '合同库' },
  { key: 'reviewed', icon: <CheckCircle2 size={20} />, label: '已审核' },
  { key: 'alerts', icon: <AlertCircle size={20} />, label: '风险预警' },
  { key: 'pending', icon: <Clock size={20} />, label: '待处理' },
  { key: 'templates', icon: <LayoutTemplate size={20} />, label: '公司模板' },
];

const adminNav: NavItem[] = [
  { key: 'employees', icon: <Users size={20} />, label: '员工管理' },
  { key: 'add-employee', icon: <UserPlus size={20} />, label: '添加员工' },
];

const bottomNav: NavItem[] = [
  { key: 'system-settings', icon: <Settings size={20} />, label: '系统设置' },
];

export default function Sidebar({ currentUser, currentPage, expanded, onNavigate, onLogout }: SidebarProps) {
  const isAdmin = currentUser.role === 'admin';

  return (
    <aside
      id="sidebar"
      className={cn(
        'bg-sidebar flex flex-col shrink-0 transition-all duration-200',
        expanded ? 'w-[200px]' : 'w-[60px]',
      )}
    >
      {/* Logo */}
      <div className={cn('flex items-center gap-2.5 h-16 shrink-0', expanded ? 'px-4' : 'justify-center')}>
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-600 flex items-center justify-center text-white font-bold text-sm shrink-0">
          S
        </div>
        {expanded && <span className="text-white font-semibold text-base tracking-tight">SmartAudit</span>}
      </div>

      {/* Main nav */}
      <nav aria-label="主导航" className="flex-1 px-2 space-y-0.5">
        {mainNav.map((item) => (
          <SidebarItem
            key={item.key}
            icon={item.icon}
            label={item.label}
            active={currentPage === item.key}
            expanded={expanded}
            onClick={() => onNavigate(item.key)}
          />
        ))}

        {isAdmin && (
          <>
            {expanded && (
              <div className="px-3 pt-4 pb-1 text-[11px] font-semibold text-text-muted uppercase tracking-wider">
                管理
              </div>
            )}
            {adminNav.map((item) => (
              <SidebarItem
                key={item.key}
                icon={item.icon}
                label={item.label}
                active={currentPage === item.key}
                expanded={expanded}
                onClick={() => onNavigate(item.key)}
              />
            ))}
          </>
        )}
      </nav>

      {/* Bottom nav */}
      <nav aria-label="底部导航" className="px-2 pb-3 space-y-0.5">
        {bottomNav.map((item) => (
          <SidebarItem
            key={item.key}
            icon={item.icon}
            label={item.label}
            active={currentPage === item.key}
            expanded={expanded}
            onClick={() => onNavigate(item.key)}
          />
        ))}
        <SidebarItem
          icon={<LogOut size={20} />}
          label="退出登录"
          active={false}
          expanded={expanded}
          onClick={onLogout}
        />
      </nav>
    </aside>
  );
}

function SidebarItem({
  icon,
  label,
  active,
  expanded,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  expanded: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'w-full flex items-center gap-3 rounded-md transition-all text-sm',
        expanded ? 'px-3 py-2.5' : 'justify-center py-2.5',
        active
          ? 'bg-sidebar-active text-text-sidebar-active shadow-sm'
          : 'text-text-sidebar hover:bg-sidebar-hover hover:text-text-sidebar-active',
      )}
      title={!expanded ? label : undefined}
    >
      <span className="shrink-0">{icon}</span>
      {expanded && (
        <>
          <span className="font-medium">{label}</span>
          {active && <ChevronRight size={16} className="ml-auto opacity-60" />}
        </>
      )}
    </button>
  );
}
