import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

import { tickToolDefinitions, handleClimberProfile, handleTopRoutes } from "./tools/ticks.js";
import { routeToolDefinitions, handleCragOverview, handleAreaBreakdown, handleRouteInfo, handleFindRoutes, handleListCrags } from "./tools/routes.js";
import { gearToolDefinitions, handleSuggestGear } from "./tools/gear.js";
import { betaToolDefinitions, handleRouteBeta } from "./tools/beta.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

// ── Server ─────────────────────────────────────────────────────────────────

const server = new Server(
  { name: "mtn-mcp", version: "0.1.0" },
  { capabilities: { tools: {}, resources: {} } }
);

// ── Tools ──────────────────────────────────────────────────────────────────

const allTools = [
  ...tickToolDefinitions,
  ...routeToolDefinitions,
  ...gearToolDefinitions,
  ...betaToolDefinitions,
];

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: allTools,
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const a = (args ?? {}) as Record<string, unknown>;

  let text: string;
  try {
    switch (name) {
      case "climber_profile":        text = handleClimberProfile(a); break;
      case "top_routes":            text = handleTopRoutes(a); break;
      case "crag_overview":         text = handleCragOverview(a); break;
      case "area_breakdown":        text = handleAreaBreakdown(a); break;
      case "route_info":            text = handleRouteInfo(a); break;
      case "find_routes":           text = handleFindRoutes(a); break;
      case "list_crags":            text = handleListCrags(); break;
      case "suggest_gear":          text = handleSuggestGear(a); break;
      case "route_beta":            text = handleRouteBeta(a); break;
      default:
        return { content: [{ type: "text", text: `Unknown tool: ${name}` }], isError: true };
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return { content: [{ type: "text", text: `Error: ${msg}` }], isError: true };
  }

  return { content: [{ type: "text", text }] };
});

// ── Resources ──────────────────────────────────────────────────────────────
// Expose the context markdown files so the model can read them on demand.

const RESOURCES = [
  {
    uri: "mtn://context/climbing",
    name: "Rock Climbing Context",
    description: "Domain knowledge: disciplines, grading, tick styles, crack sizes, cam sizing",
    mimeType: "text/markdown",
    path: join(__dirname, "..", "rock_climbing_context.md"),
  },
  {
    uri: "mtn://context/data",
    name: "Data Context",
    description: "Mountain Project data structure: CSV schemas, join model, what the data can answer",
    mimeType: "text/markdown",
    path: join(__dirname, "..", "..", "mtn-data", "data-context.md"),
  },
];

server.setRequestHandler(ListResourcesRequestSchema, async () => ({
  resources: RESOURCES.map(({ uri, name, description, mimeType }) => ({
    uri,
    name,
    description,
    mimeType,
  })),
}));

server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const resource = RESOURCES.find((r) => r.uri === request.params.uri);
  if (!resource) {
    throw new Error(`Unknown resource: ${request.params.uri}`);
  }
  const text = readFileSync(resource.path, "utf-8");
  return {
    contents: [{ uri: resource.uri, mimeType: resource.mimeType, text }],
  };
});

// ── Start ──────────────────────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);
