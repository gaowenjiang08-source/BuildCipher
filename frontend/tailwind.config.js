/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#dce8ff",
          500: "#2f6fed",
          600: "#1f5bd8",
          700: "#1849a9"
        }
      },
      boxShadow: {
        panel: "0 8px 22px rgba(15, 23, 42, 0.08)",
      }
    },
  },
  plugins: [],
};
