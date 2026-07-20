import React from "react";

/**
 * Switch — on/off toggle. Green track when on.
 */
export function Switch({ checked, defaultChecked, onChange, disabled, label, id, style, ...rest }) {
  const inputId = id || React.useId();
  const isControlled = checked !== undefined;
  const [internal, setInternal] = React.useState(defaultChecked || false);
  const on = isControlled ? checked : internal;

  return (
    <label htmlFor={inputId} style={{ display: "inline-flex", alignItems: "center", gap: 10, fontFamily: "var(--font-body)", fontSize: 15, color: "var(--text-body)", cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1, ...style }}>
      <input
        id={inputId}
        type="checkbox"
        role="switch"
        checked={on}
        disabled={disabled}
        onChange={(e) => { if (!isControlled) setInternal(e.target.checked); onChange && onChange(e); }}
        style={{ position: "absolute", opacity: 0, width: 0, height: 0 }}
        {...rest}
      />
      <span aria-hidden="true" style={{
        width: 44, height: 26, flex: "none", borderRadius: "var(--radius-pill)",
        background: on ? "var(--up-green)" : "var(--border-strong)",
        position: "relative",
        transition: "background var(--dur-base) var(--ease-out)",
      }}>
        <span style={{
          position: "absolute", top: 3, left: on ? 21 : 3,
          width: 20, height: 20, borderRadius: "var(--radius-dot)",
          background: on ? "var(--up-near-black)" : "var(--up-white)",
          boxShadow: "var(--shadow-xs)",
          transition: "left var(--dur-base) var(--ease-out), background var(--dur-base) var(--ease-out)",
        }} />
      </span>
      {label}
    </label>
  );
}
