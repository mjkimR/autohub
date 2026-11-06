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
	const save = screen.getByRole('button', { name: 'Save draft' });
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

test('review back to editor preserves active creation state', async () => {
	setup();
	render(WorkPlanTemplates, { project, plans: [], onclose: vi.fn(), refresh: vi.fn() });
	const user = userEvent.setup();
	await user.click(await screen.findByRole('button', { name: 'Use template' }));
	await user.selectOptions(screen.getByRole('combobox', { name: 'Save as' }), 'active');
	await user.click(screen.getByRole('button', { name: 'Review registration' }));
	await user.click(screen.getByRole('button', { name: 'Back to editing' }));
	expect((screen.getByRole('combobox', { name: 'Save as' }) as HTMLSelectElement).value).toBe(
		'active'
	);
});

test('binding refusal prevents stale resubmission and offers fresh reviewed reload', async () => {
	setup();
	render(WorkPlanTemplates, { project, plans: [], onclose: vi.fn(), refresh: vi.fn() });
	const user = userEvent.setup();
	await user.click(await screen.findByRole('button', { name: 'Use template' }));
	await user.click(screen.getByRole('button', { name: 'Review registration' }));
	await user.click(screen.getByRole('checkbox'));
	api.POST.mockResolvedValue({
		error: { code: 'TEMPLATE_BINDING_CHANGED' },
		response: { status: 409 }
	});
	await user.click(screen.getByRole('button', { name: 'Save draft' }));
	await screen.findByText(
		'The reviewed template or binding was refused. Reload current basis for a new request.'
	);
	expect(screen.getByRole('button', { name: 'Save draft' }).hasAttribute('disabled')).toBe(true);
	const first = api.POST.mock.calls[0][1].body.request_id;
	await user.click(screen.getByRole('button', { name: 'Reload for review' }));
	await user.click(screen.getByRole('button', { name: 'Review registration' }));
	await user.click(screen.getByRole('checkbox'));
	await user.click(screen.getByRole('button', { name: 'Save draft' }));
	expect(api.POST.mock.calls[1][1].body.request_id).not.toBe(first);
});

test('acknowledged outcome preserves exact template ID and original Plan navigation on reopen', async () => {
	setup();
	sessionStorage.setItem(
		'work-plan-template-intent:account:p',
		JSON.stringify({
			version: 1,
			state: 'recorded',
			pending: { op: 'register', target: 'template', body: { request_id: 'original' } },
			outcome: {
				record_state: 'recorded',
				original_template: template,
				current_template: template,
				original_plan: { id: 'plan', state: 'draft' },
				current_plan: { state: 'active' }
			}
		})
	);
	render(WorkPlanTemplates, { project, plans: [], onclose: vi.fn(), refresh: vi.fn() });
	await screen.findByText(/Original template:.*template/);
	expect(screen.getByRole('link', { name: 'Open original Plan' }).getAttribute('href')).toContain(
		'/projects/p?tab=plans'
	);
});

test('pending basis reload removes the old review before delayed reads complete', async () => {
	setup();
	render(WorkPlanTemplates, { project, plans: [], onclose: vi.fn(), refresh: vi.fn() });
	const user = userEvent.setup();
	await user.click(await screen.findByRole('button', { name: 'Use template' }));
	await user.click(screen.getByRole('button', { name: 'Review registration' }));
	await user.click(screen.getByRole('checkbox'));
	api.POST.mockResolvedValue({
		error: { code: 'TEMPLATE_BINDING_CHANGED' },
		response: { status: 409 }
	});
	await user.click(screen.getByRole('button', { name: 'Save draft' }));
	let finish!: (value: unknown) => void;
	api.GET.mockImplementationOnce(
		() =>
			new Promise((resolve) => {
				finish = resolve;
			})
	);
	await user.click(screen.getByRole('button', { name: 'Reload for review' }));
	expect(screen.queryByRole('button', { name: 'Review registration' })).toBeNull();
	expect(screen.queryByRole('button', { name: 'Save draft' })).toBeNull();
	expect(api.POST).toHaveBeenCalledTimes(1);
	finish({ data: { ...template, revision: 2 } });
	await user.click(await screen.findByRole('button', { name: 'Review registration' }));
	await user.click(screen.getByRole('checkbox'));
	await user.click(screen.getByRole('button', { name: 'Save draft' }));
	expect(api.POST.mock.calls[1][1].body.request_id).not.toBe(
		api.POST.mock.calls[0][1].body.request_id
	);
	expect(api.POST.mock.calls[1][1].body.template_revision).toBe(2);
});

