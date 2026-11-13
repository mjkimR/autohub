import { api, type components } from '$lib/api';
import { allPages, responseData } from '$lib/api/pagination';

type ScheduleConfig = components['schemas']['ScheduleConfigRead'];

export const DISPATCH_TASK = 'pipeline.dispatch_project';
export const OBSERVATION_TASK = 'pipeline.observe_project';
export const CONNECTION_TEST_TASK = 'pipeline.connection_test';

/** Schedule configurations a project owns, by owner kind. Agent schedules load from their own API. */
export interface OwnedSchedules {
	dispatch: ScheduleConfig[];
	observation: ScheduleConfig[];
	connectionTest: ScheduleConfig[];
}

async function configsFor(taskFunc: string): Promise<ScheduleConfig[]> {
	// `task_func` is a substring filter on the server; the exact match is checked here.
	const items = await allPages(async (offset, limit) =>
		responseData(
			await api.GET('/api/v1/schedule_configs', {
				params: { query: { task_func: taskFunc, offset, limit } }
			}),
			'Could not load project schedules'
		)
	);
	return items.filter((config) => config.task_func === taskFunc);
}

function namesProject(config: ScheduleConfig, projectId: string): boolean {
	return config.payload.project_id === projectId;
}

/**
 * Dispatch and CI observation configurations name their project in `payload.project_id`.
 * Connection-test configurations carry only `payload.test_id`, so they are matched against the
 * project's own test IDs. Current connection tests advance through system maintenance; these rows
 * exist only for tests started before that.
 */
export async function loadOwnedSchedules(projectId: string): Promise<OwnedSchedules> {
	const [dispatch, observation, connectionTest, tests] = await Promise.all([
		configsFor(DISPATCH_TASK),
		configsFor(OBSERVATION_TASK),
		configsFor(CONNECTION_TEST_TASK),
		api.GET('/api/v1/projects/{project_id}/connection-tests', {
			params: { path: { project_id: projectId } }
		})
	]);
	const testIds = new Set((tests.data ?? []).map((test) => test.id));
	return {
		dispatch: dispatch.filter((config) => namesProject(config, projectId)),
		observation: observation.filter((config) => namesProject(config, projectId)),
		connectionTest: connectionTest.filter(
			(config) =>
				namesProject(config, projectId) ||
				(typeof config.payload.test_id === 'string' && testIds.has(config.payload.test_id))
		)
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
