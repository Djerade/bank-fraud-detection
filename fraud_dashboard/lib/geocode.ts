import "server-only";
import cities from "all-the-cities";

/**
 * Résolution de coordonnées à la volée pour n'importe quel nom de ville présent
 * dans le flux (`transaction_location`), au lieu d'une liste figée. Base : Geonames
 * (via `all-the-cities`, ~135k villes). En cas d'homonymie (ex. plusieurs "London"),
 * on retient la ville la plus peuplée.
 */
let index: Map<string, [number, number]> | null = null;

function buildIndex(): Map<string, [number, number]> {
  const byName = new Map<string, [number, number, number]>(); // [lon, lat, population]
  for (const city of cities) {
    const key = city.name.trim().toLowerCase();
    const existing = byName.get(key);
    if (!existing || city.population > existing[2]) {
      byName.set(key, [city.loc.coordinates[0], city.loc.coordinates[1], city.population]);
    }
  }
  const result = new Map<string, [number, number]>();
  for (const [key, [lon, lat]] of byName) {
    result.set(key, [lon, lat]);
  }
  return result;
}

export function resolveCityCoordinates(name: string): [number, number] | null {
  if (!index) {
    index = buildIndex();
  }
  return index.get(name.trim().toLowerCase()) ?? null;
}
