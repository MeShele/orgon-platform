# Self-Review Checklist — Constitutional AI Framework

**Применение принципов Anthropic на каждом этапе**

---

## 📋 Обязательный чек-лист перед завершением этапа

### 1. Code Quality ✅

- [ ] **TypeScript:** No errors, strict mode enabled
- [ ] **ESLint:** No warnings (допустимо < 5 minor warnings)
- [ ] **Prettier:** Code formatted автоматически
- [ ] **Naming:** Понятные имена переменных/функций/компонентов
- [ ] **Comments:** Критичные места закомментированы (why, not what)
- [ ] **Complexity:** Нет functions > 50 lines (рефакторить)
- [ ] **DRY:** Нет дублирования кода (extract common logic)

---

### 2. Testing 🧪

- [ ] **Unit Tests:** Coverage > 80% для нового кода
- [ ] **Integration Tests:** Happy path + edge cases
- [ ] **E2E Tests:** Main user flows протестированы
- [ ] **Manual Testing:** UI/UX проверка (desktop, mobile, tablet)
- [ ] **Regression:** Старые тесты не сломались
- [ ] **Test Quality:** Тесты понятные, быстрые (< 5s на unit)

---

### 3. Security 🔐

#### Input Validation
- [ ] Все user inputs валидируются (backend + frontend)
- [ ] XSS protection (sanitize HTML, escape output)
- [ ] SQL Injection prevention (prepared statements, ORM)
- [ ] File uploads: Type/size validation
- [ ] Rate limiting: Защита от DDoS

#### Authentication & Authorization
- [ ] Sessions: Secure (httpOnly, sameSite cookies)
- [ ] Tokens: Proper expiration, refresh logic
- [ ] Permissions: Role-based access control работает
- [ ] Tenant isolation: RLS/data filtering проверены

#### Data Protection
- [ ] Sensitive data: Encrypted at rest (если нужно)
- [ ] HTTPS: Enforced (no mixed content)
- [ ] Secrets: Не в коде (environment variables)
- [ ] Logs: Не содержат passwords, tokens, PII

#### OWASP Top 10 Check
- [ ] Broken Access Control: Fixed
- [ ] Cryptographic Failures: Fixed
- [ ] Injection: Fixed
- [ ] Insecure Design: Fixed
- [ ] Security Misconfiguration: Fixed
- [ ] Vulnerable Components: Updated
- [ ] Authentication Failures: Fixed
- [ ] Data Integrity Failures: Fixed
- [ ] Security Logging: Implemented
- [ ] SSRF: Prevented

---

### 4. Performance ⚡

#### Backend
- [ ] API response time: < 200ms (median), < 500ms (p95)
- [ ] Database queries: Optimized, indexed
- [ ] N+1 queries: Eliminated (use joins, eager loading)
- [ ] Caching: Implemented где уместно (Redis)
- [ ] Rate limiting: Configured

#### Frontend
- [ ] Bundle size: < 500KB gzipped для нового раздела
- [ ] Code splitting: Implemented (lazy loading)
- [ ] Images: Optimized (WebP, lazy load)
- [ ] Lighthouse score: > 90 (Performance, Accessibility, Best Practices)
- [ ] Core Web Vitals: LCP < 2.5s, FID < 100ms, CLS < 0.1

#### Database
- [ ] Indexes: На всех foreign keys, фильтруемых полях
- [ ] Query plans: Reviewed (EXPLAIN ANALYZE)
- [ ] Connection pooling: Configured
- [ ] Migrations: Tested, rollback готов

---

### 5. Documentation 📚

#### Code Documentation
- [ ] Complex functions: Commented (why, not what)
- [ ] Public APIs: JSDoc/docstrings
- [ ] Type definitions: Complete, exported

#### API Documentation
- [ ] OpenAPI/Swagger spec: Updated
- [ ] Request/Response examples: Provided
- [ ] Error codes: Documented
- [ ] Rate limits: Documented

#### User Documentation
- [ ] User guide: Written для новых features
- [ ] Screenshots/GIFs: Included если UI
- [ ] FAQ: Updated
- [ ] Troubleshooting: Common issues documented

#### Technical Documentation
- [ ] Architecture: Diagrams updated (если изменения)
- [ ] Database schema: ER diagram updated
- [ ] Migration guide: Written (если breaking changes)
- [ ] Deployment guide: Updated

---

### 6. Accessibility ♿

