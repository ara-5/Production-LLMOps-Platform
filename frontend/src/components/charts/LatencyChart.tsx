import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TimeseriesPoint } from "../../types/api";
import { AXIS, GRIDLINE, MUTED_INK, SERIES } from "./palette";

function formatBucket(bucket: string): string {
  const d = new Date(bucket);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" }) + " " + d.toLocaleTimeString(undefined, { hour: "2-digit" });
}

export function LatencyChart({ data }: { data: TimeseriesPoint[] }) {
  const rows = data.map((d) => ({
    bucket: formatBucket(d.bucket as string),
    avg: Number(d.avg_latency_ms ?? 0),
    p95: Number(d.p95_latency_ms ?? 0),
  }));

  return (
    <div>
      <div className="legend-row">
        <span>
          <span className="legend-dot" style={{ background: SERIES[0] }} />
          Avg latency
        </span>
        <span>
          <span className="legend-dot" style={{ background: SERIES[1] }} />
          p95 latency
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={rows} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
          <CartesianGrid stroke={GRIDLINE} vertical={false} />
          <XAxis dataKey="bucket" stroke={AXIS} tick={{ fill: MUTED_INK, fontSize: 11 }} tickLine={false} axisLine={{ stroke: AXIS }} minTickGap={40} />
          <YAxis stroke={AXIS} tick={{ fill: MUTED_INK, fontSize: 11 }} tickLine={false} axisLine={false} unit="ms" width={56} />
          <Tooltip
            contentStyle={{ background: "#1a1a19", border: "1px solid #2c2c2a", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#ffffff" }}
          />
          <Line type="monotone" dataKey="avg" name="Avg latency (ms)" stroke={SERIES[0]} strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="p95" name="p95 latency (ms)" stroke={SERIES[1]} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
