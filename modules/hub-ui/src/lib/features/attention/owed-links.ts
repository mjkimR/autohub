import type { components } from '$lib/api';
import { DECISIONS_HREF } from '$lib/components/shared/app-shell-nav';
import { runHref } from '$lib/features/project-management/pipeline-runs/run-links';
import { projectTabHref } from '$lib/features/project-management/projects/project-tabs';

export type OwedItem = components['schemas']['OwedItemRead'];
export type OwedKind = OwedItem['kind'];

/**
 * Where an owed item is resolved: the owner's existing screen, never a new action surface.
 * This is the single kind-to-URL mapping; every screen that routes an owed item uses it.
 */
export function owedHref(item: Pick<OwedItem, 'kind' | 'subject' | 'context'>): string {
	const project = item.subject.project_id;
	const { run_id: runId, work_plan_id: planId, work_item_id: workItemId } = item.context;
	const plans = projectTabHref(project, 'plans');
	switch (item.kind) {
		case 'decision':
			// The run page's Decisions section answers it; without a run the inbox row opens its Review.
			return runId ? runHref(runId, project, 'decisions') : DECISIONS_HREF;
		case 'stopped-run':
			return runHref(runId ?? item.subject.id, project);
		case 'failed-run':
			return runHref(runId ?? item.subject.id, project, 'next-step');
		case 'work-plan-proposed':
			return `${plans}#work-plan-${encodeURIComponent(planId ?? item.subject.id)}`;
		case 'work-item-recovery':
		case 'work-item-replacement':
		case 'work-item-attention':
			return workItemId ? `${plans}#work-item-${encodeURIComponent(workItemId)}` : plans;
		case 'sdd-batch-attention':
			return projectTabHref(project, 'repository');
		case 'connection-test-cleanup':
			return projectTabHref(project, 'connections');
	}
}

/** Per-kind display nouns for counts, e.g. "2 held PR runs" or "1 decision". */
export const OWED_KIND_NOUNS: Readonly<Record<OwedKind, { singular: string; plural: string }>> = {
	decision: { singular: 'decision', plural: 'decisions' },
	'stopped-run': { singular: 'held PR run', plural: 'held PR runs' },
	'work-plan-proposed': { singular: 'Work Plan to review', plural: 'Work Plans to review' },
	'work-item-recovery': { singular: 'Work Item recovery', plural: 'Work Item recoveries' },
	'work-item-replacement': { singular: 'Work Item replacement', plural: 'Work Item replacements' },
	'work-item-attention': {
		singular: 'Work Item needing attention',
		plural: 'Work Items needing attention'
	},
	'sdd-batch-attention': { singular: 'SDD batch in attention', plural: 'SDD batches in attention' },
	'connection-test-cleanup': {
		singular: 'connection-test cleanup',
		plural: 'connection-test cleanups'
	},
	'failed-run': { singular: 'failed PR run', plural: 'failed PR runs' }
};

/** "N <noun>" with the kind's singular or plural noun. */
export function owedKindCount(kind: OwedKind, count: number): string {
	const noun = OWED_KIND_NOUNS[kind];
	return `${count} ${count === 1 ? noun.singular : noun.plural}`;
}

/** The project section that holds a kind, for links that know only the project (no subject). */
export function owedProjectHref(kind: OwedKind, projectId: string): string {
	switch (kind) {
		case 'decision':
		case 'stopped-run':
		case 'failed-run':
			return projectTabHref(projectId, 'runs');
		case 'work-plan-proposed':
		case 'work-item-recovery':
		case 'work-item-replacement':
		case 'work-item-attention':
			return projectTabHref(projectId, 'plans');
		case 'sdd-batch-attention':
			return projectTabHref(projectId, 'repository');
		case 'connection-test-cleanup':
			return projectTabHref(projectId, 'connections');
	}
}

/** The Attention landing, optionally filtered to one project (`/?project=<id>`). */
export function attentionHref(projectId?: string | null): string {
	return projectId ? `/?project=${encodeURIComponent(projectId)}` : '/';
}
