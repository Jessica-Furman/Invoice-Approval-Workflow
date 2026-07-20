import React from "react";

/**
 * Tag — pill-shaped label/chip, optionally removable.
 * selected raises it to the green accent state.
 */
export function Tag({ selected = false, onRemove, children, style, ...rest }) {
  return (
    <span
      className="up-tag"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontFamily: "var(--font-body)",
        fontSize: 13,
        fontWeight: 500,
        lineHeight: 1,
        padding: "7px 12px",
        borderRadius: "var(--radius-pill)",
        border: selected ? "1px solid transparent" : "1px solid var(--border-default)",
        background: selected ? "var(--up-green)" : "transparent",
        color: selected ? "var(--up-near-black)" : "var(--text-body)",
        transition: "background var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out)",
        ...style,
      }}
      {...rest}
    >
      {children}
      {onRemove && (
        <button
          aria-label="Remove"
          onClick={onRemove}
          style={{
            border: 0, background: "transparent", cursor: "pointer",
            color: "inherit", opacity: 0.6, padding: 0, display: "inline-flex",
            fontSize: 14, lineHeight: 1,
          }}
        >
          ×
        </button>
      )}
    </span>
  );
}
