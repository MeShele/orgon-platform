"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/lib/icons";
import { pageLayout } from "@/lib/page-layout";
import { cn } from "@/lib/utils";

interface HelpSection {
  id: string;
  title: string;
  icon: string;
  description: string;
  articles: HelpArticle[];
}

interface HelpArticle {
  id: string;
  title: string;
  content: string;
  example?: string;
  steps?: string[];
  tips?: string[];
  tags: string[];
}

const helpSections: HelpSection[] = [
  {
    id: "getting-started",
    title: "Начало работы",
    icon: "solar:play-circle-bold",
    description: "Основы работы с платформой ORGON",
    articles: [
      {
        id: "what-is-orgon",
        title: "Что такое ORGON?",
        content: "ORGON — это платформа для управления мультиподписными кошельками. Она позволяет создавать кошельки, требующие подтверждения нескольких участников для проведения транзакций.",
        example: "Кошелек с 3 участниками и порогом 2 подписи: для отправки средств нужно согласие минимум 2 человек из 3.",
        tips: [
          "Используйте мультиподпись для корпоративных счетов",
          "Настройте уведомления для важных транзакций",
          "Регулярно проверяйте журнал аудита"
        ],
        tags: ["основы", "безопасность"]
      },
      {
        id: "first-steps",
        title: "Первые шаги",
        content: "После входа в систему вы попадаете на главную страницу (Dashboard), где отображается сводная информация по вашим кошелькам и транзакциям.",
        steps: [
          "Войдите в систему с вашими учетными данными",
          "Изучите главную страницу — здесь показаны ключевые метрики",
          "Перейдите в раздел 'Кошельки' для создания первого кошелька",
          "Настройте уведомления в разделе 'Настройки'"
        ],
        tips: [
          "Включите двухфакторную аутентификацию для повышения безопасности",
          "Сохраните резервные коды восстановления"
        ],
        tags: ["начало", "настройка"]
      }
    ]
  },
  {
    id: "wallets",
    title: "Кошельки",
    icon: "solar:wallet-bold",
    description: "Создание и управление мультиподписными кошельками",
    articles: [
      {
        id: "create-wallet",
        title: "Как создать кошелек?",
        content: "Для создания кошелька перейдите в раздел 'Кошельки' и нажмите кнопку 'Создать кошелек'. Укажите название, выберите участников и настройте порог подписей.",
        example: "Кошелек 'Зарплатный фонд': 5 участников, порог 3 подписи, для выплат зарплаты сотрудникам.",
        steps: [
          "Откройте раздел 'Кошельки'",
          "Нажмите 'Создать кошелек'",
          "Введите название кошелька",
          "Добавьте участников (минимум 2)",
          "Установите порог подписей (минимум 2)",
          "Подтвердите создание"
        ],
        tips: [
          "Выбирайте порог подписей исходя из баланса безопасности и удобства",
          "Для больших сумм используйте порог >50% участников",
          "Добавляйте метки к кошелькам для удобной навигации"
        ],
        tags: ["кошельки", "создание"]
      },
      {
        id: "wallet-types",
        title: "Типы кошельков",
        content: "ORGON поддерживает различные типы мультиподписных кошельков для разных сценариев использования.",
        example: "Кошелек 2/3 для малого бизнеса: 2 владельца + 1 бухгалтер, требуется согласие любых 2 из 3.",
        tips: [
          "2/2 — максимальная безопасность, оба участника должны подписать",
          "2/3 — баланс безопасности и удобства",
          "3/5 — для команд, позволяет провести транзакцию даже если 2 человека недоступны"
        ],
        tags: ["кошельки", "типы"]
      }
    ]
  },
  {
    id: "transactions",
    title: "Транзакции",
    icon: "solar:transfer-horizontal-bold",
    description: "Отправка и управление транзакциями",
    articles: [
      {
        id: "send-transaction",
        title: "Как отправить транзакцию?",
        content: "Для отправки транзакции откройте кошелек, нажмите 'Отправить', укажите получателя, сумму и токен. Транзакция будет создана и отправлена другим участникам для подписи.",
        example: "Отправка 1000 USDT на адрес 0x1234...5678 с комментарием 'Оплата за услуги'.",
        steps: [
          "Откройте нужный кошелек",
          "Нажмите 'Отправить'",
          "Введите адрес получателя",
          "Укажите сумму и выберите токен",
          "Добавьте комментарий (опционально)",
          "Подтвердите создание транзакции",
          "Дождитесь подписей других участников"
        ],
        tips: [
          "Всегда проверяйте адрес получателя дважды",
          "Используйте адресную книгу для частых получателей",
          "Добавляйте комментарии для отслеживания платежей"
        ],
        tags: ["транзакции", "отправка"]
      },
      {
        id: "transaction-status",
        title: "Статусы транзакций",
        content: "Транзакции могут находиться в разных статусах: Ожидает подписи, Подписана, Отправлена, Подтверждена, Отклонена.",
        tips: [
          "'Ожидает подписи' — нужны подписи других участников",
          "'Подписана' — собрано достаточно подписей, готова к отправке",
          "'Отправлена' — транзакция в блокчейне, ожидает подтверждений",
          "'Подтверждена' — транзакция успешно выполнена",
          "'Отклонена' — транзакция была отклонена участниками"
        ],
        tags: ["транзакции", "статусы"]
      }
    ]
  },
  {
    id: "signatures",
    title: "Подписи",
    icon: "solar:pen-bold",
    description: "Подписание и отклонение транзакций",
    articles: [
      {
        id: "sign-transaction",
        title: "Как подписать транзакцию?",
        content: "Перейдите в раздел 'Подписи', выберите транзакцию из списка ожидающих и нажмите 'Подписать'. Проверьте детали перед подписанием.",
        steps: [
          "Откройте раздел 'Подписи'",
          "Найдите транзакцию в списке 'Ожидают подписи'",
          "Нажмите на транзакцию для просмотра деталей",
          "Проверьте получателя, сумму и комментарий",
          "Нажмите 'Подписать' если все верно",
          "Подтвердите подпись"
        ],
        tips: [
          "Всегда проверяйте детали транзакции перед подписанием",
          "Если что-то кажется подозрительным — отклоните и свяжитесь с инициатором",
          "Используйте уведомления для быстрой реакции на новые транзакции"
        ],
        tags: ["подписи", "безопасность"]
      },
      {
        id: "reject-transaction",
        title: "Отклонение транзакции",
        content: "Если вы не согласны с транзакцией, вы можете отклонить ее. Укажите причину отклонения, чтобы другие участники поняли вашу позицию.",
        example: "Причина: 'Неверная сумма, должно быть 500 USDT, а не 5000'.",
        tips: [
          "Всегда указывайте причину отклонения",
          "Свяжитесь с инициатором для уточнения деталей",
          "Отклоненную транзакцию можно пересоздать с исправлениями"
        ],
        tags: ["подписи", "отклонение"]
      }
    ]
  },
  {
    id: "scheduled",
    title: "Запланированные транзакции",
    icon: "solar:calendar-bold",
    description: "Автоматические регулярные платежи",
    articles: [
      {
        id: "create-scheduled",
        title: "Создание автоплатежа",
        content: "Запланированные транзакции позволяют настроить регулярные автоматические платежи, например, ежемесячную зарплату или аренду.",
        example: "Зарплата сотруднику: каждый 1-й день месяца, 50000 USDT на адрес 0xABCD...1234.",
        steps: [
          "Откройте раздел 'Запланированные'",
          "Нажмите 'Создать автоплатеж'",
          "Укажите получателя и сумму",
          "Выберите дату и время первого платежа",
          "Настройте повторение (ежедневно/еженедельно/ежемесячно)",
          "Подтвердите создание"
        ],
        tips: [
          "Убедитесь, что на кошельке достаточно средств для всех платежей",
          "Проверяйте историю запланированных платежей в разделе 'Отправлены'",
          "Вы можете отменить запланированный платеж до его исполнения"
        ],
        tags: ["автоплатежи", "регулярные"]
      }
    ]
  },
  {
    id: "analytics",
    title: "Аналитика",
    icon: "solar:chart-bold",
    description: "Анализ активности и балансов",
    articles: [
      {
        id: "balance-history",
        title: "История балансов",
        content: "График 'История баланса' показывает изменение общей суммы активов во времени по всем вашим кошелькам.",
        tips: [
          "Выберите период (7/14/30/90 дней) для анализа",
          "Используйте для отслеживания роста/падения активов",
          "Сравнивайте периоды для выявления трендов"
        ],
        tags: ["аналитика", "балансы"]
      },
      {
        id: "transaction-volume",
        title: "Объем транзакций",
        content: "Показывает количество и общую сумму транзакций за выбранный период. Помогает понять интенсивность использования платформы.",
        tips: [
          "Высокий объем может указывать на активный бизнес",
          "Резкие изменения могут сигнализировать о проблемах",
          "Анализируйте по сетям для оптимизации комиссий"
        ],
        tags: ["аналитика", "транзакции"]
      }
    ]
  },
  {
    id: "contacts",
    title: "Адресная книга",
    icon: "solar:user-bold",
    description: "Сохранение часто используемых адресов",
    articles: [
      {
        id: "add-contact",
        title: "Добавление контакта",
        content: "Сохраняйте адреса получателей в адресной книге, чтобы не вводить их каждый раз вручную. Укажите имя и метки для удобного поиска.",
        example: "Имя: 'Поставщик А', Адрес: 0x1234...5678, Метки: поставщик, регулярный.",
        steps: [
          "Откройте 'Адресная книга'",
          "Нажмите 'Добавить контакт'",
          "Введите имя контакта",
          "Вставьте адрес получателя",
          "Добавьте метки (опционально)",
          "Отметьте 'Избранное' для часто используемых",
          "Сохраните контакт"
        ],
        tips: [
          "Проверяйте адреса перед сохранением",
          "Используйте метки для группировки (клиенты, поставщики, сотрудники)",
          "Добавляйте комментарии с дополнительной информацией"
        ],
        tags: ["контакты", "адреса"]
      }
    ]
  },
  {
    id: "audit",
    title: "Журнал аудита",
    icon: "solar:history-bold",
    description: "История всех действий в системе",
    articles: [
      {
        id: "audit-log",
        title: "Что такое журнал аудита?",
        content: "Журнал аудита фиксирует все действия пользователей: создание кошельков, отправку транзакций, подписи, изменения настроек. Это важный инструмент для безопасности и соответствия требованиям.",
        tips: [
          "Регулярно проверяйте журнал на подозрительную активность",
          "Используйте фильтры для поиска конкретных действий",
          "Экспортируйте логи для внешнего анализа или архивирования"
        ],
        tags: ["аудит", "безопасность"]
      }
    ]
  },
  {
    id: "settings",
    title: "Настройки",
    icon: "solar:settings-bold",
    description: "Настройка профиля и безопасности",
    articles: [
      {
        id: "2fa-setup",
        title: "Двухфакторная аутентификация (2FA)",
        content: "2FA добавляет дополнительный уровень защиты вашего аккаунта. При входе потребуется код из мобильного приложения (Google Authenticator, Authy).",
        steps: [
          "Откройте 'Настройки' → 'Безопасность'",
          "Нажмите 'Включить 2FA'",
          "Отсканируйте QR-код в приложении Authenticator",
          "Введите 6-значный код для подтверждения",
          "Сохраните резервные коды в надежном месте",
          "2FA активирована!"
        ],
        tips: [
          "Используйте надежное приложение для 2FA (Google Authenticator, Authy)",
          "Сохраните резервные коды в безопасном месте (не в телефоне!)",
          "Никогда не делитесь кодами 2FA с кем-либо"
        ],
        tags: ["настройки", "2fa", "безопасность"]
      },
      {
        id: "notifications",
        title: "Уведомления",
        content: "Настройте уведомления для важных событий: новые транзакции, запросы подписей, изменения в кошельках.",
        tips: [
          "Включите email-уведомления для транзакций >$10,000",
          "Настройте Telegram-бот для мгновенных уведомлений",
          "Отключите уведомления о незначительных событиях"
        ],
        tags: ["настройки", "уведомления"]
      }
    ]
  }
];

