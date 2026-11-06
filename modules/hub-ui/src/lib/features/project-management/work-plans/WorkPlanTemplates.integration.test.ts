import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import WorkPlanTemplates from './WorkPlanTemplates.svelte';
const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() }
}));
vi.mock('$lib/api', () => ({ api }));
afterEach(() => cleanup());
beforeEach(() => {
	sessionStorage.clear();
	vi.resetAllMocks();
});
const template = {
	id: 'template',
	project_id: 'p',
	name: 'Routine',
	revision: 1,
	digest: 'a'.repeat(64),
	schema_version: 1,
	deleted: false,
	definition: {
		title: 'Reusable',
		description: 'Scope',
		base_branch: 'main',
		items: [{ key: 'a', title: 'A', description: 'Do A', acceptance: 'Pass', depends_on: [] }]
	}
};
const project = {
	id: 'p',
	github: { repository: 'owner/app', github_connector_id: 'connector' }
} as never;
function setup() {
	api.GET.mockImplementation(async (path: string) => ({
		data: path.endsWith('/users/me')
			? { id: 'account' }
			: path.endsWith('/work-plan-templates')
				? { items: [template], total_count: 1 }
				: path.endsWith('/{template_id}')
					? template
					: { id: 'p', github: { repository: 'owner/app', github_connector_id: 'connector' } }
	}));
}
test('template use is a fresh draft preview; only confirmed registration writes', async () => {
	setup();
	render(WorkPlanTemplates, { project, plans: [], onclose: vi.fn(), refresh: vi.fn() });
	const user = userEvent.setup();
	await user.click(await screen.findByRole('button', { name: 'Use template' }));
	expect(screen.getByText(/Template source: Routine/)).toBeTruthy();
	expect(api.POST).not.toHaveBeenCalled();
	await user.click(screen.getByRole('button', { name: 'Review registration' }));
	const save = screen.getByRole('button', { name: 'Save reviewed plan' });
	expect(save.hasAttribute('disabled')).toBe(true);
	await user.click(screen.getByRole('checkbox'));
	api.POST.mockResolvedValue({
		data: {
			record_state: 'recorded',
			original_template: template,
			current_template: template,
			original_plan: { id: 'plan', state: 'draft' },
			current_plan: { state: 'draft' }
		}
	});
	await user.click(save);
	await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(1));
	const body = api.POST.mock.calls[0][1].body;
	expect(body.payload.state).toBe('draft');
	expect(body.payload.items[0].key).not.toBe('a');
	expect(body.expected_repository).toBe('owner/app');
});
test('source extraction binds exact source revision and unknown write locks other mutations', async () => {
	setup();
	const plan = { id: 'source', title: 'Source', revision: 7 } as never;
	render(WorkPlanTemplates, { project, plans: [plan], onclose: vi.fn(), refresh: vi.fn() });
	const user = userEvent.setup();
	await screen.findByRole('button', { name: 'Use template' });
	await user.selectOptions(screen.getByRole('combobox', { name: 'Source Plan' }), 'source');
	await user.type(screen.getByRole('textbox', { name: 'Template name' }), 'Saved');
	api.POST.mockRejectedValue(new Error('lost'));
	await user.click(screen.getByRole('button', { name: 'Save source definition' }));
	await screen.findByText(/Outcome unknown/);
	expect(api.POST.mock.calls[0][1].body).toMatchObject({
		source_plan_id: 'source',
		expected_revision: 7
	});
	expect(screen.getByRole('button', { name: 'New template' }).hasAttribute('disabled')).toBe(true);
});
test('closing and reopening restores the original account/project request', async () => {
	setup();
	const props = { project, plans: [], onclose: vi.fn(), refresh: vi.fn() };
	const view = render(WorkPlanTemplates, props);
	await screen.findByRole('button', { name: 'Use template' });
	sessionStorage.setItem(
		'work-plan-template-intent:account:p',
		JSON.stringify({
			op: 'delete',
			target: 'template',
			body: { request_id: 'original', expected_revision: 1 }
		})
	);
	view.unmount();
	render(WorkPlanTemplates, props);
	await screen.findByText(/Request original/);
	expect(screen.getByRole('button', { name: 'New template' }).hasAttribute('disabled')).toBe(true);
	await userEvent.setup().click(screen.getByRole('button', { name: 'Close Templates' }));
	expect(sessionStorage.getItem('work-plan-template-intent:account:p')).not.toBeNull();
});
