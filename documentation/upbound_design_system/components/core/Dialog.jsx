import React from "react";

/**
 * Dialog — centered modal over a dimmed navy scrim.
 */
export function Dialog({ open, onClose, title, children, footer, width = 480, style }) {
  if (!open) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        background: "rgba(26,26,26,0.55)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 24,
        animation: "upFade var(--dur-base) var(--ease-out)",
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        style={{
          width, maxWidth: "100%",
          background: "var(--surface-card)",
          borderRadius: "var(--radius-lg)",
          boxShadow: "var(--shadow-lg)",
          padding: 28,
          fontFamily: "var(--font-body)",
          animation: "upRise var(--dur-slow) var(--ease-out)",
          ...style,
        }}
      >
        {title && (
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, marginBottom: 12 }}>
            <h3 style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: 22, color: "var(--text-strong)", margin: 0 }}>{title}</h3>
            <button aria-label="Close" onClick={onClose} style={{ border: 0, background: "transparent", cursor: "pointer", fontSize: 22, lineHeight: 1, color: "var(--text-muted)" }}>×</button>
          </div>
        )}
        <div style={{ fontSize: 15, color: "var(--text-body)", lineHeight: 1.5 }}>{children}</div>
        {footer && <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", marginTop: 24 }}>{footer}</div>}
      </div>
      <style>{`
        @keyframes upFade { from { opacity: 0 } to { opacity: 1 } }
        @keyframes upRise { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: translateY(0) } }
      `}</style>
    </div>
  );
}
