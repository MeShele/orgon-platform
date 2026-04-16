"use client";

import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { SafeIcon as Icon } from '@/components/SafeIcon';
import { motion } from 'framer-motion';

export function Hero() {
  return (
    <section className="relative mx-6 sm:mx-auto max-w-7xl mt-28 mb-12 sm:p-8 bg-gradient-to-br from-slate-900/95 to-slate-950/95 w-auto bg-cover border border-white/10 rounded-3xl pt-10 pr-8 pb-10 pl-8 backdrop-blur overflow-hidden shadow-2xl min-h-[600px] flex items-center">
      
      {/* Background Image Overlay */}
      <div 
        className="absolute inset-0 z-0 rounded-3xl opacity-15"
        style={{
          backgroundImage: 'url(https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1600&q=80)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      />
      
      {/* Gradient Overlays */}
      <div className="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-transparent to-slate-900/40 pointer-events-none z-[1] rounded-3xl" />
      
      {/* Animated Background Orbs - Updated Modern Palette */}
      <motion.div
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.15, 0.25, 0.15],
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: "easeInOut"
        }}
        className="absolute top-0 right-0 w-[500px] h-[500px] bg-gradient-to-br from-cyan-400/20 via-emerald-400/15 to-slate-400/20 rounded-full blur-3xl z-[2]"
      />
      
      <motion.div
        animate={{
          scale: [1.2, 1, 1.2],
          opacity: [0.1, 0.2, 0.1],
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: "easeInOut"
        }}
        className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-gradient-to-tl from-slate-400/15 via-cyan-400/15 to-emerald-400/20 rounded-full blur-3xl z-[2]"
      />
      
      {/* Large "ORGON" Watermark */}
      <div 
        aria-hidden="true" 
        className="pointer-events-none select-none absolute bottom-0 -left-10 z-[3] opacity-100"
        style={{ letterSpacing: '-0.02em' }}
      >
        <span 
          className="block leading-none font-display font-bold text-white/[0.03]"
          style={{
            fontSize: 'min(20vw, 220px)',
            lineHeight: '0.8'
          }}
        >
          ORGON
        </span>
      </div>

      {/* Content Grid */}
      <div className="relative w-full grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16 items-start z-[10]">
        
        {/* Left Column: Headline (7 cols) */}
        <div className="lg:col-span-7">
          {/* Badge with Animated Pulse */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 text-xs font-medium tracking-wide uppercase mb-6 backdrop-blur-md"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
            </span>
            Корпоративная безопасность 3.0
          </motion.div>

          {/* Main Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-[40px] sm:text-5xl md:text-7xl leading-[1.05] font-display font-bold text-white tracking-tight mb-6"
          >
            Управление активами без компромиссов
          </motion.h1>
        </div>

        {/* Right Column: Description + CTAs (5 cols) */}
        <div className="lg:col-span-5 pt-4">
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="sm:text-lg text-base text-slate-300 max-w-[42ch] leading-relaxed font-light mb-8"
          >
            ORGON — это экосистема для безопасного хранения и управления цифровыми активами. 
            Мультиподпись, настраиваемые политики доступа и полная прозрачность операций.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="flex flex-wrap gap-4 items-center"
          >
            {/* Primary Modern Gradient Button */}
            <Link 
              href="/register"
              className="group relative inline-flex items-center justify-center overflow-hidden rounded-xl"
              style={{
                backgroundImage: 'linear-gradient(135deg, #06b6d4, #10b981 50%, #14b8a6)',
                padding: '2px',
                minWidth: '200px',
                height: '54px',
              }}
            >
              <span 
                className="relative z-10 w-full h-full flex items-center justify-center gap-2 rounded-[10px] px-7 font-semibold text-white transition-all duration-300"
                style={{ background: 'rgb(5, 6, 45)' }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'transparent'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'rgb(5, 6, 45)'}
              >
                Начать бесплатно
              </span>
            </Link>

            {/* Secondary Glass Button */}
            <Link
              href="/demo"
              className="group inline-flex items-center justify-center gap-2 px-7 h-[54px] rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm text-white font-medium hover:bg-white/10 hover:border-white/20 transition-all"
            >
              Демо доступ
              <Icon icon="solar:arrow-right-linear" className="group-hover:translate-x-1 transition-transform" />
            </Link>
          </motion.div>

          {/* Trust Indicators (optional) */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.8 }}
            className="mt-8 flex flex-wrap items-center gap-4 text-xs text-slate-400"
          >
            <div className="flex items-center gap-2">
              <Icon icon="solar:shield-check-bold" className="text-emerald-400" />
              <span>Банковское шифрование</span>
            </div>
            <div className="flex items-center gap-2">
              <Icon icon="solar:verified-check-bold" className="text-cyan-400" />
              <span>SOC2 сертификация</span>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
