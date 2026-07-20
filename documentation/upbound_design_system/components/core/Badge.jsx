import React from "react";

/**
 * Badge — small status/count marker.
 * tone: neutral | accent (green) | success | warning | danger | info
 */
export function Badge({ tone = "neutral", children, style, ...rest }) {
  const tones = {
    neutral: { background: "var(--surface-sunken)", color: "var(--text-body)" },
    accent: { background: "var(--up-green)", color: "var(--up-near-black)" },
    success: { background: "rgba(62,155,79,0.14)", color: "#2E7C3E" },
    warning: { background: "rgba(201,138,22,0.16)", color: "#966410" },
    danger: { background: "rgba(198,69,59,0.14)", color: "#A5372E" },
    info: { background: "rgba(62,111,176,0.14)", color: "#325C93" },
  }[tone];

  return (
    <span
      className={`up-badge up-badge--${tone}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        fontFamily: "var(--font-body)",
        fontSize: 12,
        fontWeight: 600,
        lineHeight: 1,
        padding: "5px 9px",
        borderRadius: "var(--radius-xs)",
        ...tones,
        ...style,
      }}
      {...rest}
    >
      {children}
    </span>
  );
}
