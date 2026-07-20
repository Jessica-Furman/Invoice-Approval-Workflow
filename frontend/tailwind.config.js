/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Inter for body/UI (default sans), Poppins for headlines/display.
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Poppins", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      colors: {
        // Upbound Group brand palette — bold green accent + deep, sophisticated darks.
        // 60% dark foundation / 30% neutrals / 10% green (see documentation/upbound_design_system).
        brand: {
          green: "#B3FF33",
          greenHover: "#A2EB2A",
          greenSoft: "#E9FFC2",
          ink: "#1A1A1A", // near-black — primary text, text-on-green, darkest surfaces
          navy: "#35323D", // primary dark surface
          navyHover: "#413E4A",
          charcoal: "#3A3A3B", // secondary dark surface (cards on dark)
          charcoalHover: "#48484A",
          grey: "#C3C2C5", // cool grey — dividers/secondary text on dark
          mist: "#F4F4F5", // off-white — light section fill
        },
      },
      boxShadow: {
        // Soft, single-layer, cool-toned shadows — no harsh drops (see design system spacing-elevation).
        xs: "0 1px 2px rgba(26,26,26,0.06)",
        sm: "0 2px 6px rgba(26,26,26,0.08)",
        md: "0 6px 18px rgba(26,26,26,0.10)",
        lg: "0 16px 40px rgba(26,26,26,0.14)",
        glow: "0 0 0 3px rgba(179,255,51,0.35)",
      },
    },
  },
  plugins: [],
};
