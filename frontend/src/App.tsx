import React, { startTransition, useDeferredValue, useMemo, useState } from 'react';
import {
  AlertCircle,
  Bell,
  CheckCircle2,
  ChevronRight,
  Clock,
  FileText,
  LayoutDashboard,
  LogOut,
  Search,
  Settings,
  UserPlus,
  Users,
} from 'lucide-react';

import { buildApiAssetUrl, getCurrentMember, logout as logoutRequest } from '@/src/lib/api';
import { clearAuthSession, getAuthSession, updateAuthSessionMember } from '@/src/lib/auth';
import { applyFontScale, applyThemePreference, resolveTheme } from '@/src/lib/preferences';
import { cn } from '@/src/lib/utils';
import type { UserMember } from '@/src/types';
import AddEmployee from './pages/AddEmployee';
import ContractLibrary from './pages/ContractLibrary';
import Dashboard from './pages/Dashboard';
import Employees from './pages/Employees';
import LoginPage from './pages/Login';
import PendingContracts from './pages/PendingContracts';
import ProfileInfo from './pages/ProfileInfo';
import Review from './pages/Review';
import ReviewedContracts from './pages/ReviewedContracts';
import RiskAlerts from './pages/RiskAlerts';
import SystemSettings from './pages/SystemSettings';

type ListPage =
  | 'dashboard'
  | 'library'
  | 'reviewed'
  | 'alerts'
  | 'pending'
  | 'employees'
  | 'add-employee'
  | 'system-settings'
  | 'profile-info';
type AppPage = ListPage | 'review';

function bootstrapCurrentMember(): UserMember | null {
  const session = getAuthSession();
  return session?.member ?? null;
}

