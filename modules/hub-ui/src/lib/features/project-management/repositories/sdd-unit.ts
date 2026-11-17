import type { components } from '$lib/api';
import { displayLabel } from '$lib/labels';
import { isTerminalRun } from '../pipeline-runs/run-actions';
import { runHref } from '../pipeline-runs/run-links';
import { sddActivityKind } from '../pipeline-runs/sdd-gate';
import { unitDirectory } from './repository-selection.svelte';

type Run = components['schemas']['PipelineRunRead'];
export type UnitActivity = 'plan' | 'dev';

export const ACTIVITY_LABELS: Record<UnitActivity, string> = {
	plan: 'Planning',
	dev: 'Development'
};

/** Activity display label for a raw activity value (`plan`, `dev`), never the raw token. */
export function activityLabel(value: string): string {
	return displayLabel(value, ACTIVITY_LABELS);
}

const EFFORT_LABELS: Record<string, string> = { low: 'Low', medium: 'Medium', high: 'High' };

/** Effort display label; an unset effort follows the repository recommendation. */
export function effortLabel(value: string | null | undefined): string {
	return value ? displayLabel(value, EFFORT_LABELS) : 'Repository recommendation';
}

/** The SDD unit directory that contains a repository path, or '' outside a unit. */
export function unitFromPath(path: string): string {
	const candidate =
		path.match(/^(specs\/\d{4}-\d{2}\/[^/]+|docs\/proposals\/PROP-[^/]+)\//)?.[1] || '';
	return unitDirectory.test(candidate) ? candidate : '';
}

/** The repository activity a PR run performs, from its retained SDD intent. */
export function runActivity(run: Run): UnitActivity | null {
	return sddActivityKind(run);
}

/** A run owes the operator a decision or recovery only while it is paused or blocked. */
export function runOwesOperator(run: Pick<Run, 'state'>): boolean {
	return run.state === 'paused' || run.state === 'blocked';
}

/** Open the decisions section only when the run is waiting for the operator. */
export function unitRunHref(run: Run, projectId: string): string {
	return runHref(run.id, projectId, runOwesOperator(run) ? 'decisions' : undefined);
}

/** Latest non-final PR run for each activity; `runs` arrive newest first. */
export function activeRunsByActivity(runs: Run[]): Partial<Record<UnitActivity, Run>> {
	const active: Partial<Record<UnitActivity, Run>> = {};
	for (const run of runs) {
		const activity = runActivity(run);
		if (activity && !active[activity] && !isTerminalRun(run)) active[activity] = run;
	}
	return active;
}

/** Latest PR run for each activity, final or not, plus runs without a known activity. */
export function latestRunsByActivity(runs: Run[]): { activity: UnitActivity | null; run: Run }[] {
	const seen = new Set<UnitActivity>();
	const latest: { activity: UnitActivity | null; run: Run }[] = [];
	for (const run of runs) {
		const activity = runActivity(run);
		if (activity && seen.has(activity)) continue;
		if (activity) seen.add(activity);
		else if (latest.some((entry) => entry.activity === null)) continue;
		latest.push({ activity, run });
	}
	return latest;
}
