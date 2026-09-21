import { api, type components } from '$lib/api';
import { responseData } from '$lib/api/pagination';
import { SvelteDate } from 'svelte/reactivity';

type Stats = components['schemas']['DashboardStats'];
type TriggerStatus = 'ok' | 'stale' | 'never' | 'unknown';

export class DashboardState {
	loading = $state(true);
	healthStatus = $state<'online' | 'offline' | 'checking'>('checking');
	dbStatus = $state<'connected' | 'error' | 'unknown'>('unknown');
	triggerStatus = $state<TriggerStatus>('unknown');
	lastTickAt = $state<string | null>(null);
	stats = $state<Stats | null>(null);
	error = $state('');
	recentRuns = $state<components['schemas']['PipelineRunRead'][]>([]);
	recentJobs = $state<components['schemas']['ScheduleJobRead'][]>([]);
	lastRefreshedAt = $state<Date | null>(null);
	private generation = 0;

	get projectCount() {
		return this.stats?.project_count ?? '—';
	}
	get scheduleCount() {
		return this.stats?.schedule_count ?? '—';
	}
	get connectorCount() {
		return this.stats?.connector_count ?? '—';
	}
	get activeConnectors() {
		return this.stats?.active_connector_count ?? '—';
	}
	get totalRuns() {
		return this.stats?.total_runs ?? '—';
	}
	get activeRuns() {
		const counts = this.stats?.runs_by_state;
		return counts
			? (counts.queued ?? 0) + (counts.dispatching ?? 0) + (counts.implementing ?? 0)
			: '—';
	}
	get awaitingCiRuns() {
		return this.stats ? (this.stats.runs_by_state.awaiting_ci ?? 0) : '—';
	}
	get completedRuns() {
		return this.stats ? (this.stats.runs_by_state.completed ?? 0) : '—';
	}
	get failedRuns() {
		const counts = this.stats?.runs_by_state;
		return counts ? (counts.failed ?? 0) + (counts.paused ?? 0) + (counts.blocked ?? 0) : '—';
	}

	async load(silent = false) {
		const generation = ++this.generation;
		if (!silent) this.loading = true;
		const [health, deep, stats, runs, jobs] = await Promise.allSettled([
			api.GET('/api/health').then((result) => responseData(result, 'Health unavailable')),
			api.GET('/api/health/deep').then((result) => responseData(result, 'Database unavailable')),
			api
				.GET('/api/v1/dashboard/stats')
				.then((result) => responseData(result, 'Statistics unavailable')),
			api
				.GET('/api/v1/pipeline-runs', { params: { query: { limit: 5 } } })
				.then((result) => responseData(result, 'Runs unavailable')),
			api
				.GET('/api/v1/schedule_jobs', { params: { query: { limit: 5 } } })
				.then((result) => responseData(result, 'Jobs unavailable'))
		]);
		if (generation !== this.generation) return;
		this.healthStatus =
			health.status === 'fulfilled' && (health.value as { status?: string }).status === 'ok'
				? 'online'
				: 'offline';
		if (deep.status === 'fulfilled') {
			const value = deep.value as {
				status?: string;
				scheduler?: TriggerStatus;
				last_tick_at?: string | null;
			};
			this.dbStatus = value.status === 'ok' ? 'connected' : 'error';
			this.triggerStatus = value.scheduler ?? 'unknown';
			this.lastTickAt = value.last_tick_at ?? null;
		} else {
			this.dbStatus = 'error';
			this.triggerStatus = 'unknown';
			this.lastTickAt = null;
		}
		this.stats = stats.status === 'fulfilled' ? stats.value : null;
		if (runs.status === 'fulfilled') this.recentRuns = runs.value.items;
		if (jobs.status === 'fulfilled') this.recentJobs = jobs.value.items;
		this.error = [stats, runs, jobs].some((result) => result.status === 'rejected')
			? 'Some dashboard data could not be refreshed. Please retry.'
			: '';
		if (!this.error) this.lastRefreshedAt = new SvelteDate();
		this.loading = false;
	}
}
