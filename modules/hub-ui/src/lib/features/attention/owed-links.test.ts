import { expect, test } from 'vitest';
import {
	OWED_KIND_NOUNS,
	attentionHref,
	owedHref,
	owedKindCount,
	owedProjectHref
} from './owed-links';
import { OWED_KINDS } from './owed-kinds';
import { BATCH, ITEM, PLAN, PROJECT, RUN, owedItem } from './owed-fixtures';

const project = `/projects/${PROJECT}`;
const run = `${project}/runs/${RUN}`;

test.each([
	['decision', { context: { run_id: RUN } }, `${run}#decisions`],
	['decision', {}, '/decisions'],
	['stopped-run', { subject: { id: RUN }, context: { run_id: RUN } }, run],
	['stopped-run', { subject: { id: RUN } }, run],
	['failed-run', { subject: { id: RUN }, context: { run_id: RUN } }, `${run}#next-step`],
	[
		'work-plan-proposed',
		{ subject: { id: PLAN }, context: { work_plan_id: PLAN } },
		`${project}?tab=plans#work-plan-${PLAN}`
	],
	[
		'work-item-recovery',
		{ context: { work_item_id: ITEM, work_plan_id: PLAN } },
		`${project}?tab=plans#work-item-${ITEM}`
	],
	['work-item-recovery', {}, `${project}?tab=plans`],
	[
		'work-item-replacement',
		{ context: { work_item_id: ITEM } },
		`${project}?tab=plans#work-item-${ITEM}`
	],
	[
		'work-item-attention',
		{ subject: { id: ITEM }, context: { work_item_id: ITEM } },
		`${project}?tab=plans#work-item-${ITEM}`
	],
	[
		'sdd-batch-attention',
		{ subject: { id: BATCH }, context: { sdd_batch_id: BATCH } },
		`${project}?tab=repository`
	],
	['connection-test-cleanup', {}, `${project}?tab=connections`]
] as const)('%s resolves to its owner (%#)', (kind, overrides, href) => {
	expect(owedHref(owedItem(kind, overrides))).toBe(href);
});

test('every kind has a landing section and a deep link', () => {
	const kinds = OWED_KINDS.map((entry) => entry.kind);
	expect(new Set(kinds).size).toBe(9);
	for (const kind of kinds) expect(owedHref(owedItem(kind))).toMatch(/^\//);
});

test.each([
	['decision', 'runs'],
	['stopped-run', 'runs'],
	['failed-run', 'runs'],
	['work-plan-proposed', 'plans'],
	['work-item-recovery', 'plans'],
	['work-item-replacement', 'plans'],
	['work-item-attention', 'plans'],
	['sdd-batch-attention', 'repository'],
	['connection-test-cleanup', 'connections']
] as const)('%s falls back to the project %s section', (kind, tab) => {
	expect(owedProjectHref(kind, PROJECT)).toBe(`/projects/${PROJECT}?tab=${tab}`);
});

test('kind counts use singular and plural nouns for every kind', () => {
	for (const { kind } of OWED_KINDS) {
		expect(owedKindCount(kind, 1)).toBe(`1 ${OWED_KIND_NOUNS[kind].singular}`);
		expect(owedKindCount(kind, 2)).toBe(`2 ${OWED_KIND_NOUNS[kind].plural}`);
	}
	expect(owedKindCount('stopped-run', 2)).toBe('2 held PR runs');
});

test('the landing link carries an optional project filter', () => {
	expect(attentionHref()).toBe('/');
	expect(attentionHref(PROJECT)).toBe(`/?project=${PROJECT}`);
});
