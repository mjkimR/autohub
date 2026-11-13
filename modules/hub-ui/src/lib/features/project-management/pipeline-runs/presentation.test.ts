import { Ban, Check, CircleDashed, Clock, Hammer, OctagonX, Pause, Slash } from '@lucide/svelte';
import { describe, expect, test } from 'vitest';
import type { components } from '$lib/api';
import {
	attemptStateLabel,
	getRunStatePresentation,
	getStateBadgeVariant,
	questionStateLabel
} from './presentation';

type RunState = components['schemas']['PipelineRunState'];

const expected: [RunState, string, unknown, string][] = [
	['queued', 'outline', CircleDashed, 'Queued'],
	['dispatching', 'info', Hammer, 'Dispatching'],
	['implementing', 'info', Hammer, 'Implementing'],
	['awaiting_ci', 'outline', Clock, 'Awaiting CI'],
	['completed', 'success', Check, 'Completed'],
	['canceled', 'secondary', Slash, 'Canceled'],
	['paused', 'attention', Pause, 'Paused'],
	['blocked', 'attention', Ban, 'Blocked'],
	['failed', 'destructive', OctagonX, 'Failed']
];

describe('getRunStatePresentation', () => {
	test.each(expected)('%s → %s', (state, variant, icon, label) => {
		const view = getRunStatePresentation(state);
		expect(view).toEqual({ variant, icon, label });
		expect(getStateBadgeVariant(state)).toBe(variant);
	});

	test('no run state maps to warning', () => {
		for (const [state] of expected) {
			expect(getRunStatePresentation(state).variant).not.toBe('warning');
		}
	});

	test('an unknown future state falls back to a neutral labeled badge', () => {
		const view = getRunStatePresentation('rehydrating' as RunState);
		expect(view).toEqual({ variant: 'secondary', icon: CircleDashed, label: 'Rehydrating' });
	});
});

describe('attempt and question state labels', () => {
	test('attempt states read in display case', () => {
		expect(attemptStateLabel('planned')).toBe('Planned');
		expect(attemptStateLabel('suspended')).toBe('Suspended');
	});

	test('question states read in display case, unknown states fall back', () => {
		expect(questionStateLabel('open')).toBe('Open');
		expect(questionStateLabel('dismissed')).toBe('Dismissed');
		expect(questionStateLabel('needs_review')).toBe('Needs review');
	});
});
