import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import MachinesAdminView from './MachinesAdminView.svelte';

const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() }
}));
vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));
afterEach(() => {
	cleanup();
	vi.resetAllMocks();
});

const machine = {
	id: 'machine-1',
	name: 'personal-mcp',
	scopes: ['autohub:mcp:read', 'autohub:mcp:write'],
	is_active: true
};
const activeKey = {
	id: 'key-1',
	machine_id: 'machine-1',
	label: 'laptop',
	created_at: '2026-09-23T00:00:00Z',
	expires_at: null,
	revoked_at: null
};

function serve(keys: unknown[] = [], scopes = machine.scopes) {
	api.GET.mockImplementation((path: string) =>
		Promise.resolve({
			data: path.endsWith('/me')
				? { id: 'admin', is_superadmin: true }
				: path.endsWith('/keys')
					? keys
					: [{ ...machine, scopes }]
		})
	);
}

test('a regular user cannot load machines', async () => {
	api.GET.mockResolvedValue({ data: { id: 'regular', is_superadmin: false } });
	render(MachinesAdminView);
	expect(await screen.findByRole('alert')).toHaveProperty(
		'textContent',
		'Administrator access is required.'
	);
	expect(api.GET).toHaveBeenCalledExactlyOnceWith('/api/v1/users/me');
});

test('creating a machine defaults to both MCP scopes', async () => {
	serve();
	api.POST.mockResolvedValue({ data: { ...machine, id: 'machine-2' }, response: new Response() });
	const user = userEvent.setup();
	render(MachinesAdminView);
	await user.type(await screen.findByLabelText('Name'), 'codex-laptop');
	await user.click(screen.getByRole('button', { name: 'Create machine' }));
	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/machines', {
			body: { name: 'codex-laptop', scopes: ['autohub:mcp:read', 'autohub:mcp:write'] }
		})
	);
});

test('an issued key is shown once with MCP connection snippets', async () => {
	serve();
	api.POST.mockResolvedValue({ data: { ...activeKey, key: 'ahk_secret' } });
	const user = userEvent.setup();
	render(MachinesAdminView);
	await user.click(await screen.findByRole('button', { name: 'Keys' }));
	await user.type(await screen.findByLabelText('Key label'), 'laptop');
	await user.click(screen.getByRole('button', { name: 'Issue key' }));
	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/machines/{machine_id}/keys', {
			params: { path: { machine_id: 'machine-1' } },
			body: { label: 'laptop', expires_at: null }
		})
	);
	expect((await screen.findByTestId('issued-key')).textContent).toBe('ahk_secret');
	expect(screen.getByText(/Antigravity \(\.agents\/mcp_config\.json\)/)).toBeDefined();
	expect(screen.getByText(/claude mcp add --transport http autohub/).textContent).toContain(
		'Bearer ahk_secret'
	);
	await user.click(screen.getByRole('tab', { name: 'Global' }));
	expect(screen.getByText(/Antigravity \(~\/\.gemini\/config\/mcp_config\.json\)/)).toBeDefined();
	expect(screen.getByText(/--scope user/).textContent).toContain('Bearer ahk_secret');
	await user.click(screen.getByRole('button', { name: 'I stored the key' }));
	expect(screen.queryByTestId('issued-key')).toBeNull();
});

test('revoking a key requires confirmation', async () => {
	serve([activeKey]);
	api.DELETE.mockResolvedValue({ data: { ...activeKey, revoked_at: '2026-09-23T01:00:00Z' } });
	const user = userEvent.setup();
	render(MachinesAdminView);
	await user.click(await screen.findByRole('button', { name: 'Keys' }));
	await user.click(await screen.findByRole('button', { name: 'Revoke' }));
	expect(api.DELETE).not.toHaveBeenCalled();
	await user.click(screen.getByRole('button', { name: 'Confirm revoke' }));
	await waitFor(() =>
		expect(api.DELETE).toHaveBeenCalledWith('/api/v1/machines/{machine_id}/keys/{key_id}', {
			params: { path: { machine_id: 'machine-1', key_id: 'key-1' } }
		})
	);
});

test.each([
	{ scopes: ['autohub:mcp:ops'], names: ['autohub-ops'] },
	{ scopes: [...machine.scopes, 'autohub:mcp:ops'], names: ['autohub', 'autohub-ops'] },
	{ scopes: ['autohub:dispatch'], names: [] }
])('issued key snippets match scopes $scopes', async ({ scopes, names }) => {
	serve([], scopes);
	api.POST.mockResolvedValue({ data: { ...activeKey, key: 'ahk_secret' } });
	const user = userEvent.setup();
	render(MachinesAdminView);
	await user.click(await screen.findByRole('button', { name: 'Keys' }));
	await user.type(await screen.findByLabelText('Key label'), 'operator');
	await user.click(screen.getByRole('button', { name: 'Issue key' }));
	await screen.findByTestId('issued-key');
	const configs = screen.queryAllByText(/\[mcp_servers\./).map((node) => node.textContent);
	expect(configs).toHaveLength(names.length);
	for (const name of names) {
		const config = configs.find((text) => text?.includes(`[mcp_servers.${name}]`));
		expect(config).toContain(name === 'autohub-ops' ? '/ops/mcp/' : '/mcp/');
		expect(config).toContain(name === 'autohub-ops' ? 'AUTOHUB_OPS_MCP_KEY' : 'AUTOHUB_MCP_KEY');
	}
});
