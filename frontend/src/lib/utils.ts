import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

export function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—";
  return `${seconds.toFixed(1)}s`;
}

/**
 * Symbol units sit tight against the number ("31.4°", "1.8:1"); word units need
 * a space ("0.2 shoulder widths"). One `ml-1` for both gave us "31.4 °" and
 * "0.2shoulder widths" at the same time.
 */
const TIGHT_UNITS = new Set(["°", ":1", "%"]);

export function unitIsTight(unit: string): boolean {
  return TIGHT_UNITS.has(unit);
}

/** Render an ideal range with its unit, e.g. "60–120°" or "0–0.6 shoulder widths". */
export function formatRange(range: [number, number], unit: string): string {
  const span = `${range[0]}–${range[1]}`;
  if (!unit || unit === ":1") return span; // "2.2–3.8" already reads as a ratio
  return unitIsTight(unit) ? `${span}${unit}` : `${span} ${unit}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
