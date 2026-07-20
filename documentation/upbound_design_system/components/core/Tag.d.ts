import * as React from "react";

export interface TagProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Green accent selected state. */
  selected?: boolean;
  /** If provided, renders a remove (×) affordance. */
  onRemove?: () => void;
  children?: React.ReactNode;
}

/** Pill-shaped label / filter chip, optionally removable. */
export function Tag(props: TagProps): JSX.Element;
