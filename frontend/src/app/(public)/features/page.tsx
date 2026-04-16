"use client";

import { SafeIcon as Icon } from '@/components/SafeIcon';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { motion } from 'framer-motion';

const features = [
  {
    icon: 'solar:shield-network-bold',
    title: 'Мультиподписная безопасность',
    description: 'Требуйте несколько подтверждений для каждой транзакции. Настраиваемые пороги (2-из-3, 3-из-5, etc). Исключите единую точку отказа.',
    details: [
      'Настраиваемые пороги подписей',
      'Поддержка до 20 подписантов',
      'Иерархические права доступа',
      'Аппаратные кошельки (Ledger, Trezor)',
    ],
    gradient: 'from-blue-500 to-cyan-500',
    iconBg: 'from-blue-500/10 to-cyan-500/10',
  },
  {
    icon: 'solar:calendar-mark-bold',
    title: 'Планирование транзакций',
    description: 'Запланируйте регулярные платежи и автоматические переводы. Настройте повторяющиеся операции с уверенностью.',
    details: [
      'Cron-выражения для гибкого планирования',
      'Повторяющиеся платежи (ежедневно, еженедельно, ежемесячно)',
      'Отложенное исполнение транзакций',
      'Автоматическая отмена просроченных задач',
    ],
    gradient: 'from-teal-500 to-cyan-500',
    iconBg: 'from-teal-500/10 to-cyan-500/10',
  },
  {
    icon: 'solar:chart-2-bold',
    title: 'Аналитика в реальном времени',
    description: 'Отслеживайте производительность кошельков, мониторьте историю транзакций и генерируйте пользовательские отчеты.',
    details: [
      'Графики баланса и объема транзакций',
      'Статистика по подписям',
      'Распределение токенов',
      'Экспорт данных в CSV/JSON',
    ],
    gradient: 'from-emerald-500 to-teal-500',
    iconBg: 'from-emerald-500/10 to-teal-500/10',
  },
  {
    icon: 'solar:book-2-bold',
    title: 'Адресная книга',
    description: 'Сохраняйте проверенные контакты, организуйте частых получателей и уменьшайте ошибки с верифицированными адресами.',
    details: [
      'Быстрый доступ к частым получателям',
      'Метки и категории контактов',
      'Проверка адресов перед отправкой',
      'Импорт/экспорт контактов',
    ],
    gradient: 'from-orange-500 to-amber-500',
    iconBg: 'from-orange-500/10 to-amber-500/10',
  },
  {
    icon: 'solar:document-text-bold',
    title: 'Комплексный журнал аудита',
    description: 'Отслеживайте каждое действие, смотрите кто что одобрил и экспортируйте данные для соответствия требованиям.',
    details: [
      'Полная история всех действий',
      'Фильтрация по пользователям и типам событий',
      'Временные метки с точностью до секунды',
      'Неизменяемый журнал для соответствия требованиям',
    ],
    gradient: 'from-slate-500 to-cyan-500',
    iconBg: 'from-slate-500/10 to-cyan-500/10',
  },
  {
    icon: 'solar:global-bold',
    title: 'Поддержка сетей',
    description: 'Интеграция с Safina Pay, кросс-чейн совместимость и быстрые надежные транзакции.',
    details: [
      'Safina Pay интеграция',
      'Поддержка EVM-совместимых сетей',
      'Кросс-чейн переводы',
      'Автоматическое определение комиссий',
    ],
    gradient: 'from-cyan-500 to-blue-500',
    iconBg: 'from-cyan-500/10 to-blue-500/10',
  },
];

