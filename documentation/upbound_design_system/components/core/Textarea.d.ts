import * as React from "react";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
  rows?: number;
}

/** Multi-line text field, matching Input's visual language. */
export function Textarea(props: TextareaProps): JSX.Element;
