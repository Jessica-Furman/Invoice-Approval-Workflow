import React from "react";

/**
 * Radio — single choice within a RadioGroup (or standalone).
 */
export function Radio({ label, checked, name, value, onChange, disabled, id, style, ...rest }) {
  const inputId = id || React.useId();
  return (
    <label htmlFor={inputId} style={{ display: "inline-flex", alignItems: "center", gap: 10, fontFamily: "var(--font-body)", fontSize: 15, color: "var(--text-body)", cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1, ...style }}>
      <input
        id={inputId}
        type="radio"
        name={name}
        value={value}
        checked={checked}
        disabled={disabled}
        onChange={onChange}
        style={{ position: "absolute", opacity: 0, width: 0, height: 0 }}
        {...rest}
      />
      <span aria-hidden="true" style={{
        width: 20, height: 20, flex: "none", borderRadius: "var(--radius-dot)",
        border: checked ? "6px solid var(--up-near-black)" : "1px solid var(--border-strong)",
        background: checked ? "var(--up-green)" : "var(--surface-card)",
        boxSizing: "border-box",
        transition: "border-color var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out)",
      }} />
      {label}
    </label>
  );
}

/**
 * RadioGroup — manages a set of Radios by value.
 */
export function RadioGroup({ name, value, onChange, options = [], style }) {
  const groupName = name || React.useId();
  return (
    <div role="radiogroup" style={{ display: "flex", flexDirection: "column", gap: 10, ...style }}>
      {options.map((o) => {
        const val = o.value ?? o;
        return (
          <Radio
            key={val}
            name={groupName}
            value={val}
            label={o.label ?? o}
            checked={value === val}
            onChange={() => onChange && onChange(val)}
          />
        );
      })}
    </div>
  );
}
