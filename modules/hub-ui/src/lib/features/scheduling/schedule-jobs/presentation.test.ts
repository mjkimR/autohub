import { AlertTriangle, CheckCircle2, Clock, XCircle } from '@lucide/svelte';
import { describe, expect, test } from 'vitest';
import { getScheduleJobStatusPresentation } from './presentation';

describe('getScheduleJobStatusPresentation', () => {
	test.each([
		['pending', 'outline', Clock, 'Pending'],
		['success', 'success', CheckCircle2, 'Success'],
		['failure', 'destructive', XCircle, 'Failure'],
		['retrying_soon', 'secondary', AlertTriangle, 'Retrying soon']
	])('%s → %s', (status, variant, icon, label) => {
		expect(getScheduleJobStatusPresentation(status)).toEqual({ variant, icon, label });
	});
});
