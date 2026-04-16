# DESIGN UNIFICATION PROGRESS

**Started:** 2026-02-07 18:33 GMT+6  
**Session:** Design System & Header Simplification  
**Goal:** Унификация дизайна всех страниц на основе стандарта Dashboard

---

## 🎯 Проблемы (исходные)

1. **Нет единого дизайн-стандарта** - каждая страница использует разные размеры, цвета, отступы
2. **Header перегружен** - Language, Theme, User Menu (нужно минимизировать)
3. **Нет ProfileCard в Sidebar** - неудобный доступ к настройкам профиля
4. **Inconsistent spacing/fonts** - text-xs vs text-sm, разные gap/padding
5. **Разрозненные компоненты** - нет общего стиля для кнопок, карточек, таблиц

---

## ✅ COMPLETED (Phase 1 & 2)

### Phase 1: Design System (30 min actual: ~35 min)

#### 1.1 Design Tokens ✅
**File:** `/frontend/src/lib/design-tokens.ts` (5.3 KB)

**Создан единый источник истины для:**
- **Colors:** primary, success, warning, error, neutral (slate)
- **Typography:** fontFamily, fontSize, fontWeight, lineHeight
- **Spacing:** px/rem scale (4px grid), semantic spacing (page/card/gap)
- **Border Radius:** none, sm, md, lg, xl, full
- **Shadows:** sm, md, lg, xl
- **Transitions:** duration (fast/normal/slow), timing functions
- **Breakpoints:** sm, md, lg, xl, 2xl
- **Z-index:** dropdown, modal, toast, tooltip

**Type exports:**
```typescript
export type DesignTokens = typeof designTokens;
export type ColorPalette = keyof typeof designTokens.colors;
export type Spacing = keyof typeof designTokens.spacing;
export type FontSize = keyof typeof designTokens.typography.fontSize;
```

#### 1.2 ProfileCard Component ✅
**File:** `/frontend/src/components/layout/ProfileCard.tsx` (7.3 KB)

**Features:**
- **2 modes:** Full (desktop sidebar) + Collapsed (mobile/icon)
- **User info:** Avatar (icon), name, email, role badge
- **Dropdown menu:** Profile Settings + Sign Out
- **Role badges:** Admin (red), Signer (blue), Viewer (slate)
- **Responsive:** Works in sidebar bottom (desktop) + hamburger menu (mobile)
- **Auth state:** Shows "Sign In" link when user is not logged in

**Integration:**
- Added to Sidebar bottom (replaces old static user section)
- Full translations support (ru/en/ky)

#### 1.3 Sidebar Update ✅
**File:** `/frontend/src/components/layout/Sidebar.tsx`

**Changes:**
- Imported ProfileCard component
- Replaced static user section with `<ProfileCard />`
- Profile card appears at bottom of sidebar with full info
- Maintains current design system (border-top separator)

#### 1.4 Translations Added ✅
**Files:** `ru.json`, `en.json`, `ky.json`

**New keys in `common.*`:**
```json
{
  "signIn": "Войти / Sign In / Кирүү",
  "signOut": "Выйти / Sign Out / Чыгуу",
  "profileSettings": "Настройки профиля / Profile Settings / Профиль тууралоолору",
  "done": "Готово / Done / Даяр"
}
```

---

### Phase 2: Header Simplification (15 min actual: ~20 min)

#### 2.1 Header Minimization ✅
**File:** `/frontend/src/components/layout/Header.tsx`

**Removed:**
- ❌ LanguageSwitcher component
- ❌ Theme Toggle button  
- ❌ User Menu dropdown (with Profile Settings + Sign Out)

**Kept (minimal header):**
- ✅ Hamburger button (mobile only)
- ✅ Page Title
- ✅ Sync Status indicator (Live/Offline)

**Result:** Clean, minimal header focused on navigation and status

#### 2.2 LanguageThemeSettings Component ✅
**File:** `/frontend/src/components/profile/LanguageThemeSettings.tsx` (5.3 KB)

**Features:**
- **Language Selector:** 3 languages (Russian, English, Kyrgyz) with flags
- **Theme Selector:** Light, Dark, System preference
- **Visual feedback:** Active state with checkmark icon
- **Persistent:** Saves to cookie (language) and localStorage (theme)
- **System theme:** Auto-detects OS preference when "System" selected

**Design:**
- Grid layout (3 columns on desktop, 1 on mobile)
- Blue accent for active state
- SVG icons from Solar Icons collection
- Fully responsive with touch-friendly targets

#### 2.3 Profile Page Update ✅
**File:** `/frontend/src/app/profile/page.tsx`

**Added:** LanguageThemeSettings component before TwoFactorAuth section

**Page Structure (top to bottom):**
1. Profile Info Card (avatar, name, email, role, member since)
2. Password Change Card
3. **Language & Theme Settings** ← NEW
4. Two-Factor Authentication
5. Active Sessions

#### 2.4 Profile Translations ✅
**Added to `profile.*` in all 3 languages:**

```json
{
  "language": {
    "title": "Язык интерфейса / Interface Language / Интерфейс тили",
    "description": "...",
    "active": "Активный / Active / Активдүү"
  },
  "theme": {
    "title": "Тема оформления / Appearance Theme / Интерфейс темасы",
    "description": "...",
    "light": "Светлая / Light / Жарык",
    "dark": "Темная / Dark / Караңгы",
    "system": "Системная / System / Системалык",
    "active": "Активная / Active / Активдүү"
  }
}
```

---

## 🚧 IN PROGRESS (Phase 3)

### Phase 3: Pages Unification (45 min estimated)

#### 3.1 Page Layout Standards ✅
**File:** `/frontend/src/lib/page-layout.ts` (6.4 KB)

**Created unified layout system:**

