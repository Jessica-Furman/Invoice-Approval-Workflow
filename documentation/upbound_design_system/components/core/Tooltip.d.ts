import * as React from "react";

export interface TooltipProps {
  /** Text shown on hover/focus. */
  label: React.ReactNode;
  side?: "top" | "bottom" | "left" | "right";
  children: React.ReactNode;
  style?: React.CSSProperties;
}

/** Hover/focus label on a near-black surface. */
export function Tooltip(props: TooltipProps): JSX.Element;
