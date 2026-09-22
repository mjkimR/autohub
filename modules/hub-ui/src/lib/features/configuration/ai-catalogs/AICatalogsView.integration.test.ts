import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { toast } from 'svelte-sonner';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import AICatalogsView from './AICatalogsView.svelte';

const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() }
}));

vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const base = {
	enabled: true,
	availability_state: 'normal',
	available_at: null,
	availability_source: null,
	availability_note: null,
	configured_concurrency: 3,
	effective_concurrency: 3,
	active_dispatch_count: 0,
	held_run_count: 0,
	open_session_count: 0,
	connector_id: null,
	policy_config: {},
	policy_state: {}
};
const codex = {
	...base,
	id: 'c1',
	key: 'personal-codex',
	name: 'Personal Codex',
	kind: 'codex',
	adapter: 'codex-github-mention',
	connector_provider: null,
	pipeline_delivery: true,
	session_work_types: []
};
const jules = {
	...base,
	id: 'j1',
	key: 'personal-jules',
	name: 'Personal Jules',
	kind: 'jules',
	adapter: 'jules-api',
	connector_provider: 'jules',
	pipeline_delivery: false,
	session_work_types: ['task', 'report']
};
const connectors = [
	{ id: 'k1', name: 'Jules key', provider: 'jules', enabled: true },
	{ id: 'g1', name: 'GitHub token', provider: 'github', enabled: true }
];
const sessions = [
	{
		id: 's1',
		title: 'Weekly hygiene report [hub-session:abc]',
		work_type: 'report',
		repository: 'owner/app',
		state: 'completed',
		url: 'https://jules.google/session/1',
		pull_request_url: null,
		pipeline_run_id: null,
		result_summary: '## Weekly report\n\n- 3 stale dependencies',
		failure_detail: null,
		created_at: '2026-09-15T00:00:00Z'
	},
	{
		id: 's2',
		title: 'Tidy dependencies [hub-session:def]',
		work_type: 'task',
		repository: 'owner/app',
		state: 'completed',
		url: 'https://jules.google/session/2',
		pull_request_url: 'https://github.com/owner/app/pull/9',
		pipeline_run_id: 'run-9',
		result_summary: null,
		failure_detail: null,
		created_at: '2026-09-14T00:00:00Z'
	}
];

beforeEach(() => {
	vi.clearAllMocks();
	api.GET.mockImplementation((path: string) => {
		if (path === '/api/v1/connectors') return Promise.resolve({ data: { items: connectors } });
		if (path === '/api/v1/ai-catalogs/{catalog_key}/sessions')
			return Promise.resolve({ data: { items: sessions, total_count: 45 } });
		return Promise.resolve({ data: { items: [codex, jules] } });
	});
	api.PUT.mockResolvedValue({ data: jules });
});

afterEach(() => {
	cleanup();
	// A dialog closed by the previous test can leave the body inert until its exit animation would end.
	document.body.style.removeProperty('pointer-events');
});

test('shows each kind its own policy editor and session controls only where the kind has them', async () => {
	render(AICatalogsView);

	await screen.findByText('Personal Jules');
	expect(screen.getAllByRole('button', { name: 'Refresh policy' })).toHaveLength(1);
	expect(screen.getAllByRole('button', { name: 'Quota policy' })).toHaveLength(1);
	expect(screen.getAllByRole('button', { name: 'Connector' })).toHaveLength(1);
	expect(screen.getAllByRole('button', { name: 'Sessions' })).toHaveLength(1);
	expect(screen.getByText(/Daily quota: not configured/)).toBeTruthy();
	expect(screen.getByText(/Connector: not assigned/)).toBeTruthy();
	expect(screen.getByText(/0 open session\(s\)/)).toBeTruthy();
});

