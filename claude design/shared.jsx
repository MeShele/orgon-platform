// Shared utilities, mock data, and UI atoms for ORGON redesign

// ───────────────── Mock data ─────────────────
const MOCK = {
  user: { name: 'Айдар Бекбоев', email: 'demo-admin@orgon.io', role: 'Admin' },
  org: { name: 'Demo Exchange', license: 'Business', members: 14 },
  kpis: {
    totalBalance: { ru: '₽ 248 174 902', en: '$ 2 894 412', sub: '+1.84% / 24h' },
    wallets: { value: '11', sub: '8 multi-sig · 3 hot' },
    tx24: { value: '142', sub: '$ 18.4M volume' },
    pending: { value: '7', sub: '4 awaiting you' },
    networks: { value: '4', sub: 'TRX · BSC · ETH · POL' },
  },
  wallets: [
    { name: 'Treasury Cold', net: 'BTC', threshold: '3/5', balance: '12.482 BTC', usd: '$ 1 184 920', pct: '+0.4%' },
    { name: 'Operating EUR', net: 'ETH', threshold: '2/3', balance: '482.09 ETH', usd: '$ 1 412 408', pct: '+1.8%' },
    { name: 'Settlement TRX', net: 'TRX', threshold: '2/3', balance: '8 412 902 TRX', usd: '$ 1 092 877', pct: '−0.2%' },
    { name: 'Hot Wallet 01', net: 'BSC', threshold: '1/1', balance: '184 002 BNB', usd: '$ 78 920', pct: '+2.1%' },
    { name: 'Compliance Reserve', net: 'POL', threshold: '4/6', balance: '2.1M POL', usd: '$ 248 740', pct: '−0.4%' },
    { name: 'Client Float', net: 'USDT', threshold: '2/3', balance: '1 482 920 USDT', usd: '$ 1 482 920', pct: '+0.0%' },
  ],
  txs: [
    { hash: '0x4f2a…b81c', wallet: 'Treasury Cold', to: 'TWmh8N…aLpQ', token: 'BTC', amount: '0.482', usd: '$ 45 720', status: 'pending', sigs: '2/5', time: '14:02:18' },
    { hash: '0xa182…7f3d', wallet: 'Operating EUR', to: '0x842c…91Ee', token: 'ETH', amount: '12.4', usd: '$ 36 290', status: 'confirmed', sigs: '3/3', time: '13:48:01' },
    { hash: '0xc7e1…2104', wallet: 'Settlement TRX', to: 'TXn8aP…kQ91', token: 'USDT', amount: '184 200', usd: '$ 184 200', status: 'sent', sigs: '2/3', time: '13:32:44' },
    { hash: '0x9b32…5e44', wallet: 'Hot Wallet 01', to: '0x1c4e…77Aa', token: 'BNB', amount: '4.18', usd: '$ 2 408', status: 'rejected', sigs: '1/1', time: '13:18:09' },
    { hash: '0x21d8…f0b2', wallet: 'Client Float', to: '0xee82…3a17', token: 'USDT', amount: '50 000', usd: '$ 50 000', status: 'pending', sigs: '1/3', time: '12:51:40' },
    { hash: '0x4a02…91ca', wallet: 'Treasury Cold', to: '1A1zP1…iVmF', token: 'BTC', amount: '0.084', usd: '$ 7 880', status: 'confirmed', sigs: '4/5', time: '12:22:18' },
    { hash: '0x77fe…482b', wallet: 'Compliance Reserve', to: '0x4a02…1bb1', token: 'POL', amount: '120 000', usd: '$ 14 400', status: 'confirmed', sigs: '4/6', time: '11:48:02' },
  ],
  signers: [
    { name: 'Айдар Бекбоев', initials: 'АБ', role: 'CFO', state: 'signed', time: '14:02:18' },
    { name: 'Дина Сагынбаева', initials: 'ДС', role: 'CEO', state: 'signed', time: '14:04:51' },
    { name: 'Тимур Орозалиев', initials: 'ТО', role: 'COO', state: 'pending', time: null },
    { name: 'Алия Жунусова', initials: 'АЖ', role: 'CTO', state: 'pending', time: null },
    { name: 'Нурбек Иманов', initials: 'НИ', role: 'CRO', state: 'pending', time: null },
  ],
  // Plans (KGS prices per ТЗ)
  plans: [
    { id: 'start', name: 'Start', priceMo: '50 000', priceYr: '540 000', txs: '500', wallets: '5', users: '5', sla: '99.5%' },
    { id: 'business', name: 'Business', priceMo: '100 000', priceYr: '1 080 000', txs: '5 000', wallets: '50', users: '20', sla: '99.9%', popular: true },
    { id: 'enterprise', name: 'Enterprise', priceMo: '200 000', priceYr: '2 160 000', txs: '∞', wallets: '∞', users: '∞', sla: '99.99%' },
  ],
};

