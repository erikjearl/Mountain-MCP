import { loadRoutes, loadAreas, loadTicks, availableCrags } from "../data-loader.js";

export const routeToolDefinitions = [
  {
    name: "route_info",
    description:
      "Look up a specific route by name or slug. Returns grade, type, length, " +
      "area/wall location, and total tick count.",
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
          description:
            "Route name (e.g. 'Illusion Dweller') or URL slug (e.g. 'illusion-dweller'). " +
            "Case-insensitive name search is used if no exact slug match is found.",
        },
      },
    },
  },
  {
    name: "find_routes",
    description:
      "Search for routes at a crag by grade, type, or area. Returns matching routes " +
      "sorted by tick count (most popular first).",
    inputSchema: {
      type: "object",
      required: ["crag"],
      properties: {
        crag: {
          type: "string",
          description: "Crag key, e.g. TAHQUITZ, JTREE_CENTRAL, MISSION_GORGE",
        },
        grade: {
          type: "string",
          description: "Grade to filter by, e.g. '5.10b', '5.11', 'V3'. Partial match supported.",
        },
        route_type: {
          type: "string",
          description: "Type filter: Trad, Sport, Boulder, TR. Optional.",
        },
        area_name: {
          type: "string",
          description: "Filter by wall or sub-area name (partial match). Optional.",
        },
        limit: {
          type: "number",
          description: "Max results. Defaults to 15.",
        },
      },
    },
  },
  {
    name: "list_crags",
    description: "List all crags that have collected data available in mtn-data/.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
] as const;

// ── Handlers ───────────────────────────────────────────────────────────────

export function handleRouteInfo(args: Record<string, unknown>): string {
  const crag = args.crag as string;
  const query = (args.route as string).toLowerCase();

  const routes = loadRoutes(crag);
  const areas = Object.fromEntries(loadAreas(crag).map((a) => [a.AreaID, a]));
  const ticks = loadTicks(crag);

  const tickCounts: Record<string, number> = {};
  for (const t of ticks) tickCounts[t.Route] = (tickCounts[t.Route] ?? 0) + 1;

  const route =
    routes.find((r) => r.Route === query) ??
    routes.find((r) => r.Name.toLowerCase() === query) ??
    routes.find((r) => r.Name.toLowerCase().includes(query));

  if (!route) return `Route "${args.route}" not found at ${crag}.`;

  const area = areas[route.AreaID];
  const tCount = tickCounts[route.Route] ?? 0;

  return [
    `Route: ${route.Name}`,
    `Grade: ${route.Grade}  |  Type: ${route.Type}  |  Length: ${route.Length || "N/A"}`,
    `Wall: ${area?.Name ?? "Unknown"} (${area?.FullPath ?? ""})`,
    `Tick count: ${tCount}`,
    `Slug: ${route.Route}`,
  ].join("\n");
}

export function handleFindRoutes(args: Record<string, unknown>): string {
  const crag = args.crag as string;
  const gradeFilter = (args.grade as string | undefined)?.toLowerCase();
  const typeFilter = args.route_type as string | undefined;
  const areaFilter = (args.area_name as string | undefined)?.toLowerCase();
  const limit = (args.limit as number) ?? 15;

  const routes = loadRoutes(crag);
  const areas = Object.fromEntries(loadAreas(crag).map((a) => [a.AreaID, a]));
  const ticks = loadTicks(crag);

  const tickCounts: Record<string, number> = {};
  for (const t of ticks) tickCounts[t.Route] = (tickCounts[t.Route] ?? 0) + 1;

  let filtered = routes;

  if (gradeFilter) {
    filtered = filtered.filter((r) => r.Grade.toLowerCase().includes(gradeFilter));
  }
  if (typeFilter) {
    filtered = filtered.filter((r) => r.Type.includes(typeFilter));
  }
  if (areaFilter) {
    filtered = filtered.filter((r) => {
      const area = areas[r.AreaID];
      return area?.FullPath.toLowerCase().includes(areaFilter) ||
             area?.Name.toLowerCase().includes(areaFilter);
    });
  }

  if (filtered.length === 0) return `No routes matched the given filters at ${crag}.`;

  const ranked = filtered
    .sort((a, b) => (tickCounts[b.Route] ?? 0) - (tickCounts[a.Route] ?? 0))
    .slice(0, limit);

  const lines = ranked.map((r, i) => {
    const tCount = tickCounts[r.Route] ?? 0;
    const area = areas[r.AreaID]?.Name ?? "";
    return `${String(i + 1).padStart(2)}. ${r.Name} (${r.Grade} ${r.Type}) — ${tCount} ticks — ${area}`;
  });

  return [`Found ${filtered.length} routes at ${crag} (showing top ${ranked.length}):\n`, ...lines].join("\n");
}

export function handleListCrags(): string {
  const crags = availableCrags();
  if (crags.length === 0) return "No crag data found in mtn-data/.";
  return `Available crags:\n${crags.map((c) => `  ${c}`).join("\n")}`;
}
