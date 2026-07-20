# Upbound Group — Marketing UI Kit

Interactive click-through recreation of the Upbound Group marketing site, built from the brand guidelines (no product source was provided — these are original, on-brand interpretations, not recreations of an existing site).

## Run
Open `index.html`. It loads the design-system bundle (`_ds_bundle.js`), the Lucide icon CDN, and the view files below, then mounts an interactive single-page app.

## Screens / routes
- **Home** (`HomeView.jsx`) — navy hero with the signature diagonal + green dot, trust strip, solutions grid, dark stat band, CTA band.
- **Solutions** (`SolutionsView.jsx`) — tabbed detail (Lending / Payments / Marketplace / Analytics) with a live-metrics card.
- **Investors** (`InvestorsView.jsx`) — financial highlights, events & filings, IR resources.
- **Careers** (`InvestorsView.jsx`) — values from the brand personality + open roles.
- **Sign in** (`SolutionsView.jsx` → `SignInView`) — split navy/form layout.
- **About** + **Request-a-demo dialog** — inline in `index.html`.

## Interactions
Nav routing, solution tabs, request-a-demo dialog (with a sent state), sign-in submit returns home.

## Composition
Chrome (`Chrome.jsx`: `Wordmark`, `Header`, `Footer`) and all views compose the core components (`Button`, `Card`, `Tabs`, `Input`, `Select`, `Checkbox`, `Badge`, `Tag`, `Dialog`, `Icon`) from the bundle — they do not re-implement primitives. The `upbound` wordmark is a Poppins type stand-in (no logo artwork supplied).
