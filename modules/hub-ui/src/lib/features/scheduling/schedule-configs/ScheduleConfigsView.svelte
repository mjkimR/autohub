<script lang="ts">
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { PaginatedState } from '$lib/state/paginated.svelte';
	import ListPagination from '$lib/components/shared/ListPagination.svelte';
	import ScheduleEditorDialog from './ScheduleEditorDialog.svelte';
	import ScheduleOwnerLabel from './ScheduleOwnerLabel.svelte';
	import type { ScheduleEditor } from './schedule-form';
	import LoadError from '$lib/components/shared/LoadError.svelte';
	import { allPages, countedPage, responseData } from '$lib/api/pagination';
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
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
		DialogFooter
	} from '$lib/components/ui/dialog';
	import {
		CalendarClock,
		RefreshCw,
		Search,
		CheckCircle2,
		PauseCircle,
		Play,
		Plus,
		Pencil,
		Trash2,
		AlertTriangle
	} from '@lucide/svelte';

	type ScheduleConfig = components['schemas']['ScheduleConfigRead'];
	type TaskSpec = components['schemas']['TaskSpecResponse'];

	const list = new PaginatedState<ScheduleConfig>();
	let configs = $derived(list.items);
	let taskSpecs = $state<TaskSpec[]>([]);
	let loading = $derived(list.loading);
	let loadError = $derived(list.error);
	let isTriggering = $state(false);
	let searchQuery = $state('');
	let enabledFilter = $state<'' | 'true' | 'false'>('');

	let editor = $state<ScheduleEditor | null>(null);

	// Delete dialog state
	let isDeleteDialogOpen = $state(false);
	let isDeleting = $state(false);
	let deletingConfig = $state<ScheduleConfig | null>(null);

	let projectId = $state('');
	let projects = $state<components['schemas']['ProjectRead'][]>([]);
	let projectError = $state('');
	let projectRequest = 0;
	const projectNames = $derived(new Map(projects.map((project) => [project.id, project.name])));

	function isProjectManaged(config: ScheduleConfig): boolean {
		return config.owner?.kind !== 'operator' && config.owner?.kind !== 'system_maintenance';
	}

	async function loadProjects() {
		const request = ++projectRequest;
		projectError = '';
		try {
			const next = await allPages(async (offset, limit) =>
				responseData(
					await api.GET('/api/v1/projects', {
						params: { query: { offset, limit, skip_count: false } }
					}),
					'Failed to load projects'
				)
			);
			if (request === projectRequest) projects = next;
		} catch {
			if (request === projectRequest)
				projectError = 'Failed to load project options. Retry to choose a project.';
		}
	}

	async function loadConfigs(offset = list.offset) {
		const filters = {
			search: searchQuery.trim(),
			...(projectId ? { project_id: projectId } : {}),
			enabled: enabledFilter === '' ? undefined : enabledFilter === 'true'
		};
		await list.load(
			async (offset, limit) =>
				countedPage(
					responseData(
						await api.GET('/api/v1/schedule_configs', {
							params: { query: { ...filters, offset, limit, skip_count: false } }
						}),
						'Failed to load schedule configs'
					)
				),
			offset
		);
	}

	let taskSpecsError = $state('');
	async function loadTaskSpecs() {
		taskSpecsError = '';
		try {
			taskSpecs = responseData(await api.GET('/api/v1/tasks/specs'), 'Failed to load task specs');
		} catch {
			taskSpecsError = 'Failed to load task specs. Retry to configure schedule payloads.';
		}
	}
	function refresh() {
		void loadConfigs();
		void loadTaskSpecs();
		void loadProjects();
	}

	async function toggleEnable(config: ScheduleConfig) {
		try {
			const res = await api.PATCH('/api/v1/schedule_configs/{schedule_config_id}', {
				params: { path: { schedule_config_id: config.id } },
				body: { enabled: !config.enabled }
			});
			if (res.error) {
				toast.error(apiErrorMessage(res.error, 'Failed to update schedule status'));
			} else {
				toast.success(`Schedule ${!config.enabled ? 'enabled' : 'disabled'}`);
				loadConfigs();
			}
		} catch {
			toast.error('Error updating schedule');
		}
	}

	async function triggerDispatcher() {
		isTriggering = true;
		try {
			const res = await api.POST('/api/v1/dispatchers/trigger', {});
			if (res.error) {
				toast.error('Dispatcher trigger failed');
			} else {
				toast.success(`Dispatcher tick completed! Dispatched: ${res.data?.dispatched ?? 0}`);
				loadConfigs();
			}
		} catch {
			toast.error('Error triggering dispatcher');
		} finally {
			isTriggering = false;
		}
	}

	function openEdit(config: ScheduleConfig) {
		editor = { mode: 'edit', config };
	}

	function openDelete(config: ScheduleConfig) {
		deletingConfig = config;
		isDeleteDialogOpen = true;
	}

	async function confirmDelete() {
		if (!deletingConfig) return;

		isDeleting = true;
		try {
			const res = await api.DELETE('/api/v1/schedule_configs/{schedule_config_id}', {
				params: { path: { schedule_config_id: deletingConfig.id } }
			});

			if (res.error) {
				toast.error(apiErrorMessage(res.error, 'Failed to delete schedule'));
			} else {
				toast.success(`Schedule ${deletingConfig.name} deleted`);
				isDeleteDialogOpen = false;
				deletingConfig = null;
				loadConfigs();
			}
		} catch {
			toast.error('Error deleting schedule');
		} finally {
			isDeleting = false;
		}
	}

	onMount(() => {
		refresh();
	});
