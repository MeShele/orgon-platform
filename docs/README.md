# ORGON Documentation

**ORGON** — система управления кошельками с интеграцией Safina Pay API

---

## 📚 Навигация по Документации

### 🚀 Начало Работы

**Новичкам читать в этом порядке:**

1. **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)** — 5 минут
   - Краткая сводка проекта
   - Текущий статус (40% готово)
   - Что делать дальше

2. **[CRITICAL_REFERENCE.md](./CRITICAL_REFERENCE.md)** — 10 минут
   - 5 критических ошибок (ОБЯЗАТЕЛЬНО прочитать!)
   - Частые проблемы и решения
   - Cheat sheet с примерами кода

3. **[API_IMPLEMENTATION_VISUAL.md](./API_IMPLEMENTATION_VISUAL.md)** — 15 минут
   - 6 Mermaid диаграмм
   - Визуализация архитектуры
   - Потоки данных

4. **[GOTCHA_API_IMPLEMENTATION_PLAN.md](./GOTCHA_API_IMPLEMENTATION_PLAN.md)** — 30 минут
   - Полный план внедрения API
   - Все 7 слоев GOTCHA Framework
   - Детальные спецификации

5. **[QUICKSTART_CHECKLIST.md](./QUICKSTART_CHECKLIST.md)** — reference
   - Ежедневный чеклист
   - Tracking progress
   - Acceptance criteria

---

### 📖 API Reference

**Официальная документация Safina Pay:**

- **[safina.html](./safina.html)** — Safina Pay API Reference
  - 19 методов API
  - Параметры запросов/ответов
  - Форматы данных

- **[Examples.html](./Examples.html)** — Примеры кода
  - Node.js примеры
  - GET/POST запросы
  - Создание кошельков и транзакций

- **[H2K_Pay.html](./H2K_Pay.html)** — H2K Pay Widget
  - Встраивание виджета платежей
  - Получение временных адресов
  - Token list API

---

## 🎯 Быстрый Старт

### Проблема? Смотри Сюда:

```
❌ Ошибка подписи?
   → Читай: CRITICAL_REFERENCE.md → "Критические Ошибки"

❌ Transaction stuck?
   → Читай: CRITICAL_REFERENCE.md → "Частые Ошибки"

❓ Как создать multi-sig wallet?
   → Читай: CRITICAL_REFERENCE.md → "Cheat Sheet"

❓ Какая архитектура?
   → Читай: API_IMPLEMENTATION_VISUAL.md

❓ Что делать сегодня?
   → Читай: QUICKSTART_CHECKLIST.md
```

---

## 📊 Статус Проекта

### ✅ Готово (40%)
- SafinaClient (19/19 методов)
- Wallet CRUD
- Dashboard stats
- EC подписание

### ⚠️ В Процессе (30%)
- TransactionService
- REST API endpoints
- Frontend UI

### ❌ Осталось (30%)
- SignatureService
- NetworkService
- Telegram/ASAGENT интеграции
- Multi-sig UI

---

## 🔥 Критические Моменты

### 1. Decimal Separator
```python
❌ "10.5"  → Ошибка подписи!
✅ "10,5"  → Safina требует запятую
```

### 2. JSON Compact
```python
❌ json.dumps(data)
✅ json.dumps(data, separators=(",", ":"))
```

### 3. Token Format
```python
❌ "TRX"
✅ "5010:::TRX###945C6F4C54B3921F4625890300235114"
```

