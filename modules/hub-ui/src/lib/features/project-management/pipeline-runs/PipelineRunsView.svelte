<script lang="ts">
	import PipelineRunRow from './PipelineRunRow.svelte';
	import AttemptHistoryDialog from './AttemptHistoryDialog.svelte';
	import EnrollPullRequestDialog from './EnrollPullRequestDialog.svelte';
	import AttachPullRequestDialog from './AttachPullRequestDialog.svelte';
	import { PaginatedState } from '$lib/state/paginated.svelte';
	import { allPages, responseData } from '$lib/api/pagination';
	import ListPagination from '$lib/components/shared/ListPagination.svelte';
	import LoadError from '$lib/components/shared/LoadError.svelte';

	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
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

	let selectedRun = $state<PipelineRun | null>(null);
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

	async function loadRuns(offset = list.offset) {
		const filters = {
			search: searchQuery.trim(),
			state: selectedState || undefined,
			project_id: scopedProject?.id ?? (selectedProjectId || undefined)
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

	function openAttempts(run: PipelineRun) {
		selectedRun = run;
	}

	async function handleAdvance(runId: string) {
		operatingRunId = runId;
		try {
			const res = await api.POST('/api/v1/pipeline-runs/{run_id}/advance', {
				params: { path: { run_id: runId } }
			});
			if (res.error) {
				const detail = apiErrorMessage(res.error, 'Failed to advance run');
				toast.error(detail);
			} else {
				toast.success(`Run advanced to ${res.data?.state ?? 'next state'}`);
				loadRuns();
			}
		} catch {
			toast.error('Error advancing run');
		} finally {
			operatingRunId = null;
		}
	}

	async function handlePause(runId: string) {
		operatingRunId = runId;
		try {
			const res = await api.POST('/api/v1/pipeline-runs/{run_id}/pause', {
				params: { path: { run_id: runId } },
				body: { reason: 'Paused via UI' }
			});
			if (res.error) {
				const detail = apiErrorMessage(res.error, 'Failed to pause run');
				toast.error(detail);
			} else {
				toast.success('Run paused');
				loadRuns();
			}
		} catch {
			toast.error('Error pausing run');
		} finally {
			operatingRunId = null;
		}
	}

	async function handleResume(run: PipelineRun) {
		// A blocked run's reason can warn that resuming would duplicate work still running at Codex.
		if (
			run.state === 'blocked' &&
			run.pause_reason &&
			!confirm(`${run.pause_reason}\n\nResume this run?`)
		)
			return;
		const runId = run.id;
		operatingRunId = runId;
		try {
			const res = await api.POST('/api/v1/pipeline-runs/{run_id}/resume', {
				params: { path: { run_id: runId } }
			});
			if (res.error) {
				const detail = apiErrorMessage(res.error, 'Failed to resume run');
				toast.error(detail);
			} else {
				toast.success(`Run resumed (${res.data?.state})`);
				loadRuns();
			}
		} catch {
			toast.error('Error resuming run');
		} finally {
			operatingRunId = null;
		}
	}

	async function handleCancel(runId: string) {
		if (!confirm('Are you sure you want to cancel this pipeline run?')) return;
		operatingRunId = runId;
		try {
			const res = await api.POST('/api/v1/pipeline-runs/{run_id}/cancel', {
				params: { path: { run_id: runId } }
			});
			if (res.error) {
				const detail = apiErrorMessage(res.error, 'Failed to cancel run');
				toast.error(detail);
			} else {
				toast.success('Run canceled');
				loadRuns();
			}
		} catch {
			toast.error('Error canceling run');
		} finally {
			operatingRunId = null;
		}
	}

	function openAttachPr(run: PipelineRun) {
		attachTargetRun = run;
	}

	/** A link such as a catalog session's "Pipeline run" names a run to open: `/projects/runs?run=<id>`. */
	async function openLinkedRun() {
		let runId: string | null;
		try {
			runId = new URLSearchParams(window.location.search).get('run');
		} catch {
			return;
		}
		if (!runId) return;
		try {
			const res = await api.GET('/api/v1/pipeline-runs/{run_id}', {
				params: { path: { run_id: runId } }
			});
			if (!res.data) {
				toast.error('The linked pipeline run was not found');
				return;
			}
			selectedProjectId = res.data.project_id;
			if (scopedProject && res.data.project_id !== scopedProject.id) return;
			await loadRuns(0);
			openAttempts(res.data);
		} catch {
			toast.error('Failed to load the linked pipeline run. Please refresh to retry.');
		}
	}

	onMount(() => {
		selectedProjectId = scopedProject?.id ?? '';
		loadProjects();
		loadCatalogs();
		loadRuns().then(openLinkedRun);
	});
</script>

<div class="space-y-6">
	<!-- Page Header -->
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-3xl font-bold tracking-tight">Pipeline Runs</h1>
			<p class="text-sm text-muted-foreground">
				Durable issue implementation lifecycle, attempt execution history, and CI status
			</p>
		</div>
		<div class="flex items-center gap-3">
			<Button variant="default" size="sm" onclick={() => (isAcquireOpen = true)} class="gap-1.5">
				<Plus class="size-4" />
				Enroll PR
			</Button>
			<Button
				variant="outline"
				size="sm"
				onclick={() => {
					loadRuns();
					loadProjects();
					loadCatalogs();
				}}
				disabled={loading}
				class="min-h-11 gap-2 sm:min-h-0"
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
				class="h-11 pl-9 text-base sm:h-10 sm:text-sm"
			/>
		</div>

		<!-- Project selector -->
		<select
			aria-label="Project filter"
			disabled={!!scopedProject}
			bind:value={selectedProjectId}
			onchange={() => loadRuns(0)}
			class="h-11 max-w-full min-w-0 rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs focus:ring-1 focus:ring-ring"
		>
			{#if !scopedProject}<option value="">All Projects</option>{/if}
			{#each projects as project (project.id)}
				<option value={project.id}>{project.name}</option>
			{/each}
		</select>

		<!-- State selector -->
		<select
			aria-label="Run state"
			bind:value={selectedState}
			onchange={() => loadRuns(0)}
			class="h-11 max-w-full min-w-0 rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs focus:ring-1 focus:ring-ring"
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
		</select>
	</div>

	{#if list.error}
		<LoadError message={list.error} retry={() => loadRuns()} />
	{/if}

	<div
		class="overflow-hidden rounded-xl border border-border/80 bg-card/60 shadow-xs backdrop-blur-xs"
	>
		<Table class="block md:table">
			<TableHeader class="hidden md:table-header-group">
				<TableRow>
					<TableHead class="w-[180px]">Pull Request</TableHead>
					<TableHead class="w-[160px]">Project</TableHead>
					<TableHead class="w-[130px]">State</TableHead>
					<TableHead>Branch & Pull Request</TableHead>
					<TableHead class="w-[160px]">Lease Status</TableHead>
					<TableHead class="w-[140px]">Created</TableHead>
					<TableHead class="w-[90px] text-right">Attempts</TableHead>
				</TableRow>
			</TableHeader>
			<TableBody class="block md:table-row-group">
				{#if loading}
					<TableRow>
						<TableCell colspan={7} class="h-32 text-center text-muted-foreground">
							Loading pipeline runs...
						</TableCell>
					</TableRow>
				{:else if list.error}
					<TableRow><TableCell colspan={7}>List unavailable</TableCell></TableRow>
				{:else if runs.length === 0}
					<TableRow>
						<TableCell colspan={7} class="h-32 text-center text-muted-foreground">
							<div class="flex flex-col items-center justify-center gap-2">
								<Workflow class="size-8 text-muted-foreground/40" />
								<span>No pipeline runs found</span>
							</div>
						</TableCell>
					</TableRow>
				{:else}
					{#each runs as run (run.id)}
						<PipelineRunRow
							{run}
							projectName={getProjectName(run.project_id)}
							operating={operatingRunId === run.id}
							onadvance={handleAdvance}
							onpause={handlePause}
							onresume={handleResume}
							oncancel={handleCancel}
							onattach={openAttachPr}
							onhistory={openAttempts}
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

	{#if selectedRun}
		{#key selectedRun.id}
			<AttemptHistoryDialog run={selectedRun} onclose={() => (selectedRun = null)} />
		{/key}
	{/if}
	{#if isAcquireOpen}
		<EnrollPullRequestDialog
			initialProjectId={selectedProjectId || (projects[0]?.id ?? '')}
			{projects}
			{pipelineCatalogs}
			onclose={() => (isAcquireOpen = false)}
			onsaved={() => loadRuns()}
		/>
	{/if}
	{#if attachTargetRun}
		{#key attachTargetRun.id}
			<AttachPullRequestDialog
				run={attachTargetRun}
				onclose={() => (attachTargetRun = null)}
				onsaved={() => loadRuns()}
			/>
		{/key}
	{/if}
</div>
