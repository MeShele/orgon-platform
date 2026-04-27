# 2FA API Fix - Исправление ошибки TypeError

**Дата**: 2026-02-07  
**Время**: 5 минут  
**Статус**: ✅ FIXED

## 🐛 Проблема

### Ошибка
```
TypeError: api.get is not a function
at loadStatus (src/app/settings/TwoFactorAuth.tsx:39:34)
```

### Причина
В компоненте `TwoFactorAuth.tsx` использовались несуществующие методы:
- `api.get()` - не существует в `api.ts`
- `api.post()` - не существует в `api.ts`

Вместо этого использовались прямые вызовы:
```typescript
// НЕПРАВИЛЬНО ❌
const response = await api.get('/api/2fa/status');
const response = await api.post('/api/2fa/totp/setup');
```

### Код ошибки
```typescript
const loadStatus = async () => {
  try {
    const response = await api.get('/api/2fa/status');  // ❌ api.get не существует!
    setStatus(response.data);
  } catch (err: any) {
    console.error('Failed to load 2FA status:', err);
  } finally {
    setLoading(false);
  }
};
```

---

## ✅ Решение

### 1. Добавлены методы 2FA в `api.ts`

Создано 5 новых методов для работы с 2FA:

```typescript
// Two-Factor Authentication
/** Get 2FA status */
getTwoFactorStatus: () =>
  fetchAPI("/api/2fa/status"),

/** Start 2FA setup (get QR code) */
setupTwoFactor: () =>
  fetchAPI("/api/2fa/totp/setup", { method: "POST" }),

/** Enable 2FA with verification code */
enableTwoFactor: (verificationCode: string) =>
  fetchAPI("/api/2fa/totp/enable", {
    method: "POST",
    body: JSON.stringify({ verification_code: verificationCode }),
  }),

/** Disable 2FA */
disableTwoFactor: (code: string) =>
  fetchAPI("/api/2fa/totp/disable", {
    method: "POST",
    body: JSON.stringify({ code }),
  }),

/** Regenerate backup codes */
regenerateBackupCodes: (code: string) =>
  fetchAPI("/api/2fa/backup-codes/regenerate", {
    method: "POST",
    body: JSON.stringify({ code }),
  }),
```

### 2. Обновлён `TwoFactorAuth.tsx`

Заменены все неправильные вызовы на правильные методы API:

#### loadStatus (до/после):
```typescript
// ДО ❌
const response = await api.get('/api/2fa/status');
setStatus(response.data);

// ПОСЛЕ ✅
const data = await api.getTwoFactorStatus();
setStatus(data);
```

#### startSetup (до/после):
```typescript
// ДО ❌
const response = await api.post('/api/2fa/totp/setup');
setQrCode(response.data.qr_code);
setSecret(response.data.secret);
setBackupCodes(response.data.backup_codes);

// ПОСЛЕ ✅
const data = await api.setupTwoFactor();
setQrCode(data.qr_code);
setSecret(data.secret);
setBackupCodes(data.backup_codes);
```

#### verifyAndEnable (до/после):
```typescript
// ДО ❌
await api.post('/api/2fa/totp/enable', {
  verification_code: verificationCode
});

// ПОСЛЕ ✅
await api.enableTwoFactor(verificationCode);
```

#### disable2FA (до/после):
```typescript
// ДО ❌
await api.post('/api/2fa/totp/disable', {
  code: disableCode
});

// ПОСЛЕ ✅
await api.disableTwoFactor(disableCode);
```

#### regenerateBackupCodes (до/после):
```typescript
// ДО ❌
const response = await api.post('/api/2fa/backup-codes/regenerate', { code });
setBackupCodes(response.data.backup_codes);

// ПОСЛЕ ✅
const data = await api.regenerateBackupCodes(code);
setBackupCodes(data.backup_codes);
```

---

## 📁 Обновленные файлы

1. ✅ `/frontend/src/lib/api.ts` - добавлено 5 методов 2FA
2. ✅ `/frontend/src/app/settings/TwoFactorAuth.tsx` - обновлено 5 методов

---

## 🎯 Результат

### До исправления:
- ❌ TypeError при открытии страницы Settings
- ❌ 2FA не загружается
- ❌ Невозможно включить/отключить 2FA

### После исправления:
- ✅ Страница Settings открывается без ошибок
- ✅ 2FA статус загружается корректно
- ✅ Можно включить/отключить 2FA
- ✅ Можно сгенерировать резервные коды
- ✅ Все API вызовы работают правильно

---

## 🔧 Техническая информация

### Используемые endpoints:
- `GET /api/2fa/status` - получить статус 2FA
- `POST /api/2fa/totp/setup` - начать настройку (получить QR код)
- `POST /api/2fa/totp/enable` - включить 2FA с кодом подтверждения
- `POST /api/2fa/totp/disable` - отключить 2FA
- `POST /api/2fa/backup-codes/regenerate` - сгенерировать новые резервные коды

### Паттерн использования:
```typescript
// Правильный способ вызова API ✅
import { api } from '@/lib/api';

// Получить статус
const status = await api.getTwoFactorStatus();

// Начать настройку
const setup = await api.setupTwoFactor();
console.log(setup.qr_code, setup.secret, setup.backup_codes);

// Включить 2FA
await api.enableTwoFactor('123456');

// Отключить 2FA
await api.disableTwoFactor('123456');

// Обновить резервные коды
const newCodes = await api.regenerateBackupCodes('123456');
console.log(newCodes.backup_codes);
```

---

## 🚀 Deployment

**Frontend перезапущен**: ✅  
**URL**: https://orgon.asystem.ai/settings  
**Статус**: Ошибка исправлена, 2FA работает

### Тестирование:
1. ✅ Откройте https://orgon.asystem.ai/settings
2. ✅ Страница загружается без ошибок
3. ✅ Отображается статус 2FA
4. ✅ Можно включить/отключить 2FA
5. ✅ QR код генерируется корректно
6. ✅ Резервные коды работают

---

## 📝 Уроки

### Что пошло не так:
1. В `TwoFactorAuth.tsx` использовались несуществующие методы `api.get()` и `api.post()`
2. Не были созданы типизированные методы для 2FA в `api.ts`
3. Ошибка проявилась только при открытии страницы Settings

### Как избежать в будущем:
1. ✅ Всегда создавать типизированные методы в `api.ts` для новых endpoints
2. ✅ Использовать только существующие методы из `api` объекта
3. ✅ Тестировать страницы после добавления новых API вызовов
4. ✅ Проверять TypeScript errors перед коммитом

### Best practices:
```typescript
// ✅ ПРАВИЛЬНО - типизированный метод
const data = await api.getTwoFactorStatus();

// ❌ НЕПРАВИЛЬНО - прямой вызов
const response = await api.get('/api/2fa/status');

// ✅ ПРАВИЛЬНО - метод с параметрами
await api.enableTwoFactor(code);

// ❌ НЕПРАВИЛЬНО - прямой POST
await api.post('/api/2fa/totp/enable', { verification_code: code });
```

---

**Подготовлено**: AI Agent  
**Дата**: 2026-02-07 17:30 GMT+6  
**Время исправления**: 5 минут ⚡  
**Статус**: ✅ FIXED - 2FA работает корректно