- [ ] **Semantic HTML:** Правильные теги (header, nav, main, footer)
- [ ] **ARIA labels:** Добавлены где нужно
- [ ] **Keyboard navigation:** Работает (Tab, Enter, Esc)
- [ ] **Focus indicators:** Видны
- [ ] **Color contrast:** WCAG AA (4.5:1 для текста)
- [ ] **Screen reader:** Протестировано (NVDA/JAWS)
- [ ] **Forms:** Labels связаны с inputs

---

### 7. UX/UI 🎨

#### Design Consistency
- [ ] Дизайн соответствует остальному приложению
- [ ] Spacing: Consistent (Tailwind classes)
- [ ] Typography: Правильные размеры/веса
- [ ] Colors: Из color palette

#### States
- [ ] Loading: Skeleton screens или spinners
- [ ] Empty: Friendly empty states
- [ ] Error: Понятные error messages
- [ ] Success: Toast notifications

#### Responsive
- [ ] Mobile (< 640px): Работает
- [ ] Tablet (640-1024px): Работает
- [ ] Desktop (> 1024px): Работает
- [ ] Touch targets: > 44x44px

---

### 8. Error Handling 🐛

#### Frontend
- [ ] Try-catch: В async functions
- [ ] Error boundaries: Для React components
- [ ] User feedback: Понятные сообщения (не "Error 500")
- [ ] Retry logic: Для network requests

#### Backend
- [ ] Validation errors: 400 с понятным message
- [ ] Auth errors: 401/403 с правильным кодом
- [ ] Server errors: 500 logged, generic message пользователю
- [ ] Rate limit: 429 с Retry-After header

---

### 9. Deployment 🚀

#### Pre-Deployment
- [ ] Environment variables: Configured
- [ ] Database migrations: Готовы, tested
- [ ] Rollback plan: Готов
- [ ] Backup: До deploy
- [ ] Monitoring: Alerts настроены

#### Post-Deployment
- [ ] Smoke tests: Passed на production/staging
- [ ] Health check: Endpoint работает
- [ ] Logs: Мониторятся (Sentry, CloudWatch)
- [ ] Performance: Metrics в норме

---

## 🤔 Constitutional AI Self-Reflection Questions

### После каждого этапа задай себе:

1. **Безопасно ли это?**
   - Могу ли я навредить пользователям?
   - Есть ли security holes?
   - Защищены ли данные?

2. **Масштабируется ли это?**
   - Сработает ли при 1000 организаций?
   - Сработает ли при 100K транзакций/день?
   - Нет ли bottlenecks?

3. **Понятно ли пользователю?**
   - Интуитивный ли UI?
   - Понятны ли error messages?
   - Достаточно ли подсказок?

4. **Соответствует ли бизнес-требованиям?**
   - Решает ли это проблему обменников?
   - Alignment с целями Asystem?

5. **Есть ли edge cases?**
   - Что если organization_id = null?
   - Что если 0 транзакций?
   - Что если API недоступно?

6. **Прозрачно ли это?**
   - Понятно ли как работает код?
   - Достаточно ли логов?
   - Понятно ли пользователю что происходит?

7. **Обратимо ли это?**
   - Можно ли rollback миграцию?
   - Можно ли отменить действие?
   - Есть ли audit trail?

---

## ✅ Критерии "Done"

Этап считается завершенным только если:

- ✅ Все пункты чек-листа выполнены (> 95%)
- ✅ Все тесты passing
- ✅ Code review пройден (self-review + peer если есть)
- ✅ Documentation написана
- ✅ Deployable (миграции готовы, rollback tested)
- ✅ No critical/high bugs

**Если хотя бы один критерий не выполнен → этап не завершен.**

---

## 🚫 Red Flags (Стоп-сигналы)

Останови работу и разбери проблему если:

- 🚨 Security vulnerability found (критичная)
- 🚨 Data loss possible (миграция может удалить данные)
- 🚨 Performance degradation > 2x (queries стали медленнее)
- 🚨 Breaking changes без migration path
- 🚨 Test coverage упала < 70%
- 🚨 Production incident (если уже deployed)

---

**Помни:** Лучше потратить +1 день на качество, чем +1 неделю на исправление багов в production.

**Принцип:** "Делай правильно с первого раза" (Do it right the first time)

---

**Автор:** Forge 🔥  
**Фреймворк:** Constitutional AI (Anthropic)  
**Дата:** 2026-02-10
