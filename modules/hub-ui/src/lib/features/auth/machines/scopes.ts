export const MACHINE_SCOPES = [
	{ value: 'autohub:mcp:read', label: 'MCP read', hint: 'List projects, runs and attempts' },
	{ value: 'autohub:mcp:write', label: 'MCP write', hint: 'Create projects and control runs' },
	{ value: 'autohub:dispatch', label: 'Dispatch', hint: 'External scheduler trigger only' }
] as const;

export const DEFAULT_MACHINE_SCOPES = ['autohub:mcp:read', 'autohub:mcp:write'];
