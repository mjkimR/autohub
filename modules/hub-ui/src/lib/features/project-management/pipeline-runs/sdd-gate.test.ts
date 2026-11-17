import { expect, test } from 'vitest';
import type { components } from '$lib/api';
import { gateSteps, sddQuestionHeading } from './sdd-gate';

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

test('tracks the gate from question to applied answer', () => {
	const status = (steps: ReturnType<typeof gateSteps>) => steps.map((step) => step.status);
	expect(status(gateSteps(run('paused'), question('agent')))).toEqual([
		'done',
		'current',
		'next',
		'next'
	]);
	expect(
		status(gateSteps(run('paused'), question('agent', [{ applied_attempt_id: null }])))
	).toEqual(['done', 'done', 'current', 'next']);
	expect(
		status(gateSteps(run('implementing'), question('agent', [{ applied_attempt_id: 'a' }])))
	).toEqual(['done', 'done', 'done', 'current']);
});