**Utilities:**
- `pageLayout.container` - main page wrapper with responsive padding
- `pageLayout.header.*` - page title, description, subtitle classes
- `pageLayout.actionBar` - filters/buttons bar (responsive flex)
- `pageLayout.grid.*` - responsive grid layouts (cols1-4, auto, stats)
- `pageLayout.empty.*` - empty state pattern
- `pageLayout.loading` - centered loading spinner
- `pageLayout.error/success/warning/info` - alert messages

**Standard Components:**
- `spacing.*` - page, card, gap, stack spacing presets
- `buttonStyles.*` - primary, secondary, danger, ghost
- `badgeStyles.*` - default + 5 color variants
- `tableStyles.*` - wrapper, table, thead, th, tbody, td

**Usage Pattern:**
```tsx
<div className={pageLayout.container}>
  <div className={pageLayout.header.wrapper}>
    <h1 className={pageLayout.header.title}>Title</h1>
    <p className={pageLayout.header.description}>Description</p>
  </div>
  {/* content */}
</div>
```

---

## 📋 TODO (Next Steps)

### 3.2 Apply Standards to All Pages

**Priority 1 - Main Pages (15 min each):**
- [ ] `/wallets/page.tsx` - Apply pageLayout, unify card/table styles
- [ ] `/transactions/page.tsx` - Apply pageLayout, unify filters/table
- [ ] `/signatures/page.tsx` - Apply pageLayout, unify pending/history tables

**Priority 2 - Feature Pages (10 min each):**
- [ ] `/scheduled/page.tsx` - Apply pageLayout, unify schedule UI
- [ ] `/contacts/page.tsx` - Apply pageLayout, unify contact cards
- [ ] `/analytics/page.tsx` - Apply pageLayout, ensure charts spacing
- [ ] `/audit/page.tsx` - Apply pageLayout, unify timeline/filters

**Priority 3 - System Pages (5 min each):**
- [ ] `/networks/page.tsx` - Apply pageLayout, unify network cards
- [ ] `/settings/page.tsx` - Apply pageLayout (if still exists separately)

**Components to Update:**
- [ ] Update Button component to match buttonStyles
- [ ] Update Card component padding to match spacing.card
- [ ] Update Badge component to match badgeStyles
- [ ] Create/update Table component with tableStyles
- [ ] Update Empty states across all pages

### 3.3 Responsive Testing

**Test all pages on:**
- [ ] Mobile (375px, 414px)
- [ ] Tablet (768px, 1024px)
- [ ] Desktop (1280px, 1920px)

**Verify:**
- [ ] All text is readable (min 14px body)
- [ ] Touch targets are 44x44px minimum
- [ ] Horizontal scrolling is eliminated
- [ ] Cards/tables adapt properly
- [ ] Spacing is consistent

### 3.4 Dark Mode Audit

- [ ] Test all pages in dark mode
- [ ] Verify contrast ratios (WCAG AA minimum)
- [ ] Check icon visibility
- [ ] Ensure hover states work

---

## 📊 Metrics

**Time Spent:**
- Phase 1: ~35 min (planned 30)
- Phase 2: ~20 min (planned 15)
- Phase 3.1: ~15 min (standards created)
- **Total so far:** ~70 min / ~90 min planned

**Files Created:** 4
- design-tokens.ts (5.3 KB)
- ProfileCard.tsx (7.3 KB)
- LanguageThemeSettings.tsx (5.3 KB)
- page-layout.ts (6.4 KB)

**Files Modified:** 8
- Sidebar.tsx (added ProfileCard)
- Header.tsx (simplified, removed controls)
- profile/page.tsx (added Language/Theme settings)
- ru.json, en.json, ky.json (translations × 3)
- ProfileCard import added

**Lines Added:** ~600
**Lines Removed:** ~150

---

## 🎨 Design Principles Established

1. **Single Source of Truth:** design-tokens.ts for all values
2. **Consistent Spacing:** 4px grid system (4, 8, 12, 16, 24, 32, 48, 64)
3. **Mobile-First:** Responsive patterns start from mobile
4. **Dark Mode Native:** All components support dark mode
5. **Semantic Naming:** spacing.page, spacing.card, spacing.gap
6. **Reusable Utilities:** pageLayout.* for common patterns
7. **Type-Safe:** TypeScript exports for design tokens
8. **Accessibility:** WCAG AA contrast, touch targets 44px

---

## 🔍 Key Decisions

1. **ProfileCard in Sidebar** (not Header) - better UX, less clutter
2. **Language/Theme in Profile Settings** - centralized preferences
3. **Minimal Header** - only essential navigation elements
4. **Design Tokens** - centralized, not scattered across components
5. **Page Layout Standards** - utilities over inline classes
6. **Slate as Neutral** - replaced gray with slate for modern look

---

## 🚀 Next Session Goals

1. **Apply page-layout.ts to 3-5 pages** (Wallets, Transactions, Signatures)
2. **Test responsive behavior** on real devices
3. **Create unified Table component** if needed
4. **Document Before/After screenshots** for visual audit

---

## 📸 Visual Changes

### Header
**Before:** Title + Sync + Language + Theme + User Menu (5 elements)  
**After:** Title + Sync (2 elements, hamburger on mobile)

### Sidebar
**Before:** Static "Admin User / orgon-admin" card  
**After:** Dynamic ProfileCard with dropdown (Profile Settings + Sign Out)

### Profile Page
**Before:** Password + 2FA + Sessions (3 sections)  
**After:** Info + Password + **Language/Theme** + 2FA + Sessions (5 sections)

---

**Status:** Phase 1 & 2 COMPLETE ✅  
**Next:** Apply page-layout.ts standards to all pages  
**ETA:** ~45 minutes for remaining pages
