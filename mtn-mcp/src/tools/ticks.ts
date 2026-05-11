import { loadTicks, loadRoutes, loadAreas, parsePitches, parseStyle, parseDateFromTick, ydsToNum, vGradeToNum } from "../data-loader.js";

export const tickToolDefinitions = [
  {
    name: "climber_profile",
    description:
      "Full profile for a climber at a crag: style breakdown, grade pyramid (sends only), " +
      "hardest onsights and redpoints, total pitches, activity date range, favorite walls, " +
      "and most-repeated routes. Optionally filter by date range.",
    inputSchema: {
      type: "object",
      required: ["crag", "climber_name"],
      properties: {
        crag: {
          type: "string",
          description: "Crag key, e.g. TAHQUITZ, JTREE_CENTRAL, MISSION_GORGE",
        },
        climber_name: {
          type: "string",
          description: "Mountain Project username (case-sensitive)",
        },
        start_date: {
          type: "string",
          description: "Only include ticks on or after this date (YYYY-MM-DD). Optional.",
        },
        end_date: {
          type: "string",
          description: "Only include ticks on or before this date (YYYY-MM-DD). Optional.",
        },
      },
    },
  },
  {
    name: "top_routes",
    description:
      "Return the most-ticked routes at a crag, ranked by tick count. " +
      "Optionally filter by date range, route type, or grade.",
    inputSchema: {
      type: "object",
      required: ["crag"],
      properties: {
        crag: {
          type: "string",
          description: "Crag key, e.g. TAHQUITZ, JTREE_CENTRAL, MISSION_GORGE",
        },
        limit: {
          type: "number",
          description: "Max results to return. Defaults to 20.",
        },
        route_type: {
          type: "string",
          description: "Filter by type: Trad, Sport, Boulder, TR. Optional.",
        },
        start_date: {
          type: "string",
          description: "Filter to ticks on or after this date (YYYY-MM-DD). Optional.",
        },
        end_date: {
          type: "string",
          description: "Filter to ticks on or before this date (YYYY-MM-DD). Optional.",
        },
      },
    },
  },
] as const;

// ── Handlers ───────────────────────────────────────────────────────────────

const SEND_STYLES = new Set([
  "Lead / Onsight", "Lead / Flash", "Lead / Redpoint", "Lead / Pinkpoint",
]);

function filterByDate(
  ticks: ReturnType<typeof loadTicks>,
  startDate: Date | null,
  endDate: Date | null
) {
  if (!startDate && !endDate) return ticks;
  return ticks.filter((t) => {
    const d = parseDateFromTick(t.Date);
    if (!d) return false;
    if (startDate && d < startDate) return false;
    if (endDate && d > endDate) return false;
    return true;
  });
}

