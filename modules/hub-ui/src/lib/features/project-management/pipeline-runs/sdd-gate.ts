import type { components } from '$lib/api';
import { verificationPresentation } from './pull-status';
import { isTerminalRun } from './run-actions';

type Run = components['schemas']['PipelineRunRead'];
type Question = components['schemas']['QuestionRead'];
export type GateStep = {
	label: string;
	status: 'done' | 'current' | 'next';
	/** Observed detail shown beside the step, such as "CI failed". */
	note?: string;
};

/** Free-text guidance only: Hub neither reads nor records gate state (CAP-SDD-native-delivery 15). */
export const GATE_ANSWER_PLACEHOLDER =
	'Answer in the form the question asks for, such as accept, request changes (say which) or reject, and note any constraints to keep.';

export function sddUnit(run: Run): string {
	const unit = run.sdd_snapshot?.spec_dir;
	return typeof unit === 'string' ? unit : '';
}

/**
 * The repository activity an SDD run was asked to perform. A snapshot without a kind was sent
 * as Development by the request builder, so it reads as `dev`; an unknown kind stays null.
 */
export function sddActivityKind(run: Pick<Run, 'sdd_snapshot'>): 'plan' | 'dev' | null {
	const snapshot = run.sdd_snapshot;
	if (!snapshot || typeof snapshot.spec_dir !== 'string' || !snapshot.spec_dir) return null;
	const kind = snapshot.activity_kind;
	if (kind === undefined || kind === null || kind === '') return 'dev';
	return kind === 'plan' || kind === 'dev' ? kind : null;
}

/** Display label of the run's repository activity, or null outside SDD activity runs. */
export function sddActivityLabel(run: Run): string | null {
	const kind = sddActivityKind(run);
	return kind === 'plan' ? 'Planning' : kind === 'dev' ? 'Development' : null;
}

/** "Planning gate · <unit>" for an agent question on an SDD activity run. */
export function sddQuestionHeading(run: Run, question: Question): string | null {
	if (!run.sdd_snapshot) return null;
	const activity = sddActivityLabel(run) ?? 'SDD';
	const unit = sddUnit(run);
	const kind = question.source === 'agent' ? 'gate' : 'question';
	return unit ? `${activity} ${kind} · ${unit}` : `${activity} ${kind}`;
}

/**
 * The gate's path through the run, then delivery, from data Hub already holds: the question and
 * its answers, the run state and the last observed PR status. Hub records no gate state
 * (CAP-SDD-native-delivery 15); the delivery steps only mirror what GitHub was last observed to
 * report, and only an observation of a head pushed after the answer counts for them.
 */
export function gateSteps(run: Run, question: Question): GateStep[] {
	const answers = question.answers ?? [];
	const answered = answers.length > 0;
	const applied = answers.some((answer) => !!answer.applied_attempt_id);
	const finished = run.state === 'completed';
	const observation = run.pull_observation ?? null;
	const lastAnswer = Math.max(...answers.map((answer) => Date.parse(answer.created_at)), 0);
	// The agent pushes its applied decision as a new head; an older head says nothing about it.
	const fresh =
		applied &&
		!!observation &&
		observation.head_sha !== question.head_sha &&
		Date.parse(observation.observed_at) > lastAnswer
			? observation
			: null;
	const ready = finished || (!!fresh && !fresh.draft);
	const verification = fresh ? verificationPresentation(fresh.verification).label : null;
	return [
		{ label: 'Agent asked', status: 'done' },
		{ label: 'Save an answer', status: answered ? 'done' : 'current' },
		{
			label: 'Resume with the answer',
			status: applied ? 'done' : answered ? 'current' : 'next'
		},
		{
			label: 'Agent applies the decision',
			status: finished || fresh ? 'done' : applied && !isTerminalRun(run) ? 'current' : 'next'
		},
		{
			label: 'Mark Ready in GitHub',
			status: ready ? 'done' : fresh?.draft ? 'current' : 'next',
			note: fresh?.draft ? 'observed as Draft' : undefined
		},
		{
			label: 'CI passes',
			status:
				finished || fresh?.verification === 'passed'
					? 'done'
					: fresh && !fresh.draft
						? 'current'
						: 'next',
			note:
				verification && !fresh?.draft && fresh?.verification !== 'passed' ? verification : undefined
		}
	];
}
