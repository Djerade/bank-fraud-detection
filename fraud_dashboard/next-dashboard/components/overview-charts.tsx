"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { DashboardSnapshot } from "@/lib/types";

const COLORS = ["#66b2ff", "#8fe388", "#ffb55e", "#ff7a7a", "#c6a5ff", "#4dd0e1"];

type Props = {
  data: DashboardSnapshot;
};

export function OverviewCharts({ data }: Props) {
  return (
    <>
      <div className="grid chart-grid">
        <div className="panel">
          <h3>Volume et taux d alerte (par minute)</h3>
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer>
              <LineChart data={data.series}>
                <CartesianGrid stroke="#203150" strokeDasharray="3 3" />
                <XAxis
                  dataKey="minute"
                  tickFormatter={(v) => new Date(v).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
                  stroke="#92a5cb"
                />
                <YAxis yAxisId="left" stroke="#92a5cb" />
                <YAxis yAxisId="right" orientation="right" stroke="#92a5cb" />
                <Tooltip
                  contentStyle={{ background: "#081427", border: "1px solid #28416a" }}
                  labelFormatter={(v) => new Date(v).toLocaleString("fr-FR")}
                />
                <Bar yAxisId="left" dataKey="volume" fill="#4ea2ff" radius={[8, 8, 0, 0]} />
                <Line yAxisId="right" dataKey="alertRatePct" stroke="#ff875c" strokeWidth={2.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <h3>Distribution des scores</h3>
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer>
              <BarChart data={data.scoreDistribution}>
                <CartesianGrid stroke="#203150" strokeDasharray="3 3" />
                <XAxis dataKey="bucket" stroke="#92a5cb" />
                <YAxis stroke="#92a5cb" />
                <Tooltip contentStyle={{ background: "#081427", border: "1px solid #28416a" }} />
                <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                  {data.scoreDistribution.map((entry, idx) => (
                    <Cell key={entry.bucket} fill={COLORS[idx % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid chart-grid-eq" style={{ marginTop: 16 }}>
        <div className="panel">
          <h3>Alertes par type de transaction</h3>
          <div style={{ width: "100%", height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={data.byType}>
                <CartesianGrid stroke="#203150" strokeDasharray="3 3" />
                <XAxis dataKey="name" stroke="#92a5cb" />
                <YAxis stroke="#92a5cb" />
                <Tooltip contentStyle={{ background: "#081427", border: "1px solid #28416a" }} />
                <Bar dataKey="volume" fill="#3f9bff" radius={[8, 8, 0, 0]} />
                <Bar dataKey="alerts" fill="#ff5d7e" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <h3>Alertes par categorie marchande</h3>
          <div style={{ width: "100%", height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={data.byMerchant} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid stroke="#203150" strokeDasharray="3 3" />
                <XAxis type="number" stroke="#92a5cb" />
                <YAxis type="category" dataKey="name" stroke="#92a5cb" width={90} />
                <Tooltip contentStyle={{ background: "#081427", border: "1px solid #28416a" }} />
                <Bar dataKey="alerts" fill="#ff7a55" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </>
  );
}
