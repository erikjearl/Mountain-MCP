import { loadRoutes, loadTicks, parseStyle } from "../data-loader.js";

export const betaToolDefinitions = [
  {
    name: "route_beta",
    description:
      "Synthesize crowd-sourced beta for a route by mining all tick notes. " +
      "Returns style breakdown, gear mentions, condition keywords, and a sample of recent notes. " +
      "This is the primary tool for answering 'what should I know before climbing X?'",
    inputSchema: {
      type: "object",
      required: ["crag", "route"],
      properties: {
        crag: {
          type: "string",
          description: "Crag key, e.g. TAHQUITZ, JTREE_CENTRAL, MISSION_GORGE",
        },
        route: {
          type: "string",
          description: "Route name or URL slug (case-insensitive).",
        },
      },
    },
  },
] as const;

// ── Note extraction ────────────────────────────────────────────────────────

function extractNote(details: string): string {
  // Strip date prefix: "Apr 21, 2026 ·  "
  let text = details.replace(/^[A-Z][a-z]+ \d{1,2}, \d{4}\s*[·•]\s*/u, "").trim();
  // Strip pitch count: "4 pitches.  "
  text = text.replace(/^\d+\s+pitche?s?\.\s*/i, "").trim();
  // Strip style tag (everything up to and including the first ".")
  const dotIdx = text.indexOf(".");
  if (dotIdx !== -1) text = text.slice(dotIdx + 1).trim();
  return text;
}

// ── Gear parsing ───────────────────────────────────────────────────────────

function extractGearMentions(notes: string[]): string[] {
  const sizeCounts: Record<string, number> = {};
  const rangeSeen: string[] = [];
  const doublesSeen: string[] = [];

  for (const note of notes) {
    // Size ranges: "0.5-3", "0.5–3", "from .5 to #3", "gear from 0.5 to 3"
    const rangeMatches = note.matchAll(
      /(?:from|gear|rack|sizes?|took|bring)[:\s]+(\d*\.?\d+)\s*[-–to]+\s*#?(\d*\.?\d+)/gi
    );
    for (const m of rangeMatches) {
      const r = `${m[1]}–${m[2]}`.toLowerCase();
      if (!rangeSeen.includes(r)) rangeSeen.push(r);
    }

    // Doubles / triples
    const doublesMatches = note.matchAll(
      /\b(double|triple)\s+(?:up\s+)?(?:on\s+)?(?:the\s+)?#?(\d*\.?\d+)/gi
    );
    for (const m of doublesMatches) {
      const d = `${m[1].toLowerCase()} ${m[2]}`;
      if (!doublesSeen.includes(d)) doublesSeen.push(d);
    }

    // # prefixed sizes: #1, #2, #0.75
    for (const m of note.matchAll(/#(\d+(?:\.\d+)?)/g)) {
      const size = `#${m[1]}`;
      sizeCounts[size] = (sizeCounts[size] ?? 0) + 1;
    }

    // Known fractional cam sizes: 0.3, 0.4, 0.5, 0.75
    for (const m of note.matchAll(/\b(0\.(?:1|2|3|4|5|75))\b/g)) {
      sizeCounts[m[1]] = (sizeCounts[m[1]] ?? 0) + 1;
    }
  }

  const results: string[] = [];

  if (Object.keys(sizeCounts).length > 0) {
    const sorted = Object.entries(sizeCounts)
      .sort(([, a], [, b]) => b - a)
      .map(([size, c]) => `${size} ×${c}`);
    results.push(`Cam sizes: ${sorted.join(", ")}`);
  }

  if (rangeSeen.length > 0) {
    results.push(`Size ranges: ${rangeSeen.slice(0, 3).join(" | ")}`);
  }

  if (doublesSeen.length > 0) {
    results.push(`Doubles/triples: ${doublesSeen.slice(0, 4).join(", ")}`);
  }

  // Passive gear
  const combined = notes.join(" ").toLowerCase();
  const passiveFound = ["stopper", "nut", "hex", "tricam", "offset"].filter((kw) =>
    combined.includes(kw)
  );
  if (passiveFound.length > 0) {
    results.push(`Passive gear: ${passiveFound.join(", ")}`);
  }

  return results;
}

// ── Keyword scanning ───────────────────────────────────────────────────────

const QUALITY_KEYWORDS = [
  "classic", "stellar", "excellent", "amazing", "beautiful", "must do", "must-do",
  "avoid", "terrible", "choss",
  "sandbagged", "stiff", "soft",
  "runout", "spooky", "serious", "R-rated",
  "pumpy", "sustained", "technical", "slabby", "polished",
];

const CONDITION_KEYWORDS = [
  "wet", "damp", "dry", "seeping",
  "lichen", "dirty", "dusty", "loose",
  "cold", "hot", "shade", "sunny", "windy",
];

function scanKeywords(notes: string[], keywords: string[]): string[] {
  const combined = notes.join(" ").toLowerCase();
  return keywords.filter((kw) => combined.includes(kw.toLowerCase()));
}

// ── Handler ────────────────────────────────────────────────────────────────

export function handleRouteBeta(args: Record<string, unknown>): string {
  const crag = args.crag as string;
  const query = (args.route as string).toLowerCase();

  const routes = loadRoutes(crag);
  const route =
    routes.find((r) => r.Route === query) ??
    routes.find((r) => r.Name.toLowerCase() === query) ??
    routes.find((r) => r.Name.toLowerCase().includes(query));

  if (!route) return `Route "${args.route}" not found at ${crag}.`;

  const ticks = loadTicks(crag).filter((t) => t.Route === route.Route);
  if (ticks.length === 0) return `No ticks found for "${route.Name}" at ${crag}.`;

  // Style breakdown
  const styleCounts: Record<string, number> = {};
  for (const t of ticks) {
    const s = parseStyle(t.Details);
    styleCounts[s] = (styleCounts[s] ?? 0) + 1;
  }

  // Freetext notes
  const notes = ticks
    .map((t) => extractNote(t.Details))
    .filter((n) => n.length > 5);

  const gearLines = extractGearMentions(notes);
  const qualityFlags = scanKeywords(notes, QUALITY_KEYWORDS);
  const conditionFlags = scanKeywords(notes, CONDITION_KEYWORDS);

  // Recent notes sample (up to 8, most recent first)
  const recentNotedTicks = ticks
    .filter((t) => extractNote(t.Details).length > 5)
    .slice(-8)
    .reverse()
    .map((t) => `  "${extractNote(t.Details)}" — ${t.Name} (${t.Date})`);

  const total = ticks.length;
  const styleLines = Object.entries(styleCounts)
    .sort(([, a], [, b]) => b - a)
    .map(([s, c]) => `  ${s}: ${c} (${Math.round((c / total) * 100)}%)`)
    .join("\n");

  const out: string[] = [
    `Route Beta: ${route.Name} (${route.Grade} ${route.Type})`,
    "─".repeat(50),
    `Total ticks: ${total}  |  Notes with text: ${notes.length}`,
    `\nStyle breakdown:\n${styleLines}`,
  ];

  if (gearLines.length > 0) {
    out.push(`\nGear (from tick notes):\n${gearLines.map((l) => `  ${l}`).join("\n")}`);
  }

  const allKeywords = [...qualityFlags, ...conditionFlags];
  if (allKeywords.length > 0) {
    out.push(`\nKeywords spotted: ${allKeywords.join(", ")}`);
  }

  if (recentNotedTicks.length > 0) {
    out.push(`\nRecent notes:\n${recentNotedTicks.join("\n")}`);
  }

  return out.join("\n");
}
