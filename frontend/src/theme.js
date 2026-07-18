// Categorical (identity) colors for incident types, as CSS custom property
// references so light/dark resolution happens via the cascade in index.css
// rather than being duplicated here. Backend's /api/config/incident-types
// returns the matching light-mode hex + icon + severity_base; this map only
// owns *which CSS var* (i.e. which validated slot) each type uses.
//
// Only 4 hues (blue/green/magenta/yellow) pass the all-pairs CVD/contrast
// check the map view needs (see dataviz skill: "first four slots validate
// all-pairs in both modes"). violence_suspected and unknown share a muted
// gray and rely on their icon, not color, for identity.
export const TYPE_COLOR_VAR = {
  accident: "var(--series-blue)",
  emergency: "var(--series-green)",
  fire: "var(--series-magenta)",
  traffic: "var(--series-yellow)",
  violence_suspected: "var(--text-muted)",
  unknown: "var(--text-muted)",
};

// Status (state) palette — fixed, reserved meaning, never themed. Same hex
// in both modes (validated to clear 3:1 contrast on both surfaces).
export const SEVERITY = {
  critical: { color: "#d03b3b", label: "Critical" },
  high: { color: "#ec835a", label: "High" },
  medium: { color: "#fab219", label: "Medium" },
  low: { color: "#0ca30c", label: "Low" },
};

export function severityFromScore(score) {
  if (score >= 0.8) return "critical";
  if (score >= 0.6) return "high";
  if (score >= 0.4) return "medium";
  return "low";
}

export function prefersDark() {
  return (
    document.documentElement.getAttribute("data-theme") === "dark" ||
    (document.documentElement.getAttribute("data-theme") !== "light" &&
      window.matchMedia?.("(prefers-color-scheme: dark)").matches)
  );
}
