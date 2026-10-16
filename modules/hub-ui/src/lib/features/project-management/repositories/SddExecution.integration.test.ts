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
