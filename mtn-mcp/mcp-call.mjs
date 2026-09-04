#!/usr/bin/env node
// Call a single MCP tool from the shell and print its text output.
// Usage: node mcp-call.mjs <tool_name> '<json-args>'
//   node mcp-call.mjs list_crags
//   node mcp-call.mjs crag_overview '{"crag":"YOSEMITE_VALLEY_NORTH"}'
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const [, , toolName, argsJson] = process.argv;
if (!toolName) {
  console.error("Usage: node mcp-call.mjs <tool_name> '<json-args>'");
  process.exit(1);
}

const transport = new StdioClientTransport({ command: "node", args: ["dist/index.js"] });
const client = new Client({ name: "mcp-call-cli", version: "1.0.0" }, { capabilities: {} });
await client.connect(transport);
const res = await client.callTool({
  name: toolName,
  arguments: argsJson ? JSON.parse(argsJson) : {},
});
for (const c of res.content ?? []) {
  if (c.type === "text") console.log(c.text);
}
await client.close();
