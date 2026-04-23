"use client";

import Link from 'next/link';
import { SafeIcon } from '@/components/SafeIcon';
import { motion } from 'framer-motion';

export function CTA() {
  return (
    <section className="relative py-32 overflow-hidden bg-slate-900 dark:bg-slate-950">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-cyan-900/10 to-transparent pointer-events-none" />
      <div className="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg%20viewBox%3D%220%200%20256%20256%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cfilter%20id%3D%22n%22%3E%3CfeTurbulence%20type%3D%22fractalNoise%22%20baseFrequency%3D%220.7%22%20numOctaves%3D%224%22%20stitchTiles%3D%22stitch%22%2F%3E%3C%2Ffilter%3E%3Crect%20width%3D%22100%25%22%20height%3D%22100%25%22%20filter%3D%22url(%23n)%22%2F%3E%3C%2Fsvg%3E')] opacity-10" />
      
      {/* Animated Gradient Orbs - Modern Palette */}
      <motion.div
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.2, 0.35, 0.2],
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: "easeInOut"
        }}
        className="absolute top-1/4 left-1/4 w-96 h-96 bg-gradient-to-r from-cyan-500/20 via-emerald-500/20 to-teal-500/20 rounded-full blur-3xl"
      />
      <motion.div
        animate={{
          scale: [1.2, 1, 1.2],
          opacity: [0.15, 0.3, 0.15],
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: "easeInOut"
        }}
        className="absolute bottom-1/4 right-1/4 w-[32rem] h-[32rem] bg-gradient-to-l from-slate-400/15 via-cyan-500/15 to-emerald-500/20 rounded-full blur-3xl"
      />

      <div className="max-w-4xl mx-auto px-6 text-center relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="font-display text-4xl md:text-6xl font-medium text-white mb-6 tracking-tight">
            Готовы усилить защиту?
          </h2>
          <p className="text-slate-300 text-lg font-light mb-10 max-w-2xl mx-auto leading-relaxed">
            Создайте учетную запись за 2 минуты. Без кредитной карты, с полным доступом к тестовой сети.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-6"
        >
          {/* Primary Button */}
          <Link
            href="/register"
            className="w-full sm:w-auto px-10 py-4 bg-white text-slate-900 rounded-xl text-sm font-bold tracking-wide hover:bg-slate-100 transition-all shadow-xl shadow-white/10 hover:shadow-white/20 hover:scale-105"
          >
            Создать аккаунт
          </Link>

          {/* Secondary Link */}
          <Link
            href="#contact"
            className="text-slate-300 hover:text-white font-medium text-sm flex items-center gap-2 transition-colors group"
          >
            Связаться с отделом продаж
            <SafeIcon icon="solar:arrow-right-linear" className="group-hover:translate-x-1 transition-transform" />
          </Link>
        </motion.div>

        {/* Trust Indicators */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mt-12 flex flex-wrap items-center justify-center gap-6 text-sm text-slate-400"
        >
          <div className="flex items-center gap-2">
            <SafeIcon icon="solar:shield-check-bold" className="text-emerald-400" />
            <span>SOC2 сертификация</span>
          </div>
          <div className="flex items-center gap-2">
            <SafeIcon icon="solar:clock-circle-bold" className="text-blue-400" />
            <span>24/7 поддержка</span>
          </div>
          <div className="flex items-center gap-2">
            <SafeIcon icon="solar:verified-check-bold" className="text-cyan-400" />
            <span>Без привязки карты</span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
