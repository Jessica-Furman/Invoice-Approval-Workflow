import React from "react";

/**
 * Textarea — multi-line text field. Same visual language as Input.
 */
export function Textarea({ label, hint, error, id, rows = 4, style, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  const inputId = id || React.useId();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, fontFamily: "var(--font-body)" }}>
      {label && (
        <label htmlFor={inputId} style={{ fontSize: 13, fontWeight: 600, color: "var(--text-strong)" }}>{label}</label>
      )}
      <textarea
        id={inputId}
        rows={rows}
        onFocus={() => setFocus(true)}
        onBlur={() => setFocus(false)}
        style={{
          width: "100%",
          boxSizing: "border-box",
          fontFamily: "var(--font-body)",
          fontSize: 15,
          lineHeight: 1.5,
          color: "var(--text-strong)",
          background: "var(--surface-card)",
          padding: "11px 14px",
          borderRadius: "var(--radius-sm)",
          border: `1px solid ${error ? "var(--status-danger)" : focus ? "var(--up-near-black)" : "var(--border-default)"}`,
          boxShadow: focus && !error ? "var(--shadow-focus)" : "none",
          outline: "none",
          resize: "vertical",
          transition: "border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out)",
          ...style,
        }}
        {...rest}
      />
      {(hint || error) && (
        <span style={{ fontSize: 12, color: error ? "var(--status-danger)" : "var(--text-muted)" }}>{error || hint}</span>
      )}
    </div>
  );
}
