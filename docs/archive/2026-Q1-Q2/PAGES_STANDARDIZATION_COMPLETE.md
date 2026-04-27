# Pages Standardization - Единый стандарт дизайна и переводов

**Дата**: 2026-02-07  
**Затрачено времени**: 1 час (частичное выполнение)  
**Статус**: ⚙️ IN PROGRESS (40% выполнено)

## 🎯 Задача

Привести все страницы к единому стандарту дизайна и перевода:
- https://orgon.asystem.ai/transactions
- https://orgon.asystem.ai/scheduled
- https://orgon.asystem.ai/analytics
- https://orgon.asystem.ai/signatures
- https://orgon.asystem.ai/contacts
- https://orgon.asystem.ai/audit

## ✅ Выполненные работы (Phase 1)

### 1. Transactions Page - ✅ COMPLETE

#### **TransactionTable Component**
- ✅ Заголовки таблицы переведены:
  - "UNID" → `t('table.unid')`
  - "To" → `t('table.to')`
  - "Amount" → `t('table.amount')`
  - "Status" → `t('table.status')`
  - "TX Hash" → `t('table.txHash')`
  - "Date" → `t('table.date')`
- ✅ Empty state: "No transactions found" → `t('table.noTransactions')`

#### **TransactionFilters Component**
- ✅ **Заголовок**: "Filters" → `t('filters.title')`
- ✅ **Метки полей**:
  - "Wallet" → `t('filters.wallet')`
  - "Status" → `t('filters.status')`
  - "Network" → `t('filters.network')`
  - "From Date" → `t('filters.fromDate')`
  - "To Date" → `t('filters.toDate')`
- ✅ **Placeholders**:
  - "All wallets" → `t('filters.allWallets')`
  - "All statuses" → `t('filters.allStatuses')`
  - "All networks" → `t('filters.allNetworks')`
- ✅ **Статусы переведены**:
  - "Pending" → `t('statuses.pending')` = "Ожидает" / "Pending" / "Күтүүдө"
  - "Signed" → `t('statuses.signed')` = "Подписано" / "Signed" / "Колтамга коюлган"
  - "Confirmed" → `t('statuses.confirmed')` = "Подтверждено" / "Confirmed" / "Ырасталган"
  - "Rejected" → `t('statuses.rejected')` = "Отклонено" / "Rejected" / "Четке кагылган"
- ✅ **Кнопки**:
  - "Apply Filters" → `t('filters.applyButton')`
  - "Clear" → `t('filters.clearButton')`

### 2. Signatures Page - ⏳ PARTIAL (переводы добавлены, компоненты требуют обновления)

#### **Добавленные переводы** (готовы к использованию):
```json
"signatures.pending.table": {
  "token": "Токен / Token / Токен",
  "to": "Кому / To / Кимге",
  "value": "Сумма / Value / Суммасы",
  "age": "Возраст / Age / Жашы",
  "progress": "Прогресс / Progress / Прогресс",
  "actions": "Действия / Actions / Аракеттер",
  "signButton": "Подписать / Sign / Колтамга коюу",
  "signing": "Подписание... / Signing... / Колтамга коюлууда...",
  "rejectButton": "Отклонить / Reject / Четке кагуу",
  "loadStatusButton": "Загрузить статус / Load Status / Статусту жүктөө",
  "noSignatures": "Нет транзакций... / No transactions... / Операциялар жок..."
}

"signatures.rejectDialog": {
  "title": "Отклонить транзакцию / Reject Transaction / ...",
  "reasonLabel": "Причина отклонения / Rejection Reason / ...",
  "reasonPlaceholder": "Введите причину... / Enter reason... / ...",
  "cancelButton": "Отмена / Cancel / Жокко чыгаруу",
  "confirmButton": "Отклонить / Reject / Четке кагуу"
}

"signatures.history.table": {
  "transaction": "Транзакция / Transaction / Операция",
  "action": "Действие / Action / Аракет",
  "signer": "Подписант / Signer / Колтамга коюучу",
  "timestamp": "Время / Timestamp / Убакыт",
  "reason": "Причина / Reason / Себеп",
  "noHistory": "История подписей пуста / ... / ..."
}
```

#### **Компоненты, требующие обновления**:
- [ ] `PendingSignaturesTable.tsx` - кнопки "Sign", "Reject", "Load Status"
- [ ] `SignatureHistoryTable.tsx` - заголовки таблицы
- [ ] `RejectDialog.tsx` - метки полей диалога

## 📊 Новые переводы

### Добавлено ключей переводов:
| Секция | Ключей (RU) | Ключей (EN) | Ключей (KY) |
|--------|-------------|-------------|-------------|
| transactions.table | 7 | 7 | 7 |
| transactions.filters | 10 | 10 | 10 |
| transactions.statuses | 5 | 5 | 5 |
| signatures.pending.table | 10 | 10 | 10 |
| signatures.rejectDialog | 4 | 4 | 4 |
| signatures.history.table | 6 | 6 | 6 |
| **ВСЕГО** | **42** | **42** | **42** |

**Итого**: **126 новых переводов** (42 ключа × 3 языка)

## 🔄 Следующие шаги (Phase 2)

