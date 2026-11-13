<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { allPages, responseData } from '$lib/api/pagination';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import { ChevronLeft } from '@lucide/svelte';
	import { toast } from 'svelte-sonner';
	import WorkPlansPanel from '../work-plans/WorkPlansPanel.svelte';
	import ProjectOverview from './ProjectOverview.svelte';
	import ProjectConnections from './ProjectConnections.svelte';
	import ProjectSettingsForm from './ProjectSettingsForm.svelte';
	import ProjectAutomation from './ProjectAutomation.svelte';
	import ProjectHeader from './ProjectHeader.svelte';
	import ProjectExceptionStrip from './ProjectExceptionStrip.svelte';
	import ProjectSectionNav from './ProjectSectionNav.svelte';
	import PipelineRunsView from '../pipeline-runs/PipelineRunsView.svelte';
	import RepositoryView from '../repositories/RepositoryView.svelte';
	import type { ProjectTab } from './project-tabs';
	let { projectId, tab = 'overview' }: { projectId: string; tab?: ProjectTab } = $props();
	let project = $state<components['schemas']['ProjectRead'] | null>(null);
	let connectors = $state<components['schemas']['ConnectorRead'][]>([]);
	let catalogs = $state<components['schemas']['AICatalogRead'][]>([]);
	let error = $state('');
	let loading = $state(true);
	let deleting = $state(false);
	// Each completed project load (including after a save) refreshes the exception strip once.
	let loads = $state(0);
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
			loads += 1;
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
	{#if !project}
		<a
			href="/projects"
			class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
			><ChevronLeft aria-hidden="true" class="size-4" />Projects</a
		>
	{/if}
	{#if error}<div role="alert" class="rounded-lg border border-destructive/30 p-4">
			{error} <button type="button" onclick={load} class="underline">Retry</button>
		</div>{/if}
	{#if loading}<p role="status" class="text-sm text-muted-foreground">Loading project…</p>
	{:else if project}
		<ProjectHeader {project}>
			{#snippet signals()}
				<!-- Changing section or reloading the project re-reads the counts; there is no polling. -->
				<ProjectExceptionStrip {projectId} refreshKey={`${tab}:${loads}`} />
			{/snippet}
		</ProjectHeader>
		<ProjectSectionNav {projectId} {tab} />
		{#key `${project.id}:${project.revision}:${tab}`}
			{#if tab === 'overview'}<ProjectOverview {project} />
			{:else if tab === 'repository'}<RepositoryView {project} />
			{:else if tab === 'plans'}<WorkPlansPanel {project} />
			{:else if tab === 'runs'}<PipelineRunsView scopedProject={project} />
			{:else if tab === 'connections'}<ProjectConnections
					{project}
					{connectors}
					{catalogs}
					onsaved={load}
				/>
			{:else if tab === 'automation'}<ProjectAutomation
					{project}
					{connectors}
					{catalogs}
					onsaved={load}
				/>
			{:else}
				<section class="rounded-xl border bg-card p-6">
					<h2 class="text-lg font-semibold">Project settings</h2>
					<ProjectSettingsForm {project} {connectors} {catalogs} section="general" onsaved={load} />
				</section>
				<section
					class="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-destructive/30 p-6"
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
