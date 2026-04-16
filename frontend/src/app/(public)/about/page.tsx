"use client";

import { SafeIcon as Icon } from '@/components/SafeIcon';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { motion } from 'framer-motion';

const values = [
  {
    icon: 'solar:shield-check-bold',
    title: 'Безопасность прежде всего',
    description: 'Мы используем лучшие практики индустрии для защиты ваших активов: банковское шифрование, мультиподпись и полный аудит.',
    color: 'cyan',
    gradient: 'from-cyan-500/10 to-emerald-500/10',
  },
  {
    icon: 'solar:eye-bold',
    title: 'Прозрачность',
    description: 'Каждое действие логируется и доступно для проверки. Вы всегда знаете, кто, что и когда делал.',
    color: 'teal',
    gradient: 'from-teal-500/10 to-cyan-500/10',
  },
  {
    icon: 'solar:user-check-bold',
    title: 'Простота использования',
    description: 'Мощные функции не должны быть сложными. Мы создали интуитивный интерфейс, понятный каждому.',
    color: 'emerald',
    gradient: 'from-emerald-500/10 to-teal-500/10',
  },
  {
    icon: 'solar:rocket-2-bold',
    title: 'Инновации',
    description: 'Мы постоянно развиваемся, добавляя новые функции и улучшая существующие на основе обратной связи пользователей.',
    color: 'orange',
    gradient: 'from-orange-500/10 to-amber-500/10',
  },
];

const timeline = [
  { year: '2024', event: 'Основание ASYSTEM', description: 'Запуск технологической компании' },
  { year: '2025', event: 'Разработка ORGON', description: 'Создание платформы управления активами' },
  { year: '2026', event: 'Production Launch', description: 'Выход на рынок' },
];