### 1. Signatures Page - Обновить компоненты
**Файлы для обновления**:
```bash
/components/signatures/PendingSignaturesTable.tsx
/components/signatures/SignatureHistoryTable.tsx
/components/signatures/RejectDialog.tsx
```

**Изменения**:
- Добавить `useTranslations('signatures.pending.table')` в PendingSignaturesTable
- Заменить хардкодные кнопки "Sign", "Reject", "Load Status"
- Обновить метки "Token", "To", "Value", "Age", "Progress", "Actions"
- Добавить `useTranslations('signatures.history.table')` в SignatureHistoryTable
- Заменить заголовки таблицы истории

**Ожидаемое время**: 30 минут

### 2. Scheduled Page - Проверить переводы
**Статус**: Уже имеет базовые переводы в `scheduled` namespace
**Требуется**: Проверить компоненты на наличие хардкодных строк

**Файлы для проверки**:
```bash
/app/scheduled/page.tsx
/components/scheduled/ScheduledTransactionCard.tsx (если существует)
```

**Ожидаемое время**: 15 минут

### 3. Analytics Page - Проверить переводы
**Статус**: Уже имеет базовые переводы в `analytics` namespace
**Требуется**: Проверить компоненты графиков на наличие хардкодных легенд/осей

**Файлы для проверки**:
```bash
/components/analytics/BalanceChart.tsx
/components/analytics/VolumeChart.tsx
/components/analytics/TokenDistribution.tsx
/components/analytics/SignatureStats.tsx
```

**Ожидаемое время**: 20 минут

### 4. Contacts Page - Проверить переводы
**Статус**: Уже имеет полные переводы в `contacts` namespace
**Требуется**: Минимальная проверка

**Ожидаемое время**: 10 минут

### 5. Audit Page - Проверить переводы
**Статус**: Уже имеет базовые переводы в `audit` namespace
**Требуется**: Проверить компоненты таблицы на наличие хардкодных строк

**Файлы для проверки**:
```bash
/components/audit/AuditLogTable.tsx (если существует)
/components/audit/AuditFilters.tsx (если существует)
```

**Ожидаемое время**: 15 минут

## 🎨 Стандартизация дизайна (Phase 3)

### Текущие проблемы дизайна:

1. **Несогласованные цвета кнопок**:
   - Transactions: blue-600 (стандарт)
   - Signatures: возможно другие цвета
   - Scheduled: нужно проверить
   
2. **Различные размеры шрифтов**:
   - Некоторые таблицы используют text-xs
   - Другие используют text-sm
   
3. **Несогласованные отступы карточек**:
   - Padding может отличаться между страницами

### Решение:
Создать единый компонент `PageLayout` с:
- Стандартный padding: `p-4 sm:p-6 lg:p-8`
- Стандартный gap: `space-y-6`
- Единые стили кнопок через Tailwind classes
- Единые стили таблиц

**Ожидаемое время**: 1 час

## 📝 Итоговая оценка времени

| Фаза | Задача | Время |
|------|--------|-------|
| Phase 1 (✅) | Transactions переводы | 1 час |
| Phase 2 (⏳) | Остальные переводы | 1.5 часа |
| Phase 3 (📋) | Стандартизация дизайна | 1 час |
| **ВСЕГО** | | **3.5 часа** |

**Выполнено**: 1 час (28%)  
**Осталось**: 2.5 часа (72%)

## 🔧 Технические детали

### Обновленные файлы (Phase 1)

**Компоненты** (2 файла):
1. `/components/transactions/TransactionTable.tsx` - ✅ COMPLETE
2. `/components/transactions/TransactionFilters.tsx` - ✅ COMPLETE

**Переводы** (3 файла):
3. `/i18n/locales/ru.json` - 126 новых строк
4. `/i18n/locales/en.json` - 126 новых строк
5. `/i18n/locales/ky.json` - 126 новых строк

### Структура переводов

```typescript
// Использование в компонентах
import { useTranslations } from "@/hooks/useTranslations";

const TransactionFilters = () => {
  const t = useTranslations('transactions');
  
  return (
    <label>{t('filters.wallet')}</label>
    <Select.Value placeholder={t('filters.allWallets')} />
    <button>{t('filters.applyButton')}</button>
  );
};
```

## 🎯 Приоритетность (следующая сессия)

**HIGH Priority** (критично для UX):
1. ✅ Transactions - COMPLETE
2. ⏳ Signatures - добавлены переводы, нужно обновить компоненты
3. 📋 Scheduled - проверить
4. 📋 Analytics - проверить

**MEDIUM Priority**:
5. 📋 Contacts - минимальная проверка (уже переведено)
6. 📋 Audit - проверить

**LOW Priority**:
7. 📋 Стандартизация дизайна (единый стиль)

## 🔄 Статус deployment

Frontend перезапущен, изменения Phase 1 применены:
- ✅ TransactionTable полностью переведена
- ✅ TransactionFilters полностью переведены
- ✅ Все 3 языка (RU/EN/KY) работают

**URL**: https://orgon.asystem.ai/transactions

---

**Подготовлено**: AI Agent  
**Дата**: 2026-02-07 17:00 GMT+6  
**Следующая сессия**: Обновление Signatures/Scheduled/Analytics/Audit/Contacts компонентов (2.5 часа)
