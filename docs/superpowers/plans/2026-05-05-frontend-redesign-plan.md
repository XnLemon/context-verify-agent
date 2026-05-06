# Frontend UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This plan follows the [frontend redesign spec](../specs/2026-05-05-frontend-redesign-design.md).

**Goal:** Redesign the frontend UI with a cohesive professional SaaS look: login page, color system, collapsible sidebar, top header, and a reusable base component library.

**Architecture:** CSS design tokens (`index.css`) → `components/ui/` component library → replace page-level markup piecewise. All business logic preserved; only the visual layer changes.

**Tech Stack:** React 19, TypeScript, Tailwind CSS v4, lucide-react, motion (framer-motion), CSS custom properties

---

## File Map

### Modified
- `frontend/src/index.css` — Replace with @theme design tokens + dark mode CSS variables
- `frontend/src/App.tsx` — Replace sidebar + header with Sidebar + Header components
- `frontend/src/pages/Login.tsx` — Immersive Option C layout

### Created
- `frontend/src/components/ui/Spinner.tsx`
- `frontend/src/components/ui/Button.tsx`
- `frontend/src/components/ui/Card.tsx`
- `frontend/src/components/ui/Badge.tsx`
- `frontend/src/components/ui/Avatar.tsx`
- `frontend/src/components/ui/Input.tsx`
- `frontend/src/components/ui/Modal.tsx`
- `frontend/src/components/ui/Toast.tsx`
- `frontend/src/components/ui/Header.tsx`
- `frontend/src/components/ui/Sidebar.tsx`

### Not Modified (out of scope)
- Any other page components (Dashboard, Review, etc.)
- Backend, API, types, or routing
- `frontend/src/lib/utils.ts` (cn() stays)

---

### Task 1: Design token system in index.css

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Replace index.css with design token system**

Replace the entire file with:

