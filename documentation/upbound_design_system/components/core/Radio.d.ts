import * as React from "react";

export interface RadioProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: React.ReactNode;
  checked?: boolean;
  disabled?: boolean;
}

export interface RadioGroupProps {
  name?: string;
  value?: string;
  onChange?: (value: string) => void;
  options?: Array<{ label: string; value: string } | string>;
  style?: React.CSSProperties;
}

/** Single choice control. */
export function Radio(props: RadioProps): JSX.Element;
/** Manages a set of Radios by value. */
export function RadioGroup(props: RadioGroupProps): JSX.Element;
