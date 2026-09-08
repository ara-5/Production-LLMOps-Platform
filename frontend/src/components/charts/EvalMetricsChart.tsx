import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { MetricSummary } from "../../types/api";
import { AXIS, colorForMetric, GRIDLINE, MUTED_INK } from "./palette";

export function EvalMetricsChart({ data }: { data: MetricSummary[] }) {
  const rows = data.map((d) => ({ metric: d.metric_name, mean: d.mean, p50: d.p50 }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={rows} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
        <CartesianGrid stroke={GRIDLINE} vertical={false} />
        <XAxis dataKey="metric" stroke={AXIS} tick={{ fill: MUTED_INK, fontSize: 11 }} tickLine={false} axisLine={{ stroke: AXIS }} interval={0} angle={-20} textAnchor="end" height={60} />
        <YAxis domain={[0, 1]} stroke={AXIS} tick={{ fill: MUTED_INK, fontSize: 11 }} tickLine={false} axisLine={false} width={40} />
        <Tooltip
          contentStyle={{ background: "#1a1a19", border: "1px solid #2c2c2a", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "#ffffff" }}
          formatter={(value: number) => [value.toFixed(3), "Mean score"]}
        />
        <Bar dataKey="mean" radius={[4, 4, 0, 0]} maxBarSize={40}>
          {rows.map((row) => (
            <Cell key={row.metric} fill={colorForMetric(row.metric)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
