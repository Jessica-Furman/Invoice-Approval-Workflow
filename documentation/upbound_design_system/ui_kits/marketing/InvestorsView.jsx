// Investors & Careers views.
const _NSI = window.UpboundGroupDesignSystem_ca0950;
const { Button: IButton, Icon: IIcon, Card: ICard, Badge: IBadge } = _NSI;

function InvestorsView({ onDemo }) {
  const highlights = [["Revenue", "$1.28B", "+11% YoY"], ["Adj. EBITDA", "$214M", "+16% YoY"], ["Free cash flow", "$168M", "+9% YoY"], ["Dividend", "$0.37", "per share"]];
  const events = [
    ["Q2 2026 Earnings Call", "Aug 4, 2026", "Upcoming"],
    ["Annual Shareholder Meeting", "Jun 12, 2026", "Replay"],
    ["Investor Day 2026", "Mar 20, 2026", "Replay"],
  ];
  return (
    <div>
      <section style={{ background: "var(--up-navy)", padding: "64px 40px" }}>
        <div style={{ maxWidth: 1120, margin: "0 auto" }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--up-green)", marginBottom: 14 }}>Investors</div>
          <h1 style={{ color: "var(--up-off-white)", fontSize: 46, maxWidth: 640 }}>Disciplined growth. Grounded ambition.</h1>
          <p style={{ color: "var(--up-cool-grey)", marginTop: 18, maxWidth: 520, fontSize: 17, lineHeight: 1.5 }}>A durable business built to compound financial opportunity — for our customers and our shareholders.</p>
        </div>
      </section>
      <section style={{ background: "var(--surface-card)", padding: "48px 40px", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ maxWidth: 1120, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 20 }}>
          {highlights.map(([k, v, d]) => (
            <div key={k}>
              <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-muted)" }}>{k}</div>
              <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 38, color: "var(--text-strong)", marginTop: 8, lineHeight: 1 }}>{v}</div>
              <div style={{ fontSize: 13, color: "var(--status-success)", marginTop: 6, fontWeight: 600 }}>{d}</div>
            </div>
          ))}
        </div>
      </section>
      <section style={{ background: "var(--surface-page)", padding: "72px 40px" }}>
        <div style={{ maxWidth: 1120, margin: "0 auto", display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: 40 }}>
          <div>
            <h2 style={{ fontSize: 30, marginBottom: 24 }}>Events & filings</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {events.map(([t, d, s]) => (
                <ICard key={t} interactive padding={20} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 17, color: "var(--text-strong)" }}>{t}</div>
                    <div style={{ fontSize: 14, color: "var(--text-muted)", marginTop: 4 }}>{d}</div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                    <IBadge tone={s === "Upcoming" ? "accent" : "neutral"}>{s}</IBadge>
                    <IIcon name="arrow-up-right" size={18} color="var(--text-muted)" />
                  </div>
                </ICard>
              ))}
            </div>
          </div>
          <ICard padding={26} style={{ background: "var(--up-near-black)" }}>
            <h3 style={{ color: "var(--up-off-white)", fontSize: 20, marginBottom: 10 }}>Investor resources</h3>
            <p style={{ color: "var(--up-cool-grey)", fontSize: 14, lineHeight: 1.5, marginBottom: 20 }}>Latest reports, presentations, and SEC filings in one place.</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {["Q2 2026 10-Q", "2025 Annual Report", "Investor Presentation"].map((f) => (
                <a key={f} style={{ cursor: "pointer", textDecoration: "none", display: "flex", alignItems: "center", justifyContent: "space-between", color: "var(--up-off-white)", fontSize: 14, paddingBottom: 12, borderBottom: "1px solid var(--divider-on-dark)" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 10 }}><IIcon name="file-text" size={16} color="var(--up-green)" />{f}</span>
                  <IIcon name="download" size={15} color="var(--up-cool-grey)" />
                </a>
              ))}
            </div>
            <IButton variant="primary" fullWidth style={{ marginTop: 22 }} onClick={onDemo}>Contact IR</IButton>
          </ICard>
        </div>
      </section>
    </div>
  );
}

function CareersView({ onDemo }) {
  const values = [
    ["compass", "Forward-looking", "We move people and outcomes upward."],
    ["shield-check", "Confident, not loud", "Authoritative without being aggressive."],
    ["sparkles", "Optimistic", "A sense of possibility runs through everything."],
  ];
  const roles = [
    ["Senior Product Designer", "Design", "Remote — US"],
    ["Staff Software Engineer", "Engineering", "Plano, TX"],
    ["Risk Analytics Lead", "Data", "Remote — US"],
    ["Partnerships Manager", "Growth", "New York, NY"],
  ];
  return (
    <div>
      <section style={{ position: "relative", background: "var(--up-navy)", overflow: "hidden", padding: "80px 40px" }}>
        <div style={{ position: "absolute", inset: "0 -30% 0 60%", background: "var(--up-charcoal)", transform: "skewX(-30deg)", opacity: 0.6 }} />
        <div style={{ position: "relative", maxWidth: 1120, margin: "0 auto" }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--up-green)", marginBottom: 14 }}>Careers</div>
          <h1 style={{ color: "var(--up-off-white)", fontSize: 52, maxWidth: 640 }}>Build a career that moves people upward.</h1>
          <p style={{ color: "var(--up-cool-grey)", marginTop: 18, maxWidth: 480, fontSize: 17, lineHeight: 1.5 }}>Join a team that makes the complex feel simple — and takes financial opportunity seriously.</p>
        </div>
      </section>
      <section style={{ background: "var(--surface-page)", padding: "72px 40px" }}>
        <div style={{ maxWidth: 1120, margin: "0 auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20, marginBottom: 64 }}>
            {values.map(([ic, t, b]) => (
              <ICard key={t} padding={26}>
                <div style={{ width: 44, height: 44, borderRadius: "var(--radius-md)", background: "var(--up-navy)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
                  <IIcon name={ic} size={22} color="var(--up-green)" />
                </div>
                <h3 style={{ fontSize: 19, marginBottom: 8 }}>{t}</h3>
                <p style={{ fontSize: 15, color: "var(--text-muted)", lineHeight: 1.5, margin: 0 }}>{b}</p>
              </ICard>
            ))}
          </div>
          <h2 style={{ fontSize: 30, marginBottom: 24 }}>Open roles</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {roles.map(([t, d, l]) => (
              <ICard key={t} interactive padding={22} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 18, color: "var(--text-strong)" }}>{t}</div>
                  <div style={{ fontSize: 14, color: "var(--text-muted)", marginTop: 4, display: "flex", gap: 16 }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 6 }}><IIcon name="layers" size={14} />{d}</span>
                    <span style={{ display: "flex", alignItems: "center", gap: 6 }}><IIcon name="map-pin" size={14} />{l}</span>
                  </div>
                </div>
                <IButton variant="outline" size="sm" iconRight={<IIcon name="arrow-up-right" size={16} />}>Apply</IButton>
              </ICard>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

Object.assign(window, { InvestorsView, CareersView });
