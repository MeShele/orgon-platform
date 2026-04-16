# Aceternity UI Migration Plan

**Цель**: Преобразовать дизайн ORGON с использованием компонентов Aceternity UI для создания современного, анимированного и профессионального интерфейса.

**Дата создания**: 2026-02-07  
**Автор**: Claude Code  
**Статус**: Планирование

---

## 📋 Обзор Aceternity UI

### Технологический стек
- **Next.js 15** (ORGON использует Next.js 16 ✅)
- **Tailwind CSS v4** (ORGON использует v3 → требуется обновление)
- **Framer Motion** (Motion for React) → новая зависимость
- **TypeScript** (ORGON уже использует ✅)
- **Shadcn CLI 3.0** (для установки компонентов)

### Особенности
- 200+ production-ready компонентов
- Встроенные анимации (Framer Motion)
- Copy-paste подход (без пакетной установки)
- Shadcn CLI совместимость
- Dark mode support
- Mobile responsive

### Модель лицензирования
- **Free**: Ограниченный набор компонентов (Sidebar, Background Gradient, и др.)
- **All-Access Pass** ($99-299): 70+ премиум шаблонов и блоков

---

## 🎯 Цели миграции

### 1. **Визуальное обновление**
- Современные анимированные компоненты
- Плавные переходы и эффекты
- Профессиональный внешний вид

### 2. **UX улучшения**
- Интерактивные элементы
- Микро-взаимодействия
- Лучшая обратная связь

### 3. **Единый стиль**
- Согласованные компоненты
- Централизованный design system
- Reusable patterns

### 4. **Производительность**
- Оптимизированные анимации
- Lazy loading компонентов
- Tree-shaking неиспользуемого кода

---

## 📦 Подготовка (Этап 0)

### 0.1. Обновление зависимостей
**Время**: 1 час

```bash
# Tailwind CSS v4 (major update)
npm install tailwindcss@next @tailwindcss/postcss@next

# Framer Motion
npm install framer-motion

# Shadcn CLI
npm install -g shadcn@latest

# Другие зависимости Aceternity
npm install clsx tailwind-merge
```

**Задачи**:
- [x] Инвентаризация текущих зависимостей
- [ ] Обновление Tailwind CSS v3 → v4
- [ ] Установка Framer Motion
- [ ] Установка Shadcn CLI
- [ ] Проверка совместимости с Next.js 16

**Риски**:
- ⚠️ Breaking changes в Tailwind v4
- ⚠️ Конфликты конфигурации
- ⚠️ Необходимость рефакторинга стилей

### 0.2. Инициализация Shadcn
**Время**: 0.5 часа

```bash
npx shadcn@latest init
```

**Задачи**:
- [ ] Настройка components.json
- [ ] Выбор style (default/new-york)
- [ ] Настройка путей (components/, lib/, etc.)
- [ ] Проверка интеграции с существующей структурой

---

## 🏗️ Этап 1: Layout & Navigation (2-3 часа)

### 1.1. Sidebar Migration
**Приоритет**: 🔴 Высокий  
**Время**: 1.5 часа

