**Icon** — a single-weight, monochrome geometric line icon (Lucide substitute set); use anywhere a small glyph is needed, keeping icons `currentColor` and reserving green for the one thing that matters most.

```jsx
<Icon name="trending-up" size={20} />
<Icon name="arrow-up-right" size={16} strokeWidth={1.75} />
```

Requires the Lucide CDN on the page: `<script src="https://unpkg.com/lucide@latest"></script>`. Props: `name` (Lucide id), `size` (px, default 20), `strokeWidth` (default 1.75), `color` (defaults to inherit).