test.each(['active', 'paused'])(
	'unsent %s preview remains structurally editable after review',
	async (mode) => {
		setup();
		render(WorkPlanTemplates, { project, plans: [], onclose: vi.fn(), refresh: vi.fn() });
		const user = userEvent.setup();
		await user.click(await screen.findByRole('button', { name: 'Use template' }));
		await user.selectOptions(screen.getByRole('combobox', { name: 'Save as' }), mode);
		await user.click(screen.getByRole('button', { name: 'Review registration' }));
		await user.click(screen.getByRole('button', { name: 'Back to editing' }));
		expect(screen.getByRole('button', { name: 'Add task' })).toBeTruthy();
		expect(screen.getByRole('textbox', { name: 'Key' }).hasAttribute('readonly')).toBe(false);
	}
);

test('stale definition keeps unsent input until explicit current-definition reload', async () => {
	setup();
	render(WorkPlanTemplates, { project, plans: [], onclose: vi.fn(), refresh: vi.fn() });
	const user = userEvent.setup();
	await user.click(await screen.findByRole('button', { name: 'Edit template' }));
	await user.clear(screen.getAllByRole('textbox', { name: 'Template name' })[0]);
	await user.type(screen.getAllByRole('textbox', { name: 'Template name' })[0], 'Unsent');
	api.PUT.mockResolvedValue({
		error: { code: 'TEMPLATE_REVISION_CHANGED' },
		response: { status: 409 }
	});
	await user.click(screen.getByRole('button', { name: 'Save definition' }));
	expect(
		(screen.getAllByRole('textbox', { name: 'Template name' })[0] as HTMLInputElement).value
	).toBe('Unsent');
	api.GET.mockImplementationOnce(async () => ({
		data: { ...template, name: 'Current', revision: 2 }
	}));
	await user.click(await screen.findByRole('button', { name: 'Reload definition for review' }));
	await waitFor(() =>
		expect(
			(screen.getAllByRole('textbox', { name: 'Template name' })[0] as HTMLInputElement).value
		).toBe('Current')
	);
	await user.click(screen.getByRole('button', { name: 'Save definition' }));
	expect(api.PUT.mock.calls[1][1].body.expected_revision).toBe(2);
	expect(api.PUT.mock.calls[1][1].body.request_id).not.toBe(
		api.PUT.mock.calls[0][1].body.request_id
	);
});

test.each(['extract', 'delete'])(
	'pending template read disables prepared %s mutations',
	async (operation) => {
		setup();
		render(WorkPlanTemplates, {
			project,
			plans: [{ id: 'source', title: 'Source', revision: 7 } as never],
			onclose: vi.fn(),
			refresh: vi.fn()
		});
		const user = userEvent.setup();
		await screen.findByRole('button', { name: 'Use template' });
		if (operation === 'extract') {
			await user.selectOptions(screen.getByRole('combobox', { name: 'Source Plan' }), 'source');
			await user.type(screen.getByRole('textbox', { name: 'Template name' }), 'Saved');
		} else {
			await user.click(screen.getByRole('button', { name: 'Delete template' }));
			await user.click(screen.getByRole('checkbox'));
		}
		let finish!: (value: unknown) => void;
		api.GET.mockImplementationOnce(
			() =>
				new Promise((resolve) => {
					finish = resolve;
				})
		);
		await user.click(screen.getByRole('button', { name: 'Refresh templates' }));
		if (operation === 'delete') await user.click(screen.getByRole('checkbox'));
		const button = screen.getByRole('button', {
			name: operation === 'extract' ? 'Save source definition' : 'Confirm template deletion'
		});
		expect(button.hasAttribute('disabled')).toBe(true);
		await user.click(button);
		expect(api.POST).not.toHaveBeenCalled();
		expect(api.DELETE).not.toHaveBeenCalled();
		finish({ data: { items: [template], total_count: 1 } });
		await screen.findByRole('button', { name: 'Use template' });
	}
);
