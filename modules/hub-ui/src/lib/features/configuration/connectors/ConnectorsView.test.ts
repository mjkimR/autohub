import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { toast } from 'svelte-sonner';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import ConnectorsView from './ConnectorsView.svelte';

const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() }
}));

vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const github = {
	id: 'c1',
	name: 'Org GitHub PAT',
	provider: 'github',
	config: {},
	enabled: true,
	has_credentials: true,
	created_at: '2026-09-21T00:00:00Z',
	updated_at: '2026-09-21T00:00:00Z'
};

beforeEach(() => {
	api.GET.mockResolvedValue({ data: { items: [github] } });
	api.POST.mockResolvedValue({ data: github });
	api.PUT.mockResolvedValue({ data: github });
	api.PATCH.mockResolvedValue({ data: github });
	api.DELETE.mockResolvedValue({ data: {} });
});

afterEach(() => {
	cleanup();
	document.body.style.removeProperty('pointer-events');
	vi.clearAllMocks();
	vi.unstubAllGlobals();
});

// Set in one step: a dialog moves focus while it opens, which drops keystrokes typed one by one.
const fill = (id: string, value: string) =>
	fireEvent.input(document.getElementById(id) as HTMLInputElement, { target: { value } });

test('registers a connector with its token and never shows a stored secret', async () => {
	const user = userEvent.setup();
	render(ConnectorsView);
	expect(await screen.findByText('Org GitHub PAT')).toBeTruthy();
	// Only providers a backend feature reads are offered.
	await user.click(screen.getByRole('button', { name: 'New Connector' }));
	const providers = Array.from(document.querySelectorAll('#cProvider option')).map(
		(option) => (option as HTMLOptionElement).value
	);
	expect(providers).toEqual(['github', 'jules']);

	await fill('cName', ' Jules key ');
	await fireEvent.change(document.getElementById('cProvider') as HTMLSelectElement, {
		target: { value: 'jules' }
	});
	await fill('cToken', ' secret-token ');
	await user.click(screen.getByRole('button', { name: 'Register Connector' }));

	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/connectors', {
			body: {
				name: 'Jules key',
				provider: 'jules',
				enabled: true,
				config: {},
				credentials: { token: 'secret-token' }
			}
		})
	);
});

test('an edit keeps the stored credentials unless a new token is entered', async () => {
	const user = userEvent.setup();
	render(ConnectorsView);
	await screen.findByText('Org GitHub PAT');

	await user.click(screen.getByRole('button', { name: 'Edit Connector' }));
	expect((document.getElementById('editCToken') as HTMLInputElement).value).toBe('');
	await fill('editCName', 'Renamed');
	await user.click(screen.getByRole('button', { name: /Save/ }));

	await waitFor(() =>
		expect(api.PATCH).toHaveBeenCalledWith('/api/v1/connectors/{connector_id}', {
			params: { path: { connector_id: 'c1' } },
			body: { name: 'Renamed', enabled: true }
		})
	);
	expect(api.PUT).not.toHaveBeenCalled();
});

test('entering a new token replaces the credentials', async () => {
	const user = userEvent.setup();
	render(ConnectorsView);
	await screen.findByText('Org GitHub PAT');

	await user.click(screen.getByRole('button', { name: 'Edit Connector' }));
	await fill('editCToken', 'ghp_rotated');
	await user.click(screen.getByRole('button', { name: /Save/ }));

	await waitFor(() =>
		expect(api.PUT).toHaveBeenCalledWith('/api/v1/connectors/{connector_id}', {
			params: { path: { connector_id: 'c1' } },
			body: {
				name: 'Org GitHub PAT',
				provider: 'github',
				enabled: true,
				config: {},
				credentials: { token: 'ghp_rotated' }
			}
		})
	);
});

test('a delete asks first and reports why the backend refused', async () => {
	const user = userEvent.setup();
	const confirmed = vi.fn().mockReturnValueOnce(false).mockReturnValue(true);
	vi.stubGlobal('confirm', confirmed);
	api.DELETE.mockResolvedValue({ error: { detail: 'Connector is used by a project' } });
	render(ConnectorsView);
	await screen.findByText('Org GitHub PAT');

	await user.click(screen.getByRole('button', { name: 'Delete Connector' }));
	expect(api.DELETE).not.toHaveBeenCalled();

	await user.click(screen.getByRole('button', { name: 'Delete Connector' }));
	await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Connector is used by a project'));
	expect(api.DELETE).toHaveBeenCalledWith('/api/v1/connectors/{connector_id}', {
		params: { path: { connector_id: 'c1' } }
	});
});
