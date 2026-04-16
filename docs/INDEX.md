# 📚 ORGON Documentation Index

**Последнее обновление:** 2026-02-05

---

## 🚀 Быстрый Доступ

### Для Нового Разработчика
1. [README.md](./README.md) — начать здесь
2. [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) — сводка проекта
3. [CRITICAL_REFERENCE.md](./CRITICAL_REFERENCE.md) — критические ошибки
4. [QUICKSTART_CHECKLIST.md](./QUICKSTART_CHECKLIST.md) — что делать

### При Проблемах
- **Ошибка подписи?** → [CRITICAL_REFERENCE.md](./CRITICAL_REFERENCE.md#критические-ошибки)
- **Transaction stuck?** → [CRITICAL_REFERENCE.md](./CRITICAL_REFERENCE.md#частые-ошибки)
- **Как работает multi-sig?** → [API_IMPLEMENTATION_VISUAL.md](./API_IMPLEMENTATION_VISUAL.md#поток-данных-мультиподпись)
- **Архитектура?** → [API_IMPLEMENTATION_VISUAL.md](./API_IMPLEMENTATION_VISUAL.md#архитектура-gotcha)

---

## 📖 Все Документы

### Планирование и Архитектура

| Файл | Размер | Описание | Когда Читать |
|------|--------|----------|--------------|
| [README.md](./README.md) | 300 строк | Навигация по всей документации | Первым делом |
| [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) | 600 строк | Краткая сводка плана | После README |
| [GOTCHA_API_IMPLEMENTATION_PLAN.md](./GOTCHA_API_IMPLEMENTATION_PLAN.md) | 12000 строк | Полный план внедрения API | Для глубокого понимания |
| [API_IMPLEMENTATION_VISUAL.md](./API_IMPLEMENTATION_VISUAL.md) | 1500 строк | 6 диаграмм + визуализация | Для визуального понимания |
| [QUICKSTART_CHECKLIST.md](./QUICKSTART_CHECKLIST.md) | 800 строк | Ежедневный чеклист задач | Каждый день |
| [CRITICAL_REFERENCE.md](./CRITICAL_REFERENCE.md) | 600 строк | Справочник при проблемах | При ошибках |

### Safina API Reference

| Файл | Описание |
|------|----------|
| [safina.html](./safina.html) | Официальная документация API (19 методов) |
| [Examples.html](./Examples.html) | Примеры кода на Node.js |
| [H2K_Pay.html](./H2K_Pay.html) | H2K Pay виджет |

---

## 📊 Статус Документации

```
PLANNING & ARCHITECTURE
├── README.md                              ✅ Complete
├── IMPLEMENTATION_SUMMARY.md              ✅ Complete
├── GOTCHA_API_IMPLEMENTATION_PLAN.md      ✅ Complete
├── API_IMPLEMENTATION_VISUAL.md           ✅ Complete
├── QUICKSTART_CHECKLIST.md                ✅ Complete
└── CRITICAL_REFERENCE.md                  ✅ Complete

SAFINA API REFERENCE
├── safina.html                            ✅ Exists
├── Examples.html                          ✅ Exists
└── H2K_Pay.html                           ✅ Exists

IMPLEMENTATION STATUS
├── Backend Client Layer                   ✅ 100% (19/19 methods)
├── Backend Service Layer                  ⚠️  50% (2/4 services)
├── Backend REST API Layer                 ⚠️  30% (partial endpoints)
├── Frontend Components                    ⚠️  30% (wallets only)
└── Integrations                           ❌  0% (not started)

OVERALL PROGRESS: 40% Complete
```

---

## 🎯 Roadmap

```
Week 1 (Feb 5-9)                           Week 2 (Feb 10-15)
├── Day 1-2: Service Layer                 ├── Day 6-7: Frontend (cont.)
├── Day 3:   REST API                      ├── Day 8-9: Integrations
└── Day 4-5: Frontend                      └── Day 10:  Testing & Docs

TARGET: Feb 15, 2026 (10 days)
```

---

## 🔥 Critical Knowledge

### Must Know Before Coding

**1. Decimal Separator**
```
❌ "10.5" → ERROR
✅ "10,5" → OK
```

**2. JSON Format**
```
❌ '{"value": "10,5"}'  → ERROR (пробелы!)
✅ '{"value":"10,5"}'   → OK (compact)
```

**3. Token Format**
```
❌ "TRX"
✅ "5010:::TRX###945C6F4C54B3921F4625890300235114"
```

**Подробности:** [CRITICAL_REFERENCE.md](./CRITICAL_REFERENCE.md)

---

## 🏗️ GOTCHA Framework

```
┌──────────────────────────────────────┐
│  Layer 1: GOALS                       │
│  → What to achieve                   │
│  Files: goals/orgon_*.md             │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  Layer 2: ORCHESTRATION              │
│  → AI Manager coordinates            │
│  Logic: In AI reasoning              │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  Layer 3: TOOLS                      │
│  → Deterministic scripts             │
│  Files: backend/services/*.py        │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  Layer 4: CONTEXT                    │
│  → Reference material                │
│  Files: context/safina_*.md          │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  Layer 5: HARDPROMPTS                │
│  → Instruction templates             │
│  Files: hardprompts/safina/*.md      │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  Layer 6: ARGS                       │
│  → Behavior settings                 │
│  Files: args/safina_*.yaml           │
└──────────────────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│  Layer 7: EXPERTS                    │
│  → Domain knowledge                  │
│  Files: experts/domains/safina/      │
└──────────────────────────────────────┘
```

**Подробности:** [GOTCHA_API_IMPLEMENTATION_PLAN.md](./GOTCHA_API_IMPLEMENTATION_PLAN.md)

---

## 📱 Quick Commands

### Start Development
```bash
# Backend
cd backend && source ../../.venv/bin/activate && uvicorn main:app --reload --port 8890

# Frontend
cd frontend && npm run dev

# Open
open http://localhost:3000
```

### Run Tests
```bash
pytest --cov
```

### Check Docs
```bash
cd docs
ls -la
```

---

## 🎓 Learning Path

### Beginner (30 minutes)
1. ✅ Read [README.md](./README.md) — 5 min
2. ✅ Read [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) — 10 min
3. ✅ Read [CRITICAL_REFERENCE.md](./CRITICAL_REFERENCE.md) — 15 min

### Intermediate (1 hour)
4. ✅ Read [API_IMPLEMENTATION_VISUAL.md](./API_IMPLEMENTATION_VISUAL.md) — 20 min
5. ✅ Browse [safina.html](./safina.html) — 20 min
6. ✅ Run project locally — 20 min

### Advanced (2 hours)
7. ✅ Read [GOTCHA_API_IMPLEMENTATION_PLAN.md](./GOTCHA_API_IMPLEMENTATION_PLAN.md) — 60 min
8. ✅ Start implementing Phase 1 — 60 min

---

## 📞 Support

### Documentation Issues
- Missing info? → Update this INDEX.md
- Unclear section? → Update relevant .md file
- New pattern discovered? → Update CRITICAL_REFERENCE.md

### Code Issues
- Signature error? → [CRITICAL_REFERENCE.md](./CRITICAL_REFERENCE.md)
- API error? → [safina.html](./safina.html)
- Architecture question? → [GOTCHA_API_IMPLEMENTATION_PLAN.md](./GOTCHA_API_IMPLEMENTATION_PLAN.md)

### GOTCHA Framework
- Main guide: `/Users/macbook/AGENT/CLAUDE.md`
- Goals: `/Users/macbook/AGENT/goals/`
- Tools: `/Users/macbook/AGENT/tools/`

---

## 🎯 Next Steps

1. ✅ Read this INDEX.md
2. → Open [README.md](./README.md)
3. → Follow the learning path
4. → Start [QUICKSTART_CHECKLIST.md](./QUICKSTART_CHECKLIST.md)

---

**Ready to start?** → Open [README.md](./README.md) 🚀

**Last updated:** 2026-02-05
**Version:** 1.0.0
