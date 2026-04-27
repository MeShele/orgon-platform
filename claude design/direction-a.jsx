// Direction A — "Crimson Ledger" — institutional, banking-grade.
// Light = primary (clean white paper, crimson used sparingly).
// Dark = midnight navy from the logo + bolder crimson play.

const A_LIGHT = {
  bg: '#ffffff',
  surface: '#fafaf9',
  surface2: '#f3f2ef',
  border: '#e6e4df',
  borderStrong: '#cbc8c1',
  fg: '#0e1320',         // ink with a navy whisper
  fgMuted: '#5a5e6a',
  fgFaint: '#8a8d96',
  accent: '#b81e2f',     // crimson (logo)
  accentSoft: '#fbe8ea',
  accentDeep: '#7a1320',
  positive: '#2e6f3b',
  negative: '#b81e2f',
  pending: '#a86a00',
  card: '#ffffff',
  navy: '#0a1428',       // logo navy — used for accents/blocks in light
};
const A_DARK = {
  bg: '#070d1a',         // logo navy, slightly deeper
  surface: '#0e1830',
  surface2: '#142142',
  border: '#1f2c4d',
  borderStrong: '#2e3d65',
  fg: '#eef2f8',
  fgMuted: '#9aa3b8',
  fgFaint: '#5e6886',
  accent: '#e23b50',     // crimson, brighter on navy
  accentSoft: '#3d0f15',
  accentDeep: '#ff5d72',
  positive: '#5fbf78',
  negative: '#e23b50',
  pending: '#e0a040',
  card: '#0e1830',
  navy: '#070d1a',
};

const A_FONT_DISPLAY = '"IBM Plex Sans", "IBM Plex Sans Display", -apple-system, sans-serif';
const A_FONT_SANS = 'Inter, -apple-system, sans-serif';
const A_FONT_MONO = '"IBM Plex Mono", ui-monospace, monospace';

function ABase({ T, children, w = 1280, h = 800, padding = 0 }) {
  return (
    <div style={{
      width: w, height: h, background: T.bg, color: T.fg, fontFamily: A_FONT_SANS,
      overflow: 'hidden', position: 'relative', padding, boxSizing: 'border-box',
      fontFeatureSettings: '"ss01", "cv11"',
    }}>{children}</div>
  );
}

// Wordmark — concentric ring (logo abstraction) + ASYSTEM·ORGON typography
function AWordmark({ T, size = 18, full = false }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <svg width={size + 4} height={size + 4} viewBox="0 0 28 28">
        <circle cx="14" cy="14" r="12" fill="none" stroke={T.accent} strokeWidth="1.5"/>
        <circle cx="14" cy="14" r="7.5" fill="none" stroke={T.accent} strokeWidth="1.5"/>
        <circle cx="14" cy="14" r="2.2" fill={T.accent}/>
        <circle cx="22" cy="9" r="0.9" fill={T.accent}/>
        <circle cx="6" cy="18" r="0.7" fill={T.accent}/>
      </svg>
      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1 }}>
        <span style={{ fontFamily: A_FONT_DISPLAY, fontWeight: 600, fontSize: size, letterSpacing: '0.06em', color: T.fg }}>
          {full ? 'ASYSTEM' : 'ORGON'}
        </span>
        {full && <span style={{ fontFamily: A_FONT_DISPLAY, fontWeight: 400, fontSize: size * 0.55, letterSpacing: '0.18em', color: T.fgMuted, marginTop: 3 }}>ORGON</span>}
      </div>
    </div>
  );
}

