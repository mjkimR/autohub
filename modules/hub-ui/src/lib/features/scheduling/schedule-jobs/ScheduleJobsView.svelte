<script lang="ts">
	import { PaginatedState } from '$lib/state/paginated.svelte';
	import ListPagination from '$lib/components/shared/ListPagination.svelte';
	import LoadError from '$lib/components/shared/LoadError.svelte';
	import { countedPage, responseData } from '$lib/api/pagination';
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
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
	import {
		History,
		RefreshCw,
		Search,
		CheckCircle2,
		XCircle,
		Clock,
		AlertTriangle
	} from '@lucide/svelte';

	type ScheduleJob = components['schemas']['ScheduleJobRead'];

	const list = new PaginatedState<ScheduleJob>();
	let jobs = $derived(list.items);
	let loading = $derived(list.loading);
	let loadError = $derived(list.error);
	let searchQuery = $state('');
	let statusFilter = $state<components['schemas']['ScheduleJobStatus'] | ''>('');

	async function loadJobs(offset = list.offset) {
		const filters = { search: searchQuery.trim(), status: statusFilter || undefined };
		await list.load(
			async (offset, limit) =>
				countedPage(
					responseData(
						await api.GET('/api/v1/schedule_jobs', {
							params: { query: { ...filters, offset, limit, skip_count: false } }
						}),
						'Failed to load schedule jobs'
					)
				),
			offset
		);
	}

	function getStatusVariant(status: string) {
		switch (status) {
			case 'success':
				return {
					class: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
					icon: CheckCircle2
				};
			case 'failure':
				return { class: 'bg-destructive/15 text-destructive', icon: XCircle };
			case 'pending':
				return { class: 'bg-amber-500/15 text-amber-600 dark:text-amber-400', icon: Clock };
			default:
				return { class: 'bg-secondary text-secondary-foreground', icon: AlertTriangle };
		}
	}

	onMount(() => {
		loadJobs();
	});
</script>

<div class="space-y-6">
	{#if loadError}<LoadError message={loadError} retry={() => loadJobs()} />{/if}
	<!-- Page Header -->
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-3xl font-bold tracking-tight">Execution History</h1>
			<p class="text-sm text-muted-foreground">Execution audit logs and real-time job run states</p>
		</div>
		<div class="flex flex-wrap items-center gap-3">
			<Button
				variant="outline"
				size="sm"
				onclick={() => loadJobs()}
				disabled={loading}
				class="min-h-11 gap-2 sm:min-h-0"
			>
				<RefreshCw class="size-4 {loading ? 'animate-spin' : ''}" />
				Refresh
			</Button>
		</div>
	</div>

	<!-- Controls & Search -->
	<div class="flex flex-wrap items-center gap-3">
		<div class="relative min-w-0 basis-full sm:max-w-sm sm:flex-1 sm:basis-auto">
			<Search class="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
			<Input
				placeholder="Filter jobs by name or status..."
				bind:value={searchQuery}
				oninput={() => loadJobs(0)}
				class="h-11 pl-9 text-base sm:h-10 sm:text-sm"
			/>
		</div>
		<select
			aria-label="Job status"
			bind:value={statusFilter}
			onchange={() => loadJobs(0)}
			class="h-11 max-w-full min-w-0 rounded-md border border-input bg-background px-3 text-sm"
		>
			<option value="">All statuses</option><option value="pending">Pending</option>
			<option value="success">Success</option><option value="failure">Failure</option>
		</select>
	</div>

	<!-- Table Container -->
	<div
		class="overflow-hidden rounded-xl border border-border/80 bg-card/60 shadow-sm backdrop-blur-sm"
	>
		<Table class="block md:table">
			<TableHeader class="hidden md:table-header-group">
				<TableRow>
					<TableHead class="w-[200px]">Job Name</TableHead>
					<TableHead>Status</TableHead>
					<TableHead class="w-[180px]">Started At</TableHead>
					<TableHead class="w-[180px]">Finished At</TableHead>
					<TableHead class="w-[300px]">Dispatcher Run ID</TableHead>
				</TableRow>
			</TableHeader>
			<TableBody class="block md:table-row-group">
				{#if loading}
					<TableRow>
						<TableCell colspan={5} class="h-32 text-center text-muted-foreground">
							Loading job runs...
						</TableCell>
					</TableRow>
				{:else if loadError}
					<TableRow><TableCell colspan={5}>List unavailable</TableCell></TableRow>
				{:else if jobs.length === 0}
					<TableRow>
						<TableCell colspan={5} class="h-32 text-center text-muted-foreground">
							<div class="flex flex-col items-center justify-center gap-2">
								<History class="size-8 text-muted-foreground/40" />
								<span>No execution logs recorded</span>
							</div>
						</TableCell>
					</TableRow>
				{:else}
					{#each jobs as job (job.id)}
						{@const st = getStatusVariant(job.status)}
						<TableRow
							class="grid min-w-0 gap-1 p-3 transition-colors hover:bg-muted/40 md:table-row md:p-0 [&>td]:min-w-0 [&>td]:whitespace-normal"
						>
							<TableCell class="font-semibold text-foreground">
								{job.name}
							</TableCell>
							<TableCell>
								<span
									class="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium {st.class}"
								>
									<st.icon class="size-3.5" />
									<span class="capitalize">{job.status}</span>
								</span>
								{#if job.error_message}
									<p class="mt-1 max-w-md text-xs whitespace-normal text-destructive">
										{job.error_message}
									</p>
								{/if}
							</TableCell>
							<TableCell class="font-mono text-xs text-muted-foreground">
								<span class="mr-1 md:hidden">Started:</span>{new Date(
									job.started_at
								).toLocaleString()}
							</TableCell>
							<TableCell class="font-mono text-xs text-muted-foreground">
								<span class="mr-1 md:hidden">Finished:</span>{job.finished_at
									? new Date(job.finished_at).toLocaleString()
									: '—'}
							</TableCell>
							<TableCell class="font-mono text-xs text-muted-foreground">
								<span class="mr-1 md:hidden">Dispatcher:</span>{job.dispatcher_run_id || 'manual'}
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
			onpage={loadJobs}
		/>
	{/if}
</div>
