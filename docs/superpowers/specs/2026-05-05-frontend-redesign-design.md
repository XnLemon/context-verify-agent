# Frontend UI Redesign — Design Spec

> **For agentic workers:** This spec describes the visual redesign of the frontend. Implementation should use the frontend-design skill for UI decisions. No backend changes required.

**Goal:** Redesign the frontend UI with a cohesive professional SaaS look: login page, color system, sidebar, top header, and a reusable base component library.

**Architecture:** Tailwind CSS v4 design tokens → `components/ui/` component library → replace page-level markup piecewise. All business logic preserved; only the visual layer changes.

**Tech Stack:** React 19, TypeScript, Tailwind CSS v4, lucide-react, motion (framer-motion), CSS custom properties

---

## Scope

### In Scope
1. Design token system (CSS variables replacing hardcoded Tailwind classes and !important dark overrides)
2. Login page — full-screen immersive layout (Option C from brainstorming)
3. Sidebar — narrow collapsed mode (60px) with expandable state (200px), dark theme (`#0f172a`)
4. Top header bar — hamburger toggle, refined search bar, notification bell, user avatar menu
5. Base UI components — Button, Card, Input, Modal, Badge, Avatar, Toast, Spinner
6. Dark mode — via CSS variable switching, no `!important`

### Out of Scope
- Page content restructuring (Dashboard stats, Review layout, Contract list, etc.)
- Routing changes
- Backend API changes
- New features or business logic

## Design Tokens

### Color System

```css
@theme {
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
```

### Dark Mode

```css
html[data-theme='dark'] {
  --color-surface: #0f172a;
  --color-surface-subtle: #1e293b;
  --color-sidebar: #020617;
  --color-text-primary: #e2e8f0;
  --color-text-secondary: #94a3b8;
  --color-border: #334155;
  --color-border-light: #1e293b;
}
```

No `!important` overrides. Each component references variables, dark mode Just Works.

## Login Page (Option C)

Full-screen immersive layout:

```
┌──────────────────────────────────────────────┐
│ ████████████████████████████████████████████ │  ← Top brand bar (#1e40af -> #2563eb gradient)
│                                              │
│                ┌──────────────────────┐      │
│                │  品牌名称 / 标语      │      │
│                │                      │      │
│                │  ┌────────────────┐  │      │
│                │  │ 用户名 input   │  │      │  ← Card on subtle grid background
│                │  │ 密码 input     │  │      │
│                │  │ 登录 button    │  │      │
│                │  └────────────────┘  │      │
│                └──────────────────────┘      │
│                                              │
│ ████████████████████████████████████████████ │  ← Bottom dark bar (#1e293b)
└──────────────────────────────────────────────┘
```

- Top bar: brand gradient, SmartAudit logo + name (white text)
- Center: brand text (left) + login card (right), on subtle grid background
- Bottom bar: copyright + optional link
- Card: white, `--radius-xl`, `--shadow-card`

## Sidebar

**Collapsed (default):** 60px wide, dark background (`--color-sidebar`). Icons only. Hover shows tooltip.

**Expanded (toggle via hamburger):** 200px wide. Icons + labels. Section dividers for "管理" group (admin only).

```
Collapsed:                    Expanded:
┌────┐                        ┌──────────────┐
│  S │  ← logo                │  S SmartAudit │
│    │                        │              │
│ ◻  │  ← active (brand bg)   │  ◻ 工作台    │ ← active
│ 📄 │                        │  📄 合同库    │
│ ✓  │                        │  ✓ 已审核    │
│ ⚠  │                        │  ⚠ 风险预警  │
│ ⏳ │                        │  ⏳ 待处理    │
│    │                        │  ── 管理 ──  │
│    │                        │  👥 员工管理  │ ← admin only
│    │                        │  ＋ 添加员工  │ ← admin only
│    │                        │              │
│ ⚙  │                        │  ⚙ 系统设置  │
│ 🚪 │                        │  🚪 退出登录  │
└────┘                        └──────────────┘
```

## Top Header Bar

- Height: 64px, white background, `--color-border-light` bottom border
- Left: hamburger button (36x36, rounded, hover bg `--color-surface-subtle`)
- Center: search input with icon (max-width 420px, rounded, focus ring brand)
- Right: notification bell (36x36, with red dot) + user avatar menu (rounded, hover bg)

## Component Library: `components/ui/`

### Button

Props: `variant` (primary | secondary | ghost | danger), `size` (sm | md | lg), `loading`, `disabled`, plus native button props.

| Variant | Style |
|---------|-------|
| primary | bg brand-600, white text, hover brand-700 |
| secondary | bg white, border, text-primary, hover bg surface-subtle |
| ghost | no bg/border, text-secondary, hover bg surface-subtle |
| danger | bg danger, white text, hover darker red |

Sizes: sm (32px), md (40px), lg (48px).

Loading state: show Spinner, disable interaction.

### Card

White bg, `--radius-lg`, `--shadow-card`, optional `hover` prop for lift effect.

### Input

Container with label + optional error. Input styled with `--color-border`, focus ring brand. Error state: red border + error text below.

### Modal

Based on motion `AnimatePresence`. Overlay with backdrop blur, centered card with slide-up animation. Close on escape/overlay click.

### Badge

Small inline pill. Variants: default (gray), success (green), warning (yellow), danger (red), info (blue). Used for contract status etc.

### Avatar

Props: `src`, `name` (fallback initials), `size`. Circular, with brand gradient fallback when no image.

### Toast

Global notification. Types: success, error, info, warning. Auto-dismiss after 3s. Slide-in from top-right via motion.

### Spinner

Animated spinning circle. Props: `size` (sm | md | lg), `color`.

## Migration Strategy

No big bang. Replace in this order:

1. **Design tokens** → `index.css` (add variables, remove `!important`)
2. **UI components** → create `components/ui/` files (no behavioral changes)
3. **Login page** → replace layout with immersive Option C
4. **App.tsx layout** → replace sidebar + header with Sidebar + Header components
5. **Other pages** → replace Button/Card/Badge usage piecewise (optional follow-up)

## Error / Edge Cases

- Sidebar: when collapsed, ensure all nav items remain accessible via tooltip
- Modal: prevent body scroll when open, handle escape key
- Toast: max 3 visible at once, queue subsequent toasts
- Avatar: handle broken image src gracefully (show initials fallback)
- Button loading: disable click, show spinner, preserve width (no layout shift)
- Dark mode: validate every component against both themes
