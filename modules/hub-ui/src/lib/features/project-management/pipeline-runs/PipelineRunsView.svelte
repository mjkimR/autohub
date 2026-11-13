<script lang="ts">
	import { NativeSelect } from '$lib/components/ui/native-select';
	import RunGroupFilter from './RunGroupFilter.svelte';
	import PipelineRunRow from './PipelineRunRow.svelte';
	import EnrollPullRequestDialog from './EnrollPullRequestDialog.svelte';
	import AttachPullRequestDialog from './AttachPullRequestDialog.svelte';
	import { advanceRun, cancelRun, pauseRun, resumeRun } from './run-operations';
	import { decisionsFor, loadPendingDecisions, type DecisionEntry } from './run-actions';
	import { legacyRunRedirect } from './run-links';
	import { PaginatedState } from '$lib/state/paginated.svelte';
	import { allPages, responseData } from '$lib/api/pagination';
	import ListPagination from '$lib/components/shared/ListPagination.svelte';
	import LoadError from '$lib/components/shared/LoadError.svelte';

	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api, type components } from '$lib/api';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import {
		Table,
		TableHeader,
		TableBody,
		TableRow,
		TableHead,
		TableCell
	} from '$lib/components/ui/table';
	import { Workflow, RefreshCw, Search, Plus } from '@lucide/svelte';

	type PipelineRun = components['schemas']['PipelineRunRead'];
	type Project = components['schemas']['ProjectRead'];
	let { scopedProject }: { scopedProject?: Project } = $props();

	const list = new PaginatedState<PipelineRun>();
	let runs = $derived(list.items);
	let projects = $state<Project[]>([]);
	// Catalogs that can deliver pull request work, offered when enrolling by hand.
	let pipelineCatalogs = $state<components['schemas']['AICatalogRead'][]>([]);
	let loading = $derived(list.loading);
	let searchQuery = $state('');
	let selectedProjectId = $state<string>('');
	let selectedState = $state<components['schemas']['PipelineRunState'] | ''>('');
	let selectedGroupKey = $state<string | undefined>();
	// Observed pending decisions grouped by run: one bounded read, never one request per row.
	let pending = $state<{ byRun: Map<string, DecisionEntry[]>; complete: boolean } | null>(null);

	let isAcquireOpen = $state(false);
	let attachTargetRun = $state<PipelineRun | null>(null);

	// Action loading state
	let operatingRunId = $state<string | null>(null);

	function getProjectName(projectId: string): string {
		const found = projects.find((p) => p.id === projectId);
		return found ? found.name : projectId.slice(0, 8);
	}

	async function loadProjects() {
		if (scopedProject) {
			projects = [scopedProject];
			return;
		}
		try {
			projects = await allPages(async (offset, limit) =>
				responseData(
					await api.GET('/api/v1/projects', { params: { query: { offset, limit } } }),
					'Failed to load projects'
				)
			);
		} catch {
			toast.error('Failed to load project options; refresh to retry');
		}
	}

	async function loadCatalogs() {
		try {
			const res = await api.GET('/api/v1/ai-catalogs');
			pipelineCatalogs = responseData(res, 'Failed to load AI catalogs').items.filter(
				(item) => item.pipeline_delivery && item.enabled
			);
		} catch {
			toast.error('Failed to load AI catalog options; refresh to retry');
		}
	}

	function filterProjectId(): string | undefined {
		return scopedProject?.id ?? (selectedProjectId || undefined);
	}

	// Pending decisions follow the project filter only; search and state filters reuse them.
	let pendingSeq = 0;
	async function loadPending() {
		const projectId = filterProjectId();
		const seq = ++pendingSeq;
		let next: typeof pending = null;
		try {
			next = await loadPendingDecisions(projectId);
		} catch {
			// Unknown decisions keep conservative row actions; the list itself stays usable.
		}
		// Drop responses overtaken by a newer read or a project filter change.
		if (seq === pendingSeq && projectId === filterProjectId()) pending = next;
	}

	async function loadRuns(offset = list.offset) {
		const filters = {
			search: searchQuery.trim(),
			state: selectedState || undefined,
			group_key: selectedGroupKey,
			project_id: filterProjectId()
		};
		await list.load(
			async (offset, limit) =>
				responseData(
					await api.GET('/api/v1/pipeline-runs', {
						params: { query: { ...filters, offset, limit } }
					}),
					'Failed to load runs'
				),
			offset
		);
	}

	function reload(offset?: number) {
		return Promise.all([loadRuns(offset), loadPending()]);
	}

	async function operate(runId: string, action: () => Promise<boolean>) {
		operatingRunId = runId;
		try {
			if (await action()) void reload();
		} finally {
			operatingRunId = null;
		}
	}

	onMount(() => {
		// Old run deep links (`?run=<id>[&view=decisions]`) now open the PR run page.
		const legacy = legacyRunRedirect(window.location.search);
		if (legacy) {
			void goto(legacy, { replaceState: true });
			return;
		}
		selectedProjectId = scopedProject?.id ?? '';
		loadProjects();
		loadCatalogs();
		reload();
	});
</script>

