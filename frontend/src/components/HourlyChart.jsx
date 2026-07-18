import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// Single metric (incident count) across an ordered axis (hour-of-day) ->
// magnitude job -> sequential single hue, not categorical. Deliberately
// plots only actual_count: /api/forecast's predicted_count is actual*1.05
// (see backend/core/forecast.py), not a real model output, so showing it
// as a second series would imply a precision the backend doesn't have.
export default function HourlyChart({ forecast }) {
  const hours = forecast?.hourly_timeline;
  if (!hours || hours.length === 0) {
    return <p className="panel-empty">Not enough data yet (need 3+ incidents)</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={hours} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <XAxis
          dataKey="hour"
          tickFormatter={(h) => (h % 6 === 0 ? `${h}:00` : "")}
          tick={{ fill: "var(--text-muted)", fontSize: 11 }}
          axisLine={{ stroke: "var(--baseline)" }}
          tickLine={false}
          interval={0}
        />
        <YAxis
          tick={{ fill: "var(--text-muted)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          allowDecimals={false}
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
          labelFormatter={(h) => `${h}:00`}
        />
        <Bar dataKey="actual_count" fill="var(--series-blue)" radius={[3, 3, 0, 0]} maxBarSize={18} />
      </BarChart>
    </ResponsiveContainer>
  );
}
