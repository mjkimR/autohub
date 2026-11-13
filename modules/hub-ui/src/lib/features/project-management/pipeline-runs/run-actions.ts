import { api, type components } from '$lib/api';
import { responseData } from '$lib/api/pagination';
import type { RunSection } from './run-links';

type Run = components['schemas']['PipelineRunRead'];
export type DecisionEntry = components['schemas']['DecisionEntryRead'];

const TERMINAL = ['completed', 'failed', 'canceled'];

export function isTerminalRun(
	run: Pick<Run, 'state'> & Partial<Pick<Run, 'sdd_snapshot'>>
): boolean {
	return (
		!!(run.sdd_snapshot && run.sdd_snapshot.execution_version !== 2) || TERMINAL.includes(run.state)
	);
}

/**
 * Pending decisions a PR run carries, as the Decision inbox observes them. `unknown` means the
 * list could not be read completely, so callers keep their conservative defaults.
 */
export type RunDecisions = { status: 'known'; entries: DecisionEntry[] } | { status: 'unknown' };

const QUESTION_KINDS: DecisionEntry['kind'][] = [
	'run-question',
	'native-hub-question',
	'native-worker-question'
];

/** What a pending decision asks of the operator, from the most to the least urgent. */
export type DecisionWait = 'question' | 'saved-answer' | 'approval' | 'publication';

export function decisionWait(entries: DecisionEntry[]): DecisionWait | null {
	const actionable = entries.filter((entry) => entry.actionable);
	const questions = actionable.filter((entry) => QUESTION_KINDS.includes(entry.kind));
	if (questions.some((entry) => entry.question_state !== 'answered')) return 'question';
	if (questions.length) return 'saved-answer';
	if (actionable.length) return 'approval';
	return entries.length ? 'publication' : null;
}

/** Short marker text for a run row or header; null when nothing waits on the operator. */
export function decisionWaitLabel(wait: DecisionWait | null): string | null {
	switch (wait) {
		case 'question':
			return 'Question waiting';
		case 'saved-answer':
			return 'Answer saved — resume pending';
		case 'approval':
			return 'Approval waiting';
		default:
			return null;
	}
}

export type RunActionKind =
	| 'answer'
	| 'resume-saved'
	| 'review-approval'
	| 'check-decision'
	| 'resume'
	| 'next-step'
	| 'attach-pr'
	| 'open';

/**
 * `short` is the compact row label; `label` names the action in full (page, accessible name).
 * Row accessible names must contain the visible `short` text (WCAG 2.5.3).
 */
export type RunAction = { kind: RunActionKind; label: string; short: string; section?: RunSection };

/**
 * The single state-driven primary action of a PR run. A run held by a pending question or
 * approval never offers a plain Resume, because the backend refuses it until that decision is made.
 * When its decisions are unknown, the primary action stays non-mutating (Open run) and plain
 * Resume is only a secondary action.
 */
export function primaryRunAction(run: Run, decisions: RunDecisions): RunAction {
	if (run.sdd_snapshot && run.sdd_snapshot.execution_version !== 2)
		return { kind: 'open', label: 'Inspect retired run', short: 'Inspect', section: 'decisions' };
	const wait =
		decisions.status === 'known' && !isTerminalRun(run) ? decisionWait(decisions.entries) : null;
	if (wait === 'question')
		return { kind: 'answer', label: 'Answer question', short: 'Answer', section: 'decisions' };
	if (wait === 'saved-answer')
		return {
			kind: 'resume-saved',
			label: 'Resume with saved answer',
			short: 'Apply answer',
			section: 'decisions'
		};
	if (wait === 'approval')
		return {
			kind: 'review-approval',
			label: 'Review approval',
			short: 'Review',
			section: 'decisions'
		};
	if (wait === 'publication')
		return {
			kind: 'check-decision',
			label: 'Check decision',
			short: 'Check',
			section: 'decisions'
		};
	if (run.state === 'failed')
		return { kind: 'next-step', label: 'Next step', short: 'Next step', section: 'next-step' };
	if ((run.state === 'paused' || run.state === 'blocked') && decisions.status === 'known')
		return { kind: 'resume', label: 'Resume', short: 'Resume' };
	if (!isTerminalRun(run) && !run.pull_number)
		return { kind: 'attach-pr', label: 'Attach PR', short: 'Attach PR' };
	return { kind: 'open', label: 'Open run', short: 'Open' };
}

/** Accessible name of a row's primary action: contains its visible text and names the PR. */
export function rowActionName(action: RunAction, run: Pick<Run, 'pull_number'>): string {
	const full = action.label.includes(action.short)
		? action.label
		: `${action.short} (${action.label.toLowerCase()})`;
	return `${full} for PR #${run.pull_number || 'pending'}`;
}

/** Plain Resume is offered only for a stopped run that no known decision holds. */
export function canResume(run: Run, decisions: RunDecisions): boolean {
	if (run.sdd_snapshot && run.sdd_snapshot.execution_version !== 2) return false;
	if (run.state !== 'paused' && run.state !== 'blocked') return false;
	return decisions.status === 'unknown' || decisionWait(decisions.entries) === null;
}

/** Group a decisions page by run; incomplete pages mark runs without entries as unknown. */
export function decisionsFor(
	runId: string,
	page: { byRun: Map<string, DecisionEntry[]>; complete: boolean } | null
): RunDecisions {
	if (!page) return { status: 'unknown' };
	const entries = page.byRun.get(runId);
	if (entries) return { status: 'known', entries };
	return page.complete ? { status: 'known', entries: [] } : { status: 'unknown' };
}

/**
 * One bounded read of observed pending decisions (optionally for one project), grouped by run.
 * Used for list markers and run actions instead of a per-row request.
 */
export async function loadPendingDecisions(
	projectId?: string,
	maxPages = 1
): Promise<{ byRun: Map<string, DecisionEntry[]>; complete: boolean }> {
	const byRun = new Map<string, DecisionEntry[]>();
	let cursor: string | undefined;
	for (let page = 0; page < maxPages; page += 1) {
		const data = responseData(
			await api.GET('/api/v1/pipeline-runs/decisions', {
				params: { query: { project_id: projectId, cursor, limit: 100 } }
			}),
			'Unable to load pending decisions'
		);
		for (const entry of data.items)
			byRun.set(entry.run_id, [...(byRun.get(entry.run_id) ?? []), entry]);
		if (!data.has_more || !data.next_cursor) return { byRun, complete: true };
		cursor = data.next_cursor;
	}
	return { byRun, complete: false };
}
