<script lang="ts">
	import ProjectConnectionCheckDialog from './ProjectConnectionCheckDialog.svelte';
	import ProjectScheduleDialog from './ProjectScheduleDialog.svelte';
	import ProjectSettingsDialog from './ProjectSettingsDialog.svelte';
	import { PaginatedState } from '$lib/state/paginated.svelte';
	import { allPages, responseData } from '$lib/api/pagination';
	import ListPagination from '$lib/components/shared/ListPagination.svelte';
	import LoadError from '$lib/components/shared/LoadError.svelte';

	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import AgentSchedulesDialog from '$lib/features/project-management/agent-schedules/AgentSchedulesDialog.svelte';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Badge } from '$lib/components/ui/badge';
	import {
		Table,
		TableHeader,
		TableBody,
		TableRow,
		TableHead,
		TableCell
	} from '$lib/components/ui/table';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogFooter,
		DialogDescription
	} from '$lib/components/ui/dialog';
	import {
		FolderKanban,
		Plus,
		RefreshCw,
		Search,
		Trash2,
		CheckCircle2,
		XCircle,
		Settings2,
		Activity,
		AlertCircle,
		GitBranch,
		CalendarClock
	} from '@lucide/svelte';

	type Project = components['schemas']['ProjectRead'];
	type Connector = components['schemas']['ConnectorRead'];
	type AICatalog = components['schemas']['AICatalogRead'];

	const list = new PaginatedState<Project>();
	let projects = $derived(list.items);
	let connectors = $state<Connector[]>([]);
	let catalogs = $state<AICatalog[]>([]);
	let schedulesProject = $state<Project | null>(null);
	let loading = $derived(list.loading);
	let searchQuery = $state('');

	// Create dialog
	let isCreateOpen = $state(false);
	let isCreating = $state(false);
	let newName = $state('');

	let editingProject = $state<Project | null>(null);

	let checkingProject = $state<Project | null>(null);
	let schedulingProject = $state<Project | null>(null);

	async function loadConnectors() {
		try {
			const [options, result] = await Promise.all([
				allPages(async (offset, limit) =>
					responseData(
						await api.GET('/api/v1/connectors', { params: { query: { offset, limit } } }),
						'Failed to load connectors'
					)
				),
				api.GET('/api/v1/ai-catalogs')
			]);
			const catalogData = responseData(result, 'Failed to load AI catalogs');
			connectors = options;
			catalogs = catalogData.items;
		} catch {
			toast.error('Failed to load project options; refresh to retry');
		}
	}

	async function loadProjects(offset = list.offset) {
		const filters = { search: searchQuery.trim() };
		await list.load(
			async (offset, limit) =>
				responseData(
					await api.GET('/api/v1/projects', { params: { query: { ...filters, offset, limit } } }),
					'Failed to load projects'
				),
			offset
		);
	}

	async function handleCreateProject(e: SubmitEvent) {
		e.preventDefault();
		if (!newName.trim()) {
			toast.error('Project name is required');
			return;
		}

		isCreating = true;
		try {
			const res = await api.POST('/api/v1/projects', {
				body: {
					name: newName.trim(),
					enabled: true
				}
			});

			if (res.error) {
				toast.error('Failed to create project');
			} else {
				toast.success(`Project ${newName} created`);
				isCreateOpen = false;
				newName = '';
				loadProjects();
			}
		} catch {
			toast.error('An error occurred creating the project');
		} finally {
			isCreating = false;
		}
	}

	function openEdit(project: Project) {
		editingProject = project;
	}

	function openCheck(project: Project) {
		checkingProject = project;
	}
	function openSchedule(project: Project) {
		schedulingProject = project;
	}

	async function handleDelete(projectId: string) {
		if (!confirm('Are you sure you want to delete this project?')) return;
		try {
			const res = await api.DELETE('/api/v1/projects/{project_id}', {
				params: { path: { project_id: projectId } }
			});
			if (res.error) {
				const detail = apiErrorMessage(res.error, 'Failed to delete project');
				toast.error(detail);
			} else {
				toast.success('Project deleted');
				loadProjects();
			}
		} catch {
			toast.error('Failed to delete project');
		}
	}

	onMount(() => {
		loadProjects();
		loadConnectors();
	});
</script>

