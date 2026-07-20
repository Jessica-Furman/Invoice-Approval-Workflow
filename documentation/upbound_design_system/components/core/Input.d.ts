import * as React from "react";

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> {
  label?: string;
  /** Helper text below the field. */
  hint?: string;
  /** Error message; overrides hint and turns the field red. */
  error?: string;
  /** Optional leading icon node. */
  iconLeft?: React.ReactNode;
}

/** Single-line text field with label, hint, and error states. */
export function Input(props: InputProps): JSX.Element;
