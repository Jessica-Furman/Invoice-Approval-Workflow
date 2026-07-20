import React from "react";
import { Icon } from "./Icon.jsx";

/**
 * IconButton — a square/round button holding a single icon.
 * variant: primary | secondary | outline | ghost · matches Button.
 */
export function IconButton({
  icon,
  name,
  variant = "ghost",
  size = "md",
  round = false,
  disabled = false,
  "aria-label": ariaLabel,
  style,
  ...rest
}) {
  const dims = { sm: 36, md: 44, lg: 52 }[size];
  const iconSize = { sm: 18, md: 20, lg: 24 }[size];

  const variants = {
    primary: { background: "var(--up-green)", color: "var(--up-near-black)", border: "1px solid transparent" },
    secondary: { background: "var(--up-near-black)", color: "var(--up-off-white)", border: "1px solid transparent" },
    outline: { background: "transparent", color: "var(--text-strong)", border: "1px solid var(--border-strong)" },
    ghost: { background: "transparent", color: "var(--text-strong)", border: "1px solid transparent" },
  }[variant];

  return (
    <button
      aria-label={ariaLabel}
      disabled={disabled}
      className={`up-iconbtn up-iconbtn--${variant}`}
      style={{
        width: dims,
        height: dims,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: round ? "var(--radius-pill)" : "var(--radius-sm)",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.45 : 1,
        transition: "background var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--ease-out)",
        ...variants,
        ...style,
      }}
      onMouseDown={(e) => { if (!disabled) e.currentTarget.style.transform = "scale(0.94)"; }}
      onMouseUp={(e) => { e.currentTarget.style.transform = "scale(1)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.transform = "scale(1)"; }}
      {...rest}
    >
      {icon || <Icon name={name} size={iconSize} />}
    </button>
  );
}
