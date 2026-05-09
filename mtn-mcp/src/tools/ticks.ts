import { loadTicks, loadRoutes, parsePitches, parseStyle, parseDateFromTick } from "../data-loader.js";

export const tickToolDefinitions = [
  {
    name: "analyze_climber_ticks",
    description:
      "Analyze all ticks logged by a specific climber at a crag. Returns tick count, " +
      "total pitches, style breakdown (onsight/redpoint/etc.), and their most-climbed routes.",
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
          description: "Filter to ticks on or after this date (YYYY-MM-DD). Optional.",
        },
        end_date: {
          type: "string",
          description: "Filter to ticks on or before this date (YYYY-MM-DD). Optional.",
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

export function handleAnalyzeClimberTicks(args: Record<string, unknown>): string {
  const crag = args.crag as string;
  const climberName = args.climber_name as string;
  const startDate = args.start_date ? new Date(args.start_date as string) : null;
  const endDate = args.end_date ? new Date(args.end_date as string) : null;

  const allTicks = loadTicks(crag);
  const routes = Object.fromEntries(
    loadRoutes(crag).map((r) => [r.Route, r])
  );

  let ticks = allTicks.filter((t) => t.Name === climberName);

  if (startDate || endDate) {
    ticks = ticks.filter((t) => {
      const d = parseDateFromTick(t.Date);
      if (!d) return false;
      if (startDate && d < startDate) return false;
      if (endDate && d > endDate) return false;
      return true;
    });
  }

  if (ticks.length === 0) {
    return `No ticks found for climber "${climberName}" at ${crag}.`;
  }

  const totalPitches = ticks.reduce((sum, t) => sum + parsePitches(t.Details), 0);

  const styleCounts: Record<string, number> = {};
  const routeCounts: Record<string, number> = {};
  for (const t of ticks) {
    const style = parseStyle(t.Details);
    styleCounts[style] = (styleCounts[style] ?? 0) + 1;
    routeCounts[t.Route] = (routeCounts[t.Route] ?? 0) + 1;
  }

  const topRoutes = Object.entries(routeCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10)
    .map(([slug, count]) => {
      const r = routes[slug];
      const label = r ? `${r.Name} (${r.Grade} ${r.Type})` : slug;
      return `  ${count}x ${label}`;
    });

  const styleLines = Object.entries(styleCounts)
    .sort(([, a], [, b]) => b - a)
    .map(([s, c]) => `  ${s}: ${c}`)
    .join("\n");

  return [
    `Climber: ${climberName} @ ${crag}`,
    `Total ticks: ${ticks.length}  |  Total pitches: ${totalPitches}`,
    `\nStyle breakdown:\n${styleLines}`,
    `\nTop routes:\n${topRoutes.join("\n")}`,
  ].join("\n");
}

export function handleTopRoutes(args: Record<string, unknown>): string {
  const crag = args.crag as string;
  const limit = (args.limit as number) ?? 20;
  const routeType = args.route_type as string | undefined;
  const startDate = args.start_date ? new Date(args.start_date as string) : null;
  const endDate = args.end_date ? new Date(args.end_date as string) : null;

  const routes = Object.fromEntries(
    loadRoutes(crag).map((r) => [r.Route, r])
  );

  let ticks = loadTicks(crag);

  if (startDate || endDate) {
    ticks = ticks.filter((t) => {
      const d = parseDateFromTick(t.Date);
      if (!d) return false;
      if (startDate && d < startDate) return false;
      if (endDate && d > endDate) return false;
      return true;
    });
  }

  if (routeType) {
    ticks = ticks.filter((t) => routes[t.Route]?.Type?.includes(routeType));
  }

  const tickCounts: Record<string, number> = {};
  for (const t of ticks) {
    tickCounts[t.Route] = (tickCounts[t.Route] ?? 0) + 1;
  }

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
