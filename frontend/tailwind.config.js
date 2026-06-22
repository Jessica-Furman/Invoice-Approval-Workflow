/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      colors: {
        // Upbound brand: deep charcoal-purple "ink" + chartreuse "lime" accent.
        brand: {
          ink: "#2a2833",
          inkdark: "#1d1c26",
          inklight: "#3a3848",
          lime: "#a4d61e",
          limedark: "#8bbb12",
          limeglow: "#c6f24a",
        },
      },
      boxShadow: {
        glow: "0 0 0 3px rgba(164,214,30,0.25)",
      },
    },
  },
  plugins: [],
};
