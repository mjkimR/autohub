import { describe, expect, test, vi } from 'vitest';

vi.mock('$lib/api', () => ({ api: {} }));
import type { components } from '$lib/api';
import {
	canResume,
	decisionWait,
	decisionsFor,
	primaryRunAction,
	type DecisionEntry
} from './run-actions';
import { legacyRunRedirect, runHref } from './run-links';

type Run = components['schemas']['PipelineRunRead'];
const run = (state: Run['state'], extra: Partial<Run> = {}) =>
	({ id: 'r1', project_id: 'p1', state, pull_number: 7, ...extra }) as Run;
const entry = (kind: DecisionEntry['kind'], extra: Partial<DecisionEntry> = {}) =>
	({ run_id: 'r1', kind, actionable: true, question_state: null, ...extra }) as DecisionEntry;
const known = (...entries: DecisionEntry[]) => ({ status: 'known' as const, entries });

describe('primaryRunAction', () => {
	test.each([
		[
			'open question',
			run('paused'),
			known(entry('run-question', { question_state: 'open' })),
			'answer'
		],
		[
			'saved answer',
			run('paused'),
			known(entry('native-hub-question', { question_state: 'answered' })),
			'resume-saved'
		],
		['native approval', run('blocked'), known(entry('native-workflow')), 'review-approval'],
		[
			'publication pending',
			run('paused'),
			known(entry('native-worker-question', { actionable: false })),
			'check-decision'
		],
		['failed', run('failed'), known(), 'next-step'],
		['paused without decisions', run('paused'), known(), 'resume'],
		['paused with unknown decisions', run('paused'), { status: 'unknown' as const }, 'resume'],
		['no PR', run('queued', { pull_number: 0 }), known(), 'attach-pr'],
		['implementing', run('implementing'), known(), 'open'],
		['completed', run('completed'), known(entry('run-question')), 'open']
	])('%s', (_name, value, decisions, kind) => {
		expect(primaryRunAction(value, decisions).kind).toBe(kind);
	});

	test('a question outranks an approval on the same run', () => {
		expect(
			decisionWait([entry('native-workflow'), entry('run-question', { question_state: 'open' })])
		).toBe('question');
	});
});

test('plain Resume is withheld while a known decision holds the run', () => {
	expect(canResume(run('paused'), known(entry('native-proposal')))).toBe(false);
	expect(canResume(run('paused'), known())).toBe(true);
	expect(canResume(run('implementing'), known())).toBe(false);
});

test('an incomplete decisions page leaves runs without entries unknown', () => {
	const byRun = new Map([['r1', [entry('run-question')]]]);
	expect(decisionsFor('r2', { byRun, complete: false })).toEqual({ status: 'unknown' });
	expect(decisionsFor('r2', { byRun, complete: true })).toEqual(known());
	expect(decisionsFor('r1', null)).toEqual({ status: 'unknown' });
});

test('run links use the project route when known and keep old deep links working', () => {
	expect(runHref('r1', 'p1', 'decisions')).toBe('/projects/p1/runs/r1#decisions');
	expect(runHref('r1')).toBe('/runs/r1');
	expect(legacyRunRedirect('?run=r1&view=decisions')).toBe('/runs/r1#decisions');
	expect(legacyRunRedirect('?tab=runs&run=r1')).toBe('/runs/r1');
	expect(legacyRunRedirect('?tab=runs')).toBeNull();
});