test('saves a calendar daily quota for a Jules catalog', async () => {
	const user = userEvent.setup();
	render(AICatalogsView);
	await screen.findByText('Personal Jules');

	await user.click(screen.getByRole('button', { name: 'Quota policy' }));
	// Edit the multi-character limit last: the dialog moves focus once while it opens.
	await user.selectOptions(screen.getByLabelText('Daily window'), 'calendar');
	await user.clear(screen.getByLabelText('Reset timezone'));
	await user.type(screen.getByLabelText('Reset timezone'), 'America/Los_Angeles');
	await user.clear(screen.getByLabelText('Daily task limit'));
	await user.type(screen.getByLabelText('Daily task limit'), '250');
	await user.click(screen.getByRole('button', { name: 'Save quota policy' }));

	await waitFor(() =>
		expect(api.PUT).toHaveBeenCalledWith('/api/v1/ai-catalogs/{catalog_key}/policy-config', {
			params: { path: { catalog_key: 'personal-jules' } },
			body: {
				policy_config: {
					daily_task_limit: 250,
					window: 'calendar',
					timezone: 'America/Los_Angeles'
				}
			}
		})
	);
});

test('rejects an unknown calendar timezone before saving', async () => {
	const user = userEvent.setup();
	render(AICatalogsView);
	await screen.findByText('Personal Jules');

	await user.click(screen.getByRole('button', { name: 'Quota policy' }));
	await user.selectOptions(screen.getByLabelText('Daily window'), 'calendar');
	await user.clear(screen.getByLabelText('Reset timezone'));
	await user.type(screen.getByLabelText('Reset timezone'), 'Mars/Olympus');
	await user.click(screen.getByRole('button', { name: 'Save quota policy' }));

	await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Unknown timezone: Mars/Olympus'));
	expect(api.PUT).not.toHaveBeenCalled();
});

test('saves the Codex refresh policy as policy config', async () => {
	const user = userEvent.setup();
	render(AICatalogsView);
	await screen.findByText('Personal Codex');

	await user.click(screen.getByRole('button', { name: 'Refresh policy' }));
	await user.clear(screen.getByLabelText('Short cycle (hours)'));
	await user.type(screen.getByLabelText('Short cycle (hours)'), '4');
	await user.click(screen.getByRole('button', { name: 'Save policy' }));

	await waitFor(() =>
		expect(api.PUT).toHaveBeenCalledWith('/api/v1/ai-catalogs/{catalog_key}/policy-config', {
			params: { path: { catalog_key: 'personal-codex' } },
			body: {
				policy_config: {
					short_refresh_enabled: true,
					short_refresh_cycle_minutes: 240,
					long_refresh_cycle_minutes: 10080,
					probe_window_minutes: 10
				}
			}
		})
	);
});

test('assigns only a connector of the catalog provider', async () => {
	const user = userEvent.setup();
	render(AICatalogsView);
	await screen.findByText('Personal Jules');

	await user.click(screen.getByRole('button', { name: 'Connector' }));
	const select = screen.getByLabelText('Provider connector');
	expect(screen.queryByRole('option', { name: 'GitHub token' })).toBeNull();
	await user.selectOptions(select, 'k1');
	await user.click(screen.getByRole('button', { name: 'Save connector' }));

	await waitFor(() =>
		expect(api.PUT).toHaveBeenCalledWith('/api/v1/ai-catalogs/{catalog_key}/connector', {
			params: { path: { catalog_key: 'personal-jules' } },
			body: { connector_id: 'k1' }
		})
	);
});