export default function App() {
  const [currentUser, setCurrentUser] = useState<UserMember | null>(() => bootstrapCurrentMember());
  const [currentPage, setCurrentPage] = useState<AppPage>('dashboard');
  const [listPageBeforeReview, setListPageBeforeReview] = useState<ListPage>('dashboard');
  const [selectedContractId, setSelectedContractId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const deferredSearchQuery = useDeferredValue(searchQuery);

  const isAdmin = currentUser?.role === 'admin';

  const visibleListPages = useMemo<ListPage[]>(() => {
    const base: ListPage[] = ['dashboard', 'library', 'reviewed', 'alerts', 'pending', 'system-settings', 'profile-info'];
    if (isAdmin) {
      base.push('employees', 'add-employee');
    }
    return base;
  }, [isAdmin]);

  React.useEffect(() => {
    if (!currentUser) {
      return;
    }

    let cancelled = false;
    const syncCurrentUser = async () => {
      try {
        const member = await getCurrentMember();
        if (!cancelled) {
          setCurrentUser(member);
        }
      } catch {
        if (!cancelled) {
          clearAuthSession();
          setCurrentUser(null);
        }
      }
    };

    void syncCurrentUser();

    return () => {
      cancelled = true;
    };
  }, [currentUser?.id]);

  React.useEffect(() => {
    if (!currentUser) {
      return;
    }

    applyThemePreference(currentUser.themePreference ?? 'system');
    applyFontScale(currentUser.fontScale ?? 'medium');

    if (currentUser.themePreference !== 'system') {
      return;
    }

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => {
      document.documentElement.dataset.theme = resolveTheme('system');
    };
    mediaQuery.addEventListener('change', onChange);
    return () => mediaQuery.removeEventListener('change', onChange);
  }, [currentUser]);

  const navigateToList = (page: ListPage) => {
    if (!visibleListPages.includes(page)) {
      return;
    }
    startTransition(() => {
      setCurrentPage(page);
    });
  };

  const navigateToReview = (id: string, fromPage: ListPage) => {
    if (!visibleListPages.includes(fromPage)) {
      return;
    }
    startTransition(() => {
      setListPageBeforeReview(fromPage);
      setSelectedContractId(id);
      setCurrentPage('review');
    });
  };

  const navigateBackFromReview = () => {
    startTransition(() => {
      setCurrentPage(listPageBeforeReview);
    });
  };

  const logout = async () => {
    try {
      await logoutRequest();
    } catch {
      // Ignore backend logout failure and clear local session anyway.
    }
    clearAuthSession();
    setCurrentUser(null);
    setCurrentPage('dashboard');
  };

  const handleCurrentUserUpdated = (member: UserMember) => {
    setCurrentUser(member);
    updateAuthSessionMember(member);
  };

  const pageTitles: Record<AppPage, string> = {
    dashboard: '工作台 - SmartAudit',
    library: '合同库 - SmartAudit',
    reviewed: '已审核 - SmartAudit',
    alerts: '风险预警 - SmartAudit',
    pending: '待处理 - SmartAudit',
    employees: '员工管理 - SmartAudit',
    'add-employee': '添加员工 - SmartAudit',
    'system-settings': '系统设置 - SmartAudit',
    'profile-info': '个人信息 - SmartAudit',
    review: '合同审核 - SmartAudit',
  };

  React.useEffect(() => {
    document.title = pageTitles[currentPage] ?? 'SmartAudit';
  }, [currentPage]);

  if (!currentUser) {
    return <LoginPage onLoginSuccess={(member) => setCurrentUser(member)} />;
  }

  return (
    <div className="flex h-screen font-sans" style={{ backgroundColor: 'var(--app-bg)', color: 'var(--app-text)' }}>
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">S</div>
          <span className="font-bold text-xl tracking-tight">SmartAudit</span>
        </div>

        <nav className="flex-1 px-4 space-y-1">
          <NavItem icon={<LayoutDashboard size={20} />} label="工作台" active={currentPage === 'dashboard'} onClick={() => navigateToList('dashboard')} />
          <NavItem icon={<FileText size={20} />} label="合同库" active={currentPage === 'library'} onClick={() => navigateToList('library')} />
          <NavItem icon={<CheckCircle2 size={20} />} label="已审核" active={currentPage === 'reviewed'} onClick={() => navigateToList('reviewed')} />
          <NavItem icon={<AlertCircle size={20} />} label="风险预警" active={currentPage === 'alerts'} onClick={() => navigateToList('alerts')} />
          <NavItem icon={<Clock size={20} />} label="待处理" active={currentPage === 'pending'} onClick={() => navigateToList('pending')} />
          {isAdmin && <NavItem icon={<Users size={20} />} label="员工页" active={currentPage === 'employees'} onClick={() => navigateToList('employees')} />}
          {isAdmin && <NavItem icon={<UserPlus size={20} />} label="添加员工" active={currentPage === 'add-employee'} onClick={() => navigateToList('add-employee')} />}
        </nav>

        <div className="p-4 border-t border-slate-100 space-y-1">
          <NavItem
            icon={<Settings size={20} />}
            label="系统设置"
            active={currentPage === 'system-settings'}
            onClick={() => navigateToList('system-settings')}
          />
          <NavItem icon={<LogOut size={20} />} label="退出登录" active={false} onClick={logout} />
        </div>
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shrink-0">
          <div className="flex items-center gap-4 flex-1 max-w-xl">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <input
                type="text"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="搜索合同、类型或提交人..."
                className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button className="p-2 text-slate-500 hover:bg-slate-100 rounded-full relative">
              <Bell size={20} />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white" />
            </button>
            <div className="h-8 w-px bg-slate-200 mx-2" />
            <button
              type="button"
              className="flex items-center gap-3 pl-2 hover:bg-slate-50 rounded-xl p-1 transition-colors"
              onClick={() => navigateToList('profile-info')}
            >
              <div className="text-right">
                <p className="text-sm font-medium">{currentUser.displayName}</p>
                <p className="text-xs text-slate-500">{currentUser.role === 'admin' ? '管理员' : '员工'} / {currentUser.memberType}</p>
              </div>
              <div className="w-10 h-10 bg-slate-200 rounded-full overflow-hidden border border-slate-200">
                <img
                  src={buildApiAssetUrl(currentUser.avatarUrl) ?? `https://picsum.photos/seed/${currentUser.username}/100/100`}
                  alt="Avatar"
                  referrerPolicy="no-referrer"
                />
              </div>
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-auto">
          {currentPage === 'dashboard' && (
            <Dashboard
              currentUser={currentUser}
              onReviewContract={(id) => navigateToReview(id, 'dashboard')}
              searchQuery={deferredSearchQuery}
            />
          )}
          {currentPage === 'library' && <ContractLibrary onReviewContract={(id) => navigateToReview(id, 'library')} searchQuery={deferredSearchQuery} />}
          {currentPage === 'reviewed' && <ReviewedContracts onReviewContract={(id) => navigateToReview(id, 'reviewed')} searchQuery={deferredSearchQuery} />}
          {currentPage === 'alerts' && <RiskAlerts onReviewContract={(id) => navigateToReview(id, 'alerts')} searchQuery={deferredSearchQuery} />}
          {currentPage === 'pending' && <PendingContracts onReviewContract={(id) => navigateToReview(id, 'pending')} searchQuery={deferredSearchQuery} />}
          {currentPage === 'employees' && isAdmin && <Employees />}
          {currentPage === 'add-employee' && isAdmin && <AddEmployee />}
          {currentPage === 'system-settings' && (
            <SystemSettings currentUser={currentUser} onUserUpdated={handleCurrentUserUpdated} />
          )}
          {currentPage === 'profile-info' && (
            <ProfileInfo currentUser={currentUser} onUserUpdated={handleCurrentUserUpdated} />
          )}
          {currentPage === 'review' && <Review currentUser={currentUser} contractId={selectedContractId} onBack={navigateBackFromReview} />}
        </div>
      </main>
    </div>
  );
}

function NavItem({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all',
        active
          ? 'bg-blue-50 text-blue-600 shadow-sm shadow-blue-100/50'
          : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900',
      )}
    >
      {icon}
      <span>{label}</span>
      {active && <ChevronRight className="ml-auto" size={16} />}
    </button>
  );
}

