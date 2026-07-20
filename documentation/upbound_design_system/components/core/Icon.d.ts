import * as React from "react";

export interface IconProps extends React.HTMLAttributes<HTMLElement> {
  /** Lucide icon name, e.g. "arrow-up-right", "check", "trending-up" */
  name: string;
  /** Pixel size (width & height). Default 20. */
  size?: number;
  /** Stroke width. Brand default 1.75 (single weight). */
  strokeWidth?: number;
  /** Override color. Defaults to currentColor (monochrome). */
  color?: string;
}

/**
 * Single-weight, monochrome geometric line icon (Lucide substitute set).
 * Reserve green for at most one icon per view.
 */
export function Icon(props: IconProps): JSX.Element;
