/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#f5f3ff",
          100: "#ede9fe",
          200: "#ddd6fe",
          500: "#7c3aed",
          600: "#6d28d9"
        },
        surface: {
          900: "#050816",
          800: "#0b1020"
        }
      },
      boxShadow: {
        card: "0 18px 40px rgba(15, 23, 42, 0.45)"
      }
    }
  },
  plugins: []
};