<div class="space-y-6">
	<!-- Page Header -->
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-3xl font-bold tracking-tight">PR runs</h1>
			<p class="text-sm text-muted-foreground">
				Each enrolled pull request's delivery state, decisions waiting on you and attempt history
			</p>
		</div>
		<div class="flex items-center gap-3">
			<Button variant="default" size="sm" onclick={() => (isAcquireOpen = true)}>
				<Plus class="size-4" />
				Enroll PR
			</Button>
			<Button
				variant="outline"
				size="sm"
				onclick={() => {
					reload();
					loadProjects();
					loadCatalogs();
				}}
				disabled={loading}
			>
				<RefreshCw class="size-4 {loading ? 'animate-spin' : ''}" />
				Refresh
			</Button>
		</div>
	</div>

	<!-- Controls & Filters -->
	<div class="flex flex-wrap items-center gap-3">
		<div class="relative min-w-0 basis-full sm:flex-1 sm:basis-auto">
			<Search class="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
			<Input
				placeholder="Search PR number, title, branch..."
				bind:value={searchQuery}
				oninput={() => loadRuns(0)}
				class="pl-9"
			/>
		</div>

		<!-- Project selector -->
		<NativeSelect
			aria-label="Project filter"
			disabled={!!scopedProject}
			bind:value={selectedProjectId}
			onchange={() => {
				// Decisions read for the previous filter may not cover the new one.
				pending = null;
				void reload(0);
			}}
			class="max-w-full min-w-0"
		>
			{#if !scopedProject}<option value="">All Projects</option>{/if}
			{#each projects as project (project.id)}
				<option value={project.id}>{project.name}</option>
			{/each}
		</NativeSelect>

		<!-- State selector -->
		<RunGroupFilter
			onchange={(value) => {
				selectedGroupKey = value;
				void loadRuns(0);
			}}
		/>
		<NativeSelect
			aria-label="Run state"
			bind:value={selectedState}
			onchange={() => loadRuns(0)}
			class="max-w-full min-w-0"
		>
			<option value="">All States</option>
			<option value="queued">Queued</option>
			<option value="dispatching">Dispatching</option>
			<option value="implementing">Implementing</option>
			<option value="awaiting_ci">Awaiting CI</option>
			<option value="completed">Completed</option>
			<option value="failed">Failed</option>
			<option value="paused">Paused</option>
			<option value="blocked">Blocked</option>
			<option value="canceled">Canceled</option>
		</NativeSelect>
	</div>

	{#if list.error}
		<LoadError message={list.error} retry={() => reload()} />
	{/if}

	<div
		class="overflow-x-auto rounded-xl border border-border/80 bg-card/60 shadow-xs backdrop-blur-xs"
	>
		<Table class="block md:table">
			<TableHeader class="hidden md:table-header-group">
				<TableRow>
					<TableHead class="w-45">Pull Request</TableHead>
					<TableHead class="w-40">Project</TableHead>
					<TableHead class="w-32.5">State</TableHead>
					<TableHead>Branch & Pull Request</TableHead>
					<TableHead class="w-40">Lease Status</TableHead>
					<TableHead class="w-35">Created</TableHead>
					<TableHead class="w-40 text-right">Actions</TableHead>
				</TableRow>
			</TableHeader>
			<TableBody class="block md:table-row-group">
				{#if loading}
					<TableRow>
						<TableCell colspan={7} class="h-32 text-center text-muted-foreground">
							Loading PR runs…
						</TableCell>
					</TableRow>
				{:else if list.error}
					<TableRow><TableCell colspan={7}>List unavailable</TableCell></TableRow>
				{:else if runs.length === 0}
					<TableRow>
						<TableCell colspan={7} class="h-32 text-center text-muted-foreground">
							<div class="flex flex-col items-center justify-center gap-2">
								<Workflow class="size-8 text-muted-foreground/40" />
								<span>No PR runs found</span>
							</div>
						</TableCell>
					</TableRow>
				{:else}
					{#each runs as run (run.id)}
						<PipelineRunRow
							{run}
							projectName={getProjectName(run.project_id)}
							operating={operatingRunId === run.id}
							decisions={decisionsFor(run.id, pending)}
							onadvance={(id) => operate(id, () => advanceRun(id))}
							onpause={(id) => operate(id, () => pauseRun(id))}
							onresume={(run) => operate(run.id, () => resumeRun(run))}
							oncancel={(id) => operate(id, () => cancelRun(id))}
							onattach={(run) => (attachTargetRun = run)}
						/>
					{/each}
				{/if}
			</TableBody>
		</Table>
	</div>
	{#if !list.error}
		<ListPagination
			offset={list.offset}
			limit={list.limit}
			total={list.total}
			{loading}
			onpage={loadRuns}
		/>
	{/if}

	{#if isAcquireOpen}
		<EnrollPullRequestDialog
			initialProjectId={selectedProjectId || (projects[0]?.id ?? '')}
			{projects}
			{pipelineCatalogs}
			onclose={() => (isAcquireOpen = false)}
			onsaved={() => reload()}
		/>
	{/if}
	{#if attachTargetRun}
		{#key attachTargetRun.id}
			<AttachPullRequestDialog
				run={attachTargetRun}
				onclose={() => (attachTargetRun = null)}
				onsaved={() => reload()}
			/>
		{/key}
	{/if}
</div>
