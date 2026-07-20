import React from "react";

/**
 * Card — flat surface with hairline border + soft single-layer shadow.
 * No colored left-borders. Optional hover lift for interactive cards.
 */
export function Card({ interactive = false, padding = 24, children, style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  return (
    <div
      className="up-card"
      onMouseEnter={() => interactive && setHover(true)}
      onMouseLeave={() => interactive && setHover(false)}
      style={{
        background: "var(--surface-card)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        boxShadow: hover ? "var(--shadow-md)" : "var(--shadow-sm)",
        padding,
        transition: "box-shadow var(--dur-base) var(--ease-out), transform var(--dur-base) var(--ease-out)",
        transform: hover ? "translateY(-2px)" : "translateY(0)",
        cursor: interactive ? "pointer" : "default",
        ...style,
      }}
      {...rest}
    >
      {children}
    </div>
  );
}
