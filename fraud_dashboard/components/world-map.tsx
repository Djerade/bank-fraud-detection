"use client";

import { useId, useMemo, useState } from "react";
import { geoGraticule10, geoNaturalEarth1, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";
import worldTopology from "world-atlas/countries-110m.json";
import type { DashboardSnapshot } from "@/lib/types";
import { riskToneGlow, RISK_LEGEND, type RiskLevel } from "@/lib/risk";

const WIDTH = 960;
const HEIGHT = 620;
const MAP_PADDING = 42;

const countryFeatures = feature(
  worldTopology as unknown as Topology,
  (worldTopology as unknown as Topology).objects.countries as GeometryCollection
).features;

type LocationPoint = DashboardSnapshot["byLocation"][number];

function pct(value: number, digits = 1): string {
  return `${value.toFixed(digits)} %`;
}

function nf(value: number): string {
  return new Intl.NumberFormat("fr-FR").format(value);
}

/** Sévérité relative au taux d'alerte le plus élevé parmi les zones affichées (quartiles). */
function relativeSeverity(ratio: number): RiskLevel {
  if (ratio >= 0.75) return "critical";
  if (ratio >= 0.5) return "high";
  if (ratio >= 0.25) return "medium";
  return "low";
}

export function WorldMap({ points, maxAlerts }: { points: LocationPoint[]; maxAlerts: number }) {
  const clipId = useId();
  const [hovered, setHovered] = useState<string | null>(null);

  /** Recentre et zoome sur les villes réellement actives plutôt que d'afficher le globe entier. */
  const { pathGenerator, spherePath, graticulePath, projection } = useMemo(() => {
    const proj = geoNaturalEarth1();
    const pointFeatures = points
      .filter((loc): loc is LocationPoint & { coords: [number, number] } => Boolean(loc.coords))
      .map((loc) => ({
        type: "Feature" as const,
        geometry: { type: "Point" as const, coordinates: loc.coords },
        properties: {}
      }));
    const uniqueCoords = new Set(pointFeatures.map((f) => f.geometry.coordinates.join(","))).size;

    if (uniqueCoords > 1) {
      proj.fitExtent(
        [
          [MAP_PADDING, MAP_PADDING],
          [WIDTH - MAP_PADDING, HEIGHT - MAP_PADDING]
        ],
        { type: "FeatureCollection", features: pointFeatures }
      );
    } else {
      // Pas assez de villes distinctes pour cadrer dessus : globe entier par défaut.
      proj.fitSize([WIDTH, HEIGHT], { type: "Sphere" });
    }

    const gen = geoPath(proj);
    return {
      projection: proj,
      pathGenerator: gen,
      spherePath: gen({ type: "Sphere" }) ?? "",
      graticulePath: gen(geoGraticule10()) ?? ""
    };
  }, [points]);

  const pins = useMemo(() => {
    const maxRate = Math.max(0.0001, ...points.map((loc) => loc.ratePct));
    return points
      .map((loc) => {
        if (!loc.coords) return null;
        const projected = projection(loc.coords);
        if (!projected) return null;
        const [x, y] = projected;
        const volumeRatio = loc.alerts / Math.max(1, maxAlerts);
        const level = relativeSeverity(loc.ratePct / maxRate);
        return {
          loc,
          x,
          y,
          radius: 5 + Math.max(0.18, volumeRatio) * 11,
          color: riskToneGlow(level)
        };
      })
      .filter((p): p is NonNullable<typeof p> => p !== null)
      .sort((a, b) => b.radius - a.radius);
  }, [points, maxAlerts, projection]);

  const topPin = pins[0];

  const active = pins.find((p) => p.loc.name === hovered) ?? null;

  return (
    <div className="td-geo-map" aria-label="Carte de répartition géographique des transactions">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="xMidYMid meet">
        <defs>
          <radialGradient id={`${clipId}-ocean`} cx="35%" cy="30%" r="85%">
            <stop offset="0%" stopColor="#16233f" />
            <stop offset="100%" stopColor="#0a1220" />
          </radialGradient>
          <radialGradient id={`${clipId}-glow`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.55" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
          </radialGradient>
          <clipPath id={`${clipId}-sphere`}>
            <path d={spherePath} />
          </clipPath>
        </defs>

        <g clipPath={`url(#${clipId}-sphere)`}>
          <path d={spherePath} fill={`url(#${clipId}-ocean)`} />
          <path d={graticulePath} className="td-graticule" />
          {countryFeatures.map((f, i) => (
            <path key={i} d={pathGenerator(f) ?? undefined} className="td-land" />
          ))}
        </g>
        <path d={spherePath} className="td-sphere-outline" />

        {pins.map(({ loc, x, y, radius, color }) => {
          const isActive = hovered === loc.name;
          const showLabel = isActive || loc.name === topPin?.loc.name;
          return (
            <g
              key={loc.name}
              transform={`translate(${x} ${y})`}
              className="td-map-pin-group"
              style={{ color }}
              onMouseEnter={() => setHovered(loc.name)}
              onMouseLeave={() => setHovered((cur) => (cur === loc.name ? null : cur))}
            >
              <circle r={radius + 14} fill={`url(#${clipId}-glow)`} />
              {isActive && <circle r={radius + 6} className="td-map-pulse" style={{ stroke: color }} />}
              <circle r={radius} className="td-map-pin" style={{ fill: color }} />
              {showLabel && (
                <text x={radius + 7} y={4} className="td-map-label">
                  {loc.name}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {active && (
        <div
          className="td-map-tooltip"
          style={{ left: `${(active.x / WIDTH) * 100}%`, top: `${(active.y / HEIGHT) * 100}%` }}
        >
          <div className="td-map-tooltip-title">{active.loc.name}</div>
          <div className="td-map-tooltip-row">
            <span>Alertes</span>
            <strong>{nf(active.loc.alerts)}</strong>
          </div>
          <div className="td-map-tooltip-row">
            <span>Taux</span>
            <strong>{pct(active.loc.ratePct)}</strong>
          </div>
        </div>
      )}

      <div className="td-map-legend">
        {RISK_LEGEND.map((item) => (
          <span key={item.level} className="td-map-legend-item">
            <span className="td-map-legend-dot" style={{ background: riskToneGlow(item.level) }} />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}