**Детали:** → [CRITICAL_REFERENCE.md](./CRITICAL_REFERENCE.md)

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────┐
│           GOTCHA Framework                   │
├─────────────────────────────────────────────┤
│ Goals    → Что делать                       │
│ Orchestr → AI координатор                   │
│ Tools    → Детерминистические скрипты       │
│ Context  → Справочники и примеры            │
│ Hardpro  → Шаблоны инструкций              │
│ Args     → Настройки поведения              │
│ Experts  → Доменные знания                  │
└─────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│           ORGON Layers                       │
├─────────────────────────────────────────────┤
│ Frontend → Next.js + React 19               │
│    ↓                                         │
│ REST API → FastAPI endpoints                │
│    ↓                                         │
│ Services → Business logic                   │
│    ↓                                         │
│ Client   → SafinaPayClient                  │
│    ↓                                         │
│ External → Safina Pay API                   │
└─────────────────────────────────────────────┘
```

**Детали:** → [API_IMPLEMENTATION_VISUAL.md](./API_IMPLEMENTATION_VISUAL.md)

---

## 📋 Фазы Реализации

### Phase 1: Service Layer (День 1-2)
- [ ] NetworkService
- [ ] SignatureService
- [ ] TransactionService улучшения

### Phase 2: REST API (День 3)
- [ ] `/api/transactions/*`
- [ ] `/api/signatures/*`
- [ ] `/api/networks/*`

### Phase 3: Frontend (День 4-6)
- [ ] Transaction components
- [ ] Signature components
- [ ] Multi-sig components

### Phase 4: Integrations (День 7-8)
- [ ] Telegram notifications
- [ ] ASAGENT auto-approve
- [ ] Vault integration

### Phase 5: Testing (День 9-10)
- [ ] Unit tests
- [ ] Integration tests
- [ ] Documentation

**Детали:** → [QUICKSTART_CHECKLIST.md](./QUICKSTART_CHECKLIST.md)

---

## 🛠️ Инструменты

### Backend
```bash
cd backend
source ../../.venv/bin/activate
uvicorn main:app --reload --port 8890
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Tests
```bash
pytest --cov
```

---

## 📞 Поддержка

### Документация по Проекту
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) — сводка
- [GOTCHA_API_IMPLEMENTATION_PLAN.md](./GOTCHA_API_IMPLEMENTATION_PLAN.md) — план
- [API_IMPLEMENTATION_VISUAL.md](./API_IMPLEMENTATION_VISUAL.md) — диаграммы
- [CRITICAL_REFERENCE.md](./CRITICAL_REFERENCE.md) — справочник
- [QUICKSTART_CHECKLIST.md](./QUICKSTART_CHECKLIST.md) — чеклист

### Safina API
- [safina.html](./safina.html) — API Reference
- [Examples.html](./Examples.html) — примеры кода
- [H2K_Pay.html](./H2K_Pay.html) — виджет

### GOTCHA Framework
- `/Users/macbook/AGENT/CLAUDE.md` — main guide
- `/Users/macbook/AGENT/goals/` — процессы
- `/Users/macbook/AGENT/tools/` — инструменты

### ASAGENT
- `/Users/macbook/AGENT/asagent/` — система
- `/Users/macbook/AGENT/asagent/gateway/` — бот

---

## 🎓 Для Новых Разработчиков

**30-минутный онбординг:**

1. ✅ (5 мин) Читать [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
2. ✅ (10 мин) Читать [CRITICAL_REFERENCE.md](./CRITICAL_REFERENCE.md)
3. ✅ (15 мин) Читать [API_IMPLEMENTATION_VISUAL.md](./API_IMPLEMENTATION_VISUAL.md)

**Потом:**
4. ⚠️ Запустить проект локально (backend + frontend)
5. ⚠️ Протестировать dashboard и wallet list
6. ⚠️ Прочитать [GOTCHA_API_IMPLEMENTATION_PLAN.md](./GOTCHA_API_IMPLEMENTATION_PLAN.md)
7. ⚠️ Начать с Phase 1 по [QUICKSTART_CHECKLIST.md](./QUICKSTART_CHECKLIST.md)

---

## 🎯 Next Actions

### Сегодня
- [ ] Прочитать CRITICAL_REFERENCE.md
- [ ] Прочитать IMPLEMENTATION_SUMMARY.md
- [ ] Начать Phase 1

### Эта Неделя
- [ ] Завершить Phase 1-2
- [ ] Начать Phase 3

### Следующая Неделя
- [ ] Завершить Phase 3-5
- [ ] Release!

---

## 📈 Metrics

**Code Coverage Target:** >80%
**API Coverage:** 19/19 методов в client ✅
**Service Coverage:** 2/4 сервисов ⚠️
**Frontend Coverage:** 30% ⚠️
**Integration Coverage:** 0% ❌

**Target Completion:** 2026-02-15 (10 дней)

---

**Последнее обновление:** 2026-02-05
**Версия:** 1.0.0

---

**Готовы начать?**

→ Откройте [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)

→ Затем [QUICKSTART_CHECKLIST.md](./QUICKSTART_CHECKLIST.md)

→ Начните с Phase 1! 🚀
