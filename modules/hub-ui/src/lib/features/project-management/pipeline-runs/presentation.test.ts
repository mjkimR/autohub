import { Ban, Check, CircleDashed, Clock, Hammer, OctagonX, Pause, Slash } from '@lucide/svelte';
import { describe, expect, test } from 'vitest';
import type { components } from '$lib/api';
import { getRunStatePresentation, getStateBadgeVariant } from './presentation';

type RunState = components['schemas']['PipelineRunState'];

const expected: [RunState, string, unknown, string][] = [
	['queued', 'outline', CircleDashed, 'queued'],
	['dispatching', 'info', Hammer, 'dispatching'],
	['implementing', 'info', Hammer, 'implementing'],
	['awaiting_ci', 'outline', Clock, 'awaiting ci'],
	['completed', 'success', Check, 'completed'],
	['canceled', 'secondary', Slash, 'canceled'],
	['paused', 'attention', Pause, 'paused'],
	['blocked', 'attention', Ban, 'blocked'],
	['failed', 'destructive', OctagonX, 'failed']
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
		expect(view).toEqual({ variant: 'secondary', icon: CircleDashed, label: 'rehydrating' });
	});
});