test('pages through sessions and hides their reconciliation marker', async () => {
	const user = userEvent.setup();
	render(AICatalogsView);
	await screen.findByText('Personal Jules');

	await user.click(screen.getByRole('button', { name: 'Sessions' }));

	expect(await screen.findByText('Weekly hygiene report')).toBeTruthy();
	expect(screen.getByText('report')).toBeTruthy();
	expect(screen.getByText('1–2 of 45')).toBeTruthy();
	// A report keeps its final message; a task links the pipeline run that adopted its pull request.
	expect(screen.getByText(/3 stale dependencies/)).toBeTruthy();
	expect(screen.getByRole('link', { name: 'Pipeline run' })).toHaveProperty(
		'href',
		expect.stringContaining('/projects/runs?run=run-9')
	);
	expect(api.GET).toHaveBeenCalledWith('/api/v1/ai-catalogs/{catalog_key}/sessions', {
		params: { path: { catalog_key: 'personal-jules' }, query: { offset: 0, limit: 20 } }
	});
	expect(screen.getByRole('button', { name: 'Previous' })).toHaveProperty('disabled', true);

	await user.click(screen.getByRole('button', { name: 'Next' }));

	await waitFor(() =>
		expect(api.GET).toHaveBeenCalledWith('/api/v1/ai-catalogs/{catalog_key}/sessions', {
			params: { path: { catalog_key: 'personal-jules' }, query: { offset: 20, limit: 20 } }
		})
	);

	// Changing the filter starts again from the first page.
	await user.selectOptions(screen.getByRole('combobox', { name: 'Show' }), 'failed');

	await waitFor(() =>
		expect(api.GET).toHaveBeenCalledWith('/api/v1/ai-catalogs/{catalog_key}/sessions', {
			params: {
				path: { catalog_key: 'personal-jules' },
				query: { offset: 0, limit: 20, status: 'failed' }
			}
		})
	);
});

test('creates a Jules catalog with a matching connector and shows it immediately', async () => {
	const user = userEvent.setup();
	api.POST.mockResolvedValue({
		data: {
			...jules,
			id: 'team-jules-id',
			key: 'team-jules',
			name: 'Team Jules',
			connector_id: 'k1'
		}
	});
	render(AICatalogsView);
	await screen.findByText('Personal Jules');
	await user.click(screen.getByRole('button', { name: 'Add catalog' }));
	await user.selectOptions(screen.getByLabelText('Provider'), 'jules');
	expect(screen.queryByRole('option', { name: 'GitHub token' })).toBeNull();
	await user.selectOptions(screen.getByLabelText('Jules connector'), 'k1');
	await user.type(screen.getByLabelText('Name'), 'Team Jules');
	await user.type(screen.getByLabelText(/^Catalog key/), 'team-jules');
	await user.clear(screen.getByLabelText('Concurrent work limit'));
	await user.type(screen.getByLabelText('Concurrent work limit'), '2');
	await user.clear(screen.getByLabelText('Daily task limit'));
	await user.type(screen.getByLabelText('Daily task limit'), '25');
	await user.click(screen.getByRole('button', { name: 'Create catalog' }));
	await screen.findByText('Team Jules');
	expect(api.POST).toHaveBeenCalledWith('/api/v1/ai-catalogs', {
		body: {
			name: 'Team Jules',
			key: 'team-jules',
			kind: 'jules',
			connector_id: 'k1',
			configured_concurrency: 2,
			policy_config: { daily_task_limit: 25, window: 'rolling', timezone: 'UTC' },
			enabled: true
		}
	});
	await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
});

test('switching from Jules to Codex does not submit Jules credentials or daily quota', async () => {
	const user = userEvent.setup();
	api.POST.mockResolvedValue({
		data: { ...codex, id: 'team-codex-id', key: 'team-codex', name: 'Team Codex' }
	});
	render(AICatalogsView);
	await screen.findByText('Personal Codex');
	await user.click(screen.getByRole('button', { name: 'Add catalog' }));
	await user.selectOptions(screen.getByLabelText('Provider'), 'jules');
	await user.selectOptions(screen.getByLabelText('Jules connector'), 'k1');
	await user.selectOptions(screen.getByLabelText('Provider'), 'codex');
	expect(screen.queryByLabelText('Jules connector')).toBeNull();
	await user.type(screen.getByLabelText('Name'), 'Team Codex');
	await user.type(screen.getByLabelText(/^Catalog key/), 'team-codex');
	await user.click(screen.getByRole('button', { name: 'Create catalog' }));
	await screen.findByText('Team Codex');
	expect(api.POST).toHaveBeenCalledWith('/api/v1/ai-catalogs', {
		body: {
			name: 'Team Codex',
			key: 'team-codex',
			kind: 'codex',
			connector_id: null,
			configured_concurrency: 1,
			policy_config: {},
			enabled: true
		}
	});
});

