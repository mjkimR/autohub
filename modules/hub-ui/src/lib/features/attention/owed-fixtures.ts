import type { OwedItem, OwedKind } from './owed-links';

export const PROJECT = '11111111-1111-4111-8111-111111111111';
export const RUN = '22222222-2222-4222-8222-222222222222';
export const PLAN = '33333333-3333-4333-8333-333333333333';
export const ITEM = '44444444-4444-4444-8444-444444444444';
export const BATCH = '55555555-5555-4555-8555-555555555555';

const ACTIONS: Record<
	OwedKind,
	[OwedItem['primary_action']['name'], string, OwedItem['subject']['type']]
> = {
	decision: ['answer', 'Answer', 'decision'],
	'stopped-run': ['resume-run', 'Resume run', 'pipeline-run'],
	'work-plan-proposed': ['review-plan', 'Review plan', 'work-plan'],
	'work-item-recovery': ['inspect-recovery', 'Inspect recovery', 'work-item-recovery'],
	'work-item-replacement': ['accept-replacement', 'Accept replacement', 'replacement-link'],
	'work-item-attention': ['inspect-work-item', 'Inspect Work Item', 'work-item'],
	'sdd-batch-attention': ['inspect-batch', 'Inspect batch', 'sdd-batch'],
	'connection-test-cleanup': ['review-cleanup', 'Review cleanup', 'connection-test'],
	'failed-run': ['inspect-run', 'Inspect run', 'pipeline-run']
};

/** A typed owed item as the API returns it; overrides patch any field. */
export function owedItem(
	kind: OwedKind,
	overrides: Partial<Omit<OwedItem, 'context' | 'subject'>> & {
		subject?: Partial<OwedItem['subject']>;
		context?: Partial<OwedItem['context']>;
	} = {}
): OwedItem {
	const [name, label, type] = ACTIONS[kind];
	const id = overrides.subject?.id ?? (kind === 'decision' ? 'run-question:q1' : `${kind}-id`);
	return {
		key: `${kind}:${id}`,
		kind,
		counted: kind !== 'failed-run',
		cause: `${label} cause`,
		waiting_since: '2026-11-12T06:30:00Z',
		primary_action: { name, label },
		...overrides,
		subject: { type, id, project_id: PROJECT, title: `${kind} title`, ...overrides.subject },
		context: {
			run_id: null,
			work_plan_id: null,
			work_item_id: null,
			sdd_batch_id: null,
			catalog_hold: null,
			...overrides.context
		}
	};
}
