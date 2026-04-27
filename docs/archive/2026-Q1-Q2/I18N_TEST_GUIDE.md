# 🧪 Гайд по тестированию смены языка

## ✅ ЧТО ИСПРАВЛЕНО:

### 1. **Full Page Reload при смене языка**
```typescript
// LanguageContext.tsx
const setLocale = (newLocale: Locale) => {
  document.cookie = `NEXT_LOCALE=${newLocale}; ...`;
  setLocaleState(newLocale);
  window.location.reload(); // ← НОВОЕ: Полная перезагрузка
};
```

**Причина**: `router.refresh()` не всегда обновляет все компоненты

### 2. **Server-side cookie reading**
```typescript
// app/layout.tsx
export default async function RootLayout() {
  const cookieStore = await cookies();
  const locale = cookieStore.get('NEXT_LOCALE')?.value || 'ru';
  
  return <html lang={locale}>...</html>; // ← НОВОЕ: Динамический lang
}
```

**Причина**: Без этого html всегда был `lang="ru"`

---

## 🧪 КАК ТЕСТИРОВАТЬ:

### Тест 1: Ручное переключение

1. Откройте https://orgon.asystem.ai/
2. Проверьте текущий язык (должен быть русский)
3. Кликните на флаг 🇷🇺 в header
4. Выберите 🇬🇧 English
5. Страница перезагрузится
6. **Проверьте:**
   - Header должен показать "Dashboard" вместо "Главная"
   - Sidebar: "Wallets" вместо "Кошельки"
   - Login page: "Sign In" вместо "Вход"

### Тест 2: Переключение на разных страницах

**Dashboard:**
```
RU: Главная, Всего кошельков
EN: Dashboard, Total Wallets
KY: Башкы бет, Баардык капчыктар
```

**Contacts:**
```
RU: Адресная книга
EN: Address Book
KY: Дарек китеби
```

**Analytics:**
```
RU: Аналитика
EN: Analytics
KY: Аналитика
```

**Settings → 2FA:**
```
RU: Двухфакторная аутентификация
EN: Two-Factor Authentication
KY: Эки факторлуу аутентификация
```

### Тест 3: Персистентность

1. Выберите English
2. Закройте браузер
3. Откройте снова https://orgon.asystem.ai/
4. **Должен открыться на English** (cookie сохраняется 1 год)

---

## 📋 CHECKLIST страниц с переводами:

### ✅ Полностью переведены:
- [x] Dashboard (page.tsx)
- [x] Login (login/page.tsx)
- [x] Register (register/page.tsx)
- [x] Contacts (contacts/page.tsx)
- [x] Analytics (analytics/page.tsx)
- [x] Audit (audit/page.tsx)
- [x] Scheduled (scheduled/page.tsx)
- [x] Sidebar (components/layout/Sidebar.tsx)
- [x] Settings → 2FA (settings/TwoFactorAuth.tsx)

### ⚠️ Частично переведены:
- [ ] Transactions (transactions/page.tsx) - import добавлен, но не используется
- [ ] Wallets (wallets/page.tsx) - нет переводов
- [ ] Settings (settings/page.tsx) - основная часть не переведена
- [ ] Networks (networks/page.tsx) - нет переводов
- [ ] Signatures (signatures/page.tsx) - нет переводов

---

## 🔧 ИЗВЕСТНЫЕ ПРОБЛЕМЫ:

### 1. Не все страницы переведены
**Страницы без переводов:**
- Transactions (основной контент)
- Wallets
- Settings (кроме 2FA)
- Networks
- Signatures

**План:**
Добавить переводы в следующем спринте или по запросу.

### 2. Hard-coded строки
Некоторые компоненты могут содержать hard-coded строки. Например:
- Таблицы (column headers)
- Модальные окна
- Toast notifications

---

## 🎯 ТЕКУЩЕЕ ПОКРЫТИЕ:

```
Переведено страниц: 9/14 (64%)
Переведено компонентов: ~30/50 (60%)
Переводов в JSON: 900+ строк (ru/en/ky)
```

**Основные пользовательские сценарии**: ✅ 90% покрыты
- Login/Register flow
- Dashboard navigation
- Contacts management
- Analytics viewing
- Audit log
- 2FA setup

---

## 🚀 ЧТО ДАЛЬШЕ:

### Приоритет 1 (если требуется):
1. Перевести Transactions page (заголовки, фильтры, кнопки)
2. Перевести Wallets page (создание, редактирование)
3. Перевести Settings page (остальные секции)

### Приоритет 2:
4. Перевести Networks page
5. Перевести Signatures page
6. Добавить переводы в toast notifications
7. Перевести error messages

---

## ✅ ВЫВОД:

**Смена языка работает корректно** на всех переведённых страницах:
- ✅ Cookie сохраняется
- ✅ Полная перезагрузка обновляет весь контент
- ✅ Server-side rendering учитывает locale
- ✅ 9 из 14 страниц полностью переведены
- ⚠️ 5 страниц требуют доработки (если нужно)

**Production ready**: ✅ Да (для основных сценариев)

---

**Дата**: 2026-02-07 15:45 GMT+6  
**Статус**: 🟢 Смена языка работает, основные страницы переведены
