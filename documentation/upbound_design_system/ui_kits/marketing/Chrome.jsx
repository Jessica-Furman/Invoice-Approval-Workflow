// Shared chrome for the Upbound marketing site: Wordmark, Header, Footer.
// Composes the design-system bundle (window.UpboundGroupDesignSystem_ca0950).
const _NS = window.UpboundGroupDesignSystem_ca0950;
const { Button: CButton, IconButton: CIconButton, Icon: CIcon } = _NS;

function Wordmark({ dark = false, dot = true, size = 24 }) {
  return (
    <span style={{
      fontFamily: "var(--font-display)", fontWeight: 600, fontSize: size,
      letterSpacing: "-0.01em", color: dark ? "var(--up-off-white)" : "var(--up-near-black)",
      lineHeight: 1, userSelect: "none",
    }}>
      upbound{dot && <span style={{ color: "var(--up-green)" }}>.</span>}
    </span>
  );
}

const NAV = ["Solutions", "Investors", "Careers", "About"];

function Header({ route, onNavigate, onDemo }) {
  return (
    <header style={{
      position: "sticky", top: 0, zIndex: 50,
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "16px 40px", background: "rgba(53,50,61,0.92)", backdropFilter: "blur(8px)",
      borderBottom: "1px solid var(--divider-on-dark)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 44 }}>
        <a onClick={() => onNavigate("home")} style={{ cursor: "pointer", textDecoration: "none" }}><Wordmark dark /></a>
        <nav style={{ display: "flex", gap: 28 }}>
          {NAV.map((item) => {
            const key = item.toLowerCase();
            const active = route === key;
            return (
              <a key={item} onClick={() => onNavigate(key)} style={{
                cursor: "pointer", textDecoration: "none", fontFamily: "var(--font-body)",
                fontSize: 14, fontWeight: 500,
                color: active ? "var(--up-off-white)" : "var(--up-cool-grey)",
                transition: "color var(--dur-fast) var(--ease-out)",
              }}>{item}</a>
            );
          })}
        </nav>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <a onClick={() => onNavigate("signin")} style={{ cursor: "pointer", textDecoration: "none", fontFamily: "var(--font-body)", fontSize: 14, fontWeight: 500, color: "var(--up-cool-grey)" }}>Sign in</a>
        <CButton variant="primary" size="sm" onClick={onDemo} iconRight={<CIcon name="arrow-up-right" size={16} />}>Request a demo</CButton>
      </div>
    </header>
  );
}

function Footer({ onNavigate }) {
  const cols = [
    { h: "Solutions", items: ["Lending", "Payments", "Marketplace", "Analytics"] },
    { h: "Company", items: ["About", "Investors", "Careers", "Newsroom"] },
    { h: "Resources", items: ["Insights", "Help center", "Security", "Contact"] },
  ];
  return (
    <footer style={{ background: "var(--up-near-black)", color: "var(--up-off-white)", padding: "56px 40px 32px" }}>
      <div style={{ maxWidth: 1120, margin: "0 auto", display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr 1fr", gap: 40 }}>
        <div>
          <Wordmark dark />
          <p style={{ marginTop: 16, maxWidth: 240, fontSize: 14, color: "var(--up-cool-grey)", lineHeight: 1.5 }}>
            We exist to elevate financial opportunity for all.
          </p>
        </div>
        {cols.map((c) => (
          <div key={c.h}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--up-cool-grey)", marginBottom: 16 }}>{c.h}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {c.items.map((i) => (
                <a key={i} style={{ cursor: "pointer", textDecoration: "none", fontSize: 14, color: "var(--up-off-white)", opacity: 0.85 }}>{i}</a>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div style={{ maxWidth: 1120, margin: "40px auto 0", paddingTop: 24, borderTop: "1px solid var(--divider-on-dark)", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 13, color: "var(--up-cool-grey)" }}>
        <span>© 2026 Upbound Group. All rights reserved.</span>
        <span style={{ display: "flex", gap: 20 }}>
          <a style={{ cursor: "pointer", color: "inherit", textDecoration: "none" }}>Privacy</a>
          <a style={{ cursor: "pointer", color: "inherit", textDecoration: "none" }}>Terms</a>
        </span>
      </div>
    </footer>
  );
}

Object.assign(window, { Wordmark, Header, Footer, MKT_NAV: NAV });