<div class="space-y-6">
	<!-- Page Header -->
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-3xl font-bold tracking-tight">Projects</h1>
			<p class="text-sm text-muted-foreground">
				Manage repository connections and verify CI pipelines
			</p>
		</div>
		<div class="flex items-center gap-3">
			<Button
				variant="outline"
				size="sm"
				onclick={() => {
					loadProjects();
					loadConnectors();
				}}
				disabled={loading}
				class="gap-2"
			>
				<RefreshCw class="size-4 {loading ? 'animate-spin' : ''}" />
				Refresh
			</Button>
			<Button size="sm" onclick={() => (isCreateOpen = true)} class="gap-2">
				<Plus class="size-4" />
				New Project
			</Button>
		</div>
	</div>

	<!-- Controls & Search -->
	<div class="flex items-center gap-3">
		<div class="relative max-w-sm flex-1">
			<Search class="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
			<Input
				placeholder="Search projects or repositories..."
				bind:value={searchQuery}
				oninput={() => loadProjects(0)}
				class="h-10 pl-9"
			/>
		</div>
	</div>

	{#if list.error}
		<LoadError message={list.error} retry={() => loadProjects()} />
	{/if}

	<div
		class="overflow-hidden rounded-xl border border-border/80 bg-card/60 shadow-xs backdrop-blur-xs"
	>
		<Table>
			<TableHeader>
				<TableRow>
					<TableHead class="w-[200px]">Project Name</TableHead>
					<TableHead>Providers & Verification</TableHead>
					<TableHead class="w-[140px]">Last CI Check</TableHead>
					<TableHead class="w-[100px]">Status</TableHead>
					<TableHead class="w-[180px] text-right">Actions</TableHead>
				</TableRow>
			</TableHeader>
			<TableBody>
				{#if loading}
					<TableRow>
						<TableCell colspan={5} class="h-32 text-center text-muted-foreground">
							Loading projects...
						</TableCell>
					</TableRow>
				{:else if list.error}
					<TableRow><TableCell colspan={5}>List unavailable</TableCell></TableRow>
				{:else if projects.length === 0}
					<TableRow>
						<TableCell colspan={5} class="h-32 text-center text-muted-foreground">
							<div class="flex flex-col items-center justify-center gap-2">
								<FolderKanban class="size-8 text-muted-foreground/40" />
								<span>No projects found</span>
							</div>
						</TableCell>
					</TableRow>
				{:else}
					{#each projects as project (project.id)}
						<TableRow class="transition-colors hover:bg-muted/40">
							<TableCell class="font-semibold text-foreground">
								<div class="flex flex-col gap-0.5">
									<a class="hover:text-primary hover:underline" href={`/projects/${project.id}`}
										>{project.name}</a
									>
									<span class="font-mono text-[11px] text-muted-foreground"
										>rev {project.revision}</span
									>
								</div>
							</TableCell>
							<TableCell class="text-xs">
								<div class="flex flex-wrap items-center gap-1.5">
									{#if project.github}
										<Badge
											variant="outline"
											class="gap-1.5 border-primary/20 bg-primary/5 font-mono text-primary"
										>
											<GitBranch class="size-3" />
											{project.github.repository}
										</Badge>
										<Badge variant="secondary" class="font-mono text-[10px]">
											{project.github.verification.workflow}
										</Badge>
									{:else}
										<span class="text-muted-foreground">No GitHub</span>
									{/if}
								</div>
							</TableCell>
							<TableCell>
								{#if project.last_check}
									{#if project.last_check.ready}
										<Badge
											variant="default"
											class="cursor-pointer gap-1 bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/25 dark:text-emerald-400"
											onclick={() => openCheck(project)}
										>
											<CheckCircle2 class="size-3" />
											Access OK
										</Badge>
									{:else}
										<Badge
											variant="secondary"
											class="cursor-pointer gap-1 bg-amber-500/15 text-amber-600 hover:bg-amber-500/25 dark:text-amber-400"
											onclick={() => openCheck(project)}
										>
											<AlertCircle class="size-3" />
											Issue
										</Badge>
									{/if}
								{:else}
									<span class="text-xs text-muted-foreground">Unchecked</span>
								{/if}
							</TableCell>
							<TableCell>
								{#if project.enabled}
									<Badge
										variant="default"
										class="gap-1 bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/20 dark:text-emerald-400"
									>
										<CheckCircle2 class="size-3" />
										Active
									</Badge>
								{:else}
									<Badge variant="secondary" class="gap-1 text-muted-foreground">
										<XCircle class="size-3" />
										Disabled
									</Badge>
								{/if}
							</TableCell>
							<TableCell class="text-right">
								<div class="flex items-center justify-end gap-3">
									<a class="text-sm text-primary hover:underline" href={`/projects/${project.id}`}
										>Open</a
									>
									<details class="relative">
										<summary class="cursor-pointer text-xs text-muted-foreground"
											>Quick actions</summary
										>
										<div
											class="mt-2 flex flex-wrap justify-end gap-1 rounded-lg border bg-popover p-2 shadow-md"
										>
											<Button
												variant="ghost"
												size="icon"
												onclick={() => openCheck(project)}
												class="size-8 text-muted-foreground hover:text-primary"
												title="Connection Check"
												aria-label="Connection Check"
											>
												<Activity class="size-4" />
											</Button>
											<Button
												variant="ghost"
												size="icon"
												onclick={() => openSchedule(project)}
												class="size-8 text-muted-foreground hover:text-emerald-500"
												title="Create Scheduled Automation"
												aria-label="Create Schedule"
											>
												<CalendarClock class="size-4" />
											</Button>
											<Button
												variant="ghost"
												size="icon"
												onclick={() => (schedulesProject = project)}
												class="size-8 text-muted-foreground hover:text-foreground"
												title="Agent Schedules"
												aria-label="Agent Schedules"
											>
												<CalendarClock class="size-4" />
											</Button>
											<Button
												variant="ghost"
												size="icon"
												onclick={() => openEdit(project)}
												class="size-8 text-muted-foreground hover:text-foreground"
												title="Configure Project"
												aria-label="Configure Project"
											>
												<Settings2 class="size-4" />
											</Button>
											<Button
												variant="ghost"
												size="icon"
												onclick={() => handleDelete(project.id)}
												class="size-8 text-muted-foreground hover:text-destructive"
												title="Delete Project"
												aria-label="Delete Project"
											>
												<Trash2 class="size-4" />
											</Button>
										</div>
									</details>
								</div>
							</TableCell>
						</TableRow>
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
			onpage={loadProjects}
		/>
	{/if}

	{#if schedulesProject}
		<AgentSchedulesDialog
			project={schedulesProject}
			{catalogs}
			onclose={() => (schedulesProject = null)}
		/>
	{/if}

	<!-- Create Project Dialog -->
	<Dialog bind:open={isCreateOpen}>
		<DialogContent class="sm:max-w-[425px]">
			<DialogHeader>
				<DialogTitle>Register New Project</DialogTitle>
				<DialogDescription>
					Create a project workspace. You can configure its GitHub connection right after.
				</DialogDescription>
			</DialogHeader>
			<form onsubmit={handleCreateProject} class="space-y-4 py-2">
				<div class="space-y-2">
					<label for="pName" class="text-xs font-semibold text-muted-foreground uppercase"
						>Project Name</label
					>
					<Input id="pName" placeholder="e.g. backend-pipeline" bind:value={newName} required />
				</div>
				<DialogFooter class="pt-4">
					<Button type="button" variant="outline" onclick={() => (isCreateOpen = false)}>
						Cancel
					</Button>
					<Button type="submit" disabled={isCreating}>
						{isCreating ? 'Creating...' : 'Create Project'}
					</Button>
				</DialogFooter>
			</form>
		</DialogContent>
	</Dialog>

	{#if editingProject}
		<ProjectSettingsDialog
			project={editingProject}
			{connectors}
			{catalogs}
			onclose={() => (editingProject = null)}
			onsaved={() => loadProjects()}
		/>
	{/if}

	{#if checkingProject}
		{#key checkingProject.id}
			<ProjectConnectionCheckDialog
				project={checkingProject}
				onclose={() => (checkingProject = null)}
				onchecked={() => loadProjects()}
			/>
		{/key}
	{/if}
	{#if schedulingProject}
		{#key schedulingProject.id}
			<ProjectScheduleDialog
				project={schedulingProject}
				onclose={() => (schedulingProject = null)}
			/>
		{/key}
	{/if}
</div>