// Public header
function APubHeader({ T, t }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 56px', borderBottom: `1px solid ${T.border}` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 56 }}>
        <AWordmark T={T} size={18} full/>
        <div style={{ display: 'flex', gap: 28 }}>
          {t.nav.map((n, i) => (
            <span key={i} style={{ fontSize: 13, color: i === 2 ? T.fg : T.fgMuted, fontWeight: i === 2 ? 500 : 400 }}>{n}</span>
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <span style={{ fontSize: 13, color: T.fgMuted }}>{t.login}</span>
        <button style={{ background: T.fg, color: T.bg, border: 'none', padding: '9px 18px', fontSize: 13, fontWeight: 500, fontFamily: A_FONT_SANS, cursor: 'pointer', borderRadius: 0 }}>{t.start} →</button>
      </div>
    </div>
  );
}

// ───────── HERO ─────────
function AHero({ theme = 'light' }) {
  const T = theme === 'dark' ? A_DARK : A_LIGHT;
  const t = useLang();
  return (
    <ABase T={T}>
      <APubHeader T={T} t={t}/>
      <div style={{ padding: '56px 56px 0', display: 'grid', gridTemplateColumns: '1.15fr 0.85fr', gap: 48 }}>
        <div>
          <div style={{ fontFamily: A_FONT_MONO, fontSize: 11, letterSpacing: '0.12em', color: T.accent, textTransform: 'uppercase', marginBottom: 28 }}>
            ─── {t.eyebrow}
          </div>
          <h1 style={{ fontFamily: A_FONT_DISPLAY, fontWeight: 500, fontSize: 76, lineHeight: 1.0, letterSpacing: '-0.035em', margin: 0, whiteSpace: 'pre-line', color: T.fg }}>
            {t.heroTitle}
          </h1>
          <p style={{ fontSize: 16, lineHeight: 1.55, color: T.fgMuted, marginTop: 28, maxWidth: 480 }}>
            {t.heroSub}
          </p>
          <div style={{ display: 'flex', gap: 12, marginTop: 36 }}>
            <button style={{ background: T.accent, color: '#fff', border: 'none', padding: '14px 24px', fontSize: 14, fontWeight: 500, fontFamily: A_FONT_SANS, cursor: 'pointer' }}>{t.heroPrimary} →</button>
            <button style={{ background: 'transparent', color: T.fg, border: `1px solid ${T.borderStrong}`, padding: '14px 24px', fontSize: 14, fontWeight: 500, fontFamily: A_FONT_SANS, cursor: 'pointer' }}>{t.heroSecondary}</button>
          </div>
          <div style={{ marginTop: 56, paddingTop: 28, borderTop: `1px solid ${T.border}` }}>
            <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.18em', color: T.fgFaint, marginBottom: 16 }}>{t.trustedBy}</div>
            <div style={{ display: 'flex', gap: 32, alignItems: 'center', color: T.fgMuted, fontFamily: A_FONT_DISPLAY, fontWeight: 500, fontSize: 15, letterSpacing: '0.04em' }}>
              <span>SAFINA·PAY</span><span>DEMIR</span><span>BAKAI</span><span>FREEDOM</span><span>OPTIMA</span>
            </div>
          </div>
        </div>
        {/* Network graph hero visual — stronger frame */}
        <div style={{ background: theme === 'dark' ? T.surface : T.navy, color: '#fff', padding: 28, position: 'relative' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
            <div>
              <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.12em', color: 'rgba(255,255,255,0.55)', textTransform: 'uppercase' }}>WALLET · TREASURY-COLD</div>
              <div style={{ fontFamily: A_FONT_MONO, fontSize: 11, color: 'rgba(255,255,255,0.85)', marginTop: 4 }}>0x4f2a··b81c</div>
            </div>
            <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, padding: '4px 8px', background: T.accent, color: '#fff', letterSpacing: '0.08em' }}>2 / 5 SIGNED</div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', padding: '16px 0' }}>
            <NetworkGraph signers={MOCK.signers} accent={T.accent} muted="rgba(255,255,255,0.25)" fg="#fff" signedFill={T.accent} ringColor="rgba(255,255,255,0.35)" size={280}/>
          </div>
          <div style={{ borderTop: '1px solid rgba(255,255,255,0.12)', paddingTop: 12, marginTop: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: A_FONT_MONO, fontSize: 10, color: 'rgba(255,255,255,0.55)' }}>
              <span>AMOUNT</span>
              <span style={{ color: '#fff' }}>0.482 BTC · $45 720</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: A_FONT_MONO, fontSize: 10, color: 'rgba(255,255,255,0.55)', marginTop: 4 }}>
              <span>DESTINATION</span>
              <span style={{ color: '#fff' }}>TWmh8N··aLpQ</span>
            </div>
          </div>
        </div>
      </div>
    </ABase>
  );
}

