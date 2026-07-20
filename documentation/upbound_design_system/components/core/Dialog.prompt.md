**Dialog** — a centered modal over a dimmed scrim; use for focused confirmations and short forms.

```jsx
<Dialog open={open} onClose={close} title="Request a demo"
  footer={<><Button variant="ghost" onClick={close}>Cancel</Button><Button>Send</Button></>}>
  <p>We'll be in touch within one business day.</p>
</Dialog>
```

Props: `open`, `onClose`, `title`, `footer`, `width`.
