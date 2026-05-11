import { loadRoutes, loadAreas, loadTicks, availableCrags, ydsToNum, vGradeToNum, parseDateFromTick } from "../data-loader.js";

export const routeToolDefinitions = [
  {
    name: "crag_overview",
    description:
      "High-level summary of a crag: total routes by type, grade distribution, " +
      "most-ticked routes, busiest months, most active climbers, and traffic by wall. " +
      "Use this as the entry point when a climber wants to learn about an area.",
    inputSchema: {
      type: "object",
      required: ["crag"],
      properties: {
        crag: {
          type: "string",
          description: "Crag key, e.g. TAHQUITZ, JTREE_CENTRAL, MISSION_GORGE",
        },
      },
    },
  },
  {
    name: "area_breakdown",
    description:
      "List all walls/sub-areas at a crag, ranked by tick count. Shows route count, " +
      "dominant type, grade range, and total ticks per wall. " +
      "Use when a climber wants to know which sector to visit.",
    inputSchema: {
      type: "object",
      required: ["crag"],
      properties: {
        crag: {
          type: "string",
          description: "Crag key, e.g. TAHQUITZ, JTREE_CENTRAL, MISSION_GORGE",
        },
      },
    },
  },
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

export function handleCragOverview(args: Record<string, unknown>): string {
  const crag = args.crag as string;

  const routes = loadRoutes(crag);
  const areas = Object.fromEntries(loadAreas(crag).map((a) => [a.AreaID, a]));
  const ticks = loadTicks(crag);

  // Tick counts per route
  const tickCounts: Record<string, number> = {};
  for (const t of ticks) tickCounts[t.Route] = (tickCounts[t.Route] ?? 0) + 1;

  // Route type breakdown
  const typeCounts: Record<string, number> = {};
  for (const r of routes) {
    typeCounts[r.Type] = (typeCounts[r.Type] ?? 0) + 1;
  }

  // Grade distribution (rock and boulder separate)
  const rockBuckets: Record<string, number> = {
    "5.7-": 0, "5.8-5.9": 0, "5.10": 0, "5.11": 0, "5.12": 0, "5.13+": 0,
  };
  const boulderBuckets: Record<string, number> = {
    "VB-V2": 0, "V3-V5": 0, "V6-V8": 0, "V9+": 0,
  };
  for (const r of routes) {
    if (r.Type.includes("Boulder")) {
      const v = vGradeToNum(r.Grade);
      if (v <= 2) boulderBuckets["VB-V2"]++;
      else if (v <= 5) boulderBuckets["V3-V5"]++;
      else if (v <= 8) boulderBuckets["V6-V8"]++;
      else boulderBuckets["V9+"]++;
    } else {
      const n = ydsToNum(r.Grade);
      if (n < 8) rockBuckets["5.7-"]++;
      else if (n < 10) rockBuckets["5.8-5.9"]++;
      else if (n < 11) rockBuckets["5.10"]++;
      else if (n < 12) rockBuckets["5.11"]++;
      else if (n < 13) rockBuckets["5.12"]++;
      else rockBuckets["5.13+"]++;
    }
  }

  // Top 5 routes
  const top5 = [...routes]
    .sort((a, b) => (tickCounts[b.Route] ?? 0) - (tickCounts[a.Route] ?? 0))
    .slice(0, 5)
    .map((r) => `  ${r.Name} (${r.Grade} ${r.Type}) — ${tickCounts[r.Route] ?? 0} ticks`);

  // Busiest months
  const monthCounts: Record<string, number> = {};
  for (const t of ticks) {
    const d = parseDateFromTick(t.Date);
    if (d) {
      const key = d.toLocaleString("default", { month: "short" });
      monthCounts[key] = (monthCounts[key] ?? 0) + 1;
    }
  }
  const busyMonths = Object.entries(monthCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)
    .map(([m, c]) => `${m} (${c})`);

  // Most active climbers
  const climberCounts: Record<string, number> = {};
  for (const t of ticks) climberCounts[t.Name] = (climberCounts[t.Name] ?? 0) + 1;
  const topClimbers = Object.entries(climberCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
    .map(([name, c]) => `  ${name}: ${c} ticks`);

  // Traffic by wall
  const wallCounts: Record<string, number> = {};
  const routeMap = Object.fromEntries(routes.map((r) => [r.Route, r]));
  for (const t of ticks) {
    const r = routeMap[t.Route];
    if (r) {
      const name = areas[r.AreaID]?.Name ?? "Unknown";
      wallCounts[name] = (wallCounts[name] ?? 0) + 1;
    }
  }
  const topWalls = Object.entries(wallCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
    .map(([w, c]) => `  ${w}: ${c} ticks`);

  const uniqueClimbers = Object.keys(climberCounts).length;

  const typeLines = Object.entries(typeCounts)
    .sort(([, a], [, b]) => b - a)
    .map(([t, c]) => `  ${t}: ${c}`)
    .join("\n");

  const rockLines = Object.entries(rockBuckets)
    .filter(([, c]) => c > 0)
    .map(([g, c]) => `  ${g.padEnd(10)} ${c}`)
    .join("\n");

  const boulderLines = Object.entries(boulderBuckets)
    .filter(([, c]) => c > 0)
    .map(([g, c]) => `  ${g.padEnd(10)} ${c}`)
    .join("\n");

  const hasBoulders = Object.values(boulderBuckets).some((c) => c > 0);

  return [
    `Crag Overview: ${crag}`,
    "─".repeat(50),
    `Routes: ${routes.length}  |  Total ticks: ${ticks.length}  |  Unique climbers: ${uniqueClimbers}`,
    `\nRoute types:\n${typeLines}`,
    `\nRock grade distribution:\n${rockLines}`,
    hasBoulders ? `\nBoulder grade distribution:\n${boulderLines}` : "",
    `\nTop 5 most-ticked routes:\n${top5.join("\n")}`,
    busyMonths.length > 0 ? `\nBusiest months: ${busyMonths.join(", ")}` : "",
    topWalls.length > 0 ? `\nBusiest walls:\n${topWalls.join("\n")}` : "",
    topClimbers.length > 0 ? `\nMost active climbers:\n${topClimbers.join("\n")}` : "",
  ].filter(Boolean).join("\n");
}

export function handleAreaBreakdown(args: Record<string, unknown>): string {
  const crag = args.crag as string;

  const routes = loadRoutes(crag);
  const areas = Object.fromEntries(loadAreas(crag).map((a) => [a.AreaID, a]));
  const ticks = loadTicks(crag);

  const tickCounts: Record<string, number> = {};
  for (const t of ticks) tickCounts[t.Route] = (tickCounts[t.Route] ?? 0) + 1;

  // Group routes by immediate parent area
  const areaRoutes: Record<string, typeof routes> = {};
  for (const r of routes) {
    if (!areaRoutes[r.AreaID]) areaRoutes[r.AreaID] = [];
    areaRoutes[r.AreaID].push(r);
  }

  const areaStats = Object.entries(areaRoutes).map(([areaId, aRoutes]) => {
    const area = areas[areaId];
    const totalTicks = aRoutes.reduce((sum, r) => sum + (tickCounts[r.Route] ?? 0), 0);
    const types = [...new Set(aRoutes.flatMap((r) => r.Type.split(",").map((t) => t.trim())))];
    const rockGrades = aRoutes
      .filter((r) => !r.Type.includes("Boulder"))
      .map((r) => ({ grade: r.Grade, num: ydsToNum(r.Grade) }))
      .filter((g) => g.num > 0)
      .sort((a, b) => a.num - b.num);
    const gradeRange =
      rockGrades.length > 0
        ? `${rockGrades[0].grade}–${rockGrades[rockGrades.length - 1].grade}`
        : "V-scale";
    return {
      name: area?.Name ?? `Area ${areaId}`,
      routeCount: aRoutes.length,
      totalTicks,
      types: types.join("/"),
      gradeRange,
    };
  });

  areaStats.sort((a, b) => b.totalTicks - a.totalTicks);

  const lines = areaStats.slice(0, 25).map((a, i) =>
    `${String(i + 1).padStart(2)}. ${a.name}\n` +
    `    ${a.routeCount} routes | ${a.types} | ${a.gradeRange} | ${a.totalTicks} ticks`
  );

  return [
    `Area Breakdown: ${crag}`,
    "─".repeat(50),
    `${areaStats.length} walls/sub-areas\n`,
    ...lines,
  ].join("\n");
}