```css
@import "tailwindcss";

@theme {
  --font-sans: "Inter", "PingFang SC", "Microsoft YaHei", sans-serif;
  --font-serif: "Georgia", "Source Han Serif SC", "Noto Serif CJK SC", serif;

  /* Brand */
  --color-brand-50: #eff6ff;
  --color-brand-100: #dbeafe;
  --color-brand-200: #bfdbfe;
  --color-brand-500: #3b82f6;
  --color-brand-600: #2563eb;
  --color-brand-700: #1d4ed8;

  /* Surface */
  --color-surface: #ffffff;
  --color-surface-subtle: #f8fafc;
  --color-sidebar: #0f172a;
  --color-sidebar-hover: rgba(255, 255, 255, 0.08);
  --color-sidebar-active: #2563eb;

  /* Text */
  --color-text-primary: #0f172a;
  --color-text-secondary: #64748b;
  --color-text-muted: #94a3b8;
  --color-text-sidebar: #94a3b8;
  --color-text-sidebar-active: #ffffff;

  /* Border */
  --color-border: #e2e8f0;
  --color-border-light: #f1f5f9;

  /* Semantic */
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  --color-info: #3b82f6;

  /* Radius */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;

  /* Shadow */
  --shadow-card: 0 1px 3px rgba(0, 0, 0, 0.04), 0 4px 16px rgba(0, 0, 0, 0.06);
}

@layer base {
  :root {
    --app-bg: #f8fafc;
    --app-text: #0f172a;
    --app-font-scale: 1;
  }

  html[data-theme='dark'] {
    --app-bg: #0b1220;
    --app-text: #e2e8f0;
    --color-surface: #0f172a;
    --color-surface-subtle: #1e293b;
    --color-sidebar: #020617;
    --color-text-primary: #e2e8f0;
    --color-text-secondary: #94a3b8;
    --color-border: #334155;
    --color-border-light: #1e293b;
  }

  html[data-font-scale='small'] { --app-font-scale: 0.93; }
  html[data-font-scale='medium'] { --app-font-scale: 1; }
  html[data-font-scale='large'] { --app-font-scale: 1.08; }

  body {
    @apply text-slate-900;
    background: var(--app-bg);
    color: var(--app-text);
    font-size: calc(16px * var(--app-font-scale));
  }
}

/* Dark mode overrides removed — components reference CSS variables directly */

/* TipTap editor styles */
.tiptap-editor .ProseMirror {
  @apply outline-none min-h-[300px] leading-relaxed;
  color: var(--color-text-primary);
}
.tiptap-editor .ProseMirror p { @apply mb-3; }
.tiptap-editor .ProseMirror h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 1rem; color: var(--color-text-primary); }
.tiptap-editor .ProseMirror h2 { font-size: 1.25rem; font-weight: 700; margin-bottom: 0.75rem; margin-top: 1.5rem; color: var(--color-text-primary); }
.tiptap-editor .ProseMirror h3 { font-size: 1.125rem; font-weight: 700; margin-bottom: 0.5rem; margin-top: 1rem; color: var(--color-text-primary); }
.tiptap-editor .ProseMirror strong { font-weight: 700; color: var(--color-text-primary); }
.tiptap-editor .ProseMirror ul { @apply list-disc pl-6 mb-3; }
.tiptap-editor .ProseMirror ol { @apply list-decimal pl-6 mb-3; }
.tiptap-editor .ProseMirror li { @apply mb-1; }
.tiptap-editor .ProseMirror table { @apply w-full border-collapse mb-4; }
.tiptap-editor .ProseMirror th { border: 1px solid var(--color-border); background: var(--color-surface-subtle); @apply px-3 py-2 text-left font-semibold; color: var(--color-text-secondary); }
.tiptap-editor .ProseMirror td { border: 1px solid var(--color-border); @apply px-3 py-2; color: var(--color-text-primary); }
.tiptap-editor .ProseMirror table .selectedCell { background: var(--color-brand-50); }
.tiptap-editor .ProseMirror p.is-editor-empty:first-child::before {
  color: var(--color-text-muted);
  @apply pointer-events-none float-left h-0;
  content: attr(data-placeholder);
}

/* Markdown body styles */
.markdown-body { color: var(--color-text-primary); @apply leading-relaxed; }
.markdown-body h1 { @apply text-2xl font-bold mb-4; }
.markdown-body p { @apply mb-4; }
.rich-doc-content h1, .rich-doc-content h2, .rich-doc-content h3, .rich-doc-content h4 {
  color: var(--color-text-primary); @apply font-bold; margin-top: 1.5em; margin-bottom: 0.5em;
}
.rich-doc-content h1 { @apply text-3xl; }
.rich-doc-content h2 { @apply text-2xl; }
.rich-doc-content h3 { @apply text-xl; }
.rich-doc-content p { @apply leading-relaxed mb-4; color: var(--color-text-primary); }
.rich-doc-content strong { color: var(--color-text-primary); @apply font-bold; }
.rich-doc-content table { @apply w-full border-collapse mb-4; }
.rich-doc-content th { border: 1px solid var(--color-border); background: var(--color-surface-subtle); @apply px-3 py-2 text-left font-semibold; color: var(--color-text-secondary); }
.rich-doc-content td { border: 1px solid var(--color-border); @apply px-3 py-2; color: var(--color-text-primary); }
.rich-doc-content ul, .rich-doc-content ol { @apply mb-4 pl-6; color: var(--color-text-primary); }
.rich-doc-content li { @apply mb-1; }
```

- [ ] **Verify no !important overrides remain**

Run: `grep -n '!important' frontend/src/index.css`
Expected: no output (TipTap editor should have none either)

- [ ] **Commit**

```bash
git add frontend/src/index.css
git commit -m "feat: add design token system with CSS variables for brand colors, surfaces, dark mode"
```

---

### Task 2: Spinner component

**Files:**
- Create: `frontend/src/components/ui/Spinner.tsx`

- [ ] **Create Spinner component**

```tsx
import { cn } from '@/src/lib/utils';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  color?: string;
  className?: string;
}

const sizeMap = { sm: 16, md: 24, lg: 32 };

export default function Spinner({ size = 'md', color, className }: SpinnerProps) {
  const px = sizeMap[size];
  return (
    <svg
      width={px}
      height={px}
      viewBox="0 0 24 24"
      fill="none"
      className={cn('animate-spin', className)}
      style={color ? { color } : undefined}
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.2" />
      <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}
```

