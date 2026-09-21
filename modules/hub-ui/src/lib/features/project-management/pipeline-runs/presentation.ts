import type { components } from '$lib/api';

type RunState = components['schemas']['PipelineRunState'];

export function getStateBadgeClass(state: RunState): string {
	switch (state) {
		case 'queued':
			return 'bg-sky-500/15 text-sky-600 dark:text-sky-400 border-sky-500/30';
		case 'dispatching':
			return 'bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border-indigo-500/30';
		case 'implementing':
			return 'bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-500/30';
		case 'awaiting_ci':
			return 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30';
		case 'completed':
			return 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30';
		case 'failed':
			return 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30';
		case 'paused':
			return 'bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-500/30';
		case 'blocked':
			return 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30';
		case 'canceled':
		default:
			return 'bg-muted text-muted-foreground border-border';
	}
}
