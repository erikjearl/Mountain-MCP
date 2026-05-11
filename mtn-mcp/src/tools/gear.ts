import { loadRoutes } from "../data-loader.js";

export const gearToolDefinitions = [
  {
    name: "suggest_gear",
    description:
      "Suggest a protection rack for a trad route based on its grade, type, and length. " +
      "Uses rock climbing domain knowledge about crack sizes and cam ranges. " +
      "Only meaningful for Trad routes — returns a note for Sport/Boulder.",
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
          description: "Route name or URL slug.",
        },
      },
    },
  },
] as const;

// ── Grade parsing ──────────────────────────────────────────────────────────

// Converts a YDS grade string to a numeric difficulty (for comparisons).
function ydsToNum(grade: string): number {
  const m = grade.match(/5\.(\d+)([abcdABCD+\-]?)/);
  if (!m) return 0;
  const num = parseInt(m[1], 10);
  const sub = m[2]?.toLowerCase() ?? "";
  const subOffset = { a: 0, b: 0.25, c: 0.5, d: 0.75, "+": 0.5, "-": 0 }[sub] ?? 0;
  return num + subOffset;
}

// ── Gear suggestion logic ──────────────────────────────────────────────────
// This is domain-knowledge-based heuristics. Expand as needed.

function suggestGearForGradeAndType(grade: string, routeType: string, lengthStr: string): string {
  if (!routeType.includes("Trad")) {
    return routeType.includes("Sport")
      ? "Sport route — bring 12–15 quickdraws and a belay device."
      : "No trad gear needed for this route type.";
  }

  const difficulty = ydsToNum(grade);
  const lengthFt = parseInt(lengthStr?.match(/(\d+)/)?.[1] ?? "0", 10);
  const pitches = lengthFt > 200 ? Math.ceil(lengthFt / 150) : 1;

  const lines: string[] = [];

  // Cam rack — always recommend BD C4 as reference sizing
  lines.push("Cams (BD C4 reference):");

  if (difficulty < 10.5) {
    // Easier trad — hand crack range likely dominant
    lines.push("  0.5, 0.75, #1 (x2), #2 (x2), #3");
  } else if (difficulty < 11.5) {
    // Mid-grade — wider range, more doubles
    lines.push("  0.3, 0.5, 0.75 (x2), #1 (x2), #2 (x2), #3, #4");
  } else {
    // Harder trad — technical placements, thinner sizes matter
    lines.push("  0.3 (x2), 0.4, 0.5 (x2), 0.75 (x2), #1 (x2), #2 (x2), #3");
  }

  lines.push("\nNuts:");
  lines.push("  BD Stopper set #4–#11 (or equivalent)");

  if (pitches > 1) {
    lines.push(`\nMulti-pitch (est. ${pitches} pitches):`);
    lines.push("  Consider doubles on #1 and #2, extra slings, cordelette for anchors.");
  }

  lines.push("\nNote: These are general recommendations based on grade. Check route-specific");
  lines.push("beta for the actual crack size(s). See rock_climbing_context.md for cam ranges.");

  return lines.join("\n");
}

// ── Handler ────────────────────────────────────────────────────────────────

export function handleSuggestGear(args: Record<string, unknown>): string {
  const crag = args.crag as string;
  const query = (args.route as string).toLowerCase();

  const routes = loadRoutes(crag);

  const route =
    routes.find((r) => r.Route === query) ??
    routes.find((r) => r.Name.toLowerCase() === query) ??
    routes.find((r) => r.Name.toLowerCase().includes(query));

  if (!route) return `Route "${args.route}" not found at ${crag}.`;

  const header = `Gear suggestion for: ${route.Name} (${route.Grade} ${route.Type})\n${"─".repeat(50)}`;
  const suggestion = suggestGearForGradeAndType(route.Grade, route.Type, route.Length);

  return `${header}\n${suggestion}`;
}
