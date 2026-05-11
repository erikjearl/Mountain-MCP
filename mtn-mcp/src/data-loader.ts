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

// ── Grade utilities ────────────────────────────────────────────────────────

// Converts a YDS grade string to a sortable number (e.g. "5.10b" → 10.25).
export function ydsToNum(grade: string): number {
  const m = grade.match(/5\.(\d+)([abcdABCD+\-]?)/);
  if (!m) return 0;
  const num = parseInt(m[1], 10);
  const sub = m[2]?.toLowerCase() ?? "";
  const subOffset = ({ a: 0, b: 0.25, c: 0.5, d: 0.75, "+": 0.5, "-": 0 } as Record<string, number>)[sub] ?? 0;
  return num + subOffset;
}

// Converts a V-scale grade string to a number (e.g. "V6" → 6, "VB" → -1).
export function vGradeToNum(grade: string): number {
  if (/^VB$/i.test(grade)) return -1;
  const m = grade.match(/V(\d+)/i);
  return m ? parseInt(m[1], 10) : 0;
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

// Strips the leading "Month DD, YYYY · " date prefix from a Details string.
// Mountain Project includes the date in the details text scraped from the stats page.
function stripDetailsPrefix(details: string): string {
  // Remove date + separator: "Apr 21, 2026 ·  " or "Apr 18, 2026 • "
  let text = details.replace(/^[A-Z][a-z]+ \d{1,2}, \d{4}\s*[·•]\s*/u, "").trim();
  // Remove pitch count prefix if present: "4 pitches.  " or "1 pitch.  "
  text = text.replace(/^\d+\s+pitche?s?\.\s*/i, "").trim();
  return text;
}

// Extracts the leading style tag from a Details string.
// Details format (actual): "Apr 21, 2026 ·  Lead / Redpoint. notes"
//                          "Apr 4, 2026 · 4 pitches.  Lead / Onsight. notes"
//                          "Apr 18, 2026 • No names/notes"
export function parseStyle(details: string): string {
  const text = stripDetailsPrefix(details);
  // More-specific prefixes must come before "Lead" since it's a substring of all "Lead / X"
  const prefixes = [
    "Lead / Onsight",
    "Lead / Flash",
    "Lead / Redpoint",
    "Lead / Pinkpoint",
    "Lead / Fell/Hung",
    "Lead",
    "Follow",
    "Solo",
    "Boulder",
    "TR",
  ];
  for (const p of prefixes) {
    if (text.startsWith(p)) return p;
  }
  return "Unknown";
}
