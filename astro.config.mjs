// @ts-check
import { defineConfig } from "astro/config";

// Siden publiseres på GitHub Pages under /skogbranner/. Interne lenker og
// ressursstier leses fra import.meta.env.BASE_URL, aldri hardkodet (CLAUDE.md T3).
export default defineConfig({
  site: "https://sheffielddivided.github.io",
  base: "/skogbranner/",
  trailingSlash: "ignore",
  build: {
    format: "directory",
    // Én stilfil framfor innebygde <style>-blokker per komponent, så leseren
    // laster forutsigbart lite.
    inlineStylesheets: "auto",
  },
});
