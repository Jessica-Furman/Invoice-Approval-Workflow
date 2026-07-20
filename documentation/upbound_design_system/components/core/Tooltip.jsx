import React from "react";

/**
 * Tooltip — hover/focus label on a near-black surface.
 */
export function Tooltip({ label, side = "top", children, style }) {
  const [show, setShow] = React.useState(false);

  const pos = {
    top: { bottom: "calc(100% + 8px)", left: "50%", transform: "translateX(-50%)" },
    bottom: { top: "calc(100% + 8px)", left: "50%", transform: "translateX(-50%)" },
    left: { right: "calc(100% + 8px)", top: "50%", transform: "translateY(-50%)" },
    right: { left: "calc(100% + 8px)", top: "50%", transform: "translateY(-50%)" },
  }[side];

  return (
    <span
      style={{ position: "relative", display: "inline-flex" }}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
      onFocus={() => setShow(true)}
      onBlur={() => setShow(false)}
    >
      {children}
      {show && (
        <span
          role="tooltip"
          style={{
            position: "absolute", zIndex: 100, ...pos,
            background: "var(--up-near-black)",
            color: "var(--up-off-white)",
            fontFamily: "var(--font-body)", fontSize: 12, fontWeight: 500,
            padding: "6px 10px", borderRadius: "var(--radius-xs)",
            whiteSpace: "nowrap", pointerEvents: "none",
            boxShadow: "var(--shadow-md)",
            animation: "upTipIn var(--dur-fast) var(--ease-out)",
            ...style,
          }}
        >
          {label}
        </span>
      )}
      <style>{`@keyframes upTipIn { from { opacity: 0 } to { opacity: 1 } }`}</style>
    </span>
  );
}
