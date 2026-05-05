import React, { startTransition, useDeferredValue, useMemo, useState } from 'react';

import { getCurrentMember, logout as logoutRequest } from '@/src/lib/api';
import { clearAuthSession, getAuthSession, updateAuthSessionMember } from '@/src/lib/auth';
import { applyFontScale, applyThemePreference, resolveTheme } from '@/src/lib/preferences';
import Sidebar, { type ListPage } from '@/src/components/ui/Sidebar';
import Header from '@/src/components/ui/Header';
import { ToastProvider } from '@/src/components/ui/Toast';
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
import TemplateManager from './pages/TemplateManager';
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

  const [sidebarExpanded, setSidebarExpanded] = useState(false);

  const isAdmin = currentUser?.role === 'admin';

  const visibleListPages = useMemo<ListPage[]>(() => {
    const base: ListPage[] = ['dashboard', 'library', 'reviewed', 'alerts', 'pending', 'templates', 'system-settings', 'profile-info'];
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
    templates: '公司模板 - SmartAudit',
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
    <ToastProvider>
    <div className="flex h-screen font-sans" style={{ backgroundColor: 'var(--app-bg)', color: 'var(--app-text)' }}>
      <Sidebar
        currentUser={currentUser}
        currentPage={currentPage as ListPage}
        expanded={sidebarExpanded}
        onNavigate={navigateToList}
        onLogout={logout}
      />

      <main className="flex-1 flex flex-col overflow-hidden">
        <Header
          currentUser={currentUser}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onToggleSidebar={() => setSidebarExpanded((prev) => !prev)}
          onProfileClick={() => navigateToList('profile-info')}
          sidebarExpanded={sidebarExpanded}
        />

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
          {currentPage === 'templates' && <TemplateManager />}
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
    </ToastProvider>
  );
}