**Компонент**: [@aceternity/sidebar](https://ui.aceternity.com/components/sidebar)

**Функции**:
- Expandable на hover
- Mobile responsive
- Анимации открытия/закрытия
- Dark mode support

**Текущий файл**: `/frontend/src/components/layout/Sidebar.tsx` (8.5 KB)

**План**:
1. Установить компонент:
   ```bash
   npx shadcn@latest add @aceternity/sidebar
   ```
2. Создать `AceternitySidebar.tsx` с адаптацией для ORGON
3. Перенести логику навигации (9 items)
4. Интегрировать ProfileCard
5. Сохранить текущие переводы (ru/en/ky)
6. Тестирование на mobile/desktop
7. Заменить старый Sidebar

**Миграция данных**:
```typescript
// Текущая структура (сохранить)
const navItems = [
  { id: 'dashboard', icon: 'solar:home-2-linear', ... },
  { id: 'wallets', icon: 'solar:wallet-linear', ... },
  // ... 7 more items
];

// Адаптация под Aceternity
const links = navItems.map(item => ({
  label: t(`nav.${item.id}`),
  href: `/${item.id === 'dashboard' ? '' : item.id}`,
  icon: <Icon icon={item.icon} />,
}));
```

**Новые возможности**:
- ✨ Анимация expand/collapse
- ✨ Hover эффекты на линках
- ✨ Плавные переходы

### 1.2. Header Simplification
**Приоритет**: 🟡 Средний  
**Время**: 0.5 часа

**Текущий файл**: `/frontend/src/components/layout/Header.tsx`

**План**:
- Сохранить минималистичный дизайн (3 элемента)
- Добавить Aceternity Background Gradient
- Анимированный Sync Status indicator

**Компонент**: [@aceternity/background-gradient](https://ui.aceternity.com/components/background-gradient)

```bash
npx shadcn@latest add @aceternity/background-gradient
```

### 1.3. ProfileCard Enhancement
**Приоритет**: 🟡 Средний  
**Время**: 1 час

**Текущий файл**: `/frontend/src/components/layout/ProfileCard.tsx`

**План**:
- Добавить анимированный dropdown
- Hover эффекты на аватаре
- Плавные переходы меню

**Возможные компоненты**:
- [@aceternity/animated-modal] (для settings)
- [@aceternity/sparkles] (для аватара)

---

## 🎨 Этап 2: Cards & Containers (3-4 часа)

### 2.1. Card Component Redesign
**Приоритет**: 🔴 Высокий  
**Время**: 1.5 часа

**Текущий файл**: `/frontend/src/components/ui/Card.tsx`

**Использование**: 11 страниц (Dashboard, Wallets, Transactions, etc.)

**План**:
1. Исследовать доступные Aceternity card компоненты:
   - 3D Card Effect
   - Hover Border Cards
   - Gradient Cards
   - Bento Grid (для dashboard)

2. Выбрать стиль для разных контекстов:
   - **Stats Cards**: Moving Border / Gradient
   - **Data Cards**: 3D Card / Hover Effect
   - **Dashboard Grid**: Bento Grid

3. Создать универсальный `AceternityCard.tsx` с вариантами:
   ```typescript
   <AceternityCard 
     variant="stat" | "data" | "bento"
     gradient={true}
     animate={true}
   />
   ```

4. Миграция по страницам:
   - Dashboard (4 stat cards + 4 data panels)
   - Wallets (wallet cards)
   - Analytics (chart containers)
   - Settings (section cards)

**Компоненты**:
```bash
npx shadcn@latest add @aceternity/3d-card
npx shadcn@latest add @aceternity/bento-grid
npx shadcn@latest add @aceternity/moving-border
```

### 2.2. Table Styling
**Приоритет**: 🔴 Высокий  
**Время**: 1.5 часа

**Затрагиваемые файлы**:
- `PendingSignaturesTable.tsx`
- `SignatureHistoryTable.tsx`
- `TransactionTable.tsx`
- `WalletTable.tsx`

**План**:
1. Добавить анимации на строки (hover, select)
2. Gradient headers
3. Smooth scrolling
4. Loading skeletons с анимацией

**Возможные улучшения**:
- Sparkles на hover важных строк
- Moving border для selected row
- Gradient backgrounds для headers

### 2.3. Empty States
**Приоритет**: 🟡 Средний  
**Время**: 1 час

**Текущее состояние**: SVG иконки + текст

**План**:
- Добавить анимированные иконки
- Sparkles / Particles эффекты
- Interactive CTA buttons

**Компоненты**:
```bash
npx shadcn@latest add @aceternity/sparkles
npx shadcn@latest add @aceternity/particles
```

---

## 🎭 Этап 3: Interactive Components (4-5 часов)

### 3.1. Buttons
**Приоритет**: 🔴 Высокий  
**Время**: 1 час

**Текущий файл**: `/frontend/src/components/ui/Button.tsx`

**Использование**: Все страницы (100+ экземпляров)

**План**:
1. Изучить Aceternity button variants:
   - Moving Border Button
   - Shimmer Button
   - Glowing Button
   - Gradient Button

2. Создать централизованный `AceternityButton.tsx`:
   ```typescript
   <AceternityButton
     variant="primary" | "secondary" | "danger" | "success"
     effect="shimmer" | "glow" | "gradient" | "border"
     size="sm" | "md" | "lg"
   />
   ```

3. Миграция по приоритету:
   - Primary actions (Send, Create, Save) → Shimmer/Glow
   - Secondary (Cancel, Back) → Default
   - Danger (Delete, Reject) → Gradient red
   - Success (Approve, Confirm) → Gradient green

**Компоненты**:
```bash
npx shadcn@latest add @aceternity/moving-border-button
npx shadcn@latest add @aceternity/shimmer-button
```

### 3.2. Modals & Dialogs
**Приоритет**: 🔴 Высокий  
**Время**: 2 часа

**Затрагиваемые файлы**:
- `ContactModal.tsx`
- `ScheduleModal.tsx`
- `RejectDialog.tsx`
- `TwoFactorAuth.tsx` (QR modal)

**План**:
1. Установить Animated Modal:
   ```bash
   npx shadcn@latest add @aceternity/animated-modal
   ```

2. Добавить анимации:
   - Fade in/out
   - Scale effects
   - Backdrop blur animation
   - Smooth closing

3. Улучшения UX:
   - Keyboard shortcuts (ESC)
   - Click outside to close
   - Focus trap
   - Accessibility

### 3.3. Forms & Inputs
**Приоритет**: 🟡 Средний  
**Время**: 2 часа

**Текущий файл**: `/frontend/src/components/ui/Input.tsx`

**Использование**: Forms на всех страницах

**План**:
1. Изучить Aceternity input компоненты:
   - Animated Input (floating labels)
   - Glow Input (focus effect)
   - Password Input (reveal/hide animation)

2. Создать универсальный компонент
3. Добавить validation states с анимацией
4. Error messages с smooth transitions

**Особые случаи**:
- CronBuilder (select fields)
- Token amount inputs (number validation)
- Address inputs (validation + icons)

---

## 📊 Этап 4: Data Visualization (2-3 часа)

### 4.1. Analytics Charts
**Приоритет**: 🟡 Средний  
**Время**: 2 часа

**Текущие компоненты**:
- `BalanceChart.tsx` (Recharts Line)
- `VolumeChart.tsx` (Recharts Bar)
- `TokenDistribution.tsx` (Recharts Pie)
- `SignatureStats.tsx` (Stats)

**План**:
1. Сохранить Recharts (хорошо работает)
2. Обернуть в Aceternity карточки
3. Добавить анимации загрузки
4. Hover эффекты на графиках

**Улучшения**:
- Gradient fills для area charts
- Moving border для chart containers
- Sparkles на data points
- Animated tooltips

### 4.2. Stats Display
**Приоритет**: 🔴 Высокий  
**Время**: 1 час

**Текущий файл**: `StatCards.tsx`

**План**:
1. Number count-up анимация (0 → value)
2. Icon animations (pulse, glow)
3. Gradient backgrounds
4. Trend indicators (↑↓ с анимацией)

**Компоненты**:
- [@aceternity/counter-animation]
- [@aceternity/sparkles]

---

## 🎨 Этап 5: Specialized Pages (3-4 часа)

### 5.1. Dashboard Redesign
**Приоритет**: 🔴 Высокий  
**Время**: 2 часа

**Текущий файл**: `/frontend/src/app/page.tsx`

**План**:
1. **Bento Grid Layout**:
   ```bash
   npx shadcn@latest add @aceternity/bento-grid
   ```
   - 4 stat cards → Bento items
   - Token summary → Large bento item
   - Recent activity → Medium bento item
   - Alerts panel → Small bento item

2. **Анимации**:
   - Stagger появление карточек
   - Hover 3D эффекты
   - Gradient backgrounds

3. **Сохранить функциональность**:
   - WebSocket live updates
   - i18n переводы
   - Responsive design

### 5.2. Wallets Page
**Приоритет**: 🔴 Высокий  
**Время**: 1 час

**Текущий файл**: `/frontend/src/app/wallets/page.tsx`

**План**:
1. Wallet cards → 3D Cards
2. Add Wallet button → Shimmer Button
3. Balance display → Gradient text
4. QR codes → Modal with animations

### 5.3. Signatures Page
**Приоритет**: 🟡 Средний  
**Время**: 1 час

**Текущий файл**: `/frontend/src/app/signatures/page.tsx`

**План**:
1. Pending table → Animated rows
2. Action buttons → Moving Border
3. Status badges → Animated (pulse для pending)
4. Reject dialog → Animated Modal

---

## 🌐 Этап 6: Animations & Effects (2-3 часа)

### 6.1. Page Transitions
**Приоритет**: 🟡 Средний  
**Время**: 1 час

**План**:
1. Установить Framer Motion page transitions
2. Fade/Slide при смене страниц
3. Loading states с animations

**Код**:
```typescript
// AppShell.tsx
import { AnimatePresence, motion } from 'framer-motion';

<AnimatePresence mode="wait">
  <motion.div
    key={pathname}
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -20 }}
    transition={{ duration: 0.3 }}
  >
    {children}
  </motion.div>
</AnimatePresence>
```

### 6.2. Micro-interactions
**Приоритет**: 🟢 Низкий  
**Время**: 2 часа

**План**:
1. Button hover effects (scale, glow)
2. Icon animations (rotate, bounce)
3. Success/Error toasts (slide, fade)
4. Loading spinners (custom animations)

**Компоненты**:
- [@aceternity/sparkles] - для успешных действий
- [@aceternity/particles] - для фоновых эффектов
- Custom Framer Motion variants

### 6.3. Background Effects
**Приоритет**: 🟢 Низкий  
**Время**: 0.5 часа

**План**:
1. Page backgrounds → Gradient Mesh
2. Section backgrounds → Animated Gradients
3. Particles для landing sections

**Компоненты**:
```bash
npx shadcn@latest add @aceternity/background-gradient
npx shadcn@latest add @aceternity/particles
npx shadcn@latest add @aceternity/gradient-mesh
```

---

## 🧪 Этап 7: Testing & Optimization (2-3 часа)

### 7.1. Cross-browser Testing
**Приоритет**: 🔴 Высокий  
**Время**: 1 час

**Задачи**:
- [ ] Chrome (latest)
- [ ] Safari (macOS/iOS)
- [ ] Firefox
- [ ] Edge
- [ ] Mobile browsers

**Чеклист**:
- Анимации работают плавно
- Нет flickering
- Responsive на всех разрешениях
- Dark mode корректный

### 7.2. Performance Testing
**Приоритет**: 🔴 Высокий  
**Время**: 1.5 часа

**Метрики**:
- Lighthouse score (> 90)
- First Contentful Paint (< 1.5s)
- Time to Interactive (< 3s)
- Cumulative Layout Shift (< 0.1)

**Оптимизации**:
1. Lazy load animations
2. Reduce motion для accessibility
3. Code splitting по страницам
4. Image optimization

**Код**:
```typescript
// Reduce motion support
const prefersReducedMotion = window.matchMedia(
  '(prefers-reduced-motion: reduce)'
).matches;

<motion.div animate={prefersReducedMotion ? false : { ... }} />
```

### 7.3. Accessibility (a11y)
**Приоритет**: 🔴 Высокий  
**Время**: 0.5 часа

**Задачи**:
- [ ] Keyboard navigation (Tab, Enter, Esc)
- [ ] Screen reader support (ARIA labels)
- [ ] Focus indicators
- [ ] Color contrast (WCAG AA)
- [ ] Skip to content links

**Инструменты**:
- axe DevTools
- Lighthouse a11y audit
- NVDA/JAWS testing

---

## 📝 Этап 8: Documentation & Cleanup (1-2 часа)

### 8.1. Component Documentation
**Приоритет**: 🟡 Средний  
**Время**: 1 час

**Создать**:
- `ACETERNITY_COMPONENTS.md` - каталог всех компонентов
- `ANIMATION_GUIDE.md` - best practices для анимаций
- Inline JSDoc для новых компонентов

### 8.2. Code Cleanup
**Приоритет**: 🟡 Средний  
**Время**: 1 час

**Задачи**:
- [ ] Удалить старые компоненты
- [ ] Consolidate styles
- [ ] Remove unused imports
- [ ] Update design-tokens.ts

---

## 📊 Общая оценка времени

| Этап | Описание | Время |
|------|----------|-------|
| 0 | Подготовка | 1.5h |
| 1 | Layout & Navigation | 3h |
| 2 | Cards & Containers | 4h |
| 3 | Interactive Components | 5h |
| 4 | Data Visualization | 3h |
| 5 | Specialized Pages | 4h |
| 6 | Animations & Effects | 3h |
| 7 | Testing & Optimization | 3h |
| 8 | Documentation & Cleanup | 2h |
| **ИТОГО** | | **28.5 часов** |

**С учетом velocity 211%**: ~13.5 часов реального времени

---

## 🎯 Приоритизация

### Phase 1 (Критическая) - 8 часов
1. ✅ Подготовка (Этап 0)
2. ✅ Sidebar (Этап 1.1)
3. ✅ Cards (Этап 2.1)
4. ✅ Buttons (Этап 3.1)
5. ✅ Dashboard (Этап 5.1)

**Результат**: Основной UI обновлен, функциональность сохранена

### Phase 2 (Высокая) - 6 часов
6. ✅ Modals (Этап 3.2)
7. ✅ Tables (Этап 2.2)
8. ✅ Wallets Page (Этап 5.2)
9. ✅ Testing (Этап 7)

**Результат**: Все критичные страницы обновлены, стабильность проверена

### Phase 3 (Средняя) - 6 часов
10. ✅ Forms (Этап 3.3)
11. ✅ Analytics (Этап 4)
12. ✅ Page Transitions (Этап 6.1)
13. ✅ Empty States (Этап 2.3)

**Результат**: Полный функциональный набор с анимациями

### Phase 4 (Низкая) - 3 часа
14. ✅ Micro-interactions (Этап 6.2)
15. ✅ Background Effects (Этап 6.3)
16. ✅ Documentation (Этап 8)

**Результат**: Polish & finalization

---

## ⚠️ Риски и митигация

### 1. Tailwind v4 Breaking Changes
**Риск**: 🔴 Высокий

**Проблемы**:
- Новый синтаксис конфигурации
- CSS-first подход
- Изменения в utilities

**Митигация**:
- Создать feature branch
- Протестировать на dev окружении
- Постепенная миграция (codemods)
- Откат на v3 при критичных проблемах

### 2. Framer Motion Bundle Size
**Риск**: 🟡 Средний

**Проблемы**:
- +58KB gzipped
- Может замедлить загрузку

**Митигация**:
- Lazy load анимаций
- Tree-shaking неиспользуемых features
- Code splitting по роутам
- Conditional loading (reduce motion)

### 3. Component Compatibility
**Риск**: 🟡 Средний

**Проблемы**:
- Конфликты с существующим кодом
- TypeScript типы
- Props несовместимость

**Митигация**:
- Wrapper компоненты для адаптации
- Постепенная замена (не big bang)
- Сохранение fallback компонентов
- Тщательное тестирование

### 4. Learning Curve
**Риск**: 🟢 Низкий (для AI)

**Проблемы**:
- Новый API Framer Motion
- Aceternity conventions
- Tailwind v4 новшества

**Митигация**:
- Документация Aceternity
- Examples от сообщества
- Инкрементальная миграция

---

## 🚀 План выполнения

### Вариант A: Полная миграция (Big Bang)
**Время**: 2-3 дня  
**Риск**: 🔴 Высокий

**Подход**:
1. Создать новую ветку `aceternity-migration`
2. Обновить все зависимости
3. Мигрировать все компоненты
4. Тестирование
5. Merge в main

**Минусы**:
- Блокирует разработку
- Большой risk при проблемах
- Сложно откатить

### Вариант B: Инкрементальная миграция (Рекомендуется)
**Время**: 1-2 недели  
**Риск**: 🟢 Низкий

**Подход**:
1. Phase 1 → PR → Merge → Deploy
2. Phase 2 → PR → Merge → Deploy
3. Phase 3 → PR → Merge → Deploy
4. Phase 4 → PR → Merge → Deploy

**Плюсы**:
- Непрерывная работоспособность
- Легко откатить проблемные изменения
- Постепенное тестирование
- Меньше стресса

**Рекомендация**: Вариант B (инкрементальная)

---

## 📚 Ресурсы

### Документация
- [Aceternity UI Components](https://ui.aceternity.com/components)
- [Framer Motion Docs](https://www.framer.com/motion/)
- [Tailwind CSS v4 Docs](https://tailwindcss.com/docs)
- [Shadcn CLI](https://ui.shadcn.com/)

### Примеры
- [Aceternity Templates](https://ui.aceternity.com/templates)
- [Community Showcase](https://ui.aceternity.com/showcase)

### Инструменты
- [Motion Dev Tools](https://github.com/framer/motion-devtools)
- [Tailwind CSS IntelliSense](https://marketplace.visualstudio.com/items?itemName=bradlc.vscode-tailwindcss)

---

## ✅ Next Steps

1. **Решить**: Вариант миграции (A или B)?
2. **Начать**: Phase 1 (Подготовка + Sidebar)
3. **Создать**: Feature branch `aceternity-migration`
4. **Установить**: Зависимости (Tailwind v4, Framer Motion, Shadcn)
5. **Мигрировать**: Первый компонент (Sidebar)
6. **Тестировать**: На production domain
7. **Итерировать**: Следующие phases

---

**Готов начать?** Скажите "да" для старта Phase 1, или уточните что-то конкретное! 🚀
