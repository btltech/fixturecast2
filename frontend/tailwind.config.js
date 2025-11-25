
/** @type {import('tailwindcss').Config} */
export default {
    content: ['./src/**/*.{html,js,svelte,ts}'],
    theme: {
        extend: {
            colors: {
                primary: '#0f172a', // Slate 900
                secondary: '#1e293b', // Slate 800
                accent: '#38bdf8', // Sky 400
                success: '#10b981', // Emerald 500
                danger: '#ef4444', // Red 500
                warning: '#f59e0b', // Amber 500
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            }
        },
    },
    plugins: [],
}