- [ ] **Commit**

```bash
git add frontend/src/components/ui/Spinner.tsx
mkdir -p frontend/src/components/ui && git add frontend/src/components/ui/Spinner.tsx
git commit -m "feat: add Spinner UI component"
```

---

### Task 3: Button component

**Files:**
- Create: `frontend/src/components/ui/Button.tsx`

- [ ] **Create Button component**

```tsx
import { ButtonHTMLAttributes, forwardRef } from 'react';
import Spinner from '@/src/components/ui/Spinner';
import { cn } from '@/src/lib/utils';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variantStyles: Record<Variant, string> = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700 active:bg-brand-700 shadow-sm',
  secondary: 'bg-surface text-text-primary border border-border hover:bg-surface-subtle active:bg-surface-subtle',
  ghost: 'text-text-secondary hover:bg-surface-subtle active:bg-surface-subtle',
  danger: 'bg-danger text-white hover:opacity-90 active:opacity-80',
};

const sizeStyles: Record<Size, string> = {
  sm: 'h-8 px-3 text-xs rounded-md gap-1.5',
  md: 'h-10 px-4 text-sm rounded-lg gap-2',
  lg: 'h-12 px-6 text-base rounded-lg gap-2.5',
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, disabled, className, children, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center font-medium transition-all focus:outline-none focus:ring-2 focus:ring-brand-500/20 disabled:opacity-50 disabled:pointer-events-none',
        variantStyles[variant],
        sizeStyles[size],
        className,
      )}
      {...props}
    >
      {loading && <Spinner size={size === 'lg' ? 'md' : 'sm'} />}
      {children}
    </button>
  ),
);

Button.displayName = 'Button';
export default Button;
```

- [ ] **Commit**

```bash
git add frontend/src/components/ui/Button.tsx
git commit -m "feat: add Button UI component with variants (primary/secondary/ghost/danger) and sizes"
```

---

### Task 4: Card component

**Files:**
- Create: `frontend/src/components/ui/Card.tsx`

- [ ] **Create Card component**

```tsx
import { HTMLAttributes, forwardRef } from 'react';
import { cn } from '@/src/lib/utils';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ hover, className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'bg-surface rounded-lg shadow-card border border-border-light',
        hover && 'hover:shadow-md transition-shadow cursor-pointer',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  ),
);

Card.displayName = 'Card';
export default Card;
```

- [ ] **Commit**

```bash
git add frontend/src/components/ui/Card.tsx
git commit -m "feat: add Card UI component with optional hover effect"
```

---

### Task 5: Badge component

**Files:**
- Create: `frontend/src/components/ui/Badge.tsx`

- [ ] **Create Badge component**

```tsx
import { cn } from '@/src/lib/utils';

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info';

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-surface-subtle text-text-secondary border-border',
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  danger: 'bg-red-50 text-red-700 border-red-200',
  info: 'bg-brand-50 text-brand-700 border-brand-200',
};

export default function Badge({ variant = 'default', className, children }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
        variantStyles[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
```

- [ ] **Commit**

```bash
git add frontend/src/components/ui/Badge.tsx
git commit -m "feat: add Badge UI component with status variants"
```

---

### Task 6: Avatar component

**Files:**
- Create: `frontend/src/components/ui/Avatar.tsx`

- [ ] **Create Avatar component**

