import type { components } from '$lib/api';

type ScheduleConfig = components['schemas']['ScheduleConfigRead'];
export type ScheduleEditor = { mode: 'create' } | { mode: 'edit'; config: ScheduleConfig };

export interface ScheduleDraft {
	name: string;
	description: string;
	taskFunc: string;
	scheduleType: 'cron' | 'interval';
	cronExpression: string;
	intervalSeconds: number;
	payload: Record<string, unknown>;
	enabled: boolean;
}

export function createScheduleDraft(config?: ScheduleConfig): ScheduleDraft {
	return {
		name: config?.name ?? '',
		description: config?.description ?? '',
		taskFunc: config?.task_func ?? '',
		scheduleType: config ? (config.cron_expression ? 'cron' : 'interval') : 'cron',
		cronExpression: config?.cron_expression ?? '0 9 * * 1-5',
		intervalSeconds: config ? (config.interval_seconds ?? 60) : 300,
		payload: config?.payload ? JSON.parse(JSON.stringify(config.payload)) : {},
		enabled: config?.enabled ?? true
	};
}

export function scheduleBody(draft: ScheduleDraft): components['schemas']['ScheduleConfigCreate'] {
	return {
		name: draft.name.trim(),
		description: draft.description.trim() || null,
		task_func: draft.taskFunc,
		// Explicit null clears the previous trigger when editing the cadence.
		cron_expression: draft.scheduleType === 'cron' ? draft.cronExpression : null,
		interval_seconds: draft.scheduleType === 'interval' ? Number(draft.intervalSeconds) : null,
		payload: draft.payload,
		enabled: draft.enabled
	};
}
