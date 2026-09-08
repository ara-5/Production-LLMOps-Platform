import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CostBreakdownRow } from "../../types/api";
import { AXIS, colorForModel, GRIDLINE, MUTED_INK } from "./palette";

export function CostBreakdownChart({ data }: { data: CostBreakdownRow[] }) {
  const rows = data.map((d) => ({ label: String(d.group_key ?? "unknown"), cost: d.cost_usd }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 0 }}>
        <CartesianGrid stroke={GRIDLINE} horizontal={false} />
        <XAxis type="number" stroke={AXIS} tick={{ fill: MUTED_INK, fontSize: 11 }} tickLine={false} axisLine={{ stroke: AXIS }} tickFormatter={(v) => `$${v}`} />
        <YAxis type="category" dataKey="label" stroke={AXIS} tick={{ fill: MUTED_INK, fontSize: 12 }} tickLine={false} axisLine={false} width={130} />
        <Tooltip
          contentStyle={{ background: "#1a1a19", border: "1px solid #2c2c2a", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "#ffffff" }}
          formatter={(value: number) => [`$${value.toFixed(4)}`, "Cost"]}
        />
        <Bar dataKey="cost" radius={[0, 4, 4, 0]} maxBarSize={26}>
          {rows.map((row) => (
            <Cell key={row.label} fill={colorForModel(row.label)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
