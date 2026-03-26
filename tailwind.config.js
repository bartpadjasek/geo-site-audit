/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./pages/**/*.{js,jsx}", "./components/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Inter", "Georgia", "serif"],
      },
      colors: {
        burgundy: {
          DEFAULT: "#47072C",
          light: "#6B0F3E",
          50: "#FFF0F7",
          100: "#FFD6EB",
          200: "#FFC1E8",
          300: "#D873AE",
          400: "#8E2560",
          500: "#6B0F3E",
          600: "#47072C",
          700: "#350520",
        },
        fuchsia: {
          DEFAULT: "#FA1E81",
          light: "#FFC1E8",
          50: "#FFE9F7",
          100: "#FFC1E8",
          500: "#FA1E81",
        },
        beige: {
          DEFAULT: "#EEE6DD",
          50: "#FDFBFA",
          100: "#F7F3EF",
          200: "#EEE6DD",
          300: "#EBE1D6",
          400: "#E6D9CC",
        },
        teal: {
          DEFAULT: "#5B7979",
          50: "#CCD5D5",
          100: "#B4C1C1",
          200: "#91A5A5",
          300: "#7C9494",
          400: "#5B7979",
        },
        ink: "#232323",
      },
    },
  },
  plugins: [],
};
