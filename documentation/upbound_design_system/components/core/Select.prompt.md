**Select** — a styled dropdown; use for choosing one option from a short list.

```jsx
<Select label="Company size" options={["1–50", "51–500", "500+"]} />
```

Pass `options` (strings or `{label,value}`) or `<option>` children. Props: `label`, `hint`, `error`.
