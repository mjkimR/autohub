<script lang="ts">
	import { PaginatedState } from '$lib/state/paginated.svelte';
	import ListPagination from '$lib/components/shared/ListPagination.svelte';
	import ScheduleEditorDialog from './ScheduleEditorDialog.svelte';
	import type { ScheduleEditor } from './schedule-form';
	import LoadError from '$lib/components/shared/LoadError.svelte';
	import { countedPage, responseData } from '$lib/api/pagination';
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

	// Project schedules and legacy tasks retained for compatibility.
	const PROJECT_MANAGED_TASKS = new Set([
		'pipeline.dispatch_project',
		'pipeline.connection_test',
		'pipeline.observe_project',
		'jules.session',
		'jules.sync_sessions'
	]);

	function isProjectManaged(config: ScheduleConfig): boolean {
		return PROJECT_MANAGED_TASKS.has(config.task_func);
	}

	async function loadConfigs(offset = list.offset) {
		const filters = {
			search: searchQuery.trim(),
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
			<Button variant="outline" size="sm" onclick={refresh} disabled={loading} class="gap-2">
				<RefreshCw class="size-4 {loading ? 'animate-spin' : ''}" />
				Refresh
			</Button>
			<Button
				variant="secondary"
				size="sm"
				onclick={triggerDispatcher}
				disabled={isTriggering}
				class="gap-2"
			>
				<Play class="size-3.5" />
				Trigger Dispatcher
			</Button>
			<Button size="sm" onclick={() => (editor = { mode: 'create' })} class="gap-2">
				<Plus class="size-4" />
				New Schedule
			</Button>
		</div>
	</div>

	<!-- Search & Filter Bar -->
	<div class="flex items-center gap-2">
		<div class="relative max-w-sm flex-1">
			<Search class="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
			<Input
				placeholder="Search by schedule or task func..."
				bind:value={searchQuery}
				oninput={() => loadConfigs(0)}
				class="h-9 pl-9 text-xs"
			/>
		</div>
		<select
			aria-label="Schedule status"
			bind:value={enabledFilter}
			onchange={() => loadConfigs(0)}
			class="h-9 rounded-md border border-input bg-background px-3 text-xs"
		>
			<option value="">All statuses</option><option value="true">Active</option><option
				value="false">Paused</option
			>
		</select>
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
							<div class="flex items-center justify-center gap-2">
								<RefreshCw class="size-4 animate-spin" />
								<span>Loading configurations...</span>
							</div>
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
						<TableRow class="transition-colors hover:bg-muted/40">
							<TableCell>
								<div class="flex items-center gap-2">
									<span class="font-semibold text-foreground">{config.name}</span>
									{#if config.task_func === 'system.maintain' || isProjectManaged(config)}
										<Badge
											variant="outline"
											class="border-blue-500/30 bg-blue-500/10 text-[10px] text-blue-600 dark:text-blue-400"
										>
											{config.task_func === 'system.maintain'
												? 'System Managed'
												: 'Project Managed'}
										</Badge>
									{/if}
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
									<span class="rounded bg-primary/10 px-2 py-0.5 text-primary">
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
									<Badge
										variant="default"
										class="gap-1 bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/20 dark:text-emerald-400"
									>
										<CheckCircle2 class="size-3" />
										Active
									</Badge>
								{:else}
									<Badge variant="secondary" class="gap-1 text-muted-foreground">
										<PauseCircle class="size-3" />
										Paused
									</Badge>
								{/if}
							</TableCell>
							<TableCell class="text-xs text-muted-foreground">
								{config.next_run_at ? new Date(config.next_run_at).toLocaleString() : '—'}
							</TableCell>
							<TableCell class="text-right">
								{#if config.task_func === 'system.maintain'}
									<span class="text-xs text-muted-foreground">Managed by Auto Hub</span>
								{:else if config.task_func === 'pipeline.dispatch_project'}
									<Button
										variant="outline"
										size="sm"
										href={typeof config.payload.project_id === 'string'
											? `/projects/${encodeURIComponent(config.payload.project_id)}?tab=settings`
											: '/projects'}
									>
										Project settings
									</Button>
								{:else if config.task_func === 'pipeline.connection_test'}
									<span class="text-xs text-muted-foreground">Manage in project Connections</span>
								{:else}
									<div class="flex items-center justify-end gap-1.5">
										<Button
											variant="outline"
											size="sm"
											onclick={() => toggleEnable(config)}
											class="h-8 text-xs"
										>
											{config.enabled ? 'Pause' : 'Resume'}
										</Button>
										<Button
											variant="outline"
											size="icon"
											class="size-8 text-muted-foreground hover:text-foreground"
											onclick={() => openEdit(config)}
											title="Edit Schedule"
										>
											<Pencil class="size-3.5" />
										</Button>
										<Button
											variant="outline"
											size="icon"
											class="size-8 text-muted-foreground hover:border-destructive/30 hover:bg-destructive/10 hover:text-destructive"
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
		<DialogContent class="sm:max-w-[440px]">
			<DialogHeader>
				<DialogTitle class="flex items-center gap-2 text-destructive">
					<AlertTriangle class="size-5" />
					Delete Schedule Configuration
				</DialogTitle>
			</DialogHeader>

			<div class="space-y-3 py-2">
				<p class="text-sm text-foreground">
					Are you sure you want to delete <span class="font-semibold text-foreground"
						>"{deletingConfig?.name}"</span
					>?
				</p>
				{#if deletingConfig && isProjectManaged(deletingConfig)}
					<div
						class="rounded-md border border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-600 dark:text-amber-400"
					>
						<strong>Warning:</strong> This schedule is automatically managed for a project. Deleting it
						will stop automated background dispatching for this project.
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
