<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { responseData } from '$lib/api/pagination';
	import { toast } from 'svelte-sonner';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import LoadError from '$lib/components/shared/LoadError.svelte';
	import { displayLabel } from '$lib/labels';
	import { CircleCheck, CirclePause, Plus } from '@lucide/svelte';
	import { runHref } from '../pipeline-runs/run-links';
	import AgentScheduleForm from './AgentScheduleForm.svelte';

	type Project = components['schemas']['ProjectRead'];
	type AICatalog = components['schemas']['AICatalogRead'];
	type AgentSchedule = components['schemas']['AgentScheduleRead'];

	let { project, catalogs }: { project: Project; catalogs: AICatalog[] } = $props();

	let loading = $state(true);
	let loadError = $state('');
	let schedules = $state<AgentSchedule[]>([]);
	/** `null` while the list shows; `{ schedule: null }` creates one. */
	let form = $state<{ schedule: AgentSchedule | null } | null>(null);

	/** Catalogs whose sessions the hub can schedule; a catalog lists the work types it supports. */
	const sessionCatalogs = $derived(catalogs.filter((c) => (c.session_work_types ?? []).length > 0));

	async function load() {
		loading = true;
		loadError = '';
		try {
			const res = await api.GET('/api/v1/projects/{project_id}/agent-schedules', {
				params: { path: { project_id: project.id } }
			});
			schedules = responseData(res, 'Failed to load agent schedules').items;
		} catch {
			loadError = 'Failed to load agent schedules';
		} finally {
			loading = false;
		}
	}

	async function remove(schedule: AgentSchedule) {
		try {
			if (!confirm(`Delete "${schedule.title}"? Its scheduler entry is removed with it.`)) return;
			const res = await api.DELETE('/api/v1/projects/{project_id}/agent-schedules/{schedule_id}', {
				params: { path: { project_id: project.id, schedule_id: schedule.id } }
			});
			if (res.error) {
				toast.error(apiErrorMessage(res.error, 'Failed to delete agent schedule'));
				return;
			}
			toast.success('Agent schedule deleted');
			await load();
		} catch {
			toast.error('Request failed. Check your connection and retry.');
		}
	}

	async function runNow(schedule: AgentSchedule) {
		try {
			const res = await api.POST(
				'/api/v1/projects/{project_id}/agent-schedules/{schedule_id}/run-now',
				{ params: { path: { project_id: project.id, schedule_id: schedule.id } } }
			);
			if (res.error) {
				toast.error(apiErrorMessage(res.error, 'Failed to queue the agent schedule'));
				return;
			}
			toast.success('Queued for the next dispatcher tick');
			await load();
		} catch {
			toast.error('Request failed. Check your connection and retry.');
		}
	}

	function trigger(schedule: AgentSchedule): string {
		if (schedule.cron_expression) return `Cron ${schedule.cron_expression}`;
		const minutes = (schedule.interval_seconds ?? 0) / 60;
		return `Every ${Number.isInteger(minutes) ? minutes : minutes.toFixed(1)} min`;
	}

	const when = (value: string) => new Date(value).toLocaleString();

	/** An entry without a due time runs on the next tick, unless the entry itself is paused. */
	function nextRun(schedule: AgentSchedule): string {
		if (schedule.next_run_at) return when(schedule.next_run_at);
		return schedule.enabled && project.enabled ? 'due now' : 'paused';
	}

	/** Trigger, next and last run joined with separators so no fact runs into the next. */
	function timing(schedule: AgentSchedule): string {
		const parts = [trigger(schedule)];
		if (schedule.enabled) parts.push(`next ${nextRun(schedule)}`);
		if (schedule.last_run_at) parts.push(`last ${when(schedule.last_run_at)}`);
		return parts.join(' · ');
	}

	async function saved() {
		form = null;
		await load();
	}

	onMount(load);
</script>

<section
	aria-labelledby="agent-schedules-heading"
	class="space-y-4 rounded-xl border bg-card p-4 sm:p-6"
