import type { components } from '$lib/api';
import { isTerminalRun } from './run-actions';

type Run = components['schemas']['PipelineRunRead'];
type Question = components['schemas']['QuestionRead'];
export type GateStep = { label: string; status: 'done' | 'current' | 'next' };

/** Free-text guidance only: Hub neither reads nor records gate state (CAP-SDD-native-delivery 15). */
export const GATE_ANSWER_PLACEHOLDER =
	'Answer in the form the question asks for, such as accept, request changes (say which) or reject, and note any constraints to keep.';

export function sddUnit(run: Run): string {
	const unit = run.sdd_snapshot?.spec_dir;
	return typeof unit === 'string' ? unit : '';
}

/** Display label of the run's repository activity, or null outside SDD activity runs. */
export function sddActivityLabel(run: Run): string | null {
	const kind = run.sdd_snapshot?.activity_kind;
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
 * The gate's path through the run, from data Hub already holds. Draft/Ready and CI are not
 * part of the run read, so delivery after the agent applies the answer stays out of this track.
 */
export function gateSteps(run: Run, question: Question): GateStep[] {
	const answered = (question.answers ?? []).length > 0;
	const applied = (question.answers ?? []).some((answer) => !!answer.applied_attempt_id);
	const finished = run.state === 'completed';
	return [
		{ label: 'Agent asked', status: 'done' },
		{ label: 'Save an answer', status: answered ? 'done' : 'current' },
		{
			label: 'Resume with the answer',
			status: applied ? 'done' : answered ? 'current' : 'next'
		},
		{
			label: 'Agent applies the decision',
			status: finished ? 'done' : applied && !isTerminalRun(run) ? 'current' : 'next'
		}
	];
}