export default function HelpPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<HelpArticle | null>(null);

  // Filter articles by search
  const filteredSections = helpSections.map(section => ({
    ...section,
    articles: section.articles.filter(article =>
      article.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      article.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      article.tags.some(tag => tag.includes(searchQuery.toLowerCase()))
    )
  })).filter(section => section.articles.length > 0 || !searchQuery);

  return (
    <div className={pageLayout.container}>
      <Header
        title="Справка и документация"
      />

      <div className="space-y-4">
        {!selectedArticle ? (
          <>
            {/* Search */}
            <Card className="mb-6">
              <div className="relative">
                <Icon
                  icon="solar:magnifer-linear"
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                />
                <Input
                  type="text"
                  placeholder="Поиск по справке..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </Card>

            {/* Sections Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredSections.map((section) => (
                <Card
                  key={section.id}
                  className="cursor-pointer hover:border-blue-500 dark:hover:border-blue-400 transition-all"
                  onClick={() => setSelectedSection(section.id)}
                >
                  <div className="flex items-start gap-4">
                    <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                      <Icon
                        icon={section.icon}
                        className="text-2xl text-primary"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-foreground mb-1">
                        {section.title}
                      </h3>
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {section.description}
                      </p>
                      <div className="mt-2 text-xs text-primary">
                        {section.articles.length} {section.articles.length === 1 ? 'статья' : 'статей'} →
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            {/* API Documentation */}
            <Card className="mt-6">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                  <Icon
                    icon="solar:code-bold"
                    className="text-2xl text-purple-600 dark:text-purple-400"
                  />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-foreground mb-2">
                    Документация API
                  </h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Интерактивная документация REST API для интеграции и разработки. Полный список эндпоинтов с примерами запросов.
                  </p>
                  <div className="flex flex-wrap gap-3">
                    <a
                      href="/api/docs"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      <Icon icon="solar:document-bold" className="text-lg" />
                      Swagger UI
                    </a>
                    <a
                      href="/api/redoc"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      <Icon icon="solar:book-bold" className="text-lg" />
                      ReDoc
                    </a>
                    <a
                      href="/api/openapi.json"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-slate-600 hover:bg-slate-700 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      <Icon icon="solar:code-square-bold" className="text-lg" />
                      OpenAPI JSON
                    </a>
                  </div>
                </div>
              </div>
            </Card>

            {/* Quick Links */}
            <Card className="mt-6 bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-blue-950/20 dark:to-cyan-950/20">
              <div className="flex items-start gap-4">
                <Icon
                  icon="solar:light-bulb-bold"
                  className="text-3xl text-yellow-600 dark:text-yellow-400"
                />
                <div>
                  <h3 className="font-semibold text-foreground mb-2">
                    Быстрый старт
                  </h3>
                  <p className="text-sm text-muted-foreground mb-3">
                    Новый пользователь? Начните с этих статей:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {helpSections
                      .flatMap(s => s.articles)
                      .filter(a => a.tags.includes('основы') || a.tags.includes('начало'))
                      .slice(0, 3)
                      .map((article) => (
                        <Badge
                          key={article.id}
                          variant="gray"
                          className="cursor-pointer hover:bg-blue-200 dark:hover:bg-blue-800"
                          onClick={() => setSelectedArticle(article)}
                        >
                          {article.title}
                        </Badge>
                      ))}
                  </div>
                </div>
              </div>
            </Card>

            {/* Selected Section Articles */}
            {selectedSection && (
              <div className="mt-6">
                {filteredSections
                  .filter(s => s.id === selectedSection)
                  .map((section) => (
                    <div key={section.id}>
                      <div className="flex items-center gap-3 mb-4">
                        <button
                          onClick={() => setSelectedSection(null)}
                          className="text-muted-foreground hover:text-foreground dark:text-muted-foreground dark:hover:text-white"
                        >
                          <Icon icon="solar:arrow-left-linear" className="text-xl" />
                        </button>
                        <h2 className="text-xl font-bold text-foreground">
                          {section.title}
                        </h2>
                      </div>

                      <div className="space-y-3">
                        {section.articles.map((article) => (
                          <Card
                            key={article.id}
                            className="cursor-pointer hover:border-blue-500 dark:hover:border-blue-400 transition-all"
                            onClick={() => setSelectedArticle(article)}
                          >
                            <h3 className="font-semibold text-foreground mb-2">
                              {article.title}
                            </h3>
                            <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
                              {article.content}
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {article.tags.map((tag) => (
                                <Badge key={tag} variant="gray" className="text-xs">
                                  {tag}
                                </Badge>
                              ))}
                            </div>
                          </Card>
                        ))}
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </>
        ) : (
          /* Article View */
          <div>
            <div className="flex items-center gap-3 mb-6">
              <button
                onClick={() => setSelectedArticle(null)}
                className="text-muted-foreground hover:text-foreground dark:text-muted-foreground dark:hover:text-white"
              >
                <Icon icon="solar:arrow-left-linear" className="text-xl" />
              </button>
              <h2 className="text-2xl font-bold text-foreground">
                {selectedArticle.title}
              </h2>
            </div>

            <Card className="prose dark:prose-invert max-w-none">
              <p className="text-foreground leading-relaxed mb-6">
                {selectedArticle.content}
              </p>

              {selectedArticle.example && (
                <div className="bg-blue-50 dark:bg-blue-950/20 rounded-lg p-4 mb-6">
                  <div className="flex items-start gap-3">
                    <Icon
                      icon="solar:clipboard-text-bold"
                      className="text-xl text-primary mt-0.5"
                    />
                    <div>
                      <div className="font-semibold text-foreground mb-2">
                        Пример:
                      </div>
                      <p className="text-sm text-foreground">
                        {selectedArticle.example}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {selectedArticle.steps && selectedArticle.steps.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-foreground mb-3 flex items-center gap-2">
                    <Icon icon="solar:list-check-bold" className="text-xl text-success" />
                    Пошаговая инструкция:
                  </h3>
                  <ol className="space-y-2 list-none pl-0">
                    {selectedArticle.steps.map((step, idx) => (
                      <li key={idx} className="flex items-start gap-3">
                        <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-primary rounded-full flex items-center justify-center text-sm font-semibold">
                          {idx + 1}
                        </span>
                        <span className="text-foreground flex-1 pt-0.5">
                          {step}
                        </span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {selectedArticle.tips && selectedArticle.tips.length > 0 && (
                <div className="bg-yellow-50 dark:bg-yellow-950/20 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Icon
                      icon="solar:light-bulb-bold"
                      className="text-xl text-yellow-600 dark:text-yellow-400 mt-0.5"
                    />
                    <div>
                      <div className="font-semibold text-foreground mb-2">
                        💡 Полезные советы:
                      </div>
                      <ul className="space-y-1.5 list-none pl-0">
                        {selectedArticle.tips.map((tip, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="text-yellow-600 dark:text-yellow-400 mt-1">•</span>
                            <span className="text-sm text-foreground flex-1">
                              {tip}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              <div className="mt-6 pt-6 border-t border-border flex flex-wrap gap-2">
                {selectedArticle.tags.map((tag) => (
                  <Badge key={tag} variant="gray">
                    {tag}
                  </Badge>
                ))}
              </div>
            </Card>

            {/* Related Articles */}
            <div className="mt-6">
              <h3 className="text-lg font-semibold text-foreground mb-3">
                Связанные статьи
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {helpSections
                  .flatMap(s => s.articles)
                  .filter(a =>
                    a.id !== selectedArticle.id &&
                    a.tags.some(tag => selectedArticle.tags.includes(tag))
                  )
                  .slice(0, 4)
                  .map((article) => (
                    <Card
                      key={article.id}
                      className="cursor-pointer hover:border-blue-500 dark:hover:border-blue-400 transition-all"
                      onClick={() => setSelectedArticle(article)}
                    >
                      <h4 className="font-semibold text-foreground text-sm mb-1">
                        {article.title}
                      </h4>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {article.content}
                      </p>
                    </Card>
                  ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