// ───────────────── i18n strings ─────────────────
const I18N = {
  ru: {
    // header
    nav: ['Платформа', 'Возможности', 'Тарифы', 'Документация', 'О компании'],
    login: 'Войти', start: 'Начать',
    // hero
    eyebrow: 'Институциональное хранение криптоактивов',
    heroTitle: 'Совместная подпись\nкорпоративного капитала',
    heroSub: 'ORGON — multi-signature кастоди для бирж, брокеров и банков. M-of-N подписи, регулируемый KYC/AML, белый-лейбл и B2B API.',
    heroPrimary: 'Запросить демо',
    heroSecondary: 'Смотреть тарифы',
    trustedBy: 'НАМ ДОВЕРЯЮТ',
    // pillars
    pillarTitle: 'Три столпа платформы',
    pillars: [
      { tag: '01 / Кастоди', title: 'Multi-signature', body: 'Пороги M-of-N, аппаратные ключи, географическое распределение подписантов.' },
      { tag: '02 / Compliance', title: 'KYC · KYB · AML', body: 'Регулируемые потоки идентификации, очередь ревью, AML-алерты в реальном времени.' },
      { tag: '03 / Интеграции', title: 'Белый-лейбл и API', body: 'Полный B2B API, webhooks, on/off-ramp фиата, кастомный брендинг под партнёра.' },
    ],
    // dashboard
    dashboard: 'Дашборд',
    totalBalance: 'Общий баланс',
    walletsLabel: 'Кошельки',
    tx24: 'Транзакции, 24ч',
    pending: 'Ожидают подписи',
    networks: 'Сети',
    recent: 'Последние транзакции',
    alerts: 'Уведомления',
    // wallet
    walletDetail: 'Детали кошелька',
    threshold: 'Порог подписей',
    members: 'Подписанты',
    tokens: 'Токены',
    history: 'История',
    signers: 'Подписанты',
    awaitingSig: 'Ожидает подписи',
    sign: 'Подписать', reject: 'Отклонить',
    // pricing
    pricingTitle: 'Тарифы для команд любого масштаба',
    pricingSub: 'Прозрачное ценообразование в KGS. Меняйте план в любой момент.',
    monthly: 'Ежемесячно', yearly: 'Ежегодно', save: '−10%',
    perMonth: '/мес', perYear: '/год',
    contactSales: 'Связаться с отделом продаж',
    selectPlan: 'Выбрать план',
    txLimit: 'Транзакций / мес', walletLimit: 'Кошельков', userLimit: 'Пользователей', sla: 'SLA',
    // login
    loginTitle: 'Вход в ORGON',
    email: 'Электронная почта', password: 'Пароль', forgot: 'Забыли пароль?',
    twofa: 'Введите код 2FA',
    demoTitle: 'Демо-аккаунты',
    demoAdmin: 'Admin · полный доступ',
    demoSigner: 'Signer · подписание',
    demoViewer: 'Viewer · только просмотр',
    // tx list
    transactions: 'Транзакции',
    status: 'Статус', amount: 'Сумма', wallet: 'Кошелёк', destination: 'Получатель', token: 'Токен', sigsCol: 'Подписи', time: 'Время',
    confirmed: 'подтверждена', pendingS: 'в обработке', sent: 'отправлена', rejected: 'отклонена',
    // common
    copy: 'Копировать',
  },
  en: {
    nav: ['Platform', 'Features', 'Pricing', 'Docs', 'About'],
    login: 'Sign in', start: 'Get started',
    eyebrow: 'Institutional crypto custody',
    heroTitle: 'Co-signing\ncorporate capital',
    heroSub: 'ORGON is multi-signature custody for exchanges, brokers and banks. M-of-N approvals, regulated KYC/AML, white-label and B2B API.',
    heroPrimary: 'Request a demo',
    heroSecondary: 'See pricing',
    trustedBy: 'TRUSTED BY',
    pillarTitle: 'Three pillars of the platform',
    pillars: [
      { tag: '01 / Custody', title: 'Multi-signature', body: 'M-of-N thresholds, hardware keys, geographically distributed signers.' },
      { tag: '02 / Compliance', title: 'KYC · KYB · AML', body: 'Regulated identity flows, review queue, real-time AML alerts.' },
      { tag: '03 / Integrations', title: 'White-label and API', body: 'Full B2B API, webhooks, fiat on/off-ramp, partner-branded UI.' },
    ],
    dashboard: 'Dashboard',
    totalBalance: 'Total balance',
    walletsLabel: 'Wallets',
    tx24: 'Transactions, 24h',
    pending: 'Awaiting signatures',
    networks: 'Networks',
    recent: 'Recent transactions',
    alerts: 'Alerts',
    walletDetail: 'Wallet detail',
    threshold: 'Signature threshold',
    members: 'Members',
    tokens: 'Tokens',
    history: 'History',
    signers: 'Signers',
    awaitingSig: 'Awaiting signature',
    sign: 'Sign', reject: 'Reject',
    pricingTitle: 'Pricing for teams of any scale',
    pricingSub: 'Transparent pricing in KGS. Change your plan any time.',
    monthly: 'Monthly', yearly: 'Yearly', save: '−10%',
    perMonth: '/mo', perYear: '/yr',
    contactSales: 'Contact sales',
    selectPlan: 'Select plan',
    txLimit: 'Transactions / mo', walletLimit: 'Wallets', userLimit: 'Users', sla: 'SLA',
    loginTitle: 'Sign in to ORGON',
    email: 'Email', password: 'Password', forgot: 'Forgot password?',
    twofa: 'Enter 2FA code',
    demoTitle: 'Demo accounts',
    demoAdmin: 'Admin · full access',
    demoSigner: 'Signer · approvals',
    demoViewer: 'Viewer · read-only',
    transactions: 'Transactions',
    status: 'Status', amount: 'Amount', wallet: 'Wallet', destination: 'Destination', token: 'Token', sigsCol: 'Sigs', time: 'Time',
    confirmed: 'confirmed', pendingS: 'pending', sent: 'sent', rejected: 'rejected',
    copy: 'Copy',
  },
};