test('duplicate key refusal keeps the creation form editable for correction', async () => {
	const user = userEvent.setup();
	api.POST.mockResolvedValue({
		error: { detail: 'An AI catalog with this key already exists; choose another key' }
	});
	render(AICatalogsView);
	await screen.findByText('Personal Codex');
	await user.click(screen.getByRole('button', { name: 'Add catalog' }));
	await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('dialog')));
	await user.type(screen.getByLabelText('Name'), 'Another Codex');
	await user.type(screen.getByLabelText(/^Catalog key/), 'personal-codex');
	expect((screen.getByLabelText('Name') as HTMLInputElement).value).toBe('Another Codex');
	expect((screen.getByLabelText(/^Catalog key/) as HTMLInputElement).value).toBe('personal-codex');
	await user.click(screen.getByRole('button', { name: 'Create catalog' }));
	await waitFor(() =>
		expect(toast.error).toHaveBeenCalledWith(expect.stringContaining('already exists'))
	);
	expect(screen.getByRole('dialog')).toBeTruthy();
	expect((screen.getByLabelText('Name') as HTMLInputElement).value).toBe('Another Codex');
	expect(
		(screen.getByRole('button', { name: 'Create catalog' }) as HTMLButtonElement).disabled
	).toBe(false);
});

test('names the refresh target and saves the local time as an instant', async () => {
	const user = userEvent.setup();
	render(AICatalogsView);
	await screen.findByText('Personal Codex');
	await user.click(screen.getAllByRole('button', { name: 'Set refresh time' })[0]);
	const dialog = screen.getByRole('dialog');
	expect(dialog.textContent).toContain('Personal Codex');
	expect(dialog.textContent).toContain('personal-codex');
	expect(dialog.textContent).toContain(Intl.DateTimeFormat().resolvedOptions().timeZone);
	await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));
	const { fireEvent } = await import('@testing-library/svelte');
	await fireEvent.input(screen.getByLabelText('Refresh time'), {
		target: { value: '2099-10-22T09:30' }
	});
	await user.type(
		screen.getByLabelText('Operator note (optional)'),
		'Quota resets after breakfast'
	);
	expect(dialog.textContent).toContain('Will resume:');
	await user.click(screen.getByRole('button', { name: 'Save global hold' }));
	await waitFor(() =>
		expect(api.PUT).toHaveBeenCalledWith('/api/v1/ai-catalogs/{catalog_key}/availability', {
			params: { path: { catalog_key: 'personal-codex' } },
			body: {
				available_at: new Date('2099-10-22T09:30').toISOString(),
				note: 'Quota resets after breakfast',
				source: 'manual'
			}
		})
	);
	await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
});

test('a refused refresh update keeps the entered time and note for retry', async () => {
	const user = userEvent.setup();
	api.PUT.mockResolvedValue({ error: { detail: 'Catalog is unavailable' } });
	render(AICatalogsView);
	await screen.findByText('Personal Codex');
	await user.click(screen.getAllByRole('button', { name: 'Set refresh time' })[0]);
	await waitFor(() =>
		expect(screen.getByRole('dialog').contains(document.activeElement)).toBe(true)
	);
	const { fireEvent } = await import('@testing-library/svelte');
	await fireEvent.input(screen.getByLabelText('Refresh time'), {
		target: { value: '2099-10-22T09:30' }
	});
	await user.type(screen.getByLabelText('Operator note (optional)'), 'Keep this note');
	await user.click(screen.getByRole('button', { name: 'Save global hold' }));
	await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Catalog is unavailable'));
	expect((screen.getByLabelText('Refresh time') as HTMLInputElement).value).toBe(
		'2099-10-22T09:30'
	);
	expect((screen.getByLabelText('Operator note (optional)') as HTMLInputElement).value).toBe(
		'Keep this note'
	);
});
