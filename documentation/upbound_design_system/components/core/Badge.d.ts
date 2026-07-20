import * as React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: "neutral" | "accent" | "success" | "warning" | "danger" | "info";
  children?: React.ReactNode;
}

/** Small status or count marker. */
export function Badge(props: BadgeProps): JSX.Element;