>
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div class="space-y-1">
			<h2 id="agent-schedules-heading" class="text-lg font-semibold">Agent schedules</h2>
			<p class="max-w-prose text-sm text-muted-foreground">
				Recurring agent sessions this project owns. Task sessions open pull requests the pipeline
				adopts; report sessions store their final message.
			</p>
		</div>
		{#if !form}
			<Button
				size="sm"
				variant="outline"
				disabled={sessionCatalogs.length === 0 || !project.github}
				onclick={() => (form = { schedule: null })}><Plus aria-hidden="true" />New schedule</Button
			>
		{/if}
	</div>

	{#if form}
		{#key form.schedule?.id ?? 'new'}
			<AgentScheduleForm
				projectId={project.id}
				catalogs={sessionCatalogs}
				schedule={form.schedule}
				onsaved={saved}
				oncancel={() => (form = null)}
			/>
		{/key}
	{:else if loadError}
		<LoadError message={loadError} retry={load} />
	{:else if loading}
		<p role="status" class="text-sm text-muted-foreground">Loading agent schedules…</p>
	{:else if schedules.length === 0}
		<p class="text-sm text-muted-foreground">
			No agent schedules yet.
			{#if !project.github}
				Add a GitHub connection first.
			{:else if sessionCatalogs.length === 0}
				No catalog can run scheduled sessions; add a Jules catalog with a connector first.
			{/if}
		</p>
	{:else}
		<ul class="divide-y rounded-lg border">
			{#each schedules as item (item.id)}
				<li class="space-y-3 p-4">
					<div class="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
						<div class="min-w-0 space-y-1">
							<div class="flex flex-wrap items-center gap-2">
								<p class="text-sm font-medium">{item.title}</p>
								<Badge variant="outline">{displayLabel(item.work_type)}</Badge>
								{#if item.enabled}
									<Badge variant="secondary"><CircleCheck aria-hidden="true" />Enabled</Badge>
								{:else}
									<Badge variant="secondary"><CirclePause aria-hidden="true" />Disabled</Badge>
								{/if}
							</div>
							<p class="text-xs text-muted-foreground">
								{timing(item)}
							</p>
						</div>
						<div class="flex flex-wrap gap-2">
							<Button
								type="button"
								variant="outline"
								size="sm"
								disabled={!item.enabled}
								onclick={() => runNow(item)}
								>Run now<span class="sr-only">: {item.title}</span></Button
							>
							<Button
								type="button"
								variant="outline"
								size="sm"
								onclick={() => (form = { schedule: item })}
								>Edit<span class="sr-only">: {item.title}</span></Button
							>
							<Button
								type="button"
								variant="subtle-destructive"
								size="sm"
								onclick={() => remove(item)}
								>Delete<span class="sr-only">: {item.title}</span></Button
							>
						</div>
					</div>
					{#if (item.recent_sessions ?? []).length > 0}
						<div class="space-y-1">
							<p class="text-xs font-medium text-muted-foreground">Recent sessions</p>
							<ul class="space-y-1 text-xs">
								{#each item.recent_sessions ?? [] as session (session.id)}
									<li class="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
										<span class="text-muted-foreground tabular-nums"
											>{when(session.created_at)}</span
										>
										<span class="font-medium">{displayLabel(session.state)}</span>
										{#if session.pipeline_run_id && !session.pipeline_run_retired_at}
											<a
												class="font-medium underline underline-offset-4"
												href={runHref(session.pipeline_run_id, project.id)}>PR run</a
											>
										{:else if session.pipeline_run_retired_at}
											<span class="text-muted-foreground">PR run history expired</span>
										{/if}
										{#if session.pull_request_url}
											<a
												class="underline underline-offset-4"
												href={session.pull_request_url}
												target="_blank"
												rel="noreferrer">Pull request</a
											>
										{/if}
										{#if session.result_summary}
											<span class="min-w-0 truncate text-muted-foreground"
												>{session.result_summary.slice(0, 80)}</span
											>
										{/if}
									</li>
								{/each}
							</ul>
						</div>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
</section>
