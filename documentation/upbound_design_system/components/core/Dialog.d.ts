import * as React from "react";

export interface DialogProps {
  open: boolean;
  onClose?: () => void;
  title?: string;
  children?: React.ReactNode;
  /** Footer node, typically action Buttons. */
  footer?: React.ReactNode;
  /** Width in px. Default 480. */
  width?: number;
  style?: React.CSSProperties;
}

/** Centered modal over a dimmed scrim. */
export function Dialog(props: DialogProps): JSX.Element | null;
