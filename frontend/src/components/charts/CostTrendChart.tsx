import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TimeseriesPoint } from "../../types/api";
import { AXIS, GRIDLINE, MUTED_INK, SERIES } from "./palette";

export function CostTrendChart({ data }: { data: TimeseriesPoint[] }) {
  const rows = data.map((d) => ({
    bucket: new Date(d.bucket as string).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    cost: Number(d.cost_usd ?? 0),
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={rows} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
        <CartesianGrid stroke={GRIDLINE} vertical={false} />
        <XAxis dataKey="bucket" stroke={AXIS} tick={{ fill: MUTED_INK, fontSize: 11 }} tickLine={false} axisLine={{ stroke: AXIS }} />
        <YAxis stroke={AXIS} tick={{ fill: MUTED_INK, fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} width={56} />
        <Tooltip
          contentStyle={{ background: "#1a1a19", border: "1px solid #2c2c2a", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "#ffffff" }}
          formatter={(value: number) => [`$${value.toFixed(4)}`, "Cost"]}
        />
        <Bar dataKey="cost" name="Cost (USD)" fill={SERIES[0]} radius={[4, 4, 0, 0]} maxBarSize={28} />
      </BarChart>
    </ResponsiveContainer>
  );
}
