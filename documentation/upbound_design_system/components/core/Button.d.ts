import * as React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual style. primary = green CTA (one per view). */
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
  fullWidth?: boolean;
  disabled?: boolean;
  /** Optional leading element (e.g. an <Icon />). */
  iconLeft?: React.ReactNode;
  /** Optional trailing element (e.g. an <Icon />). */
  iconRight?: React.ReactNode;
  children?: React.ReactNode;
}

/** Primary action element. Pill-shaped; green primary carries the single CTA. */
export function Button(props: ButtonProps): JSX.Element;
