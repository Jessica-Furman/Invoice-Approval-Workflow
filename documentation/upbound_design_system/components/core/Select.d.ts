import * as React from "react";

export interface SelectOption { label: string; value: string; }

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
  error?: string;
  /** Options as {label,value} objects or plain strings; or pass <option> children. */
  options?: Array<SelectOption | string>;
}

/** Styled native select with label and hint. */
export function Select(props: SelectProps): JSX.Element;
