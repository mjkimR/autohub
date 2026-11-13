<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { toast } from 'svelte-sonner';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import LoadError from '$lib/components/shared/LoadError.svelte';
	import { CircleCheck, CirclePause, Plus } from '@lucide/svelte';
	import ProjectScheduleDialog from './ProjectScheduleDialog.svelte';
	import { projectTabHref } from './project-tabs';
	import {
		loadOwnedSchedules,
		observedPulls,
		scheduleTiming,
		type OwnedSchedules
	} from './owned-schedules';

	type Project = components['schemas']['ProjectRead'];
	type ScheduleConfig = components['schemas']['ScheduleConfigRead'];
	let { project }: { project: Project } = $props();

	let owned = $state<OwnedSchedules | null>(null);
	let loadError = $state('');
	let editor = $state<{ schedule: ScheduleConfig | null } | null>(null);
	let busy = $state<string | null>(null);

	async function load() {
		loadError = '';
		try {
			owned = await loadOwnedSchedules(project.id);
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Could not load project schedules';
		}
	}

	async function toggle(config: ScheduleConfig) {
		busy = config.id;
		try {
			const res = await api.PATCH('/api/v1/schedule_configs/{schedule_config_id}', {
				params: { path: { schedule_config_id: config.id } },
				body: { enabled: !config.enabled }
			});
			if (res.error) {
				toast.error(apiErrorMessage(res.error, 'Could not change the schedule'));
				return;
			}
			toast.success(config.enabled ? 'Schedule paused' : 'Schedule resumed');
			await load();
		} catch {
			toast.error('Request failed. Check your connection and retry.');
		} finally {
			busy = null;
		}
	}

	async function remove(config: ScheduleConfig) {
		if (!confirm(`Delete "${config.name}"? Its past jobs stay in Schedule jobs.`)) return;
		busy = config.id;
		try {
			const res = await api.DELETE('/api/v1/schedule_configs/{schedule_config_id}', {
				params: { path: { schedule_config_id: config.id } }
			});
			if (res.error) {
				toast.error(apiErrorMessage(res.error, 'Could not delete the schedule'));
				return;
			}
			toast.success('Schedule deleted');
			await load();
		} catch {
			toast.error('Request failed. Check your connection and retry.');
		} finally {
			busy = null;
		}
	}

	onMount(load);
</script>

{#snippet status(config: ScheduleConfig)}
	{#if config.enabled}
		<Badge variant="secondary"><CircleCheck aria-hidden="true" />Active</Badge>
	{:else}
		<Badge variant="secondary"><CirclePause aria-hidden="true" />Paused</Badge>
	{/if}
{/snippet}

{#snippet facts(config: ScheduleConfig)}
	<p class="text-xs text-muted-foreground">
		{scheduleTiming(config)}
	</p>
{/snippet}

<div class="space-y-6">
	{#if loadError}
		<LoadError message={loadError} retry={load} />
	{:else if !owned}
		<p role="status" class="text-sm text-muted-foreground">Loading project schedules…</p>
	{:else}
		<section aria-labelledby="owned-dispatch" class="space-y-2">
			<h3 id="owned-dispatch" class="text-sm font-semibold">Dispatch</h3>
			{#if owned.dispatch.length > 0}
				<ul class="divide-y rounded-lg border">
					{#each owned.dispatch as config (config.id)}
						<li class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 p-3">
							<div class="min-w-0 space-y-0.5">
								<p class="text-sm font-medium">{config.name}</p>
								{@render facts(config)}
							</div>
							<div class="flex items-center gap-3">
								{@render status(config)}
								<span class="text-xs text-muted-foreground">Follows the dispatch interval</span>
							</div>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="text-sm text-muted-foreground">
					Created when the project has a GitHub connection; it follows the dispatch interval above.
				</p>
			{/if}
		</section>

		<section aria-labelledby="owned-observation" class="space-y-2">
			<div class="flex flex-wrap items-center justify-between gap-2">
				<h3 id="owned-observation" class="text-sm font-semibold">CI observation</h3>
				<Button
					variant="outline"
					size="sm"
					disabled={!project.github}
					onclick={() => (editor = { schedule: null })}
					><Plus aria-hidden="true" />New CI observation</Button
				>
			</div>
			{#if owned.observation.length > 0}
				<ul class="divide-y rounded-lg border">
					{#each owned.observation as config (config.id)}
						<li class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 p-3">
							<div class="min-w-0 space-y-0.5">
								<p class="text-sm font-medium">{config.name}</p>
								<p class="text-xs text-muted-foreground">
									{observedPulls(config)
										.map((n) => `PR #${n}`)
										.join(', ') || 'No pull requests'}
								</p>
								{@render facts(config)}
							</div>
							<div class="flex flex-wrap items-center gap-2">
								{@render status(config)}
								<Button
									variant="outline"
									size="sm"
									disabled={busy === config.id}
									onclick={() => toggle(config)}>{config.enabled ? 'Pause' : 'Resume'}</Button
								>
								<Button
									variant="outline"
									size="sm"
									disabled={busy === config.id}
									aria-label={`Edit ${config.name}`}
									onclick={() => (editor = { schedule: config })}>Edit</Button
								>
								<Button
									variant="subtle-destructive"
									size="sm"
									disabled={busy === config.id}
									aria-label={`Delete ${config.name}`}
									onclick={() => remove(config)}>Delete</Button
								>
							</div>
						</li>
					{/each}
				</ul>
			{:else}
				<p class="text-sm text-muted-foreground">
					{project.github
						? 'No CI observation schedules. Add one to poll CI for specific pull requests.'
						: 'Add a GitHub connection before observing CI.'}
				</p>
			{/if}
		</section>

		<section aria-labelledby="owned-connection-tests" class="space-y-2">
			<h3 id="owned-connection-tests" class="text-sm font-semibold">Connection tests</h3>
			{#if owned.connectionTest.length > 0}
				<ul class="divide-y rounded-lg border">
					{#each owned.connectionTest as config (config.id)}
						<li class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 p-3">
							<div class="min-w-0 space-y-0.5">
								<p class="text-sm font-medium">{config.name}</p>
								{@render facts(config)}
							</div>
							{@render status(config)}
						</li>
					{/each}
				</ul>
			{/if}
			<p class="text-sm text-muted-foreground">
				Connection tests advance through system maintenance. Start, follow and clean them up in
				<a
					class="font-medium text-foreground underline underline-offset-4"
					href={projectTabHref(project.id, 'connections')}>Connections</a
				>.
			</p>
		</section>
	{/if}
</div>

{#if editor}
	<ProjectScheduleDialog
		{project}
		schedule={editor.schedule}
		onclose={() => (editor = null)}
		onsaved={load}
	/>
{/if}
