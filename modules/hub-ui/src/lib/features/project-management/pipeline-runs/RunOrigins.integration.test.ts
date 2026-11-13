import { cleanup, render, screen } from '@testing-library/svelte';
import { afterEach, expect, test } from 'vitest';
import type { components } from '$lib/api';
import RunOrigins from './RunOrigins.svelte';
afterEach(cleanup);
const run = {
	id: 'run',
	project_id: 'p',
	branch: 'dev/current',
	related_origins: []
} as unknown as components['schemas']['PipelineRunRead'];
test('unknown origin stays explicit without invented enrollment channel', () => {
	render(RunOrigins, { run });
	expect(screen.getByText(/Origin unknown/)).toBeTruthy();
	expect(screen.queryAllByRole('link')).toHaveLength(0);
});
test('all retained references stay distinguishable and link exact subjects', () => {
	render(RunOrigins, {
		run: {
			...run,
			sdd_snapshot: { spec_dir: 'specs/2026-11/current' },
			related_origins: [
				{ kind: 'work_plan', id: 'item', work_plan_id: 'plan' },
				{
					kind: 'provider_session',
					id: 'session',
					catalog_id: 'catalog',
					url: 'https://jules.google.com/session/exact'
				},
				{ kind: 'native_sdd', id: 'claim', unit: 'docs/proposals/PROP-old', batch_id: 'batch' }
			]
		}
	});
	expect(screen.getByRole('link', { name: 'Work Item item' }).getAttribute('href')).toBe(
		'/projects/p?tab=plans#work-item-item'
	);
	expect(screen.getByRole('link', { name: 'Provider session session' }).getAttribute('href')).toBe(
		'https://jules.google.com/session/exact'
	);
	expect(
		screen.getByRole('link', { name: 'specs/2026-11/current' }).getAttribute('href')
	).toContain('ref=dev%2Fcurrent');
	expect(screen.getByRole('link', { name: 'SDD batch batch' }).getAttribute('href')).toBe(
		'/projects/p?tab=repository&batch=batch'
	);
	expect(screen.getByText(/Related SDD history/)).toBeTruthy();
});
test('session without exact URL remains text, not a misleading catalog link', () => {
	render(RunOrigins, {
		run: {
			...run,
			related_origins: [
				{ kind: 'provider_session', id: 'retained', catalog_id: 'catalog', url: null }
			]
		}
	});
	expect(screen.getByText('Provider session retained')).toBeTruthy();
	expect(screen.queryAllByRole('link')).toHaveLength(0);
});
