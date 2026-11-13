import type { components } from '$lib/api';
import { projectTabHref, type ProjectTab } from './project-tabs';

export type OwedKind = components['schemas']['OwedItemRead']['kind'];
export type OwedCounts = components['schemas']['OwedItemCounts'];

/** Anchor of the project's exception strip; the Projects list "Needs you" count links here. */
export const NEEDS_YOU_ANCHOR = 'needs-you';

type KindSignal = {
	/** Project section where the operator resolves this kind (CAP-PR-owed-items §4). */
	tab: ProjectTab;
	one: string;
	many: string;
};

/**
 * Counted kinds in strip order (most specific root cause first), then the quiet failed-run kind.
 * Kind-to-section routing here duplicates part of the Attention landing's owed-links map; consolidate
 * once both exist.
 */
const signals: Record<OwedKind, KindSignal> = {
	decision: { tab: 'runs', one: 'decision', many: 'decisions' },
	'stopped-run': { tab: 'runs', one: 'held run', many: 'held runs' },
	'work-plan-proposed': {
		tab: 'plans',
		one: 'plan awaiting decision',
		many: 'plans awaiting decision'
	},
	'work-item-recovery': { tab: 'plans', one: 'recovery to inspect', many: 'recoveries to inspect' },
	'work-item-replacement': {
		tab: 'plans',
		one: 'replacement to accept',
		many: 'replacements to accept'
	},
	'work-item-attention': {
		tab: 'plans',
		one: 'Work Item needs attention',
		many: 'Work Items need attention'
	},
	'sdd-batch-attention': {
		tab: 'repository',
		one: 'batch needs attention',
		many: 'batches need attention'
	},
	'connection-test-cleanup': {
		tab: 'connections',
		one: 'cleanup to review',
		many: 'cleanups to review'
	},
	'failed-run': { tab: 'runs', one: 'failed run', many: 'failed runs' }
};

const kindOrder = Object.keys(signals) as OwedKind[];

export type OwedChip = {
	kind: OwedKind;
	count: number;
	label: string;
	href: string;
	quiet: boolean;
};

/** One chip per kind with a non-zero count; `failed-run` is quiet (listed, never counted). */
export function owedChips(projectId: string, byKind: Record<string, number>): OwedChip[] {
	return kindOrder.flatMap((kind) => {
		const count = byKind[kind] ?? 0;
		if (count <= 0) return [];
		const signal = signals[kind];
		return [
			{
				kind,
				count,
				label: `${count} ${count === 1 ? signal.one : signal.many}`,
				href: projectTabHref(projectId, signal.tab),
				quiet: kind === 'failed-run'
			}
		];
	});
}

/** The Attention landing (`/`) filtered to one project; the query parameter is `project`. */
export function attentionHref(projectId: string): string {
	return `/?project=${encodeURIComponent(projectId)}`;
}

/** The project's exception strip, reachable from any list. */
export function needsYouHref(projectId: string): string {
	return `${projectTabHref(projectId, 'overview')}#${NEEDS_YOU_ANCHOR}`;
}

/** Spoken form of a counted total, e.g. "3 items need you". */
export function needsYouPhrase(total: number): string {
	return `${total} ${total === 1 ? 'item needs' : 'items need'} you`;
}
