import type { components } from '$lib/api';
import { OWED_KINDS } from '$lib/features/attention/owed-kinds';
import { owedKindCount, owedProjectHref, type OwedKind } from '$lib/features/attention/owed-links';
import { projectTabHref } from './project-tabs';

export type { OwedKind };
export type OwedCounts = components['schemas']['OwedItemCounts'];

/** Anchor of the project's exception strip; the Projects list "Needs you" count links here. */
export const NEEDS_YOU_ANCHOR = 'needs-you';

export type OwedChip = {
	kind: OwedKind;
	count: number;
	label: string;
	href: string;
	quiet: boolean;
};

/**
 * One chip per kind with a non-zero count, in the Attention landing's order and wording.
 * `failed-run` is quiet (listed, never counted). Routing and nouns come from the shared
 * owed-links module so the landing and the strip never drift.
 */
export function owedChips(projectId: string, byKind: Record<string, number>): OwedChip[] {
	return OWED_KINDS.flatMap(({ kind, quiet }) => {
		const count = byKind[kind] ?? 0;
		if (count <= 0) return [];
		return [
			{
				kind,
				count,
				label: owedKindCount(kind, count),
				href: owedProjectHref(kind, projectId),
				quiet
			}
		];
	});
}

/** The project's exception strip, reachable from any list. */
export function needsYouHref(projectId: string): string {
	return `${projectTabHref(projectId, 'overview')}#${NEEDS_YOU_ANCHOR}`;
}

/** Spoken form of a counted total, e.g. "3 items need you". */
export function needsYouPhrase(total: number): string {
	return `${total} ${total === 1 ? 'item needs' : 'items need'} you`;
}