</script>

<div class="space-y-6">
	{#if projectError}<LoadError message={projectError} retry={loadProjects} />{/if}
	{#if taskSpecsError}<LoadError message={taskSpecsError} retry={loadTaskSpecs} />{/if}
	{#if loadError}<LoadError message={loadError} retry={() => loadConfigs()} />{/if}
	<!-- Page Header -->
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-3xl font-bold tracking-tight">Schedule Configurations</h1>
			<p class="text-sm text-muted-foreground">
				Automated cron triggers and execution cadence rules
			</p>
		</div>
		<div class="flex items-center gap-2">
			<Button variant="outline" size="sm" onclick={refresh} disabled={loading}>
				<RefreshCw class="size-4 {loading ? 'animate-spin' : ''}" />
				Refresh
			</Button>
			<Button variant="secondary" size="sm" onclick={triggerDispatcher} disabled={isTriggering}>
				<Play class="size-3.5" />
				Trigger Dispatcher
			</Button>
			<Button size="sm" onclick={() => (editor = { mode: 'create' })}>
				<Plus class="size-4" />
				New Schedule
			</Button>
		</div>
	</div>

	<!-- Search & Filter Bar -->
	<div class="flex items-center gap-3">
		<div class="relative max-w-sm flex-1">
			<Search class="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
			<Input
				placeholder="Search by schedule or task func..."
				bind:value={searchQuery}
				oninput={() => loadConfigs(0)}
				class="pl-9"
			/>
		</div>
		<NativeSelect aria-label="Project" bind:value={projectId} onchange={() => loadConfigs(0)}>
			<option value="">All projects</option>
			{#if projectId && !projectNames.has(projectId)}<option value={projectId}>{projectId}</option
				>{/if}
			{#each projects as project (project.id)}<option value={project.id}>{project.name}</option
				>{/each}
		</NativeSelect>
		<NativeSelect
			aria-label="Schedule status"
			bind:value={enabledFilter}
			onchange={() => loadConfigs(0)}
		>
			<option value="">All statuses</option><option value="true">Active</option><option
				value="false">Paused</option
			>
		</NativeSelect>
	</div>

	<!-- Configurations Table -->
	<div class="rounded-md border bg-card">
		<Table>
			<TableHeader>
				<TableRow>
					<TableHead>Schedule Name</TableHead>
					<TableHead>Target Task</TableHead>
					<TableHead>Trigger Cadence</TableHead>
					<TableHead>Status</TableHead>
					<TableHead>Next Run</TableHead>
					<TableHead class="text-right">Actions</TableHead>
				</TableRow>
			</TableHeader>
			<TableBody>
				{#if loading && configs.length === 0}
					<TableRow>
						<TableCell colspan={6} class="h-32 text-center text-muted-foreground">
							<span role="status">Loading configurations...</span>
						</TableCell>
					</TableRow>
				{:else if loadError}
					<TableRow><TableCell colspan={6}>List unavailable</TableCell></TableRow>
				{:else if configs.length === 0}
					<TableRow>
						<TableCell colspan={6} class="h-32 text-center text-muted-foreground">
							<div class="flex flex-col items-center justify-center gap-2">
								<CalendarClock class="size-8 text-muted-foreground/40" />
								<span>No schedule configurations found</span>
							</div>
						</TableCell>
					</TableRow>
				{:else}
					{#each configs as config (config.id)}
						<TableRow>
							<!-- Generated names (agent schedules) are long; wrap them instead of widening the table. -->
							<TableCell class="max-w-80 min-w-48 whitespace-normal">
								<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
									<span class="font-semibold text-foreground">{config.name}</span>
									<ScheduleOwnerLabel
										{config}
										projectName={projectNames.get(config.owner?.project_id ?? '')}
									/>
								</div>
								{#if config.description}
									<div class="line-clamp-1 text-xs text-muted-foreground">{config.description}</div>
								{/if}
							</TableCell>
							<TableCell class="font-mono text-xs text-muted-foreground">
								{config.task_func}
							</TableCell>
							<TableCell class="font-mono text-xs">
								{#if config.cron_expression}
									<span class="rounded bg-muted px-2 py-0.5 text-muted-foreground">
										cron: {config.cron_expression}
									</span>
								{:else if config.interval_seconds}
									<span class="rounded bg-secondary px-2 py-0.5 text-secondary-foreground">
										every {config.interval_seconds}s
									</span>
								{:else}
									<span class="text-muted-foreground">Manual only</span>
								{/if}
							</TableCell>
							<TableCell>
								{#if config.enabled}
									<Badge variant="success">
										<CheckCircle2 class="size-3" />
										Active
									</Badge>
								{:else}
									<Badge variant="secondary">
										<PauseCircle class="size-3" />
										Paused
									</Badge>
								{/if}
							</TableCell>
							<TableCell class="text-xs text-muted-foreground">
								{config.next_run_at ? new Date(config.next_run_at).toLocaleString() : '—'}
							</TableCell>
							<TableCell class="text-right">
								{#if config.owner?.kind === 'system_maintenance'}
									<span class="text-xs text-muted-foreground">Managed by Auto Hub</span>
								{:else if !config.generic_mutation_allowed}
									<span class="text-xs text-muted-foreground">Managed by owner</span>
								{:else}
									<div class="flex items-center justify-end gap-1.5">
										<Button variant="outline" onclick={() => toggleEnable(config)}>
											{config.enabled ? 'Pause' : 'Resume'}
										</Button>
										<Button
											variant="subtle"
											size="icon"
											onclick={() => openEdit(config)}
											title="Edit Schedule"
										>
											<Pencil class="size-3.5" />
										</Button>
										<Button
											variant="subtle-destructive"
											size="icon"
											onclick={() => openDelete(config)}
											title="Delete Schedule"
										>
											<Trash2 class="size-3.5" />
										</Button>
									</div>
								{/if}
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
			onpage={loadConfigs}
		/>
	{/if}

	{#if editor}
		<ScheduleEditorDialog
			{editor}
			{taskSpecs}
			onclose={() => (editor = null)}
			onsaved={() => loadConfigs()}
		/>
	{/if}

	<!-- Delete Schedule Confirmation Dialog -->
	<Dialog bind:open={isDeleteDialogOpen}>
		<DialogContent class="sm:max-w-110">
			<DialogHeader>
				<DialogTitle>
					<span class="flex items-center gap-2 text-destructive">
						<AlertTriangle class="size-5" />
						Delete Schedule Configuration
					</span>
				</DialogTitle>
			</DialogHeader>

			<div class="space-y-3 py-2">
				<p class="text-sm text-foreground">
					Are you sure you want to delete <span class="font-semibold text-foreground"
						>"{deletingConfig?.name}"</span
					>?
				</p>
				{#if deletingConfig && isProjectManaged(deletingConfig)}
					<div class="rounded-md border border-warning/20 bg-warning/10 p-3 text-xs text-warning">
						<strong>Warning:</strong> This schedule belongs to a project. Deleting it stops that project's
						scheduled work.
					</div>
				{/if}
				<p class="text-xs text-muted-foreground">
					This action cannot be undone. Past execution history under Schedule Jobs will be
					preserved.
				</p>
			</div>

			<DialogFooter>
				<Button
					type="button"
					variant="outline"
					onclick={() => (isDeleteDialogOpen = false)}
					disabled={isDeleting}
				>
					Cancel
				</Button>
				<Button type="button" variant="destructive" onclick={confirmDelete} disabled={isDeleting}>
					{isDeleting ? 'Deleting...' : 'Delete Schedule'}
				</Button>
			</DialogFooter>
		</DialogContent>
	</Dialog>
</div>