// Hook to get current language from window
function useLang() {
  const [lang, setLang] = React.useState(window.__orgonLang || 'ru');
  React.useEffect(() => {
    const handler = (e) => setLang(e.detail);
    window.addEventListener('orgon-lang', handler);
    return () => window.removeEventListener('orgon-lang', handler);
  }, []);
  return I18N[lang] || I18N.ru;
}

// ───────────────── Tiny SVG primitives ─────────────────

// Network graph: 5 nodes around a center. signed = filled with accent, pending = ring only.
function NetworkGraph({ signers, accent, muted, fg, size = 220, signedFill, ringColor }) {
  const cx = size / 2, cy = size / 2, r = size * 0.36;
  const nodes = signers.map((s, i) => {
    const angle = (i / signers.length) * Math.PI * 2 - Math.PI / 2;
    return { ...s, x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r };
  });
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ display: 'block' }}>
      {/* edges to center */}
      {nodes.map((n, i) => (
        <line key={'e' + i} x1={cx} y1={cy} x2={n.x} y2={n.y}
          stroke={n.state === 'signed' ? accent : muted} strokeWidth={n.state === 'signed' ? 1.2 : 0.6}
          strokeDasharray={n.state === 'signed' ? '0' : '2 3'} />
      ))}
      {/* center hub */}
      <circle cx={cx} cy={cy} r={size * 0.06} fill={fg} />
      <circle cx={cx} cy={cy} r={size * 0.10} fill="none" stroke={muted} strokeWidth="0.5" />
      {/* nodes */}
      {nodes.map((n, i) => (
        <g key={'n' + i}>
          <circle cx={n.x} cy={n.y} r={size * 0.085}
            fill={n.state === 'signed' ? (signedFill || accent) : 'transparent'}
            stroke={n.state === 'signed' ? accent : (ringColor || muted)} strokeWidth="1.2" />
          <text x={n.x} y={n.y + 3} textAnchor="middle" fontSize={size * 0.06}
            fontFamily="ui-monospace, monospace" fontWeight="600"
            fill={n.state === 'signed' ? '#fff' : fg}>{n.initials}</text>
        </g>
      ))}
    </svg>
  );
}

