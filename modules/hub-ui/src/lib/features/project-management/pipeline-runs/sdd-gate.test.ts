import { expect, test } from 'vitest';
import type { components } from '$lib/api';
import { gateSteps, sddActivityKind, sddQuestionHeading } from './sdd-gate';

const run = (state: string, snapshot: Record<string, unknown> | null = {}) =>
	({
		state,
		sdd_snapshot: snapshot && {
			spec_dir: 'docs/proposals/PROP-demo',
			activity_kind: 'plan',
			...snapshot
		}
	}) as unknown as components['schemas']['PipelineRunRead'];
const question = (source: string, answers: { applied_attempt_id: string | null }[] = []) =>
	({ source, answers }) as unknown as components['schemas']['QuestionRead'];

test('names the activity gate and unit only for SDD runs', () => {
	expect(sddQuestionHeading(run('paused'), question('agent'))).toBe(
		'Planning gate · docs/proposals/PROP-demo'
	);
	expect(sddQuestionHeading(run('paused', { activity_kind: 'dev' }), question('operator'))).toBe(
		'Development question · docs/proposals/PROP-demo'
	);
	expect(sddQuestionHeading(run('paused', null), question('agent'))).toBeNull();
});

test('a snapshot without an activity kind reads as Development, like the request builder', () => {
	expect(sddActivityKind(run('paused', { activity_kind: undefined }))).toBe('dev');
	expect(sddActivityKind(run('paused', { activity_kind: 'review' }))).toBeNull();
	expect(sddActivityKind(run('paused', { spec_dir: '' }))).toBeNull();
	expect(sddActivityKind(run('paused', null))).toBeNull();
	expect(sddQuestionHeading(run('paused', { activity_kind: undefined }), question('agent'))).toBe(
		'Development gate · docs/proposals/PROP-demo'
	);
});

const asked = 'a'.repeat(40);
const pushed = 'b'.repeat(40);
const gate = (answers: { applied_attempt_id: string | null }[] = []) =>
	({
		source: 'agent',
		head_sha: asked,
		answers: answers.map((answer) => ({ ...answer, created_at: '2026-11-12T08:00:00Z' }))
	}) as unknown as components['schemas']['QuestionRead'];
const observed = (state: string, observation: Record<string, unknown> | null) =>
	({ ...run(state), pull_observation: observation }) as components['schemas']['PipelineRunRead'];
const status = (steps: ReturnType<typeof gateSteps>) => steps.map((step) => step.status);

test('tracks the gate from question to applied answer', () => {
	expect(status(gateSteps(run('paused'), gate()))).toEqual([
		'done',
		'current',
		'next',
		'next',
		'next',
		'next'
	]);
	expect(status(gateSteps(run('paused'), gate([{ applied_attempt_id: null }])))).toEqual([
		'done',
		'done',
		'current',
		'next',
		'next',
		'next'
	]);
	expect(status(gateSteps(run('implementing'), gate([{ applied_attempt_id: 'a' }])))).toEqual([
		'done',
		'done',
		'done',
		'current',
		'next',
		'next'
	]);
});

test('delivery steps follow only an observation of a head pushed after the answer', () => {
	const applied = gate([{ applied_attempt_id: 'a' }]);
	const at = (
		head: string,
		draft: boolean,
		verification: string,
		when = '2026-11-12T09:00:00Z'
	) => ({ head_sha: head, draft, verification, reason: '', observed_at: when });
	const draft = gateSteps(observed('awaiting_ci', at(pushed, true, 'waiting')), applied);
	expect(status(draft).slice(3)).toEqual(['done', 'current', 'next']);
	expect(draft[4].note).toBe('observed as Draft');
	const failing = gateSteps(observed('awaiting_ci', at(pushed, false, 'failed')), applied);
	expect(status(failing).slice(4)).toEqual(['done', 'current']);
	expect(failing[5].note).toBe('CI failed');
	expect(
		status(gateSteps(observed('awaiting_ci', at(pushed, false, 'passed')), applied)).slice(4)
	).toEqual(['done', 'done']);
	// The question's own head, or anything observed before the answer, describes the old work.
	expect(
		status(gateSteps(observed('awaiting_ci', at(asked, false, 'passed')), applied)).slice(3)
	).toEqual(['current', 'next', 'next']);
	expect(
		status(
			gateSteps(
				observed('awaiting_ci', at(pushed, false, 'passed', '2026-11-12T07:00:00Z')),
				applied
			)
		).slice(4)
	).toEqual(['next', 'next']);
	expect(status(gateSteps(observed('awaiting_ci', null), applied)).slice(4)).toEqual([
		'next',
		'next'
	]);
});