```tsx
import { useState } from 'react';
import { cn } from '@/src/lib/utils';

interface AvatarProps {
  src?: string | null;
  name: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeMap = { sm: 'w-8 h-8 text-xs', md: 'w-10 h-10 text-sm', lg: 'w-12 h-12 text-base' };

function getInitials(name: string): string {
  return name.slice(0, 2).toUpperCase();
}

export default function Avatar({ src, name, size = 'md', className }: AvatarProps) {
  const [imgError, setImgError] = useState(false);
  const showImage = src && !imgError;

  return (
    <div className={cn('relative rounded-full overflow-hidden shrink-0', sizeMap[size], className)}>
      {showImage ? (
        <img
          src={src}
          alt={name}
          onError={() => setImgError(true)}
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center font-semibold text-white bg-gradient-to-br from-brand-500 to-brand-600">
          {getInitials(name)}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Commit**

```bash
git add frontend/src/components/ui/Avatar.tsx
git commit -m "feat: add Avatar UI component with image fallback to initials"
```

---

### Task 7: Input component

**Files:**
- Create: `frontend/src/components/ui/Input.tsx`

- [ ] **Create Input component**

```tsx
import { InputHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/src/lib/utils';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');

    return (
      <div className="space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="block text-sm font-medium text-text-primary">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            'w-full px-3.5 py-2.5 rounded-md border text-sm transition-all bg-surface',
            'focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500',
            error
              ? 'border-danger focus:border-danger focus:ring-danger/20'
              : 'border-border hover:border-text-muted',
            className,
          )}
          {...props}
        />
        {error && <p className="text-xs text-danger">{error}</p>}
      </div>
    );
  },
);

