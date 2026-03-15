/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          500: "#4a7fff",
          600: "#3b6fe8",
          700: "#315fd0"
        },
        surface: {
          900: "#f7f7fb",
          800: "#ffffff"
        }
      },
      boxShadow: {
        card: "0 18px 40px rgba(15, 23, 42, 0.12)"
      }
    }
  },
  plugins: []
};

