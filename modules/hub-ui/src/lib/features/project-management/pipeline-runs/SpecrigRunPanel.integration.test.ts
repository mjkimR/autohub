import { cleanup, render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import type { components } from '$lib/api';
import SpecrigRunPanel from './SpecrigRunPanel.svelte';

const { api } = vi.hoisted(() => ({ api: { POST: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const run = {
	id: 'run-1',
	revision: 3,
	state: 'paused',
	pull_url: 'https://github.com/owner/app/pull/7',
	specrig_snapshot: { spec_dir: 'specs/2026-10/20261010-feature' },
	specrig_progress: {
		head_sha: 'a'.repeat(40),
		base_sha: 'b'.repeat(40),
		current: { stage: { name: 'G3', exit: ['approval-given'] }, done: ['review'] }
	}
} as unknown as components['schemas']['PipelineRunRead'];
beforeEach(() => api.POST.mockReset());
afterEach(cleanup);

test('approval binds the inspected run revision and reuses identity after a lost response', async () => {
	const user = userEvent.setup({ delay: null });
	api.POST.mockRejectedValueOnce(new Error('Connection lost')).mockResolvedValueOnce({
		data: { ...run, state: 'dispatching' }
	});
	render(SpecrigRunPanel, { run, onchange: vi.fn() });
	await user.click(screen.getByRole('button', { name: 'Approve integration' }));
	const first = api.POST.mock.calls[0][1].body;
	expect(first).toMatchObject({ expected_revision: 3, decision: 'approve' });
	await screen.findByRole('alert');
	await user.click(screen.getByRole('button', { name: 'Approve integration' }));
	expect(api.POST.mock.calls[1][1].body.request_id).toBe(first.request_id);
	expect(screen.getByRole('link').getAttribute('href')).toContain(`/tree/${'a'.repeat(40)}/specs/`);
});

test('rework sends feedback separately from approval', async () => {
	const user = userEvent.setup();
	const onchange = vi.fn();
	api.POST.mockResolvedValue({ data: { ...run, state: 'dispatching' } });
	render(SpecrigRunPanel, { run, onchange });
	await user.type(screen.getByLabelText('Requested changes or decision reason'), 'Keep the API');
	await user.click(screen.getByRole('button', { name: 'Request changes' }));
	expect(api.POST.mock.calls[0][1].body).toMatchObject({
		decision: 'revise',
		feedback: 'Keep the API'
	});
	expect(onchange).toHaveBeenCalledOnce();
});