export default function FeaturesPage() {
  return (
    <div className="py-24 bg-slate-50 dark:bg-slate-950 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-blue-500/5 to-transparent pointer-events-none z-0" />
      
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative z-[20]">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-display font-bold text-slate-900 dark:text-white mb-6 tracking-tight">
            Возможности{' '}
            <span className="bg-gradient-to-r from-cyan-500 via-emerald-500 to-teal-500 bg-clip-text text-transparent">
              ORGON
            </span>
          </h1>
          <p className="mx-auto max-w-2xl text-xl text-slate-600 dark:text-slate-400 font-light leading-relaxed">
            Все инструменты для профессионального управления криптоактивами в одном месте
          </p>
        </motion.div>

        {/* Features List */}
        <div className="space-y-24">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className={`flex flex-col ${
                index % 2 === 0 ? 'lg:flex-row' : 'lg:flex-row-reverse'
              } gap-12 items-center`}
            >
              {/* Content */}
              <div className="lg:w-1/2 space-y-6">
                {/* Icon */}
                <div className={`inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br ${feature.iconBg} border border-white/10 backdrop-blur-sm`}>
                  <Icon icon={feature.icon} className="text-4xl text-slate-900 dark:text-white" />
                </div>
                
                {/* Title */}
                <h2 className="text-3xl sm:text-4xl font-display font-bold text-slate-900 dark:text-white">
                  {feature.title}
                </h2>
                
                {/* Description */}
                <p className="text-lg text-slate-600 dark:text-slate-400 leading-relaxed">
                  {feature.description}
                </p>
                
                {/* Details List */}
                <ul className="space-y-3">
                  {feature.details.map((detail, i) => (
                    <motion.li
                      key={i}
                      initial={{ opacity: 0, x: -20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.4, delay: i * 0.1 }}
                      className="flex items-start gap-3"
                    >
                      <Icon
                        icon="solar:check-circle-bold"
                        className="text-emerald-500 mt-1 flex-shrink-0 text-xl"
                      />
                      <span className="text-slate-700 dark:text-slate-300">{detail}</span>
                    </motion.li>
                  ))}
                </ul>
              </div>

              {/* Illustration */}
              <div className="lg:w-1/2">
                <motion.div
                  whileHover={{ scale: 1.02 }}
                  transition={{ duration: 0.3 }}
                  className="relative rounded-3xl border border-slate-200 dark:border-white/10 bg-white/60 dark:bg-white/[0.02] backdrop-blur-sm p-12 flex items-center justify-center aspect-video overflow-hidden group"
                >
                  {/* Background Gradient */}
                  <div className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-5 group-hover:opacity-10 transition-opacity`} />
                  
                  {/* Icon */}
                  <Icon
                    icon={feature.icon}
                    className="text-[12rem] text-slate-200 dark:text-slate-800 relative z-10 group-hover:scale-110 transition-transform duration-500"
                  />
                  
                  {/* Decorative Elements */}
                  <div className="absolute top-4 right-4 w-24 h-24 bg-gradient-to-br from-cyan-500/20 to-emerald-500/20 rounded-full blur-2xl" />
                  <div className="absolute bottom-4 left-4 w-32 h-32 bg-gradient-to-tl from-emerald-500/20 to-teal-500/20 rounded-full blur-2xl" />
                </motion.div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* CTA Section */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="mt-32 text-center relative"
        >
          {/* Background */}
          <div className="absolute inset-0 bg-gradient-to-r from-cyan-500 to-emerald-500 rounded-3xl blur-3xl opacity-10" />
          
          <div className="relative bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200 dark:border-white/10 rounded-3xl p-12 md:p-16">
            <h2 className="text-4xl md:text-5xl font-display font-bold text-slate-900 dark:text-white mb-6">
              Готовы начать?
            </h2>
            <p className="text-xl text-slate-600 dark:text-slate-400 mb-10 max-w-2xl mx-auto">
              Создайте бесплатный аккаунт и начните управлять своими активами безопасно
            </p>
            <Link href="/register">
              <Button variant="primary" size="lg" className="px-12 py-6 text-lg font-semibold">
                Начать бесплатно
                <Icon icon="solar:arrow-right-linear" className="ml-2" />
              </Button>
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
