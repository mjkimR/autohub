import { Ban, Check, CircleDashed, Clock, Hammer, OctagonX, Pause, Slash } from '@lucide/svelte';
import type { components } from '$lib/api';
import type { BadgeVariant } from '$lib/components/ui/badge';

type RunState = components['schemas']['PipelineRunState'];

export type RunStatePresentation = {
	variant: BadgeVariant;
	/** A `@lucide/svelte` icon; every icon shares this component type. */
	icon: typeof Check;
	label: string;
};

/** Display labels; written out so acronyms such as CI keep their case. */
const RUN_STATE_LABELS: Record<RunState, string> = {
	queued: 'Queued',
	dispatching: 'Dispatching',
	implementing: 'Implementing',
	awaiting_ci: 'Awaiting CI',
	completed: 'Completed',
	canceled: 'Canceled',
	paused: 'Paused',
	blocked: 'Blocked',
	failed: 'Failed'
};

/** Sentence-case label for a state newer than this client, e.g. `foo_bar` → `Foo bar`. */
function fallbackLabel(state: string): string {
	const words = state.replaceAll('_', ' ');
	return words.charAt(0).toUpperCase() + words.slice(1);
}

/**
 * One state → badge variant, icon and label mapping for every PR run badge.
 * Chroma is operator debt: only runs waiting for the operator (paused, blocked) take `attention`,
 * failures take `destructive`, and routine progress stays quiet or neutral.
 */
export function getRunStatePresentation(state: RunState): RunStatePresentation {
	const label = RUN_STATE_LABELS[state] ?? fallbackLabel(state);
	switch (state) {
		case 'queued':
			return { variant: 'outline', icon: CircleDashed, label };
		case 'dispatching':
		case 'implementing':
			return { variant: 'info', icon: Hammer, label };
		case 'awaiting_ci':
			return { variant: 'outline', icon: Clock, label };
		case 'completed':
			return { variant: 'success', icon: Check, label };
		case 'canceled':
			return { variant: 'secondary', icon: Slash, label };
		case 'paused':
			return { variant: 'attention', icon: Pause, label };
		case 'blocked':
			return { variant: 'attention', icon: Ban, label };
		case 'failed':
			return { variant: 'destructive', icon: OctagonX, label };
		default:
			return { variant: 'secondary', icon: CircleDashed, label };
	}
}

export function getStateBadgeVariant(state: RunState): BadgeVariant {
	return getRunStatePresentation(state).variant;
}
