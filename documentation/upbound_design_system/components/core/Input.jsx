import React from "react";

/**
 * Input — single-line text field with label, hint, and error states.
 * Focus shows the green ring.
 */
export function Input({
  label, hint, error, id, iconLeft, style, ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  const inputId = id || React.useId();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, fontFamily: "var(--font-body)" }}>
      {label && (
        <label htmlFor={inputId} style={{ fontSize: 13, fontWeight: 600, color: "var(--text-strong)" }}>{label}</label>
      )}
      <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
        {iconLeft && (
          <span style={{ position: "absolute", left: 12, display: "inline-flex", color: "var(--text-muted)", pointerEvents: "none" }}>{iconLeft}</span>
        )}
        <input
          id={inputId}
          onFocus={() => setFocus(true)}
          onBlur={() => setFocus(false)}
          style={{
            width: "100%",
            boxSizing: "border-box",
            fontFamily: "var(--font-body)",
            fontSize: 15,
            color: "var(--text-strong)",
            background: "var(--surface-card)",
            padding: iconLeft ? "11px 14px 11px 38px" : "11px 14px",
            borderRadius: "var(--radius-sm)",
            border: `1px solid ${error ? "var(--status-danger)" : focus ? "var(--up-near-black)" : "var(--border-default)"}`,
            boxShadow: focus && !error ? "var(--shadow-focus)" : "none",
            outline: "none",
            transition: "border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out)",
            ...style,
          }}
          {...rest}
        />
      </div>
      {(hint || error) && (
        <span style={{ fontSize: 12, color: error ? "var(--status-danger)" : "var(--text-muted)" }}>{error || hint}</span>
      )}
    </div>
  );
}
