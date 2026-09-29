export const MACHINE_SCOPES = [
	{ value: 'autohub:mcp:read', label: 'MCP read', hint: 'List projects, runs and attempts' },
	{ value: 'autohub:mcp:write', label: 'MCP write', hint: 'Enroll, pause, resume and cancel runs' },
	{
		value: 'autohub:mcp:ops',
		label: 'MCP operations',
		hint: 'Configure projects and run connection tests'
	},
	{ value: 'autohub:dispatch', label: 'Dispatch', hint: 'External scheduler trigger only' }
] as const;

export const DEFAULT_MACHINE_SCOPES = ['autohub:mcp:read', 'autohub:mcp:write'];
