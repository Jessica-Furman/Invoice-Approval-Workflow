import React from "react";

/**
 * Tabs — underline tab set. Active tab underlined in green.
 */
export function Tabs({ tabs = [], value, defaultValue, onChange, style }) {
  const isControlled = value !== undefined;
  const [internal, setInternal] = React.useState(defaultValue ?? (tabs[0] && (tabs[0].value ?? tabs[0])));
  const active = isControlled ? value : internal;

  return (
    <div role="tablist" style={{ display: "flex", gap: 28, borderBottom: "1px solid var(--border-subtle)", ...style }}>
      {tabs.map((t) => {
        const val = t.value ?? t;
        const label = t.label ?? t;
        const on = active === val;
        return (
          <button
            key={val}
            role="tab"
            aria-selected={on}
            onClick={() => { if (!isControlled) setInternal(val); onChange && onChange(val); }}
            style={{
              border: 0, background: "transparent", cursor: "pointer",
              fontFamily: "var(--font-body)", fontSize: 15, fontWeight: on ? 600 : 500,
              color: on ? "var(--text-strong)" : "var(--text-muted)",
              padding: "0 0 12px", position: "relative",
              transition: "color var(--dur-fast) var(--ease-out)",
            }}
          >
            {label}
            <span style={{
              position: "absolute", left: 0, right: 0, bottom: -1, height: 2,
              background: on ? "var(--up-green)" : "transparent",
              borderRadius: "var(--radius-pill)",
              transition: "background var(--dur-fast) var(--ease-out)",
            }} />
          </button>
        );
      })}
    </div>
  );
}
