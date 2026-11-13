import { api, type components } from '$lib/api';
import { allPages, responseData } from '$lib/api/pagination';

type ScheduleConfig = components['schemas']['ScheduleConfigRead'];

export const DISPATCH_TASK = 'pipeline.dispatch_project';
export const OBSERVATION_TASK = 'pipeline.observe_project';
export const CONNECTION_TEST_TASK = 'pipeline.connection_test';
/** Schedule configurations selected by the server's verified project owner. */
export interface OwnedSchedules {
	dispatch: ScheduleConfig[];
	observation: ScheduleConfig[];
	connectionTest: ScheduleConfig[];
}

export async function loadOwnedSchedules(projectId: string): Promise<OwnedSchedules> {
	const configs = await allPages<ScheduleConfig>(async (offset, limit) =>
		responseData(
			await api.GET('/api/v1/schedule_configs', {
				params: { query: { project_id: projectId, offset, limit, skip_count: false } }
			}),
			'Failed to load project schedules'
		)
	);
	return {
		dispatch: configs.filter((config) => config.owner?.kind === 'project_dispatch'),
		observation: configs.filter((config) => config.owner?.kind === 'project_observation'),
		connectionTest: configs.filter((config) => config.owner?.kind === 'connection_test')
	};
}

export function cadence(config: Pick<ScheduleConfig, 'cron_expression' | 'interval_seconds'>) {
	if (config.cron_expression) return `Cron ${config.cron_expression}`;
	const seconds = config.interval_seconds;
	if (!seconds) return 'Manual only';
	if (seconds % 3600 === 0) return `Every ${seconds / 3600} h`;
	if (seconds % 60 === 0) return `Every ${seconds / 60} min`;
	return `Every ${seconds} s`;
}

export function observedPulls(config: ScheduleConfig): number[] {
	const pulls = config.payload.pull_numbers;
	return Array.isArray(pulls) ? pulls.filter((n): n is number => typeof n === 'number') : [];
}

/** When an enabled schedule runs next; one without a due time runs on the next tick. */
export function nextRunLabel(config: ScheduleConfig): string {
	return config.next_run_at ? new Date(config.next_run_at).toLocaleString() : 'due now';
}

/** Cadence and, for an enabled schedule, its next run, separated so they never run together. */
export function scheduleTiming(config: ScheduleConfig): string {
	return config.enabled ? `${cadence(config)} · next ${nextRunLabel(config)}` : cadence(config);
}
