import React from "react";

/**
 * Select — styled native select with label and hint.
 */
export function Select({ label, hint, error, id, options = [], children, style, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  const inputId = id || React.useId();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, fontFamily: "var(--font-body)" }}>
      {label && (
        <label htmlFor={inputId} style={{ fontSize: 13, fontWeight: 600, color: "var(--text-strong)" }}>{label}</label>
      )}
      <div style={{ position: "relative" }}>
        <select
          id={inputId}
          onFocus={() => setFocus(true)}
          onBlur={() => setFocus(false)}
          style={{
            width: "100%",
            boxSizing: "border-box",
            appearance: "none",
            fontFamily: "var(--font-body)",
            fontSize: 15,
            color: "var(--text-strong)",
            background: "var(--surface-card)",
            padding: "11px 38px 11px 14px",
            borderRadius: "var(--radius-sm)",
            border: `1px solid ${error ? "var(--status-danger)" : focus ? "var(--up-near-black)" : "var(--border-default)"}`,
            boxShadow: focus && !error ? "var(--shadow-focus)" : "none",
            outline: "none",
            cursor: "pointer",
            transition: "border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out)",
            ...style,
          }}
          {...rest}
        >
          {options.length ? options.map((o) => (
            <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? o}</option>
          )) : children}
        </select>
        <span style={{ position: "absolute", right: 14, top: "50%", transform: "translateY(-50%)", pointerEvents: "none", color: "var(--text-muted)", fontSize: 12 }}>▾</span>
      </div>
      {(hint || error) && (
        <span style={{ fontSize: 12, color: error ? "var(--status-danger)" : "var(--text-muted)" }}>{error || hint}</span>
      )}
    </div>
  );
}