export default function AboutPage() {
  return (
    <div className="py-24 bg-slate-50 dark:bg-slate-950 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-b from-cyan-500/5 via-transparent to-emerald-500/5 pointer-events-none z-0" />
      <motion.div
        animate={{
          scale: [1, 1.1, 1],
          opacity: [0.2, 0.35, 0.2],
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: "easeInOut"
        }}
        className="absolute top-1/4 right-1/4 w-96 h-96 bg-gradient-to-r from-cyan-400/15 to-emerald-400/15 rounded-full blur-3xl z-[1]"
      />

      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 relative z-[20]">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-display font-bold text-slate-900 dark:text-white mb-6 tracking-tight">
            О{' '}
            <span className="bg-gradient-to-r from-cyan-500 via-emerald-500 to-teal-500 bg-clip-text text-transparent">
              ORGON
            </span>
          </h1>
          <p className="text-xl text-slate-600 dark:text-slate-400 font-light">
            Корпоративное решение для управления криптоактивами от ASYSTEM
          </p>
        </motion.div>

        {/* Mission */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="mb-24 relative"
        >
          <div className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200 dark:border-white/10 rounded-3xl p-10 md:p-12">
            <div className="flex items-start gap-4 mb-6">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-cyan-500/10 to-emerald-500/10 flex items-center justify-center flex-shrink-0">
                <Icon icon="solar:target-bold" className="text-3xl text-cyan-600 dark:text-cyan-400" />
              </div>
              <h2 className="text-3xl sm:text-4xl font-display font-bold text-slate-900 dark:text-white">
                Наша миссия
              </h2>
            </div>
            <p className="text-lg text-slate-600 dark:text-slate-400 leading-relaxed mb-6">
              ORGON создан для того, чтобы предоставить организациям, командам и частным лицам 
              инструменты корпоративного уровня для безопасного управления криптовалютными активами.
            </p>
            <p className="text-lg text-slate-600 dark:text-slate-400 leading-relaxed">
              Мы верим, что безопасность не должна быть сложной. ORGON делает мультиподписные 
              кошельки простыми в использовании, предоставляя при этом максимальный контроль 
              и прозрачность.
            </p>
          </div>
        </motion.div>

        {/* Values */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="mb-24"
        >
          <h2 className="text-3xl sm:text-4xl font-display font-bold text-slate-900 dark:text-white mb-12 text-center">
            Наши ценности
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {values.map((value, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                whileHover={{ scale: 1.02 }}
                className="p-8 rounded-2xl border border-slate-200 dark:border-white/10 bg-white/60 dark:bg-white/[0.02] backdrop-blur-sm hover:border-slate-300 dark:hover:border-white/20 transition-all group"
              >
                <div className={`inline-flex items-center justify-center w-14 h-14 rounded-xl bg-gradient-to-br ${value.gradient} border border-white/10 mb-5 group-hover:scale-110 transition-transform`}>
                  <Icon icon={value.icon} className="text-3xl text-slate-900 dark:text-white" />
                </div>
                <h3 className="text-xl font-semibold text-slate-900 dark:text-white mb-3">
                  {value.title}
                </h3>
                <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
                  {value.description}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Timeline */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="mb-24"
        >
          <h2 className="text-3xl sm:text-4xl font-display font-bold text-slate-900 dark:text-white mb-12 text-center">
            История развития
          </h2>
          <div className="relative">
            {/* Timeline Line */}
            <div className="absolute left-8 top-0 bottom-0 w-px bg-gradient-to-b from-cyan-500 via-emerald-500 to-teal-500" />
            
            <div className="space-y-8">
              {timeline.map((item, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.2 }}
                  className="relative pl-20"
                >
                  {/* Year Badge */}
                  <div className="absolute left-0 w-16 h-16 rounded-xl bg-gradient-to-br from-cyan-500 to-emerald-600 flex items-center justify-center text-white font-bold text-lg shadow-lg">
                    {item.year}
                  </div>
                  
                  {/* Content */}
                  <div className="bg-white/60 dark:bg-white/[0.02] backdrop-blur-sm border border-slate-200 dark:border-white/10 rounded-xl p-6">
                    <h3 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">
                      {item.event}
                    </h3>
                    <p className="text-slate-600 dark:text-slate-400">
                      {item.description}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* ASYSTEM */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="mb-24 relative"
        >
          <div className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200 dark:border-white/10 rounded-3xl p-10 md:p-12">
            <div className="flex items-start gap-4 mb-6">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-emerald-500/10 to-teal-500/10 flex items-center justify-center flex-shrink-0">
                <Icon icon="solar:programming-bold" className="text-3xl text-emerald-600 dark:text-emerald-400" />
              </div>
              <h2 className="text-3xl sm:text-4xl font-display font-bold text-slate-900 dark:text-white">
                ASYSTEM
              </h2>
            </div>
            <p className="text-lg text-slate-600 dark:text-slate-400 leading-relaxed mb-6">
              ORGON разработан компанией ASYSTEM — технологической компанией, специализирующейся 
              на создании решений для управления криптовалютами и блокчейн-технологиями.
            </p>
            <p className="text-lg text-slate-600 dark:text-slate-400 leading-relaxed mb-8">
              Мы работаем над тем, чтобы сделать криптовалюты более доступными и безопасными 
              для всех — от частных пользователей до крупных организаций.
            </p>
            <a
              href="https://asystem.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-cyan-600 dark:text-cyan-400 hover:underline text-lg font-medium group"
            >
              <span>Узнать больше о ASYSTEM</span>
              <Icon icon="solar:arrow-right-up-linear" className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
            </a>
          </div>
        </motion.div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="relative"
        >
          {/* Background Gradient */}
          <div className="absolute inset-0 bg-gradient-to-r from-cyan-500 to-emerald-500 rounded-3xl blur-2xl opacity-20" />
          
          <div className="relative text-center p-10 md:p-16 rounded-3xl bg-gradient-to-br from-cyan-500 to-emerald-600 overflow-hidden">
            {/* Decorative Elements */}
            <motion.div
              animate={{
                scale: [1, 1.2, 1],
                opacity: [0.2, 0.3, 0.2],
              }}
              transition={{
                duration: 6,
                repeat: Infinity,
                ease: "easeInOut"
              }}
              className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl"
            />
            
            <div className="relative z-10">
              <h2 className="text-3xl sm:text-4xl md:text-5xl font-display font-bold text-white mb-4">
                Присоединяйтесь к ORGON
              </h2>
              <p className="text-lg md:text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
                Начните управлять своими активами безопасно уже сегодня
              </p>
              <Link href="/register">
                <Button
                  size="lg"
                  className="bg-white text-cyan-600 hover:bg-cyan-50 px-12 py-6 text-lg font-semibold shadow-xl hover:shadow-2xl transition-all"
                >
                  Создать бесплатный аккаунт
                  <Icon icon="solar:arrow-right-linear" className="ml-2" />
                </Button>
              </Link>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
