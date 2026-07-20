import React from "react";

/**
 * Button — the primary action element.
 * variant: primary (green, near-black text) · secondary (dark) · outline · ghost
 * One primary (green) CTA per view.
 */
export function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  disabled = false,
  iconLeft = null,
  iconRight = null,
  children,
  style,
  ...rest
}) {
  const sizes = {
    sm: { fontSize: 14, padding: "8px 16px", gap: 6, minHeight: 36 },
    md: { fontSize: 15, padding: "11px 22px", gap: 8, minHeight: 44 },
    lg: { fontSize: 16, padding: "14px 28px", gap: 10, minHeight: 52 },
  }[size];

  const variants = {
    primary: {
      background: "var(--up-green)",
      color: "var(--up-near-black)",
      border: "1px solid transparent",
    },
    secondary: {
      background: "var(--up-near-black)",
      color: "var(--up-off-white)",
      border: "1px solid transparent",
    },
    outline: {
      background: "transparent",
      color: "var(--text-strong)",
      border: "1px solid var(--border-strong)",
    },
    ghost: {
      background: "transparent",
      color: "var(--text-strong)",
      border: "1px solid transparent",
    },
  }[variant];

  return (
    <button
      disabled={disabled}
      className={`up-btn up-btn--${variant}`}
      style={{
        fontFamily: "var(--font-body)",
        fontWeight: 600,
        letterSpacing: "0.005em",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: fullWidth ? "100%" : "auto",
        borderRadius: "var(--radius-pill)",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.45 : 1,
        transition: "background var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out)",
        whiteSpace: "nowrap",
        ...sizes,
        ...variants,
        ...style,
      }}
      onMouseDown={(e) => { if (!disabled) e.currentTarget.style.transform = "scale(0.98)"; }}
      onMouseUp={(e) => { e.currentTarget.style.transform = "scale(1)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.transform = "scale(1)"; }}
      {...rest}
    >
      {iconLeft}
      {children}
      {iconRight}
    </button>
  );
}
