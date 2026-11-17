import { expect, test } from 'vitest';
import type { components } from '$lib/api';
import { groupSummary, progressGroups, runsByUnit } from './progress';
import type { RepositoryDocument } from './model';

const doc = (path: string, meta: Record<string, unknown> = {}): RepositoryDocument => ({
	path,
	title: String(meta.title ?? path),
	id: String(meta.id ?? ''),
	status: String(meta.status ?? ''),
	meta,
	body: '',
	raw: ''
});
const run = (id: string, unit: string, state: string, kind = 'plan') =>
	({
		id,
		state,
		pull_number: 1,
		sdd_snapshot: { spec_dir: unit, activity_kind: kind }
	}) as unknown as components['schemas']['PipelineRunRead'];

test('groups milestone members, other proposals and specs, attaching latest runs per unit', () => {
	const documents = [
		doc('docs/roadmap/MS-a.md', { id: 'MS-a', title: 'A' }),
		doc('docs/proposals/PROP-x/proposal.md', { id: 'PROP-x', milestone: 'MS-a' }),
		doc('docs/proposals/PROP-y/proposal.md', { id: 'PROP-y' }),
		doc('docs/proposals/PROP-z/proposal.md', { id: 'PROP-z', status: 'rejected' }),
		doc('specs/2026-11/20261101-old/spec.md'),
		doc('specs/2026-11/20261117-new/spec.md')
	];
	const runs = runsByUnit([
		run('2', 'docs/proposals/PROP-x', 'paused', 'dev'),
		run('1', 'docs/proposals/PROP-x', 'completed', 'plan'),
		run('0', 'docs/proposals/PROP-x', 'failed', 'plan'),
		{ ...run('n', '', 'queued'), sdd_snapshot: null } as never
	]);
	const groups = progressGroups(documents, runs);
	expect(groups.map((g) => [g.title, g.rows.map((r) => r.unit)])).toEqual([
		['A', ['docs/proposals/PROP-x']],
		['Proposals outside milestones', ['docs/proposals/PROP-y']],
		['Specs', ['specs/2026-11/20261117-new', 'specs/2026-11/20261101-old']]
	]);
	expect(groups[0].rows[0].runs.map((r) => r.run.id)).toEqual(['2', '1']);
	expect(groupSummary(groups[0].rows)).toBe('1 unit · 1 with an active PR run · 1 waiting on you');
	expect(groupSummary(groups[2].rows)).toBe('2 units');
});

test('without milestones, proposals are one plain group', () => {
	const groups = progressGroups([doc('docs/proposals/PROP-y/proposal.md')]);
	expect(groups.map((g) => g.title)).toEqual(['Proposals']);
});
