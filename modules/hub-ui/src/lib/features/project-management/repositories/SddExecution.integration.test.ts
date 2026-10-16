import { cleanup, render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import SddExecution from './SddExecution.svelte';

const { api } = vi.hoisted(() => ({ api: { POST: vi.fn(), GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
beforeEach(() => {
	api.POST.mockReset();
	api.GET.mockReset().mockResolvedValue({ data: [] });
});
afterEach(cleanup);

test('readiness shows best-effort warnings without blocking the start', async () => {
	const user = userEvent.setup();
	api.POST.mockResolvedValueOnce({
		data: {
			ready: true,
			head_sha: 'a'.repeat(40),
			cli_version: 'devkit-spec:lock',
			warnings: [{ code: 'RECEIPT_STALE', detail: 'Receipt differs from the reviewed runtime' }]
		}
	});
	render(SddExecution, { projectId: 'project', selectedSpec: 'specs/2026-10/20261010-feature' });
	await user.click(screen.getByRole('button', { name: 'Check readiness' }));
	expect(await screen.findByText(/Ready at commit aaaaaaaaaaaa/)).toBeTruthy();
	expect(screen.getByText('Receipt differs from the reviewed runtime')).toBeTruthy();
	expect(
		(screen.getByRole('button', { name: 'Start execution' }) as HTMLButtonElement).disabled
	).toBe(false);
});

test('a failed inspection replaces earlier warnings with its reason', async () => {
	const user = userEvent.setup();
	api.POST.mockResolvedValueOnce({
		data: {
			ready: true,
			head_sha: 'a'.repeat(40),
			cli_version: 'devkit-spec:lock',
			warnings: [{ code: 'RUNTIME_REVISION_MISMATCH', detail: 'Repository locks another revision' }]
		}
	}).mockResolvedValueOnce({ data: { ready: false, reason: 'Select an open pull request' } });
	render(SddExecution, { projectId: 'project', selectedSpec: 'specs/2026-10/20261010-feature' });
	await user.click(screen.getByRole('button', { name: 'Check readiness' }));
	expect(await screen.findByText('Repository locks another revision')).toBeTruthy();
	await user.click(screen.getByRole('button', { name: 'Check readiness' }));
	expect(await screen.findByRole('alert')).toBeTruthy();
	expect(screen.queryByText('Repository locks another revision')).toBeNull();
	expect(
		(screen.getByRole('button', { name: 'Start execution' }) as HTMLButtonElement).disabled
	).toBe(true);
});

test('start sends the chosen activity effort and the runtime check reports the host', async () => {
	const user = userEvent.setup();
	api.GET.mockImplementation(async (path: string) =>
		path.endsWith('/sdd/runtime')
			? {
					data: { ok: true, isolation: 'bubblewrap', revisions: { 'devkit-spec': 'f'.repeat(40) } }
				}
			: { data: [] }
	);
	api.POST.mockImplementation(async (path: string) =>
		path.endsWith('/sdd/readiness')
			? {
					data: {
						ready: true,
						head_sha: 'a'.repeat(40),
						cli_version: 'devkit-spec:lock',
						warnings: []
					}
				}
			: { data: { id: 'run-1' } }
	);
	render(SddExecution, { projectId: 'project', selectedSpec: 'specs/2026-10/20261010-feature' });
	await user.click(screen.getByRole('button', { name: 'Check runtime' }));
	expect(await screen.findByText(/Runtime bubblewrap: ok · devkit-spec ffffffffffff/)).toBeTruthy();
	await user.selectOptions(screen.getByLabelText('Activity effort'), 'high');
	await user.click(screen.getByRole('button', { name: 'Check readiness' }));
	await screen.findByText(/Ready at commit/);
	await user.click(screen.getByRole('button', { name: 'Start execution' }));
	const start = api.POST.mock.calls.find((call) => String(call[0]).endsWith('/runs'));
	expect(start?.[1].body).toMatchObject({ activity_effort: 'high', implemented: false });
});

test('an unavailable runtime is reported as an error with its detail', async () => {
	const user = userEvent.setup();
	api.GET.mockResolvedValue({
		data: {
			ok: false,
			isolation: null,
			detail: 'Provision the locked runtime with just install-sdd'
		}
	});
	render(SddExecution, { projectId: 'project' });
	await user.click(screen.getByRole('button', { name: 'Check runtime' }));
	expect(await screen.findByRole('alert')).toBeTruthy();
	expect(screen.getByText(/Runtime without a sandbox: unavailable/)).toBeTruthy();
});
