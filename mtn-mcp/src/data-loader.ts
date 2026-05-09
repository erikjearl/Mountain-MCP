import { readFileSync, readdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { parse } from "csv-parse/sync";

const __dirname = dirname(fileURLToPath(import.meta.url));
export const DATA_DIR = join(__dirname, "..", "..", "mtn-data");

// ── Types ──────────────────────────────────────────────────────────────────

export interface Tick {
  Route: string;   // URL slug, e.g. "illusion-dweller"
  Name: string;    // Mountain Project username
  Date: string;    // "Apr 21, 2026"
  Details: string; // "Lead / Onsight. · 5 pitch  Great route"
}

export interface Route {
  Route: string;   // URL slug (PK)
  Name: string;    // Full route name
  Grade: string;   // "5.10b" or "V3"
  Type: string;    // "Trad", "Sport", "Boulder", "TR", "Trad, Sport"
  Length: string;  // "100 ft" or "" for boulders
  AreaID: string;  // Numeric area ID as string
}

export interface Area {
  AreaID: string;   // Numeric area ID (PK)
  Name: string;     // "Sentinel - W Face"
  ParentID: string; // Parent area ID, empty for top-level
  FullPath: string; // "California > Joshua Tree NP > ... > Sentinel - W Face"
}

// ── File discovery ─────────────────────────────────────────────────────────

// Returns the path to the most recent CSV for a given crag and file type.
// prefix: "ticks" | "routes" | "areas"
function findLatestFile(subdir: string, prefix: string, crag: string): string | null {
  const dir = join(DATA_DIR, subdir);
  let files: string[];
  try {
    files = readdirSync(dir).filter(
      (f) => f.startsWith(`${prefix}_${crag}_`) && f.endsWith(".csv")
    );
  } catch {
    return null;
  }
  if (files.length === 0) return null;
  files.sort().reverse(); // ISO date suffix sorts lexicographically
  return join(dir, files[0]);
}

// Returns all crag keys that have at least a ticks CSV.
export function availableCrags(): string[] {
  let files: string[];
  try {
    files = readdirSync(join(DATA_DIR, "ticks"));
  } catch {
    return [];
  }
  return [
    ...new Set(
      files
        .filter((f) => f.startsWith("ticks_") && f.endsWith(".csv"))
        .map((f) => f.replace(/^ticks_/, "").replace(/_\d{8}\.csv$/, ""))
    ),
  ].sort();
}

// ── Loaders ────────────────────────────────────────────────────────────────

function loadCsv<T>(path: string): T[] {
  const content = readFileSync(path, "utf-8");
  return parse(content, { columns: true, skip_empty_lines: true }) as T[];
}

export function loadTicks(crag: string): Tick[] {
  const path = findLatestFile("ticks", "ticks", crag);
  if (!path) throw new Error(`No ticks data found for crag: ${crag}`);
  return loadCsv<Tick>(path);
}

export function loadRoutes(crag: string): Route[] {
  const path = findLatestFile("routes", "routes", crag);
  if (!path) throw new Error(`No routes data found for crag: ${crag}`);
  return loadCsv<Route>(path);
}

export function loadAreas(crag: string): Area[] {
  const path = findLatestFile(join("routes", "areas"), "areas", crag);
  if (!path) throw new Error(`No areas data found for crag: ${crag}`);
  return loadCsv<Area>(path);
}

// ── Helpers ────────────────────────────────────────────────────────────────

// Parses pitch count from a Details string. Returns 1 if not found.
export function parsePitches(details: string): number {
  const match = details.match(/(\d+)\s+pitch/);
  return match ? parseInt(match[1], 10) : 1;
}

// Parses a tick date string ("Apr 21, 2026") into a Date object.
export function parseDateFromTick(dateStr: string): Date | null {
  const d = new Date(dateStr);
  return isNaN(d.getTime()) ? null : d;
}

// Extracts the leading style tag from a Details string.
export function parseStyle(details: string): string {
  const prefixes = [
    "Lead / Onsight",
    "Lead / Flash",
    "Lead / Redpoint",
    "Lead / Pinkpoint",
    "Lead / Fell/Hung",
    "Follow",
    "Solo",
    "Boulder",
    "TR",
  ];
  for (const p of prefixes) {
    if (details.startsWith(p)) return p;
  }
  return details.split(".")[0].trim();
}
