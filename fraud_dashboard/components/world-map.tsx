"use client";

import dynamic from "next/dynamic";
import type { DashboardSnapshot } from "@/lib/types";

type LocationPoint = DashboardSnapshot["byLocation"][number];

// Leaflet touche `window` dès l'import du module : impossible à rendre côté serveur.
const LeafletMap = dynamic(() => import("./leaflet-map").then((m) => m.LeafletMap), {
  ssr: false,
  loading: () => <div className="td-geo-map td-geo-map-loading">Chargement de la carte…</div>
});

export function WorldMap({ points, maxAlerts }: { points: LocationPoint[]; maxAlerts: number }) {
  return <LeafletMap points={points} maxAlerts={maxAlerts} />;
}