Input.displayName = 'Input';
export default Input;
```

- [ ] **Commit**

```bash
git add frontend/src/components/ui/Input.tsx
git commit -m "feat: add Input UI component with label and error state"
```

---

### Task 8: Modal component

**Files:**
- Create: `frontend/src/components/ui/Modal.tsx`

- [ ] **Create Modal component**

```tsx
import { useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X } from 'lucide-react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export default function Modal({ open, onClose, title, children, footer }: ModalProps) {
  const handleEscape = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
      document.addEventListener('keydown', handleEscape);
    }
    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open, handleEscape]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="absolute inset-0 bg-black/40 backdrop-blur-[2px]"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 10 }}
            transition={{ duration: 0.15 }}
            className="relative w-full max-w-lg bg-surface rounded-xl shadow-2xl border border-border-light overflow-hidden"
          >
            {title && (
              <div className="flex items-center justify-between px-6 py-4 border-b border-border-light">
                <h3 className="text-lg font-semibold text-text-primary">{title}</h3>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-md text-text-muted hover:bg-surface-subtle transition-colors"
                >
                  <X size={18} />
                </button>
              </div>
            )}
            <div className="px-6 py-5">{children}</div>
            {footer && (
              <div className="px-6 py-4 bg-surface-subtle border-t border-border-light flex items-center justify-end gap-3">
                {footer}
              </div>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
```

- [ ] **Commit**

```bash
git add frontend/src/components/ui/Modal.tsx
git commit -m "feat: add Modal UI component with backdrop blur and animations"
```

---

### Task 9: Toast component

**Files:**
- Create: `frontend/src/components/ui/Toast.tsx`

- [ ] **Create Toast component**

Create a toast context + provider pattern for global use:

```tsx
import { createContext, useContext, useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { CheckCircle2, AlertCircle, Info, X, AlertTriangle } from 'lucide-react';
import { cn } from '@/src/lib/utils';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastContextValue {
  toast: (type: ToastType, message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

const icons: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle2 size={18} />,
  error: <AlertCircle size={18} />,
  warning: <AlertTriangle size={18} />,
  info: <Info size={18} />,
};

const styles: Record<ToastType, string> = {
  success: 'bg-emerald-600 text-white',
  error: 'bg-danger text-white',
  warning: 'bg-amber-500 text-white',
  info: 'bg-brand-600 text-white',
};

const MAX_VISIBLE = 3;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = nextId.current++;
    setToasts((prev) => {
      const next = [...prev, { id, type, message }];
      return next.slice(-MAX_VISIBLE);
    });
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  }, []);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, x: 80, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 80, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className={cn(
                'pointer-events-auto flex items-center gap-2.5 px-4 py-3 rounded-lg shadow-lg text-sm font-medium min-w-[280px]',
                styles[t.type],
              )}
            >
              {icons[t.type]}
              <span className="flex-1">{t.message}</span>
              <button onClick={() => removeToast(t.id)} className="opacity-70 hover:opacity-100 transition-opacity">
                <X size={16} />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
```

- [ ] **Commit**

```bash
git add frontend/src/components/ui/Toast.tsx
git commit -m "feat: add Toast UI component with context provider"
```

---

### Task 10: Header component

**Files:**
- Create: `frontend/src/components/ui/Header.tsx`

- [ ] **Create Header component**

```tsx
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
}

export default function Header({
  currentUser,
  searchQuery,
  onSearchChange,
  onToggleSidebar,
  onProfileClick,
}: HeaderProps) {
  return (
    <header className="h-16 bg-surface border-b border-border-light flex items-center gap-4 px-5 shrink-0">
      <button
        onClick={onToggleSidebar}
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
          className="w-full pl-9 pr-4 h-9 bg-surface-subtle border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all"
        />
      </div>

      <div className="ml-auto flex items-center gap-2">
        <button className="relative w-9 h-9 rounded-md flex items-center justify-center text-text-muted hover:bg-surface-subtle hover:text-text-primary transition-colors">
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
```

- [ ] **Commit**

```bash
git add frontend/src/components/ui/Header.tsx
git commit -m "feat: add Header UI component with search, notifications, user menu"
```

---

### Task 11: Sidebar component

**Files:**
- Create: `frontend/src/components/ui/Sidebar.tsx`

- [ ] **Create Sidebar component**

```tsx
import {
  LayoutDashboard, FileText, CheckCircle2, AlertCircle, Clock,
  Users, UserPlus, Settings, LogOut, ChevronRight,
} from 'lucide-react';
import { cn } from '@/src/lib/utils';
import type { UserMember } from '@/src/types';

export type ListPage =
  | 'dashboard' | 'library' | 'reviewed' | 'alerts' | 'pending'
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
      <nav className="flex-1 px-2 space-y-0.5">
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
      <div className="px-2 pb-3 space-y-0.5">
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
      </div>
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
      onClick={onClick}
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
```

- [ ] **Commit**

```bash
git add frontend/src/components/ui/Sidebar.tsx
git commit -m "feat: add Sidebar UI component with collapsed/expanded states"
```

---

### Task 12: Login page redesign

**Files:**
- Modify: `frontend/src/pages/Login.tsx`

- [ ] **Replace Login page with immersive Option C layout**

```tsx
import { FormEvent, useState } from 'react';
import { login } from '@/src/lib/api';
import { saveAuthSession } from '@/src/lib/auth';
import type { UserMember } from '@/src/types';

interface LoginPageProps {
  onLoginSuccess: (member: UserMember) => void;
}

export default function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await login(username, password);
      saveAuthSession(response);
      onLoginSuccess(response.member);
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      {/* Top brand bar */}
      <div className="bg-gradient-to-r from-[#1e40af] to-[#2563eb] px-10 py-3.5 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center text-white font-bold text-sm">
          S
        </div>
        <span className="text-white font-semibold text-base">SmartAudit</span>
      </div>

      {/* Center content */}
      <div className="flex-1 flex items-center justify-center px-6 relative">
        {/* Grid background */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              'linear-gradient(rgba(37,99,235,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(37,99,235,0.5) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />

        <div className="flex items-center gap-20 relative z-10">
          {/* Brand text */}
          <div className="hidden lg:block max-w-xs">
            <h2 className="text-3xl font-bold text-[#0f172a] leading-tight mb-3">
              智能合同<br />
              <span className="text-brand-600">校审管理平台</span>
            </h2>
            <p className="text-sm text-text-secondary leading-relaxed">
              基于 AI 的智能合同审核系统，支持风险识别、条款比对、版本追踪，让合同管理更高效、更安全。
            </p>
          </div>

          {/* Login card */}
          <div className="w-full max-w-sm bg-surface rounded-xl shadow-card border border-border-light p-8">
            <h3 className="text-xl font-semibold text-text-primary mb-1">登录</h3>
            <p className="text-sm text-text-muted mb-6">登录后将自动识别成员类型并应用权限。</p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">用户名</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="请输入用户名"
                  className="w-full px-3.5 py-2.5 rounded-md border border-border text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1.5">密码</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="请输入密码"
                  className="w-full px-3.5 py-2.5 rounded-md border border-border text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all"
                  required
                />
              </div>

              {error && <p className="text-sm text-danger">{error}</p>}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-md bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 disabled:opacity-50 transition-all"
              >
                {loading ? '登录中...' : '登录'}
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="bg-[#1e293b] px-10 py-3 flex items-center justify-between">
        <span className="text-xs text-text-muted">© 2026 SmartAudit. All rights reserved.</span>
      </div>
    </div>
  );
}
```

- [ ] **Commit**

```bash
git add frontend/src/pages/Login.tsx
git commit -m "feat: redesign login page with immersive layout (Option C)"
```

---

### Task 13: Integrate Sidebar and Header into App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Replace sidebar + header markup with Sidebar and Header components**

Replace the App.tsx layout section. The state management stays exactly the same — only the visual markup changes:

Key changes:
1. Replace `<aside>…</aside>` with `<Sidebar expanded={sidebarExpanded} … />`
2. Replace `<header>…</header>` with `<Header … onToggleSidebar={…} />`
3. Add `sidebarExpanded` state
4. Import Sidebar (with its ListPage type) and Header

Specific code changes:

Add import at top:
```tsx
import Sidebar, { type ListPage } from '@/src/components/ui/Sidebar';
import Header from '@/src/components/ui/Header';
```

Remove the existing ListPage type definition (line 34-44):
```tsx
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
```

Add state after `deferredSearchQuery`:
```tsx
const [sidebarExpanded, setSidebarExpanded] = useState(false);
```

Replace the entire return statement JSX. The `<aside>` block becomes:
```tsx
<Sidebar
  currentUser={currentUser}
  currentPage={currentPage as ListPage}
  expanded={sidebarExpanded}
  onNavigate={navigateToList}
  onLogout={logout}
/>
```

The `<header>` block becomes:
```tsx
<Header
  currentUser={currentUser}
  searchQuery={searchQuery}
  onSearchChange={setSearchQuery}
  onToggleSidebar={() => setSidebarExpanded((prev) => !prev)}
  onProfileClick={() => navigateToList('profile-info')}
/>
```

Remove the NavItem component (lines 276-302) since it's now inside Sidebar.

The outer layout div changes from `style={{ backgroundColor: 'var(--app-bg)', color: 'var(--app-text)' }}` to just the flex layout — CSS variables are now in components.

Complete new App.tsx return JSX:
```tsx
return (
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
      />

      <div className="flex-1 overflow-auto">
        {/* existing page rendering — no changes */}
        {currentPage === 'dashboard' && (...)}
        {currentPage === 'library' && (...)}
        {/* ... rest stays the same ... */}
      </div>
    </main>
  </div>
);
```

- [ ] **Verify the app compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: no type errors

- [ ] **Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: integrate Sidebar and Header components into App layout"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - Design tokens → Task 1 ✓
   - Spinner → Task 2 ✓
   - Button → Task 3 ✓
   - Card → Task 4 ✓
   - Badge → Task 5 ✓
   - Avatar → Task 6 ✓
   - Input → Task 7 ✓
   - Modal → Task 8 ✓
   - Toast → Task 9 ✓
   - Header → Task 10 ✓
   - Sidebar → Task 11 ✓
   - Login page → Task 12 ✓
   - App.tsx integration → Task 13 ✓
   - Dark mode → Task 1 (CSS variables) + all components reference variables ✓
   - Remove `!important` → Task 1 ✓

2. **Placeholder scan:** No TBD, TODO, or "handle later" patterns.

3. **Type consistency:** ListPage type defined in Sidebar.tsx, imported in App.tsx. Props consistent across all components.

4. **Edge cases covered:**
   - Button: loading state shows Spinner ✓
   - Avatar: broken image falls back to initials ✓
   - Modal: escape key + overlay click closes ✓
   - Toast: max 3 visible, auto-dismiss ✓
   - Sidebar: collapsed items show tooltip via title attr ✓
