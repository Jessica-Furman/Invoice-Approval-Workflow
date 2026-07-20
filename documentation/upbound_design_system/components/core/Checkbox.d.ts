import * as React from "react";

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: React.ReactNode;
  checked?: boolean;
  defaultChecked?: boolean;
  disabled?: boolean;
}

/** Checkbox — green fill with near-black check when on. */
export function Checkbox(props: CheckboxProps): JSX.Element;
