"use client";

import "leaflet/dist/leaflet.css";
import { useEffect, useMemo, useState } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { DashboardSnapshot } from "@/lib/types";
import { riskToneGlow, RISK_LEGEND, type RiskLevel } from "@/lib/risk";

type LocationPoint = DashboardSnapshot["byLocation"][number];

const DARK_TILES = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const LIGHT_TILES = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

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

/** Recadre la vue sur les villes actives à chaque changement du jeu de points. */
function FitToPoints({ positions }: { positions: Array<[number, number]> }) {
  const map = useMap();

  useEffect(() => {
    if (positions.length === 0) return;
    if (positions.length === 1) {
      map.setView(positions[0], 5);
      return;
    }
    map.fitBounds(positions, { padding: [36, 36], maxZoom: 6 });
  }, [map, positions]);

  return null;
}

/**
 * Leaflet fige sa taille interne au montage : si le conteneur n'a pas encore sa
 * hauteur finale (layout grid/flex pas tout à fait résolu à cet instant), la carte
 * reste rendue en 0x0 malgré des tuiles présentes dans le DOM. On réinvalide la
 * taille à chaque changement réel de dimensions.
 */
function InvalidateOnResize() {
  const map = useMap();

  useEffect(() => {
    const container = map.getContainer();
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(container);
    return () => observer.disconnect();
  }, [map]);

  return null;
}

/** Suit le thème clair/sombre appliqué sur <html data-theme> pour choisir le fond de carte. */
function useDocumentTheme(): "light" | "dark" {
  const [theme, setTheme] = useState<"light" | "dark">("dark");

  useEffect(() => {
    const read = () =>
      setTheme(document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark");
    read();
    const observer = new MutationObserver(read);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  return theme;
}

export function LeafletMap({ points, maxAlerts }: { points: LocationPoint[]; maxAlerts: number }) {
  const theme = useDocumentTheme();

  const pins = useMemo(() => {
    const maxRate = Math.max(0.0001, ...points.map((loc) => loc.ratePct));
    return points
      .filter((loc): loc is LocationPoint & { coords: [number, number] } => Boolean(loc.coords))
      .map((loc) => {
        const volumeRatio = loc.alerts / Math.max(1, maxAlerts);
        const level = relativeSeverity(loc.ratePct / maxRate);
        return {
          loc,
          // Leaflet attend [lat, lon] ; nos coords sont stockées [lon, lat] (convention GeoJSON).
          position: [loc.coords[1], loc.coords[0]] as [number, number],
          radius: 6 + Math.max(0.18, volumeRatio) * 13,
          color: riskToneGlow(level)
        };
      });
  }, [points, maxAlerts]);

  const positions = useMemo(() => pins.map((p) => p.position), [pins]);

  return (
    <div className="td-geo-map" aria-label="Carte de répartition géographique des transactions">
      <MapContainer
        center={[20, 60]}
        zoom={3}
        scrollWheelZoom
        worldCopyJump
        className="td-leaflet-container"
      >
        <TileLayer
          key={theme}
          url={theme === "dark" ? DARK_TILES : LIGHT_TILES}
          attribution={TILE_ATTRIBUTION}
          subdomains="abcd"
          maxZoom={19}
        />
        <FitToPoints positions={positions} />
        <InvalidateOnResize />
        {pins.map(({ loc, position, radius, color }) => (
          <CircleMarker
            key={loc.name}
            center={position}
            radius={radius}
            pathOptions={{ color: "#0a1220", weight: 1.5, fillColor: color, fillOpacity: 0.85 }}
          >
            <Tooltip direction="top" offset={[0, -radius]} opacity={1} className="td-leaflet-tooltip">
              <div className="td-map-tooltip-title">{loc.name}</div>
              <div className="td-map-tooltip-row">
                <span>Alertes</span>
                <strong>{nf(loc.alerts)}</strong>
              </div>
              <div className="td-map-tooltip-row">
                <span>Taux</span>
                <strong>{pct(loc.ratePct)}</strong>
              </div>
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>

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
