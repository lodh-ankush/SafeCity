import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { TYPE_COLOR_VAR } from "../theme";

// Nominal categorical: each bar IS a distinct incident type (the subject the
// reader needs to identify and later recognize on the map), so bars use the
// same validated type-color mapping as the map markers rather than a single
// sequential hue. Direct Y-axis labels carry identity — no separate legend
// box needed, since color here is a supplementary cross-chart link, not the
// sole identity channel (each bar's own axis label already names it).
export default function IncidentTypeChart({ stats, typeMeta }) {
  const counts = stats?.incidents_by_type;
  if (!counts || Object.keys(counts).length === 0) {
    return <p className="panel-empty">No incidents yet</p>;
  }

  const data = Object.entries(counts)
    .map(([type, count]) => ({ type, count, icon: typeMeta?.[type]?.icon ?? "" }))
    .sort((a, b) => b.count - a.count);

  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * 40)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 28, left: 4, bottom: 4 }}>
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="type"
          width={110}
          tickFormatter={(type) => `${typeMeta?.[type]?.icon ?? ""} ${type.replace("_", " ")}`}
          tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
          axisLine={{ stroke: "var(--baseline)" }}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: "var(--surface-2)" }}
          contentStyle={{
            background: "var(--surface-1)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 12,
            color: "var(--text-primary)",
          }}
          formatter={(value) => [value, "incidents"]}
          labelFormatter={(type) => type.replace("_", " ")}
        />
        <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={22}>
          {data.map((d) => (
            <Cell key={d.type} fill={TYPE_COLOR_VAR[d.type] ?? "var(--text-muted)"} />
          ))}
          <LabelList dataKey="count" position="right" fill="var(--text-secondary)" fontSize={12} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
