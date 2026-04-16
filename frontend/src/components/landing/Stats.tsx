"use client";

import { motion, useInView } from 'framer-motion';
import { SafeIcon } from '@/components/SafeIcon';
import { useRef, useEffect, useState } from 'react';

const stats = [
  {
    icon: 'solar:wallet-bold',
    value: '$500M+',
    label: 'Объем транзакций',
    color: 'blue',
  },
  {
    icon: 'solar:clock-circle-bold',
    value: '24/7',
    label: 'Поддержка',
    color: 'slate',
  },
  {
    icon: 'solar:bolt-circle-bold',
    value: '0.0s',
    label: 'Задержка подписи',
    color: 'cyan',
  },
  {
    icon: 'solar:shield-check-bold',
    value: 'ISO',
    label: 'Сертификация',
    color: 'emerald',
  },
];

function AnimatedCounter({ value, inView }: { value: string; inView: boolean }) {
  const [count, setCount] = useState(0);
  const hasPercentage = value.includes('%');
  const hasPlus = value.includes('+');
  const hasDollar = value.includes('$');
  const hasM = value.includes('M');
  const hasSlash = value.includes('/');
  const hasS = value.includes('s');
  const isISO = value === 'ISO';
  
  // If it's a special string, return as is
  if (hasSlash || isISO) {
    return <span>{value}</span>;
  }
  
  const numericValue = parseFloat(value.replace(/[^0-9.]/g, ''));
  
  useEffect(() => {
    if (!inView) return;
    
    let start = 0;
    const end = numericValue;
    const duration = 2000;
    const increment = end / (duration / 16);
    
    const timer = setInterval(() => {
      start += increment;
      if (start >= end) {
        setCount(end);
        clearInterval(timer);
      } else {
        setCount(start);
      }
    }, 16);
    
    return () => clearInterval(timer);
  }, [inView, numericValue]);
  
  const displayValue = hasPercentage 
    ? count.toFixed(1) 
    : hasM 
    ? count.toFixed(0)
    : count.toFixed(1);
  
  return (
    <span>
      {hasDollar && '$'}
      {displayValue}
      {hasM && 'M'}
      {hasPlus && '+'}
      {hasPercentage && '%'}
      {hasS && 's'}
    </span>
  );
}

export function Stats() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section className="border-y border-slate-200 dark:border-white/5 bg-white dark:bg-slate-950">
      <div ref={ref} className="max-w-7xl mx-auto px-6 grid grid-cols-2 lg:grid-cols-4 divide-x divide-slate-200 dark:divide-white/5">
        {stats.map((stat, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            className="py-10 px-6 text-center group hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-colors cursor-pointer"
          >
            {/* Icon with subtle gradient */}
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500/10 to-emerald-500/5 border border-cyan-500/20 mb-4 group-hover:border-cyan-500/40 transition-all">
              <SafeIcon icon={stat.icon} className="text-2xl text-cyan-600 dark:text-cyan-400" />
            </div>
            
            {/* Value */}
            <div className="text-3xl lg:text-5xl font-display font-semibold text-slate-900 dark:text-white mb-2 tracking-tight group-hover:text-cyan-600 dark:group-hover:text-cyan-400 transition-colors">
              <AnimatedCounter value={stat.value} inView={inView} />
            </div>
            
            {/* Label */}
            <div className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-widest font-semibold">
              {stat.label}
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
