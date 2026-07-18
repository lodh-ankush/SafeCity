import { SEVERITY, severityFromScore } from "../theme";

export default function IncidentFeed({ incidents, typeMeta }) {
  if (!incidents || incidents.length === 0) {
    return <p className="panel-empty">No incidents match the current filters</p>;
  }

  return (
    <div className="feed-list">
      {incidents.map((incident) => {
        const severity = SEVERITY[severityFromScore(incident.fused_score)];
        const isLive = typeof incident.id === "string" && incident.id.startsWith("live-");
        return (
          <div key={incident.id} className={`feed-row${isLive ? " feed-row--live" : ""}`}>
            <span className="feed-icon" aria-hidden="true">
              {typeMeta?.[incident.type]?.icon ?? "❓"}
            </span>
            <div className="feed-main">
              <div className="feed-type-row">
                <span className="feed-type">{incident.type.replace("_", " ")}</span>
                <span className="feed-time">{incident.timestamp}</span>
              </div>
              {(incident.summary || incident.raw_text) && (
                <p className="feed-text">{incident.summary || incident.raw_text}</p>
              )}
            </div>
            <span
              className="feed-score"
              style={{ background: `color-mix(in srgb, ${severity.color} 18%, transparent)`, color: severity.color }}
            >
              {Number(incident.fused_score).toFixed(2)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
