import { api, type components } from '$lib/api';
import { allPages, responseData } from '$lib/api/pagination';

type ScheduleConfig = components['schemas']['ScheduleConfigRead'];

export const DISPATCH_TASK = 'pipeline.dispatch_project';
export const OBSERVATION_TASK = 'pipeline.observe_project';
export const CONNECTION_TEST_TASK = 'pipeline.connection_test';
const PIPELINE_TASK_PREFIX = 'pipeline.';

/** Schedule configurations a project owns, by owner kind. Agent schedules load from their own API. */
export interface OwnedSchedules {
	dispatch: ScheduleConfig[];
	observation: ScheduleConfig[];
	connectionTest: ScheduleConfig[];
}

/** Every pipeline-owned configuration in one paginated read; `task_func` is a server substring filter. */
async function pipelineConfigs(): Promise<ScheduleConfig[]> {
	return allPages(async (offset, limit) =>
		responseData(
			await api.GET('/api/v1/schedule_configs', {
				params: { query: { task_func: PIPELINE_TASK_PREFIX, offset, limit } }
			}),
			'Could not load project schedules'
		)
	);
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
	const configs = await pipelineConfigs();
	const byTask = (taskFunc: string) => configs.filter((config) => config.task_func === taskFunc);
	const legacyTests = byTask(CONNECTION_TEST_TASK);
	// Most projects have no legacy connection-test rows, so their tests are read only when needed.
	let testIds = new Set<string>();
	if (legacyTests.length > 0) {
		const tests = await api.GET('/api/v1/projects/{project_id}/connection-tests', {
			params: { path: { project_id: projectId } }
		});
		testIds = new Set((tests.data ?? []).map((test) => test.id));
	}
	return {
		dispatch: byTask(DISPATCH_TASK).filter((config) => namesProject(config, projectId)),
		observation: byTask(OBSERVATION_TASK).filter((config) => namesProject(config, projectId)),
		connectionTest: legacyTests.filter(
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

/** Cadence and, for an enabled schedule, its next run, separated so they never run together. */
export function scheduleTiming(config: ScheduleConfig): string {
	return config.enabled ? `${cadence(config)} · next ${nextRunLabel(config)}` : cadence(config);
}
