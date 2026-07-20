// Home / landing view for the Upbound marketing site.
const _NSH = window.UpboundGroupDesignSystem_ca0950;
const { Button: HButton, Icon: HIcon, Card: HCard, Badge: HBadge } = _NSH;

function Hero({ onDemo, onNavigate }) {
  return (
    <section style={{ position: "relative", background: "var(--up-navy)", overflow: "hidden", padding: "96px 40px 108px" }}>
      {/* signature diagonal wash */}
      <div style={{ position: "absolute", inset: "0 -30% 0 58%", background: "var(--up-charcoal)", transform: "skewX(-30deg)", transformOrigin: "bottom left", opacity: 0.7 }} />
      <div style={{ position: "relative", maxWidth: 1120, margin: "0 auto", display: "grid", gridTemplateColumns: "1.15fr 0.85fr", gap: 48, alignItems: "center" }}>
        <div>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--up-green)", marginBottom: 20 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--up-green)" }} /> Financial opportunity, elevated
          </div>
          <h1 style={{ color: "var(--up-off-white)", fontSize: 60, lineHeight: 1.02, letterSpacing: "-0.02em", maxWidth: 620 }}>
            We help people move their finances forward.
          </h1>
          <p style={{ marginTop: 22, maxWidth: 470, fontSize: 18, lineHeight: 1.5, color: "var(--up-cool-grey)" }}>
            Upbound Group builds the lending, payments, and marketplace platforms that open real financial opportunity — for enterprises and the people they serve.
          </p>
          <div style={{ display: "flex", gap: 14, marginTop: 32 }}>
            <HButton variant="primary" size="lg" onClick={onDemo} iconRight={<HIcon name="arrow-up-right" size={20} />}>Request a demo</HButton>
            <HButton variant="outline" size="lg" onClick={() => onNavigate("solutions")} style={{ color: "var(--up-off-white)", borderColor: "var(--up-cool-grey)" }}>Explore solutions</HButton>
          </div>
        </div>
        <div style={{ position: "relative" }}>
          <HCard style={{ background: "var(--up-charcoal)", border: "1px solid var(--divider-on-dark)", padding: 26 }}>
            <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--up-cool-grey)" }}>Assets enabled</div>
            <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 46, color: "var(--up-off-white)", marginTop: 6, lineHeight: 1 }}>
              $4.2B<span style={{ color: "var(--up-green)" }}>.</span>
            </div>
            <div style={{ height: 1, background: "var(--divider-on-dark)", margin: "20px 0" }} />
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {[["Approval rate", "92%"], ["Avg. time to fund", "48 hrs"], ["Partner NPS", "71"]].map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 14, color: "var(--up-cool-grey)" }}>{k}</span>
                  <span style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 18, color: "var(--up-off-white)" }}>{v}</span>
                </div>
              ))}
            </div>
          </HCard>
        </div>
      </div>
    </section>
  );
}

function LogoStrip() {
  const names = ["Meridian", "Northwind", "Cedar Bank", "Vantage", "Halcyon"];
  return (
    <section style={{ background: "var(--surface-card)", padding: "28px 40px", borderBottom: "1px solid var(--border-subtle)" }}>
      <div style={{ maxWidth: 1120, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 24, flexWrap: "wrap" }}>
        <span style={{ fontSize: 13, color: "var(--text-muted)" }}>Trusted by forward-looking finance teams</span>
        <div style={{ display: "flex", gap: 36, alignItems: "center" }}>
          {names.map((n) => (
            <span key={n} style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 17, color: "var(--text-muted)", opacity: 0.7 }}>{n}</span>
          ))}
        </div>
      </div>
    </section>
  );
}

const SOLUTIONS = [
  { icon: "landmark", title: "Lending", body: "Underwrite, approve, and fund in days — not weeks — with transparent terms." },
  { icon: "credit-card", title: "Payments", body: "Move money reliably across partners with real-time settlement and controls." },
  { icon: "store", title: "Marketplace", body: "Connect merchants and customers with flexible, opportunity-first financing." },
  { icon: "line-chart", title: "Analytics", body: "See the whole portfolio clearly and act on what moves outcomes upward." },
];

function SolutionsGrid({ onNavigate }) {
  return (
    <section style={{ background: "var(--surface-page)", padding: "80px 40px" }}>
      <div style={{ maxWidth: 1120, margin: "0 auto" }}>
        <div style={{ maxWidth: 620, marginBottom: 44 }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: 14 }}>What we build</div>
          <h2 style={{ fontSize: 36 }}>One platform for the whole financial relationship.</h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 20 }}>
          {SOLUTIONS.map((s) => (
            <HCard key={s.title} interactive onClick={() => onNavigate("solutions")} padding={28}>
              <div style={{ width: 44, height: 44, borderRadius: "var(--radius-md)", background: "var(--up-navy)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 18 }}>
                <HIcon name={s.icon} size={22} color="var(--up-green)" />
              </div>
              <h3 style={{ fontSize: 20, marginBottom: 8 }}>{s.title}</h3>
              <p style={{ fontSize: 15, color: "var(--text-muted)", lineHeight: 1.5, margin: 0 }}>{s.body}</p>
            </HCard>
          ))}
        </div>
      </div>
    </section>
  );
}

function StatBand() {
  const stats = [["1994", "Founded"], ["$4.2B", "Assets enabled"], ["3.1M", "People served"], ["18", "Markets"]];
  return (
    <section style={{ background: "var(--up-near-black)", padding: "64px 40px" }}>
      <div style={{ maxWidth: 1120, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 24 }}>
        {stats.map(([v, k], i) => (
          <div key={k} style={{ borderLeft: i === 0 ? "none" : "1px solid var(--divider-on-dark)", paddingLeft: i === 0 ? 0 : 24 }}>
            <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 42, color: "var(--up-off-white)", lineHeight: 1 }}>{v}</div>
            <div style={{ fontSize: 13, color: "var(--up-cool-grey)", marginTop: 8 }}>{k}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function CtaBand({ onDemo }) {
  return (
    <section style={{ position: "relative", background: "var(--up-navy)", padding: "72px 40px", overflow: "hidden" }}>
      <div style={{ position: "absolute", inset: "0 60% 0 -20%", background: "var(--up-charcoal)", transform: "skewX(-30deg)", transformOrigin: "bottom right", opacity: 0.6 }} />
      <div style={{ position: "relative", maxWidth: 1120, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 32, flexWrap: "wrap" }}>
        <h2 style={{ color: "var(--up-off-white)", fontSize: 34, maxWidth: 560 }}>Ready to move your finances forward?</h2>
        <HButton variant="primary" size="lg" onClick={onDemo} iconRight={<HIcon name="arrow-up-right" size={20} />}>Request a demo</HButton>
      </div>
    </section>
  );
}

function HomeView({ onDemo, onNavigate }) {
  return (
    <div>
      <Hero onDemo={onDemo} onNavigate={onNavigate} />
      <LogoStrip />
      <SolutionsGrid onNavigate={onNavigate} />
      <StatBand />
      <CtaBand onDemo={onDemo} />
    </div>
  );
}

Object.assign(window, { HomeView });
