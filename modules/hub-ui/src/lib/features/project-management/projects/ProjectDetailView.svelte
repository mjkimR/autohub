<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { allPages, responseData } from '$lib/api/pagination';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import { toast } from 'svelte-sonner';
	import ProjectOverview from './ProjectOverview.svelte';
	import ProjectConnections from './ProjectConnections.svelte';
	import ProjectSettingsForm from './ProjectSettingsForm.svelte';
	import ProjectScheduleDialog from './ProjectScheduleDialog.svelte';
	import AgentSchedulesDialog from '../agent-schedules/AgentSchedulesDialog.svelte';
	import PipelineRunsView from '../pipeline-runs/PipelineRunsView.svelte';
	import { projectTabs, type ProjectTab } from './project-tabs';
	let { projectId, tab = 'overview' }: { projectId: string; tab?: ProjectTab } = $props();
	let project = $state<components['schemas']['ProjectRead'] | null>(null);
	let connectors = $state<components['schemas']['ConnectorRead'][]>([]);
	let catalogs = $state<components['schemas']['AICatalogRead'][]>([]);
	let error = $state('');
	let loading = $state(true);
	let schedulesOpen = $state(false);
	let observationOpen = $state(false);
	let deleting = $state(false);
	async function load() {
		try {
			const results = await Promise.all([
				api.GET('/api/v1/projects/{project_id}', { params: { path: { project_id: projectId } } }),
				allPages(async (offset, limit) =>
					responseData(
						await api.GET('/api/v1/connectors', { params: { query: { offset, limit } } }),
						'Could not load connectors'
					)
				),
				api.GET('/api/v1/ai-catalogs')
			]);
			if (!results[0].data) throw new Error(apiErrorMessage(results[0].error, 'Project not found'));
			project = results[0].data;
			connectors = results[1];
			catalogs = responseData(results[2], 'Could not load AI catalogs').items;
			error = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load project';
		} finally {
			loading = false;
		}
	}
	async function remove() {
		if (!project || !confirm(`Delete project "${project.name}"?`)) return;
		deleting = true;
		try {
			const res = await api.DELETE('/api/v1/projects/{project_id}', {
				params: { path: { project_id: project.id } }
			});
			if (res.error) throw new Error(apiErrorMessage(res.error, 'Could not delete project'));
			window.location.assign('/projects');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Could not delete project');
		} finally {
			deleting = false;
		}
	}
	onMount(() => {
		void load();
	});
</script>

<svelte:head><title>{project?.name ?? 'Project'} · AutoHub</title></svelte:head>
<div class="mx-auto w-full max-w-7xl space-y-6">
	<a href="/projects" class="text-sm text-muted-foreground hover:text-foreground">← Projects</a>
	{#if error}<div role="alert" class="rounded-lg border border-destructive/30 p-4">
			{error} <button type="button" onclick={load} class="underline">Retry</button>
		</div>{/if}
	{#if loading}<p>Loading project…</p>{:else if project}
		<header class="flex flex-wrap items-center justify-between gap-4">
			<div>
				<h1 class="text-3xl font-semibold tracking-tight">{project.name}</h1>
				<p class="mt-2 text-sm text-muted-foreground">
					{project.github?.repository ?? 'No repository connected'}
				</p>
			</div>
			<div class="flex items-center gap-3 text-sm">
				<span class="rounded-full bg-muted px-3 py-1"
					>{project.enabled ? 'Active' : 'Disabled'}</span
				>{#if project.github}<a
						class="text-primary underline"
						href={`https://github.com/${project.github.repository}`}
						target="_blank"
						rel="noreferrer">Repository ↗</a
					>{/if}
			</div>
		</header>
		<nav aria-label="Project sections" class="flex gap-1 overflow-x-auto border-b">
			{#each projectTabs as item (item.id)}
				<a
					href={`/projects/${projectId}?tab=${item.id}`}
					aria-current={tab === item.id ? 'page' : undefined}
					class={`shrink-0 border-b-2 px-4 py-3 text-sm font-medium transition-colors ${tab === item.id ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
					>{item.label}</a
				>
			{/each}
		</nav>
		{#key `${project.id}:${project.revision}:${tab}`}
			{#if tab === 'overview'}<ProjectOverview {project} />
			{:else if tab === 'runs'}<PipelineRunsView scopedProject={project} />
			{:else if tab === 'connections'}<ProjectConnections
					{project}
					{connectors}
					{catalogs}
					onsaved={load}
				/>
			{:else if tab === 'automation'}
				<div class="space-y-6">
					<section class="rounded-xl border bg-card p-6">
						<h2 class="text-lg font-semibold">Development automation</h2>
						{#if project.github}<ProjectSettingsForm
								{project}
								{connectors}
								{catalogs}
								section="automation"
								onsaved={load}
							/>{:else}<p class="mt-3 text-sm text-muted-foreground">
								Add a GitHub connection first.
							</p>{/if}
					</section>
					<section class="space-y-4 rounded-xl border bg-card p-6">
						<h2 class="text-lg font-semibold">Schedules</h2>
						<p class="text-sm text-muted-foreground">
							Manage agent work and recurring CI observations for this project.
						</p>
						<div class="flex flex-wrap gap-3">
							<Button variant="outline" onclick={() => (schedulesOpen = true)}
								>Agent schedules</Button
							><Button
								variant="outline"
								disabled={!project.github}
								onclick={() => (observationOpen = true)}>Create CI observation schedule</Button
							>
						</div>
					</section>
				</div>
			{:else}
				<section class="rounded-xl border bg-card p-6">
					<h2 class="text-lg font-semibold">Project settings</h2>
					<ProjectSettingsForm {project} {connectors} {catalogs} section="general" onsaved={load} />
				</section>
				<section
					class="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-destructive/30 p-6"
				>
					<div>
						<h2 class="font-semibold">Delete project</h2>
						<p class="text-sm text-muted-foreground">
							Projects with execution or connection test history cannot be deleted.
						</p>
					</div>
					<Button variant="destructive" disabled={deleting} onclick={remove}>Delete project</Button>
				</section>
			{/if}
		{/key}
	{/if}
</div>
{#if project && schedulesOpen}<AgentSchedulesDialog
		{project}
		{catalogs}
		onclose={() => (schedulesOpen = false)}
	/>{/if}
{#if project && observationOpen}<ProjectScheduleDialog
		{project}
		onclose={() => (observationOpen = false)}
	/>{/if}
