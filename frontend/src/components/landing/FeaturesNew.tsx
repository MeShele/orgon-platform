"use client";

import { motion } from 'framer-motion';
import { SafeIcon as Icon } from '@/components/SafeIcon';

const features = [
  {
    icon: 'solar:users-group-two-rounded-linear',
    title: 'Гибкая мультиподпись',
    description: 'Настраивайте логику подтверждения транзакций. Создавайте группы подписантов для разных типов активов (например, 2 из 3 для операционных расходов, 5 из 7 для казначейства).',
    tags: ['Threshold: 3/5', 'Timelock: 24h'],
    className: "lg:col-span-2",
    iconBg: "from-cyan-500/10 to-emerald-500/5",
    iconBorder: "border-cyan-500/20",
    iconColor: "text-cyan-500 dark:text-cyan-400",
  },
  {
    icon: 'solar:smartphone-2-linear',
    title: 'Мобильный контроль',
    description: 'Подписывайте транзакции на ходу. Полнофункциональное PWA приложение работает на любых смартфонах.',
    className: "md:col-span-1",
    iconBg: "from-emerald-500/10 to-teal-500/5",
    iconBorder: "border-emerald-500/20",
    iconColor: "text-emerald-500 dark:text-emerald-400",
  },
  {
    icon: 'solar:list-check-linear',
    title: 'Умные лимиты',
    description: 'Устанавливайте дневные лимиты на вывод средств и создавайте белые списки адресов для автоматического одобрения мелких операций.',
    className: "md:col-span-1",
    iconBg: "from-indigo-500/10 to-slate-500/5",
    iconBorder: "border-indigo-500/20",
    iconColor: "text-indigo-500 dark:text-indigo-400",
  },
  {
    icon: 'solar:clipboard-list-linear',
    title: 'Полный аудит',
    description: 'История действий неизменяема. Экспорт отчетов в CSV/PDF для бухгалтерии и compliance-офицеров в один клик.',
    className: "md:col-span-1",
    iconBg: "from-slate-500/10 to-blue-500/5",
    iconBorder: "border-slate-500/20",
    iconColor: "text-slate-600 dark:text-slate-400",
  },
  {
    icon: 'solar:gas-station-linear',
    title: 'Gas Station',
    description: 'Платите комиссию за транзакции в токенах ERC-20, не беспокоясь о наличии нативного ETH или BNB на балансе.',
    className: "md:col-span-1",
    iconBg: "from-emerald-500/10 to-teal-500/5",
    iconBorder: "border-emerald-500/20",
    iconColor: "text-emerald-500 dark:text-emerald-400",
  },
];

export function Features() {
  return (
    <section id="features" className="py-24 md:py-32 relative bg-slate-50 dark:bg-slate-950">
      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="mb-16 md:w-2/3"
        >
          <h2 className="font-display text-4xl md:text-5xl font-medium text-slate-900 dark:text-white tracking-tight mb-6">
            Единая платформа для <br />
            <span className="text-slate-400">контроля финансов</span>
          </h2>
          <p className="text-slate-600 dark:text-slate-400 text-lg font-light leading-relaxed">
            Забудьте о разрозненных кошельках. ORGON объединяет управление доступом, планирование и безопасность в едином интерфейсе, адаптированном под любые устройства.
          </p>
        </motion.div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className={`${feature.className} group relative overflow-hidden rounded-3xl p-8 md:p-10 border border-slate-200 dark:border-white/5 bg-white/60 dark:bg-white/[0.02] backdrop-blur-sm hover:bg-white/80 dark:hover:bg-white/[0.04] hover:border-slate-300 dark:hover:border-white/10 transition-all duration-300`}
            >
              {/* Large Background Icon (watermark style) */}
              <div className="absolute top-0 right-0 p-10 opacity-[0.03] dark:opacity-[0.08] group-hover:opacity-[0.06] dark:group-hover:opacity-[0.15] transition-opacity transform rotate-12 pointer-events-none">
                <Icon icon={feature.icon} className="text-slate-900 dark:text-white" style={{ fontSize: '240px' }} />
              </div>

              {/* Content */}
              <div className="relative z-10 h-full flex flex-col">
                {/* Icon */}
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.iconBg} border ${feature.iconBorder} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                  <Icon icon={feature.icon} className={`text-2xl ${feature.iconColor}`} />
                </div>

                {/* Title */}
                <h3 className="text-2xl md:text-3xl text-slate-900 dark:text-white font-medium mb-4 tracking-tight">
                  {feature.title}
                </h3>

                {/* Description */}
                <p className="text-slate-600 dark:text-slate-400 font-light leading-relaxed text-base md:text-lg mb-6 flex-1">
                  {feature.description}
                </p>

                {/* Tags (if exists) */}
                {feature.tags && (
                  <div className="flex gap-3 flex-wrap">
                    {feature.tags.map((tag, i) => (
                      <span
                        key={i}
                        className="px-3 py-1 rounded-full bg-slate-100 dark:bg-white/10 border border-slate-200 dark:border-white/5 text-xs font-mono text-slate-600 dark:text-slate-300"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          ))}

        </div>
      </div>
    </section>
  );
}