export function handleClimberProfile(args: Record<string, unknown>): string {
  const crag = args.crag as string;
  const climberName = args.climber_name as string;
  const startDate = args.start_date ? new Date(args.start_date as string) : null;
  const endDate = args.end_date ? new Date(args.end_date as string) : null;

  const allTicks = loadTicks(crag);
  const routeMap = Object.fromEntries(loadRoutes(crag).map((r) => [r.Route, r]));
  const areaMap = Object.fromEntries(loadAreas(crag).map((a) => [a.AreaID, a]));

  let ticks = allTicks.filter((t) => t.Name === climberName);
  ticks = filterByDate(ticks, startDate, endDate);

  if (ticks.length === 0) return `No ticks found for "${climberName}" at ${crag}.`;

  // Total pitches — boulders have no pitches
  const totalPitches = ticks.reduce((sum, t) => {
    const route = routeMap[t.Route];
    if (route?.Type.includes("Boulder")) return sum;
    return sum + parsePitches(t.Details);
  }, 0);

  // Date range
  const dates = ticks
    .map((t) => parseDateFromTick(t.Date))
    .filter((d): d is Date => d !== null)
    .sort((a, b) => a.getTime() - b.getTime());
  const firstDate = dates[0];
  const lastDate = dates[dates.length - 1];

  // Style breakdown
  const styleCounts: Record<string, number> = {};
  for (const t of ticks) {
    const s = parseStyle(t.Details);
    styleCounts[s] = (styleCounts[s] ?? 0) + 1;
  }

  // Grade pyramid — sends only, separated into rock and boulder
  const rockBuckets: Record<string, number> = {
    "5.13+": 0, "5.12": 0, "5.11": 0, "5.10": 0, "5.8-5.9": 0, "5.7-": 0,
  };
  const boulderBuckets: Record<string, number> = {
    "V9+": 0, "V6-V8": 0, "V3-V5": 0, "VB-V2": 0,
  };

  const sendTicks = ticks.filter((t) => SEND_STYLES.has(parseStyle(t.Details)));

  for (const t of sendTicks) {
    const route = routeMap[t.Route];
    if (!route) continue;
    if (route.Type.includes("Boulder")) {
      const v = vGradeToNum(route.Grade);
      if (v >= 9) boulderBuckets["V9+"]++;
      else if (v >= 6) boulderBuckets["V6-V8"]++;
      else if (v >= 3) boulderBuckets["V3-V5"]++;
      else boulderBuckets["VB-V2"]++;
    } else {
      const n = ydsToNum(route.Grade);
      if (n >= 13) rockBuckets["5.13+"]++;
      else if (n >= 12) rockBuckets["5.12"]++;
      else if (n >= 11) rockBuckets["5.11"]++;
      else if (n >= 10) rockBuckets["5.10"]++;
      else if (n >= 8) rockBuckets["5.8-5.9"]++;
      else rockBuckets["5.7-"]++;
    }
  }

  // Hardest onsights and redpoints (non-boulder, lead only)
  const onsights = sendTicks
    .filter((t) => parseStyle(t.Details) === "Lead / Onsight")
    .map((t) => ({ route: routeMap[t.Route], num: ydsToNum(routeMap[t.Route]?.Grade ?? "") }))
    .filter((x) => x.route && !x.route.Type.includes("Boulder"))
    .sort((a, b) => b.num - a.num)
    .slice(0, 3);

  const redpoints = sendTicks
    .filter((t) => parseStyle(t.Details) === "Lead / Redpoint")
    .map((t) => ({ route: routeMap[t.Route], num: ydsToNum(routeMap[t.Route]?.Grade ?? "") }))
    .filter((x) => x.route && !x.route.Type.includes("Boulder"))
    .sort((a, b) => b.num - a.num)
    .slice(0, 3);

  // Most-repeated routes
  const routeCounts: Record<string, number> = {};
  for (const t of ticks) routeCounts[t.Route] = (routeCounts[t.Route] ?? 0) + 1;
  const topRoutes = Object.entries(routeCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
    .filter(([, c]) => c > 1)
    .map(([slug, count]) => {
      const r = routeMap[slug];
      return `  ${count}x ${r ? `${r.Name} (${r.Grade} ${r.Type})` : slug}`;
    });

  // Favorite walls
  const wallCounts: Record<string, number> = {};
  for (const t of ticks) {
    const route = routeMap[t.Route];
    if (route) {
      const name = areaMap[route.AreaID]?.Name ?? "Unknown";
      wallCounts[name] = (wallCounts[name] ?? 0) + 1;
    }
  }
  const topWalls = Object.entries(wallCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)
    .map(([w, c]) => `  ${w}: ${c} ticks`);

  const styleLines = Object.entries(styleCounts)
    .sort(([, a], [, b]) => b - a)
    .map(([s, c]) => `  ${s}: ${c} (${Math.round((c / ticks.length) * 100)}%)`)
    .join("\n");

  const rockPyramid = Object.entries(rockBuckets)
    .filter(([, c]) => c > 0)
    .map(([g, c]) => {
      const bar = "█".repeat(Math.min(c, 15)) + (c > 15 ? "+" : "");
      return `  ${g.padEnd(10)} ${bar} ${c}`;
    })
    .join("\n");

  const boulderPyramid = Object.entries(boulderBuckets)
    .filter(([, c]) => c > 0)
    .map(([g, c]) => {
      const bar = "█".repeat(Math.min(c, 15)) + (c > 15 ? "+" : "");
      return `  ${g.padEnd(10)} ${bar} ${c}`;
    })
    .join("\n");

  const out: string[] = [
    `Climber Profile: ${climberName} @ ${crag}`,
    "─".repeat(50),
    `Total ticks: ${ticks.length}  |  Pitched routes: ${totalPitches} pitches`,
  ];

  if (firstDate && lastDate) {
    out.push(`Active: ${firstDate.toDateString()} → ${lastDate.toDateString()}`);
  }

  out.push(`\nStyle breakdown:\n${styleLines}`);
  if (rockPyramid) out.push(`\nGrade pyramid (sends only):\n${rockPyramid}`);
  if (boulderPyramid) out.push(`\nBoulder pyramid (sends):\n${boulderPyramid}`);

  if (onsights.length > 0) {
    const lines = onsights.map((x) => `  ${x.route.Name} (${x.route.Grade})`).join("\n");
    out.push(`\nHardest onsights:\n${lines}`);
  }
  if (redpoints.length > 0) {
    const lines = redpoints.map((x) => `  ${x.route.Name} (${x.route.Grade})`).join("\n");
    out.push(`\nHardest redpoints:\n${lines}`);
  }

  if (topRoutes.length > 0) out.push(`\nMost repeated routes:\n${topRoutes.join("\n")}`);
  if (topWalls.length > 0) out.push(`\nFavorite walls:\n${topWalls.join("\n")}`);

  return out.join("\n");
}

export function handleTopRoutes(args: Record<string, unknown>): string {
  const crag = args.crag as string;
  const limit = (args.limit as number) ?? 20;
  const routeType = args.route_type as string | undefined;
  const startDate = args.start_date ? new Date(args.start_date as string) : null;
  const endDate = args.end_date ? new Date(args.end_date as string) : null;

  const routes = Object.fromEntries(loadRoutes(crag).map((r) => [r.Route, r]));
  let ticks = filterByDate(loadTicks(crag), startDate, endDate);

  if (routeType) {
    ticks = ticks.filter((t) => routes[t.Route]?.Type?.includes(routeType));
  }

  const tickCounts: Record<string, number> = {};
  for (const t of ticks) tickCounts[t.Route] = (tickCounts[t.Route] ?? 0) + 1;

  const ranked = Object.entries(tickCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, limit);

  if (ranked.length === 0) return `No routes found for ${crag} with the given filters.`;

  const lines = ranked.map(([slug, count], i) => {
    const r = routes[slug];
    const label = r ? `${r.Name} (${r.Grade} ${r.Type})` : slug;
    return `${String(i + 1).padStart(2)}. ${count.toString().padStart(4)} ticks — ${label}`;
  });

  return [`Top routes at ${crag}:\n`, ...lines].join("\n");
}
