import * as React from "react";

export interface ToastProps {
  tone?: "neutral" | "success" | "warning" | "danger";
  title?: string;
  children?: React.ReactNode;
  onClose?: () => void;
  style?: React.CSSProperties;
}

/** Transient notification on a dark surface with an accent bar. */
export function Toast(props: ToastProps): JSX.Element;
