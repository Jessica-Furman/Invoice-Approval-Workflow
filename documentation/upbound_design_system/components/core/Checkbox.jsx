import React from "react";

/**
 * Checkbox — green-filled when checked, near-black check.
 */
export function Checkbox({ label, checked, defaultChecked, onChange, disabled, id, style, ...rest }) {
  const inputId = id || React.useId();
  const isControlled = checked !== undefined;
  const [internal, setInternal] = React.useState(defaultChecked || false);
  const on = isControlled ? checked : internal;

  return (
    <label htmlFor={inputId} style={{ display: "inline-flex", alignItems: "center", gap: 10, fontFamily: "var(--font-body)", fontSize: 15, color: "var(--text-body)", cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1, ...style }}>
      <input
        id={inputId}
        type="checkbox"
        checked={on}
        disabled={disabled}
        onChange={(e) => { if (!isControlled) setInternal(e.target.checked); onChange && onChange(e); }}
        style={{ position: "absolute", opacity: 0, width: 0, height: 0 }}
        {...rest}
      />
      <span aria-hidden="true" style={{
        width: 20, height: 20, flex: "none",
        borderRadius: "var(--radius-xs)",
        border: on ? "1px solid transparent" : "1px solid var(--border-strong)",
        background: on ? "var(--up-green)" : "var(--surface-card)",
        display: "inline-flex", alignItems: "center", justifyContent: "center",
        transition: "background var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out)",
      }}>
        {on && (
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M2.5 6.5L5 9L9.5 3.5" stroke="#1A1A1A" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </span>
      {label}
    </label>
  );
}