// Sparkline
function Sparkline({ points = [], stroke, fill, width = 100, height = 32, strokeWidth = 1.2 }) {
  if (!points.length) points = [4, 6, 5, 7, 6, 8, 7, 9, 8, 10, 11, 10, 12, 11, 13];
  const min = Math.min(...points), max = Math.max(...points);
  const range = max - min || 1;
  const step = width / (points.length - 1);
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${i * step} ${height - ((p - min) / range) * height}`).join(' ');
  const area = path + ` L ${width} ${height} L 0 ${height} Z`;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: 'block' }}>
      {fill && <path d={area} fill={fill} />}
      <path d={path} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

// Tx flow schematic — wallet → router → destination
function TxFlow({ accent, muted, fg, width = 320, height = 80 }) {
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: 'block' }}>
      <defs>
        <pattern id="dotgrid" width="8" height="8" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="0.6" fill={muted} opacity="0.5" />
        </pattern>
      </defs>
      <rect x="0" y="0" width={width} height={height} fill="url(#dotgrid)" opacity="0.4" />
      {/* wallet */}
      <rect x="10" y={height/2 - 16} width="68" height="32" fill="none" stroke={fg} strokeWidth="0.8" />
      <text x="44" y={height/2 + 4} textAnchor="middle" fontSize="9" fontFamily="ui-monospace, monospace" fill={fg}>WALLET</text>
      {/* line */}
      <line x1="78" y1={height/2} x2="140" y2={height/2} stroke={accent} strokeWidth="1.2" />
      <circle cx="140" cy={height/2} r="3" fill={accent} />
      {/* hub */}
      <circle cx={width/2} cy={height/2} r="14" fill="none" stroke={accent} strokeWidth="1" />
      <text x={width/2} y={height/2 + 3} textAnchor="middle" fontSize="8" fontFamily="ui-monospace, monospace" fill={accent}>2/3</text>
      <line x1={width/2 + 14} y1={height/2} x2={width - 88} y2={height/2} stroke={accent} strokeWidth="1.2" strokeDasharray="3 2" />
      {/* destination */}
      <rect x={width - 78} y={height/2 - 16} width="68" height="32" fill={fg} />
      <text x={width - 44} y={height/2 + 4} textAnchor="middle" fontSize="9" fontFamily="ui-monospace, monospace" fill="#fff">CHAIN</text>
    </svg>
  );
}

// Big number with tabular-nums
function BigNum({ children, color, size = 32, weight = 500 }) {
  return (
    <div style={{ fontVariantNumeric: 'tabular-nums', fontFeatureSettings: '"tnum"', fontSize: size, fontWeight: weight, color, letterSpacing: '-0.02em', lineHeight: 1.05 }}>
      {children}
    </div>
  );
}

// Mono address (truncated)
function Mono({ children, color, size = 11, weight = 400 }) {
  return (
    <span style={{ fontFamily: 'ui-monospace, "SF Mono", Menlo, Monaco, Consolas, monospace', fontSize: size, color, fontWeight: weight, letterSpacing: '-0.01em' }}>
      {children}
    </span>
  );
}

// expose
Object.assign(window, { MOCK, I18N, useLang, NetworkGraph, Sparkline, TxFlow, BigNum, Mono });
