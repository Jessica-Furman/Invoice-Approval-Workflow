import * as React from "react";

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Lucide icon name (shortcut for rendering an <Icon />). */
  name?: string;
  /** Or pass a custom icon node. */
  icon?: React.ReactNode;
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
  /** Pill (circular) instead of rounded-square. */
  round?: boolean;
  disabled?: boolean;
  /** Required for accessibility. */
  "aria-label": string;
}

/** Square or round button holding a single icon. */
export function IconButton(props: IconButtonProps): JSX.Element;
