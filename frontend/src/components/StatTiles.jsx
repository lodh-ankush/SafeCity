import { SEVERITY } from "../theme";

const SEVERITY_ICON = { critical: "⛔", high: "🔺", medium: "🔶", low: "✅" };

function formatCompact(n) {
  if (n == null) return "—";
  return new Intl.NumberFormat("en", { notation: "compact" }).format(n);
}

export default function StatTiles({ stats }) {
  return (
    <section className="stat-row" aria-label="Key metrics">
      <div className="stat-tile">
        <span className="stat-label">Total incidents</span>
        <span className="stat-value">{formatCompact(stats?.total_incidents)}</span>
      </div>
      <div className="stat-tile">
        <span className="stat-label">Total events logged</span>
        <span className="stat-value">{formatCompact(stats?.total_events)}</span>
      </div>
      {["critical", "high", "medium", "low"].map((level) => (
        <div className="stat-tile stat-tile--status" key={level}>
          <span className="stat-label">
            <span aria-hidden="true">{SEVERITY_ICON[level]}</span> {SEVERITY[level].label}
          </span>
          <span className="stat-value" style={{ color: SEVERITY[level].color }}>
            {formatCompact(stats?.severity_breakdown?.[level])}
          </span>
        </div>
      ))}
    </section>
  );
}
