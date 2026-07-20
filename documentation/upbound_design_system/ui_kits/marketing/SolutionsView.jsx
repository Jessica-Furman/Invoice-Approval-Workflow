// Solutions detail view + sign-in split.
const _NSS = window.UpboundGroupDesignSystem_ca0950;
const { Button: SButton, Icon: SIcon, Card: SCard, Tabs: STabs, Tag: STag, Input: SInput, Checkbox: SCheckbox } = _NSS;

function SolutionsView({ onDemo }) {
  const [tab, setTab] = React.useState("Lending");
  const detail = {
    Lending: { head: "Fund opportunity in days, not weeks.", body: "Configurable underwriting, transparent terms, and real-time decisioning that keeps applicants moving upward.", points: ["Automated decisioning", "Transparent, fair terms", "48-hour funding"] },
    Payments: { head: "Move money with confidence.", body: "Real-time settlement, granular controls, and reconciliation your finance team can actually trust.", points: ["Real-time settlement", "Ledger-grade controls", "Partner payouts"] },
    Marketplace: { head: "Financing that meets people where they are.", body: "Flexible, opportunity-first financing built into the buying moment for merchants and customers alike.", points: ["Embedded checkout", "Flexible terms", "Merchant tools"] },
    Analytics: { head: "See the whole portfolio clearly.", body: "One view of performance, risk, and opportunity — so you act on what actually moves outcomes upward.", points: ["Portfolio dashboards", "Risk signals", "Cohort insights"] },
  }[tab];

  return (
    <div>
      <section style={{ background: "var(--up-navy)", padding: "64px 40px 40px" }}>
        <div style={{ maxWidth: 1120, margin: "0 auto" }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--up-green)", marginBottom: 14 }}>Solutions</div>
          <h1 style={{ color: "var(--up-off-white)", fontSize: 46, maxWidth: 700 }}>Everything you need to elevate financial opportunity.</h1>
        </div>
      </section>
      <section style={{ background: "var(--surface-card)", padding: "0 40px" }}>
        <div style={{ maxWidth: 1120, margin: "0 auto" }}>
          <div style={{ paddingTop: 8 }}>
            <STabs tabs={["Lending", "Payments", "Marketplace", "Analytics"]} value={tab} onChange={setTab} />
          </div>
        </div>
      </section>
      <section style={{ background: "var(--surface-page)", padding: "56px 40px 80px" }}>
        <div style={{ maxWidth: 1120, margin: "0 auto", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 40, alignItems: "center" }}>
          <div>
            <h2 style={{ fontSize: 32, marginBottom: 16 }}>{detail.head}</h2>
            <p style={{ fontSize: 17, color: "var(--text-muted)", lineHeight: 1.55, marginBottom: 24 }}>{detail.body}</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 28 }}>
              {detail.points.map((p) => (
                <div key={p} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ width: 24, height: 24, borderRadius: "50%", background: "var(--up-green)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}>
                    <SIcon name="check" size={15} color="var(--up-near-black)" />
                  </span>
                  <span style={{ fontSize: 15, color: "var(--text-body)" }}>{p}</span>
                </div>
              ))}
            </div>
            <SButton variant="primary" onClick={onDemo} iconRight={<SIcon name="arrow-up-right" size={18} />}>Request a demo</SButton>
          </div>
          <SCard padding={0} style={{ overflow: "hidden" }}>
            <div style={{ background: "var(--up-navy)", padding: "22px 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 16, color: "var(--up-off-white)" }}>{tab} overview</span>
              <STag selected>Live</STag>
            </div>
            <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
              {[["Active accounts", "12,480"], ["This month", "+8.2%"], ["Avg. decision", "1.4s"]].map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 14, borderBottom: "1px solid var(--border-subtle)" }}>
                  <span style={{ fontSize: 14, color: "var(--text-muted)" }}>{k}</span>
                  <span style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 20, color: "var(--text-strong)" }}>{v}</span>
                </div>
              ))}
              <div style={{ height: 120, borderRadius: "var(--radius-md)", background: "linear-gradient(180deg, var(--up-off-white), var(--surface-card))", border: "1px solid var(--border-subtle)", display: "flex", alignItems: "flex-end", gap: 8, padding: 14 }}>
                {[42, 58, 50, 71, 64, 83, 92].map((h, i) => (
                  <div key={i} style={{ flex: 1, height: `${h}%`, background: i === 6 ? "var(--up-green)" : "var(--up-cool-grey)", borderRadius: 4 }} />
                ))}
              </div>
            </div>
          </SCard>
        </div>
      </section>
    </div>
  );
}

// Sign-in screen (split navy / form)
function SignInView({ onNavigate }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", minHeight: 620 }}>
      <div style={{ position: "relative", background: "var(--up-navy)", overflow: "hidden", padding: "72px 56px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
        <div style={{ position: "absolute", inset: "40% -40% -30% 30%", background: "var(--up-charcoal)", transform: "skewX(-30deg)", opacity: 0.6 }} />
        <Wordmark dark />
        <div style={{ position: "relative" }}>
          <h2 style={{ color: "var(--up-off-white)", fontSize: 34, maxWidth: 380 }}>Welcome back. Let's keep moving forward.</h2>
          <p style={{ color: "var(--up-cool-grey)", marginTop: 16, maxWidth: 360, fontSize: 15, lineHeight: 1.5 }}>Sign in to your Upbound partner console.</p>
        </div>
        <span style={{ position: "relative", fontSize: 13, color: "var(--up-cool-grey)" }}>© 2026 Upbound Group</span>
      </div>
      <div style={{ background: "var(--surface-card)", display: "flex", alignItems: "center", justifyContent: "center", padding: 40 }}>
        <div style={{ width: "100%", maxWidth: 360, display: "flex", flexDirection: "column", gap: 18 }}>
          <h3 style={{ fontSize: 24 }}>Sign in</h3>
          <SInput label="Work email" placeholder="you@company.com" iconLeft={<SIcon name="mail" size={18} />} />
          <SInput label="Password" type="password" placeholder="••••••••" iconLeft={<SIcon name="lock" size={18} />} />
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <SCheckbox label="Remember me" />
            <a style={{ cursor: "pointer", fontSize: 14 }}>Forgot?</a>
          </div>
          <SButton variant="primary" fullWidth onClick={() => onNavigate("home")}>Sign in</SButton>
          <p style={{ fontSize: 14, color: "var(--text-muted)", textAlign: "center", margin: 0 }}>New partner? <a style={{ cursor: "pointer" }} onClick={() => onNavigate("home")}>Request access</a></p>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SolutionsView, SignInView });