// ───────── DASHBOARD ─────────
function ADashboard({ theme = 'light' }) {
  const T = theme === 'dark' ? A_DARK : A_LIGHT;
  const t = useLang();
  return (
    <ABase T={T} h={860}>
      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', height: '100%' }}>
        <div style={{ background: T.surface2, borderRight: `1px solid ${T.border}`, padding: '20px 16px', display: 'flex', flexDirection: 'column' }}>
          <AWordmark T={T} size={15} full/>
          <div style={{ marginTop: 28, fontFamily: A_FONT_MONO, fontSize: 9, letterSpacing: '0.16em', color: T.fgFaint }}>WORKSPACE</div>
          {[['Дашборд', true], ['Кошельки'], ['Транзакции'], ['Подписи · 4'], ['Расписание'], ['Контакты']].map(([n, active], i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 8px', marginTop: 2, fontSize: 13, color: active ? T.fg : T.fgMuted, background: active ? T.surface : 'transparent', borderLeft: active ? `2px solid ${T.accent}` : '2px solid transparent', fontWeight: active ? 500 : 400 }}>
              <span style={{ width: 4, height: 4, background: active ? T.accent : T.fgFaint, borderRadius: '50%' }}/>{n}
            </div>
          ))}
          <div style={{ marginTop: 24, fontFamily: A_FONT_MONO, fontSize: 9, letterSpacing: '0.16em', color: T.fgFaint }}>ОРГАНИЗАЦИЯ</div>
          {['Организации', 'Биллинг', 'Compliance'].map((n, i) => (
            <div key={i} style={{ padding: '7px 8px', marginTop: 2, fontSize: 13, color: T.fgMuted }}>{n}</div>
          ))}
          <div style={{ marginTop: 'auto', padding: 12, background: T.surface, border: `1px solid ${T.border}` }}>
            <div style={{ fontSize: 11, color: T.fgMuted }}>{MOCK.org.name}</div>
            <div style={{ fontFamily: A_FONT_MONO, fontSize: 9, color: T.accent, marginTop: 4, letterSpacing: '0.1em' }}>{MOCK.org.license.toUpperCase()}</div>
          </div>
        </div>
        <div style={{ overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 32px', borderBottom: `1px solid ${T.border}`, background: T.bg }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <span style={{ fontFamily: A_FONT_DISPLAY, fontSize: 18, fontWeight: 500 }}>{t.dashboard}</span>
              <span style={{ fontFamily: A_FONT_MONO, fontSize: 11, color: T.fgMuted }}>27.04.2026 · 14:08 GMT+6</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ padding: '6px 12px', border: `1px solid ${T.border}`, fontFamily: A_FONT_MONO, fontSize: 11, color: T.fgMuted, minWidth: 200 }}>⌘K · поиск</div>
              <div style={{ width: 28, height: 28, borderRadius: '50%', background: T.accent, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 600 }}>АБ</div>
            </div>
          </div>
          <div style={{ padding: 32, display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 1, background: T.border, border: `1px solid ${T.border}`, margin: 32 }}>
            {[
              { label: t.totalBalance, val: '$ 4 894 412', sub: '+1.84% / 24ч', big: true },
              { label: t.walletsLabel, val: '11', sub: MOCK.kpis.wallets.sub },
              { label: t.tx24, val: '142', sub: MOCK.kpis.tx24.sub },
              { label: t.pending, val: '7', sub: MOCK.kpis.pending.sub, accent: true },
              { label: t.networks, val: '4', sub: 'TRX·BSC·ETH·POL' },
            ].map((kpi, i) => (
              <div key={i} style={{ background: T.surface, padding: '20px 18px' }}>
                <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.12em', color: T.fgFaint, textTransform: 'uppercase' }}>{kpi.label}</div>
                <BigNum color={kpi.accent ? T.accent : T.fg} size={kpi.big ? 28 : 26} weight={500}>{kpi.val}</BigNum>
                <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, color: T.fgMuted, marginTop: 6 }}>{kpi.sub}</div>
              </div>
            ))}
          </div>
          <div style={{ padding: '0 32px 32px', display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 16 }}>
            <div style={{ background: T.surface, border: `1px solid ${T.border}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 18px', borderBottom: `1px solid ${T.border}` }}>
                <span style={{ fontFamily: A_FONT_DISPLAY, fontWeight: 500, fontSize: 14 }}>{t.recent}</span>
                <span style={{ fontFamily: A_FONT_MONO, fontSize: 10, color: T.fgMuted }}>142 · 24ч</span>
              </div>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ fontFamily: A_FONT_MONO, fontSize: 9, letterSpacing: '0.1em', color: T.fgFaint, textTransform: 'uppercase' }}>
                    <th style={{ textAlign: 'left', padding: '8px 18px' }}>{t.status}</th>
                    <th style={{ textAlign: 'left', padding: '8px 8px' }}>{t.wallet}</th>
                    <th style={{ textAlign: 'right', padding: '8px 8px' }}>{t.amount}</th>
                    <th style={{ textAlign: 'right', padding: '8px 8px' }}>{t.sigsCol}</th>
                    <th style={{ textAlign: 'right', padding: '8px 18px' }}>{t.time}</th>
                  </tr>
                </thead>
                <tbody>
                  {MOCK.txs.slice(0, 6).map((tx, i) => {
                    const stColor = { confirmed: T.positive, pending: T.pending, sent: T.fg, rejected: T.negative }[tx.status];
                    return (
                      <tr key={i} style={{ borderTop: `1px solid ${T.border}` }}>
                        <td style={{ padding: '10px 18px' }}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: A_FONT_MONO, fontSize: 10, color: stColor, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                            <span style={{ width: 6, height: 6, background: stColor, borderRadius: tx.status === 'pending' ? 0 : '50%' }}/>
                            {t[tx.status === 'pending' ? 'pendingS' : tx.status]}
                          </span>
                        </td>
                        <td style={{ padding: '10px 8px', color: T.fg }}>{tx.wallet}</td>
                        <td style={{ padding: '10px 8px', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}><span style={{ color: T.fg }}>{tx.amount}</span> <span style={{ color: T.fgMuted }}>{tx.token}</span></td>
                        <td style={{ padding: '10px 8px', textAlign: 'right' }}><Mono color={T.fgMuted}>{tx.sigs}</Mono></td>
                        <td style={{ padding: '10px 18px', textAlign: 'right' }}><Mono color={T.fgFaint}>{tx.time}</Mono></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ background: T.surface, border: `1px solid ${T.border}`, padding: 18 }}>
                <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.1em', color: T.fgFaint, textTransform: 'uppercase' }}>BALANCE · 30D</div>
                <BigNum color={T.fg} size={26}>$ 4 894 412</BigNum>
                <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, color: T.positive }}>+ $ 184 288 (+3.92%)</div>
                <div style={{ marginTop: 10 }}>
                  <Sparkline points={[6,7,5,8,7,9,8,10,9,11,10,12,11,13,12,14,13,15,14,16,15,17,18,17,19]} stroke={T.accent} fill={`${T.accent}1a`} width={340} height={80}/>
                </div>
              </div>
              <div style={{ background: T.surface, border: `1px solid ${T.border}`, padding: 16 }}>
                <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.1em', color: T.fgFaint, textTransform: 'uppercase', marginBottom: 10 }}>{t.alerts}</div>
                {[
                  { sev: 'high', text: 'AML алерт · Wallet «Client Float»' },
                  { sev: 'med', text: '4 транзакции ждут вашей подписи' },
                  { sev: 'low', text: 'Новый member в Demo Exchange' },
                ].map((a, i) => (
                  <div key={i} style={{ display: 'flex', gap: 10, padding: '8px 0', borderTop: i ? `1px solid ${T.border}` : 'none', alignItems: 'center' }}>
                    <span style={{ width: 6, height: 6, background: a.sev === 'high' ? T.accent : a.sev === 'med' ? T.pending : T.fgFaint, borderRadius: '50%' }}/>
                    <span style={{ fontSize: 12, color: T.fg }}>{a.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </ABase>
  );
}

// ───────── WALLET DETAIL ─────────
function AWalletDetail({ theme = 'light' }) {
  const T = theme === 'dark' ? A_DARK : A_LIGHT;
  const t = useLang();
  return (
    <ABase T={T} h={860}>
      <div style={{ padding: '24px 56px', borderBottom: `1px solid ${T.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.12em', color: T.fgFaint, textTransform: 'uppercase' }}>WALLETS / TREASURY-COLD</div>
          <div style={{ fontFamily: A_FONT_DISPLAY, fontSize: 28, fontWeight: 500, marginTop: 4 }}>Treasury Cold <span style={{ color: T.fgMuted, fontSize: 16, marginLeft: 8 }}>BTC · 3-of-5</span></div>
          <div style={{ marginTop: 6 }}><Mono color={T.fgMuted} size={12}>bc1qx7··kwm9 — bitcoin mainnet</Mono></div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button style={{ padding: '10px 16px', background: 'transparent', border: `1px solid ${T.borderStrong}`, fontSize: 13, color: T.fg, cursor: 'pointer' }}>Получить</button>
          <button style={{ padding: '10px 16px', background: T.accent, color: '#fff', border: 'none', fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>Отправить →</button>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, background: T.border }}>
        {[
          { label: 'BALANCE', val: '12.482 BTC', sub: '$ 1 184 920 · +0.4%' },
          { label: '30D VOLUME', val: '$ 482 100', sub: '12 транзакций' },
        ].map((kpi, i) => (
          <div key={i} style={{ background: T.bg, padding: '20px 56px' }}>
            <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.12em', color: T.fgFaint }}>{kpi.label}</div>
            <BigNum color={T.fg} size={32}>{kpi.val}</BigNum>
            <div style={{ fontFamily: A_FONT_MONO, fontSize: 11, color: T.fgMuted }}>{kpi.sub}</div>
          </div>
        ))}
      </div>
      <div style={{ padding: '32px 56px', display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 32 }}>
        <div style={{ background: T.surface, border: `1px solid ${T.border}` }}>
          <div style={{ padding: '16px 20px', borderBottom: `1px solid ${T.border}`, display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontFamily: A_FONT_DISPLAY, fontWeight: 500, fontSize: 14 }}>{t.awaitingSig}</span>
            <span style={{ fontFamily: A_FONT_MONO, fontSize: 10, padding: '3px 8px', background: T.accent, color: '#fff', letterSpacing: '0.08em' }}>2 / 5 SIGNED</span>
          </div>
          <div style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <div>
                <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, color: T.fgFaint, letterSpacing: '0.1em' }}>OUTGOING · BTC</div>
                <BigNum color={T.fg} size={32}>0.482 BTC</BigNum>
                <div style={{ fontFamily: A_FONT_MONO, fontSize: 11, color: T.fgMuted }}>≈ $ 45 720</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, color: T.fgFaint, letterSpacing: '0.1em' }}>TO</div>
                <Mono color={T.fg} size={13}>TWmh8N··aLpQ</Mono>
                <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, color: T.fgMuted, marginTop: 2 }}>Tron mainnet</div>
              </div>
            </div>
            <div style={{ marginTop: 24, padding: '20px 0', borderTop: `1px solid ${T.border}` }}>
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <NetworkGraph signers={MOCK.signers} accent={T.accent} muted={T.borderStrong} fg={T.fg} signedFill={T.accent} ringColor={T.borderStrong} size={220}/>
              </div>
              <div style={{ marginTop: 16 }}>
                {MOCK.signers.map((s, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderTop: i ? `1px solid ${T.border}` : 'none' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ width: 22, height: 22, background: s.state === 'signed' ? T.accent : 'transparent', border: `1px solid ${s.state === 'signed' ? T.accent : T.borderStrong}`, color: s.state === 'signed' ? '#fff' : T.fg, fontFamily: A_FONT_MONO, fontSize: 9, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600 }}>{s.initials}</div>
                      <span style={{ fontSize: 12, color: T.fg }}>{s.name}</span>
                      <span style={{ fontFamily: A_FONT_MONO, fontSize: 10, color: T.fgFaint }}>· {s.role}</span>
                    </div>
                    <Mono color={s.state === 'signed' ? T.positive : T.fgFaint} size={10}>{s.state === 'signed' ? `✓ ${s.time}` : 'AWAITING'}</Mono>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button style={{ flex: 1, padding: '12px', background: T.accent, color: '#fff', border: 'none', fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>{t.sign}</button>
              <button style={{ flex: 1, padding: '12px', background: 'transparent', color: T.fg, border: `1px solid ${T.borderStrong}`, fontSize: 13, cursor: 'pointer' }}>{t.reject}</button>
            </div>
          </div>
        </div>
        <div>
          <div style={{ fontFamily: A_FONT_DISPLAY, fontSize: 14, fontWeight: 500, marginBottom: 12 }}>{t.tokens}</div>
          <div style={{ background: T.surface, border: `1px solid ${T.border}` }}>
            {[
              { sym: 'BTC', name: 'Bitcoin', bal: '12.482', usd: '1 184 920', spark: [10, 12, 11, 13, 14, 13, 15, 16, 15, 17] },
              { sym: 'USDT', name: 'Tether (TRC-20)', bal: '184 200', usd: '184 200', spark: [10, 10, 10, 10, 10, 10, 10, 10, 10, 10] },
              { sym: 'ETH', name: 'Ethereum', bal: '4.812', usd: '14 102', spark: [12, 11, 10, 9, 11, 12, 14, 13, 14, 15] },
              { sym: 'POL', name: 'Polygon', bal: '120 000', usd: '14 400', spark: [14, 13, 12, 11, 10, 11, 10, 9, 10, 9] },
            ].map((tok, i) => (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 80px 1fr', gap: 12, padding: '14px 16px', borderTop: i ? `1px solid ${T.border}` : 'none', alignItems: 'center' }}>
                <div>
                  <div style={{ fontFamily: A_FONT_DISPLAY, fontWeight: 500, fontSize: 13 }}>{tok.sym}</div>
                  <div style={{ fontSize: 11, color: T.fgMuted }}>{tok.name}</div>
                </div>
                <Sparkline points={tok.spark} stroke={T.accent} width={80} height={20}/>
                <div style={{ textAlign: 'right' }}>
                  <BigNum color={T.fg} size={14}>{tok.bal}</BigNum>
                  <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, color: T.fgMuted }}>$ {tok.usd}</div>
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 24, fontFamily: A_FONT_DISPLAY, fontSize: 14, fontWeight: 500, marginBottom: 12 }}>Схема</div>
          <div style={{ background: T.surface, border: `1px solid ${T.border}`, padding: 12 }}>
            <TxFlow accent={T.accent} muted={T.borderStrong} fg={T.fg} width={460} height={90}/>
          </div>
        </div>
      </div>
    </ABase>
  );
}

