import type { components } from '$lib/api';
import type { BadgeVariant } from '$lib/components/ui/badge';

type RunState = components['schemas']['PipelineRunState'];

export function getStateBadgeVariant(state: RunState): BadgeVariant {
	switch (state) {
		case 'queued':
			return 'outline';
		case 'dispatching':
		case 'implementing':
			return 'info';
		case 'awaiting_ci':
		case 'paused':
			return 'warning';
		case 'completed':
			return 'success';
		case 'failed':
		case 'blocked':
			return 'destructive';
		case 'canceled':
		default:
			return 'secondary';
	}
}
