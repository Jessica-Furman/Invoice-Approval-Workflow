import * as React from "react";

export interface TabsProps {
  /** Tabs as {label,value} objects or plain strings. */
  tabs: Array<{ label: string; value: string } | string>;
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  style?: React.CSSProperties;
}

/** Underline tab set; active tab underlined in green. */
export function Tabs(props: TabsProps): JSX.Element;
