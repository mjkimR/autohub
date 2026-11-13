import { AlertTriangle, CheckCircle2, Clock, XCircle } from '@lucide/svelte';
import type { components } from '$lib/api';
import type { BadgeVariant } from '$lib/components/ui/badge';
import { displayLabel } from '$lib/labels';

type ScheduleJobStatus = components['schemas']['ScheduleJobStatus'];

export type ScheduleJobStatusPresentation = {
	variant: BadgeVariant;
	/** A `@lucide/svelte` icon; every icon shares this component type. */
	icon: typeof Clock;
	label: string;
};

const SCHEDULE_JOB_STATUS_LABELS: Record<ScheduleJobStatus, string> = {
	pending: 'Pending',
	success: 'Success',
	failure: 'Failure'
};

/**
 * One status → badge variant, icon and label mapping for every schedule job badge.
 * A pending job is routine scheduler work, not operator debt, so it stays neutral (outline).
 */
export function getScheduleJobStatusPresentation(status: string): ScheduleJobStatusPresentation {
	const label = displayLabel(status, SCHEDULE_JOB_STATUS_LABELS);
	switch (status) {
		case 'success':
			return { variant: 'success', icon: CheckCircle2, label };
		case 'failure':
			return { variant: 'destructive', icon: XCircle, label };
		case 'pending':
			return { variant: 'outline', icon: Clock, label };
		default:
			return { variant: 'secondary', icon: AlertTriangle, label };
	}
}