// ───────── PRICING ─────────
function APricing({ theme = 'light' }) {
  const T = theme === 'dark' ? A_DARK : A_LIGHT;
  const t = useLang();
  const [yearly, setYearly] = React.useState(false);
  return (
    <ABase T={T} h={1100}>
      <APubHeader T={T} t={t}/>
      <div style={{ padding: '64px 56px 24px', textAlign: 'center' }}>
        <div style={{ fontFamily: A_FONT_MONO, fontSize: 11, letterSpacing: '0.12em', color: T.accent, textTransform: 'uppercase' }}>─── ТАРИФЫ</div>
        <h2 style={{ fontFamily: A_FONT_DISPLAY, fontSize: 56, fontWeight: 500, letterSpacing: '-0.03em', margin: '20px 0 12px', lineHeight: 1.05 }}>{t.pricingTitle}</h2>
        <p style={{ color: T.fgMuted, fontSize: 15, maxWidth: 560, margin: '0 auto' }}>{t.pricingSub}</p>
        <div style={{ display: 'inline-flex', marginTop: 28, border: `1px solid ${T.borderStrong}`, padding: 3 }}>
          {[t.monthly, t.yearly].map((label, i) => (
            <button key={i} onClick={() => setYearly(i === 1)} style={{ padding: '8px 20px', background: (yearly ? 1 : 0) === i ? T.fg : 'transparent', color: (yearly ? 1 : 0) === i ? T.bg : T.fg, border: 'none', fontSize: 13, fontWeight: 500, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
              {label} {i === 1 && <span style={{ fontFamily: A_FONT_MONO, fontSize: 10, color: (yearly ? 1 : 0) === i ? T.bg : T.accent }}>{t.save}</span>}
            </button>
          ))}
        </div>
      </div>
      <div style={{ padding: '32px 56px', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 1, background: T.border, margin: '0 56px', border: `1px solid ${T.border}` }}>
        {MOCK.plans.map((p, i) => {
          const featured = p.popular;
          return (
            <div key={i} style={{ background: featured ? (theme === 'dark' ? T.surface2 : T.navy) : T.surface, color: featured ? '#fff' : T.fg, padding: 32, position: 'relative' }}>
              {featured && <div style={{ position: 'absolute', top: 16, right: 16, fontFamily: A_FONT_MONO, fontSize: 9, letterSpacing: '0.16em', color: T.accent, padding: '4px 8px', border: `1px solid ${T.accent}` }}>ПОПУЛЯРНЫЙ</div>}
              <div style={{ fontFamily: A_FONT_MONO, fontSize: 11, letterSpacing: '0.12em', color: T.accent }}>0{i+1} / {p.name.toUpperCase()}</div>
              <div style={{ fontFamily: A_FONT_DISPLAY, fontSize: 32, fontWeight: 500, marginTop: 24, letterSpacing: '-0.02em' }}>{p.name}</div>
              <div style={{ marginTop: 20, display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <BigNum color={featured ? '#fff' : T.fg} size={48} weight={500}>{yearly ? p.priceYr : p.priceMo}</BigNum>
                <span style={{ fontFamily: A_FONT_MONO, fontSize: 12, color: featured ? 'rgba(255,255,255,0.6)' : T.fgMuted }}>KGS</span>
              </div>
              <div style={{ fontFamily: A_FONT_MONO, fontSize: 11, color: featured ? 'rgba(255,255,255,0.6)' : T.fgMuted, marginTop: 4 }}>{yearly ? t.perYear : t.perMonth}</div>
              <button style={{ width: '100%', marginTop: 28, padding: '14px', background: featured ? T.accent : 'transparent', color: featured ? '#fff' : T.fg, border: featured ? 'none' : `1px solid ${T.borderStrong}`, fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>
                {p.id === 'enterprise' ? t.contactSales + ' →' : t.selectPlan + ' →'}
              </button>
              <div style={{ marginTop: 32, paddingTop: 20, borderTop: `1px solid ${featured ? 'rgba(255,255,255,0.15)' : T.border}` }}>
                {[[t.txLimit, p.txs], [t.walletLimit, p.wallets], [t.userLimit, p.users], [t.sla, p.sla]].map(([k, v], j) => (
                  <div key={j} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', fontSize: 12, borderTop: j ? `1px solid ${featured ? 'rgba(255,255,255,0.15)' : T.border}` : 'none' }}>
                    <span style={{ color: featured ? 'rgba(255,255,255,0.65)' : T.fgMuted }}>{k}</span>
                    <span style={{ fontVariantNumeric: 'tabular-nums', fontFamily: A_FONT_MONO }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ margin: '32px 56px', background: T.surface, border: `1px solid ${T.border}` }}>
        <div style={{ padding: '14px 20px', borderBottom: `1px solid ${T.border}`, fontFamily: A_FONT_DISPLAY, fontWeight: 500, fontSize: 14, display: 'flex', justifyContent: 'space-between' }}>
          <span>Сравнить возможности</span>
          <span style={{ fontFamily: A_FONT_MONO, fontSize: 11, color: T.fgMuted }}>52 функции в 5 группах</span>
        </div>
        {[
          ['Custody', 'Multi-sig 2-of-3', '✓', '✓', '✓'],
          ['Custody', 'Multi-sig до 7-of-15', '—', '✓', '✓'],
          ['Compliance', 'KYC поток', '✓', '✓', '✓'],
          ['Compliance', 'KYB для юрлиц', '—', '✓', '✓'],
          ['Integrations', 'Webhooks', '5/мес', '∞', '∞'],
          ['Support', 'SLA', '99.5%', '99.9%', '99.99%'],
        ].map((row, i) => (
          <div key={i} style={{ display: 'grid', gridTemplateColumns: '120px 1fr 100px 100px 100px', padding: '12px 20px', borderTop: `1px solid ${T.border}`, fontSize: 12, alignItems: 'center' }}>
            <span style={{ fontFamily: A_FONT_MONO, fontSize: 10, color: T.fgFaint, letterSpacing: '0.06em', textTransform: 'uppercase' }}>{row[0]}</span>
            <span style={{ color: T.fg }}>{row[1]}</span>
            <span style={{ textAlign: 'center', fontFamily: A_FONT_MONO, color: row[2] === '—' ? T.fgFaint : T.fg }}>{row[2]}</span>
            <span style={{ textAlign: 'center', fontFamily: A_FONT_MONO, color: row[3] === '—' ? T.fgFaint : T.accent, fontWeight: 600 }}>{row[3]}</span>
            <span style={{ textAlign: 'center', fontFamily: A_FONT_MONO, color: row[4] === '—' ? T.fgFaint : T.fg }}>{row[4]}</span>
          </div>
        ))}
      </div>
    </ABase>
  );
}

// ───────── LOGIN ─────────
function ALogin({ theme = 'light' }) {
  const T = theme === 'dark' ? A_DARK : A_LIGHT;
  const t = useLang();
  return (
    <ABase T={T} h={800}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', height: '100%' }}>
        {/* Left: navy block always — references logo */}
        <div style={{ background: T.navy, color: '#fff', padding: 56, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', position: 'relative', overflow: 'hidden' }}>
          <AWordmark T={{ ...T, fg: '#fff', fgMuted: 'rgba(255,255,255,0.6)', accent: T.accent }} size={20} full/>
          {/* decorative concentric ring */}
          <svg width="380" height="380" viewBox="0 0 380 380" style={{ position: 'absolute', right: -120, top: -60, opacity: 0.18 }}>
            <circle cx="190" cy="190" r="180" fill="none" stroke={T.accent} strokeWidth="1.2"/>
            <circle cx="190" cy="190" r="130" fill="none" stroke={T.accent} strokeWidth="1.2"/>
            <circle cx="190" cy="190" r="80" fill="none" stroke={T.accent} strokeWidth="1.2"/>
            <circle cx="190" cy="190" r="30" fill={T.accent} opacity="0.3"/>
          </svg>
          <div style={{ position: 'relative', zIndex: 1 }}>
            <div style={{ fontFamily: A_FONT_MONO, fontSize: 11, letterSpacing: '0.12em', color: T.accent, textTransform: 'uppercase', marginBottom: 20 }}>─── ИНСТИТУЦИОНАЛЬНОЕ КАСТОДИ</div>
            <h2 style={{ fontFamily: A_FONT_DISPLAY, fontSize: 44, fontWeight: 500, letterSpacing: '-0.025em', lineHeight: 1.05, color: '#fff', margin: 0 }}>
              «Деньги в надёжных руках. Всегда — вместе.»
            </h2>
            <div style={{ marginTop: 24, fontFamily: A_FONT_MONO, fontSize: 11, color: 'rgba(255,255,255,0.55)' }}>— М. Орозова, CFO Demo Exchange</div>
          </div>
          <div style={{ display: 'flex', gap: 32, fontFamily: A_FONT_MONO, fontSize: 10, color: 'rgba(255,255,255,0.45)', letterSpacing: '0.1em', position: 'relative', zIndex: 1 }}>
            <div>NIST · 800-57</div><div>FATF TRAVEL RULE</div><div>SOC 2 · TYPE II</div>
          </div>
        </div>
        <div style={{ padding: 56, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ maxWidth: 420 }}>
            <h1 style={{ fontFamily: A_FONT_DISPLAY, fontSize: 32, fontWeight: 500, letterSpacing: '-0.02em', margin: 0 }}>{t.loginTitle}</h1>
            <div style={{ marginTop: 32 }}>
              <label style={{ fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.1em', color: T.fgMuted, textTransform: 'uppercase' }}>{t.email}</label>
              <div style={{ marginTop: 6, padding: '12px 14px', border: `1px solid ${T.borderStrong}`, fontFamily: A_FONT_MONO, fontSize: 13, color: T.fg, background: T.surface }}>demo-admin@orgon.io</div>
            </div>
            <div style={{ marginTop: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <label style={{ fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.1em', color: T.fgMuted, textTransform: 'uppercase' }}>{t.password}</label>
                <span style={{ fontSize: 11, color: T.accent }}>{t.forgot}</span>
              </div>
              <div style={{ marginTop: 6, padding: '12px 14px', border: `1px solid ${T.border}`, fontFamily: A_FONT_MONO, fontSize: 13, color: T.fgMuted, background: T.surface }}>● ● ● ● ● ● ● ●</div>
            </div>
            <button style={{ width: '100%', marginTop: 24, padding: '14px', background: T.accent, color: '#fff', border: 'none', fontSize: 14, fontWeight: 500, cursor: 'pointer' }}>{t.login} →</button>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 32, color: T.fgFaint, fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.12em' }}>
              <div style={{ flex: 1, height: 1, background: T.border }}/>
              {t.demoTitle.toUpperCase()}
              <div style={{ flex: 1, height: 1, background: T.border }}/>
            </div>
            <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[
                { l: t.demoAdmin, mono: 'demo-admin@orgon.io' },
                { l: t.demoSigner, mono: 'demo-signer@orgon.io' },
                { l: t.demoViewer, mono: 'demo-viewer@orgon.io' },
              ].map((d, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', border: `1px solid ${T.border}`, background: T.surface, fontSize: 12 }}>
                  <span style={{ color: T.fg }}>{d.l}</span>
                  <Mono color={T.fgMuted} size={11}>{d.mono}</Mono>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </ABase>
  );
}

// ───────── TRANSACTIONS LIST ─────────
function ATransactions({ theme = 'light' }) {
  const T = theme === 'dark' ? A_DARK : A_LIGHT;
  const t = useLang();
  return (
    <ABase T={T} h={860}>
      <div style={{ padding: '24px 56px', borderBottom: `1px solid ${T.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.12em', color: T.fgFaint, textTransform: 'uppercase' }}>WORKSPACE / TRANSACTIONS</div>
          <div style={{ fontFamily: A_FONT_DISPLAY, fontSize: 28, fontWeight: 500, marginTop: 4 }}>{t.transactions}</div>
        </div>
        <button style={{ padding: '10px 18px', background: T.accent, color: '#fff', border: 'none', fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>+ Новая транзакция</button>
      </div>
      <div style={{ padding: '14px 56px', display: 'flex', gap: 8, borderBottom: `1px solid ${T.border}`, background: T.surface2 }}>
        {['Все · 142', 'Confirmed · 96', 'Pending · 28', 'Sent · 12', 'Rejected · 6'].map((f, i) => (
          <div key={i} style={{ padding: '6px 12px', fontFamily: A_FONT_MONO, fontSize: 11, color: i === 0 ? T.fg : T.fgMuted, background: i === 0 ? T.surface : 'transparent', border: `1px solid ${i === 0 ? T.borderStrong : T.border}` }}>{f}</div>
        ))}
        <div style={{ flex: 1 }}/>
        <div style={{ padding: '6px 12px', fontFamily: A_FONT_MONO, fontSize: 11, color: T.fgMuted, border: `1px solid ${T.border}` }}>27.04 — 27.04.2026</div>
        <div style={{ padding: '6px 12px', fontFamily: A_FONT_MONO, fontSize: 11, color: T.fgMuted, border: `1px solid ${T.border}` }}>Все сети</div>
      </div>
      <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ fontFamily: A_FONT_MONO, fontSize: 9, letterSpacing: '0.12em', color: T.fgFaint, textTransform: 'uppercase' }}>
            {['HASH', t.status, t.wallet, t.destination, t.token, t.amount, t.sigsCol, t.time].map((h, i) => (
              <th key={i} style={{ textAlign: i > 4 ? 'right' : 'left', padding: '12px 16px', borderBottom: `1px solid ${T.border}` }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[...MOCK.txs, ...MOCK.txs.slice(0, 4)].slice(0, 11).map((tx, i) => {
            const stColor = { confirmed: T.positive, pending: T.pending, sent: T.fg, rejected: T.negative }[tx.status];
            return (
              <tr key={i} style={{ borderBottom: `1px solid ${T.border}` }}>
                <td style={{ padding: '12px 16px' }}><Mono color={T.fg}>{tx.hash}</Mono></td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: A_FONT_MONO, fontSize: 10, color: stColor, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    <span style={{ width: 6, height: 6, background: stColor, borderRadius: tx.status === 'pending' ? 0 : '50%' }}/>
                    {t[tx.status === 'pending' ? 'pendingS' : tx.status]}
                  </span>
                </td>
                <td style={{ padding: '12px 16px', color: T.fg }}>{tx.wallet}</td>
                <td style={{ padding: '12px 16px' }}><Mono color={T.fgMuted}>{tx.to}</Mono></td>
                <td style={{ padding: '12px 16px' }}><span style={{ fontFamily: A_FONT_MONO, fontSize: 11, padding: '2px 8px', border: `1px solid ${T.border}`, color: T.fg }}>{tx.token}</span></td>
                <td style={{ padding: '12px 16px', textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: T.fg }}>{tx.amount}</td>
                <td style={{ padding: '12px 16px', textAlign: 'right' }}><Mono color={T.fgMuted}>{tx.sigs}</Mono></td>
                <td style={{ padding: '12px 16px', textAlign: 'right' }}><Mono color={T.fgFaint}>{tx.time}</Mono></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </ABase>
  );
}

// ───────── BRAND DNA CARD ─────────
function ABrand() {
  const T = A_LIGHT;
  return (
    <ABase T={T} h={640} w={1280}>
      <div style={{ padding: 56, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 48, height: '100%', boxSizing: 'border-box' }}>
        <div>
          <div style={{ fontFamily: A_FONT_MONO, fontSize: 11, letterSpacing: '0.12em', color: T.accent, textTransform: 'uppercase' }}>НАПРАВЛЕНИЕ A</div>
          <h2 style={{ fontFamily: A_FONT_DISPLAY, fontSize: 64, fontWeight: 500, letterSpacing: '-0.03em', margin: '12px 0', lineHeight: 1 }}>Crimson<br/>Ledger</h2>
          <p style={{ color: T.fgMuted, fontSize: 14, lineHeight: 1.6, maxWidth: 440 }}>
            Институциональная сдержанность. Светлая тема — белый бумажный фон, графитовая иерархия, кармин (логотипа) только для критичных действий и подписей. Тёмная тема — ночной navy с самого логотипа, кармин активнее.
          </p>
          <div style={{ marginTop: 32 }}>
            <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.16em', color: T.fgFaint, marginBottom: 8 }}>ТИПОГРАФИКА</div>
            <div style={{ fontFamily: A_FONT_DISPLAY, fontSize: 32, fontWeight: 500 }}>IBM Plex Sans Display</div>
            <div style={{ fontFamily: A_FONT_SANS, fontSize: 16, color: T.fgMuted }}>Inter — body & UI</div>
            <div style={{ fontFamily: A_FONT_MONO, fontSize: 14, color: T.accent }}>IBM Plex Mono — addresses, hashes</div>
          </div>
        </div>
        <div>
          <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.16em', color: T.fgFaint, marginBottom: 12 }}>ПАЛИТРА · LIGHT (ПЕРВИЧНАЯ)</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 1, background: T.border, marginBottom: 24 }}>
            {[
              { c: A_LIGHT.bg, n: 'Paper', h: A_LIGHT.bg },
              { c: A_LIGHT.surface2, n: 'Surface', h: A_LIGHT.surface2 },
              { c: A_LIGHT.fg, n: 'Ink', h: A_LIGHT.fg },
              { c: A_LIGHT.accent, n: 'Crimson', h: A_LIGHT.accent },
              { c: A_LIGHT.navy, n: 'Navy', h: A_LIGHT.navy },
            ].map((s, i) => (
              <div key={i} style={{ background: T.surface }}>
                <div style={{ height: 60, background: s.c, border: i === 0 ? `1px solid ${T.border}` : 'none' }}/>
                <div style={{ padding: '8px 10px' }}>
                  <div style={{ fontSize: 11, color: T.fg, fontWeight: 500 }}>{s.n}</div>
                  <Mono color={T.fgMuted} size={9}>{s.h}</Mono>
                </div>
              </div>
            ))}
          </div>
          <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.16em', color: T.fgFaint, marginBottom: 12 }}>ПАЛИТРА · DARK</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 1, background: T.border, marginBottom: 24 }}>
            {[
              { c: A_DARK.bg, n: 'Midnight', h: A_DARK.bg },
              { c: A_DARK.surface2, n: 'Surface', h: A_DARK.surface2 },
              { c: A_DARK.fg, n: 'Foreground', h: A_DARK.fg },
              { c: A_DARK.accent, n: 'Crimson', h: A_DARK.accent },
              { c: A_DARK.accentDeep, n: 'Crimson/L', h: A_DARK.accentDeep },
            ].map((s, i) => (
              <div key={i} style={{ background: T.surface }}>
                <div style={{ height: 60, background: s.c }}/>
                <div style={{ padding: '8px 10px' }}>
                  <div style={{ fontSize: 11, color: T.fg, fontWeight: 500 }}>{s.n}</div>
                  <Mono color={T.fgMuted} size={9}>{s.h}</Mono>
                </div>
              </div>
            ))}
          </div>
          <div style={{ fontFamily: A_FONT_MONO, fontSize: 10, letterSpacing: '0.16em', color: T.fgFaint, marginBottom: 12 }}>ЛОГОТИП</div>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center', justifyContent: 'space-between', padding: 24, background: T.surface, border: `1px solid ${T.border}` }}>
            <AWordmark T={T} size={24} full/>
            <div style={{ background: A_DARK.bg, padding: '20px 24px' }}>
              <AWordmark T={{ ...A_DARK }} size={24} full/>
            </div>
          </div>
        </div>
      </div>
    </ABase>
  );
}

Object.assign(window, { AHero, ADashboard, AWalletDetail, APricing, ALogin, ATransactions, ABrand });
