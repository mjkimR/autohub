import { toast } from 'svelte-sonner';
import { api, type components } from '$lib/api';
import { apiErrorMessage } from '$lib/api/errors';
import { getRunStatePresentation } from './presentation';

type Run = components['schemas']['PipelineRunRead'];
type Result = { data?: Run; error?: unknown };

async function settle(
	request: () => Promise<Result>,
	failure: string,
	success: (run?: Run) => string
): Promise<boolean> {
	try {
		const res = await request();
		if (res.error) {
			toast.error(apiErrorMessage(res.error, failure));
			return false;
		}
		toast.success(success(res.data));
		return true;
	} catch {
		toast.error(`${failure}. Check your connection and try again.`);
		return false;
	}
}

const stateLabel = (run?: Run) =>
	run ? getRunStatePresentation(run.state).label : 'the next state';

/** Ask Hub to re-evaluate the run now instead of waiting for its next scheduled check. */
export function advanceRun(runId: string) {
	return settle(
		() =>
			api.POST('/api/v1/pipeline-runs/{run_id}/advance', { params: { path: { run_id: runId } } }),
		'Failed to advance run',
		(run) => `Run advanced: ${stateLabel(run)}`
	);
}

export function pauseRun(runId: string) {
	return settle(
		() =>
			api.POST('/api/v1/pipeline-runs/{run_id}/pause', {
				params: { path: { run_id: runId } },
				body: { reason: 'Paused via UI' }
			}),
		'Failed to pause run',
		() => 'Run paused'
	);
}

/** Request identities survive retries of the same run revision. */
const resumeRequests = new Map<string, string>();

/** Resume a stopped run; a blocked run's reason can warn about duplicate work, so it is confirmed. */
export async function resumeRun(run: Run): Promise<boolean> {
	if (
		run.state === 'blocked' &&
		run.pause_reason &&
		!confirm(`${run.pause_reason}\n\nResume this run?`)
	)
		return false;
	const key = `${run.id}:${run.revision}`;
	if (!resumeRequests.has(key)) resumeRequests.set(key, crypto.randomUUID());
	return settle(
		() =>
			api.POST('/api/v1/pipeline-runs/{run_id}/resume', {
				params: { path: { run_id: run.id } },
				body: { request_id: resumeRequests.get(key)!, expected_revision: run.revision }
			}),
		'Failed to resume run',
		(next) => `Run resumed: ${stateLabel(next)}`
	);
}

export async function cancelRun(runId: string): Promise<boolean> {
	if (!confirm('Cancel this PR run? The original result is kept, but the run cannot be resumed.'))
		return false;
	return settle(
		() =>
			api.POST('/api/v1/pipeline-runs/{run_id}/cancel', { params: { path: { run_id: runId } } }),
		'Failed to cancel run',
		() => 'Run canceled'
	);
}
