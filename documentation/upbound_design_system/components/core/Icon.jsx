import React, { useEffect, useRef } from "react";

/**
 * Icon — single-weight, monochrome line icon (Lucide substitute set).
 * Renders currentColor so it inherits text color. Reserve green for at most
 * one icon per view. Requires the Lucide CDN script on the page:
 *   <script src="https://unpkg.com/lucide@latest"></script>
 */
export function Icon({ name, size = 20, strokeWidth = 1.75, color, style, className = "", ...rest }) {
  const ref = useRef(null);

  useEffect(() => {
    if (window.lucide && ref.current) {
      // Re-render just this node's icon
      window.lucide.createIcons({
        icons: window.lucide.icons,
        attrs: { "stroke-width": strokeWidth },
        nameAttr: "data-lucide",
      });
    }
  }, [name, strokeWidth]);

  return (
    <i
      ref={ref}
      data-lucide={name}
      className={`up-icon ${className}`}
      style={{
        display: "inline-flex",
        width: size,
        height: size,
        color: color || "inherit",
        verticalAlign: "middle",
        ...style,
      }}
      {...rest}
    />
  );
}
