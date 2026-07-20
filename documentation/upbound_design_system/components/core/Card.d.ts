import * as React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Adds hover lift + pointer for clickable cards. */
  interactive?: boolean;
  /** Inner padding in px. Default 24. */
  padding?: number;
  children?: React.ReactNode;
}

/** Flat content surface with hairline border and soft single-layer shadow. */
export function Card(props: CardProps): JSX.Element;
