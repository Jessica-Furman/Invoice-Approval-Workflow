import React from "react";

/**
 * Toast — transient notification. Dark surface, optional green accent bar.
 * tone: neutral | success | warning | danger
 */
export function Toast({ tone = "neutral", title, children, onClose, style }) {
  const accent = {
    neutral: "var(--up-green)",
    success: "var(--status-success)",
    warning: "var(--status-warning)",
    danger: "var(--status-danger)",
  }[tone];

  return (
    <div
      role="status"
      style={{
        display: "flex", alignItems: "flex-start", gap: 12,
        background: "var(--up-near-black)",
        color: "var(--up-off-white)",
        borderRadius: "var(--radius-md)",
        boxShadow: "var(--shadow-lg)",
        padding: "14px 16px",
        minWidth: 280, maxWidth: 420,
        fontFamily: "var(--font-body)",
        position: "relative", overflow: "hidden",
        ...style,
      }}
    >
      <span style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 4, background: accent }} />
      <div style={{ flex: 1, paddingLeft: 4 }}>
        {title && <div style={{ fontWeight: 600, fontSize: 14, marginBottom: children ? 2 : 0 }}>{title}</div>}
        {children && <div style={{ fontSize: 13, color: "var(--up-cool-grey)", lineHeight: 1.4 }}>{children}</div>}
      </div>
      {onClose && (
        <button aria-label="Dismiss" onClick={onClose} style={{ border: 0, background: "transparent", cursor: "pointer", color: "var(--up-cool-grey)", fontSize: 18, lineHeight: 1 }}>×</button>
      )}
    </div>
  );
}
