<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { DashboardState } from './dashboard.svelte';
	import LoadError from '$lib/components/shared/LoadError.svelte';
	import { getStateBadgeClass } from '$lib/features/project-management/pipeline-runs/presentation';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import {
		FolderKanban,
		CalendarClock,
		History,
		Activity,
		CheckCircle2,
		AlertCircle,
		RefreshCw,
		Workflow,
		KeyRound,
		GitBranch,
		ArrowRight,
		Radio
	} from '@lucide/svelte';

	const dashboard = new DashboardState();
	let refreshIntervalSec = $state(15);
	let refreshTimer: ReturnType<typeof setInterval> | null = null;
	const loadDashboardData = (silent = false) => dashboard.load(silent);

	function setupAutoRefresh(seconds: number) {
		if (refreshTimer) {
			clearInterval(refreshTimer);
			refreshTimer = null;
		}
		refreshIntervalSec = seconds;
		if (seconds > 0) {
			refreshTimer = setInterval(() => {
				loadDashboardData(true);
			}, seconds * 1000);
		}
	}

	onMount(() => {
		loadDashboardData();
		setupAutoRefresh(refreshIntervalSec);
	});

	onDestroy(() => {
		if (refreshTimer) {
			clearInterval(refreshTimer);
		}
	});
</script>

<div class="space-y-6">
	{#if dashboard.error}
		<LoadError message={dashboard.error} retry={() => dashboard.load()} />
	{/if}
	<!-- Header with Live Refresh Indicator -->
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-3xl font-bold tracking-tight">System Overview</h1>
			<p class="text-sm text-muted-foreground">
				Real-time orchestrator statistics, lifecycle pipeline status, and health metrics
			</p>
		</div>
		<div class="flex flex-wrap items-center gap-3">
			<!-- Auto-Refresh Controls -->
			<div
				class="flex items-center gap-1.5 rounded-lg border border-border bg-card/60 px-2.5 py-1 text-xs backdrop-blur-xs"
			>
				<div class="flex items-center gap-1.5 font-medium text-muted-foreground">
					<Radio
						class="size-3.5 {refreshIntervalSec > 0
							? 'animate-pulse text-emerald-500'
							: 'text-muted-foreground'}"
					/>
					<span>Sync:</span>
				</div>
				<button
					type="button"
					onclick={() => setupAutoRefresh(0)}
					class="rounded px-1.5 py-0.5 font-mono transition-colors {refreshIntervalSec === 0
						? 'bg-primary font-semibold text-primary-foreground'
						: 'text-muted-foreground hover:text-foreground'}"
				>
					Off
				</button>
				<button
					type="button"
					onclick={() => setupAutoRefresh(5)}
					class="rounded px-1.5 py-0.5 font-mono transition-colors {refreshIntervalSec === 5
						? 'bg-primary font-semibold text-primary-foreground'
						: 'text-muted-foreground hover:text-foreground'}"
				>
					5s
				</button>
				<button
					type="button"
					onclick={() => setupAutoRefresh(15)}
					class="rounded px-1.5 py-0.5 font-mono transition-colors {refreshIntervalSec === 15
						? 'bg-primary font-semibold text-primary-foreground'
						: 'text-muted-foreground hover:text-foreground'}"
				>
					15s
				</button>
				<button
					type="button"
					onclick={() => setupAutoRefresh(30)}
					class="rounded px-1.5 py-0.5 font-mono transition-colors {refreshIntervalSec === 30
						? 'bg-primary font-semibold text-primary-foreground'
						: 'text-muted-foreground hover:text-foreground'}"
				>
					30s
				</button>
				<span class="pl-1 font-mono text-[10px] text-muted-foreground/70">
					{dashboard.lastRefreshedAt?.toLocaleTimeString([], {
						hour: '2-digit',
						minute: '2-digit',
						second: '2-digit'
					})}
				</span>
			</div>

			<Button
				variant="outline"
				size="sm"
				onclick={() => loadDashboardData(false)}
				disabled={dashboard.loading}
				class="gap-2"
			>
				<RefreshCw class="size-4 {dashboard.loading ? 'animate-spin' : ''}" />
				Refresh
			</Button>
		</div>
	</div>

	<!-- Status & Health Banner -->
	<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
		<div
			class="flex items-center justify-between rounded-xl border border-border/80 bg-card/60 p-4 backdrop-blur-xs"
		>
			<div class="flex items-center gap-3">
				<div class="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
					<Activity class="size-5" />
				</div>
				<div>
					<p class="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
						API Health
					</p>
					<p class="text-sm font-medium">FastAPI Dispatcher Core</p>
				</div>
			</div>
			{#if dashboard.healthStatus === 'online'}
				<Badge
					variant="default"
					class="gap-1.5 bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/20 dark:text-emerald-400"
				>
					<CheckCircle2 class="size-3.5" />
					Operational
				</Badge>
			{:else}
				<Badge variant="destructive" class="gap-1.5">
					<AlertCircle class="size-3.5" />
					Unavailable
				</Badge>
			{/if}
		</div>

		<div
			class="flex items-center justify-between rounded-xl border border-border/80 bg-card/60 p-4 backdrop-blur-xs"
		>
			<div class="flex items-center gap-3">
				<div class="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
					<CheckCircle2 class="size-5" />
				</div>
				<div>
					<p class="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
						Database Connection
					</p>
					<p class="text-sm font-medium">PostgreSQL / SQLite Engine</p>
				</div>
			</div>
			{#if dashboard.dbStatus === 'connected'}
				<Badge
					variant="default"
					class="gap-1.5 bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/20 dark:text-emerald-400"
				>
					<CheckCircle2 class="size-3.5" />
					Connected
				</Badge>
			{:else}
				<Badge variant="destructive" class="gap-1.5">
					<AlertCircle class="size-3.5" />
					Disconnected
				</Badge>
			{/if}
		</div>

		<div
			class="flex items-center justify-between rounded-xl border border-border/80 bg-card/60 p-4 backdrop-blur-xs"
		>
			<div class="flex items-center gap-3">
				<div class="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
					<CalendarClock class="size-5" />
				</div>
				<div>
					<p class="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
						Scheduler Trigger
					</p>
					<p class="text-sm font-medium">
						{dashboard.lastTickAt
							? `Last tick ${new Date(dashboard.lastTickAt).toLocaleTimeString()}`
							: 'No tick recorded'}
					</p>
				</div>
			</div>
			{#if dashboard.triggerStatus === 'ok'}
				<Badge
					variant="default"
					class="gap-1.5 bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/20 dark:text-emerald-400"
				>
					<CheckCircle2 class="size-3.5" />
					Firing
				</Badge>
			{:else if dashboard.triggerStatus === 'stale'}
				<Badge variant="destructive" class="gap-1.5">
					<AlertCircle class="size-3.5" />
					Stopped
				</Badge>
			{:else}
				<Badge variant="secondary" class="gap-1.5">
					{dashboard.triggerStatus === 'never' ? 'Never fired' : 'Unknown'}
				</Badge>
			{/if}
		</div>
	</div>

	<!-- Pipeline Runs Observability Card (High-Impact Hero Banner) -->
	<Card
		class="overflow-hidden border-primary/20 bg-linear-to-br from-card via-card to-primary/5 shadow-sm"
	>
		<CardHeader class="pb-3">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2">
					<Workflow class="size-5 text-primary" />
					<CardTitle class="text-base font-semibold">Pipeline Runs Orchestration</CardTitle>
				</div>
				<Button
					variant="ghost"
					size="sm"
					onclick={() => goto('/projects/runs')}
					class="gap-1.5 text-xs text-primary hover:text-primary"
				>
					View All Runs
					<ArrowRight class="size-3.5" />
				</Button>
			</div>
		</CardHeader>
		<CardContent>
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-5">
				<div class="rounded-lg border border-border/70 bg-background/50 p-3">
					<div class="text-xs font-semibold text-muted-foreground uppercase">Total Runs</div>
					<div class="mt-1 text-2xl font-bold">{dashboard.totalRuns}</div>
					<p class="mt-0.5 text-[11px] text-muted-foreground">All time lifecycle</p>
				</div>
				<div class="rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-3">
					<div class="text-xs font-semibold text-indigo-600 uppercase dark:text-indigo-400">
						Active Work
					</div>
					<div class="mt-1 text-2xl font-bold text-indigo-600 dark:text-indigo-400">
						{dashboard.activeRuns}
					</div>
					<p class="mt-0.5 text-[11px] text-muted-foreground">Dispatch / Implementing</p>
				</div>
				<div class="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
					<div class="text-xs font-semibold text-amber-600 uppercase dark:text-amber-400">
						Awaiting CI
					</div>
					<div class="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">
						{dashboard.awaitingCiRuns}
					</div>
					<p class="mt-0.5 text-[11px] text-muted-foreground">PR verification check</p>
				</div>
				<div class="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
					<div class="text-xs font-semibold text-emerald-600 uppercase dark:text-emerald-400">
						Completed
					</div>
					<div class="mt-1 text-2xl font-bold text-emerald-600 dark:text-emerald-400">
						{dashboard.completedRuns}
					</div>
					<p class="mt-0.5 text-[11px] text-muted-foreground">Passed CI verification</p>
				</div>
				<div class="rounded-lg border border-rose-500/20 bg-rose-500/5 p-3">
					<div class="text-xs font-semibold text-rose-600 uppercase dark:text-rose-400">
						Needs you
					</div>
					<div class="mt-1 text-2xl font-bold text-rose-600 dark:text-rose-400">
						{dashboard.failedRuns}
					</div>
					<p class="mt-0.5 text-[11px] text-muted-foreground">Failed, paused, or blocked</p>
				</div>
			</div>
		</CardContent>
	</Card>

	<!-- Core Metrics Grid -->
	<div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
		<!-- Projects Metric -->
		<Card
			class="cursor-pointer transition-all hover:border-primary/40 hover:shadow-md"
			onclick={() => goto('/projects')}
		>
			<CardHeader class="flex flex-row items-center justify-between pb-2">
				<CardTitle class="text-sm font-medium text-muted-foreground">Managed Projects</CardTitle>
				<FolderKanban class="size-4 text-muted-foreground" />
			</CardHeader>
			<CardContent>
				<div class="text-3xl font-bold">{dashboard.projectCount}</div>
				<p class="mt-1 text-xs text-muted-foreground">Connected repositories & workspaces</p>
			</CardContent>
		</Card>

		<!-- Connectors Metric -->
		<Card
			class="cursor-pointer transition-all hover:border-primary/40 hover:shadow-md"
			onclick={() => goto('/settings/connectors')}
		>
			<CardHeader class="flex flex-row items-center justify-between pb-2">
				<CardTitle class="text-sm font-medium text-muted-foreground">Integrations</CardTitle>
				<KeyRound class="size-4 text-muted-foreground" />
			</CardHeader>
			<CardContent>
				<div class="text-3xl font-bold">{dashboard.connectorCount}</div>
				<p class="mt-1 text-xs text-muted-foreground">
					{dashboard.activeConnectors} active connectors
				</p>
			</CardContent>
		</Card>

		<!-- Schedules Metric -->
		<Card
			class="cursor-pointer transition-all hover:border-primary/40 hover:shadow-md"
			onclick={() => goto('/schedules/configs')}
		>
			<CardHeader class="flex flex-row items-center justify-between pb-2">
				<CardTitle class="text-sm font-medium text-muted-foreground">Schedule Configs</CardTitle>
				<CalendarClock class="size-4 text-muted-foreground" />
			</CardHeader>
			<CardContent>
				<div class="text-3xl font-bold">{dashboard.scheduleCount}</div>
				<p class="mt-1 text-xs text-muted-foreground">Automated cron & interval triggers</p>
			</CardContent>
		</Card>

		<!-- Active Runs Metric -->
		<Card
			class="cursor-pointer transition-all hover:border-primary/40 hover:shadow-md"
			onclick={() => goto('/projects/runs')}
		>
			<CardHeader class="flex flex-row items-center justify-between pb-2">
				<CardTitle class="text-sm font-medium text-muted-foreground">Active Runs</CardTitle>
				<Activity class="size-4 text-primary" />
			</CardHeader>
			<CardContent>
				<div class="text-3xl font-bold">{dashboard.activeRuns}</div>
				<p class="mt-1 text-xs text-muted-foreground">In-flight pipeline orchestrations</p>
			</CardContent>
		</Card>
	</div>

	<!-- Activity Streams (Side by Side) -->
	<div class="grid gap-6 lg:grid-cols-2">
		<!-- Recent Pipeline Runs -->
		<div class="rounded-xl border border-border/80 bg-card/60 p-5 backdrop-blur-xs">
			<div class="flex items-center justify-between pb-3">
				<div class="flex items-center gap-2">
					<Workflow class="size-4 text-primary" />
					<h2 class="text-sm font-semibold tracking-tight">Recent Pipeline Runs</h2>
				</div>
				<Button
					variant="ghost"
					size="sm"
					onclick={() => goto('/projects/runs')}
					class="text-xs text-muted-foreground hover:text-foreground"
				>
					View All
				</Button>
			</div>

			{#if dashboard.error && dashboard.recentRuns.length === 0}
				<p class="text-sm text-muted-foreground">Recent runs unavailable.</p>
			{:else if dashboard.recentRuns.length === 0}
				<div class="py-8 text-center text-xs text-muted-foreground">
					No pipeline runs dispatched yet.
				</div>
			{:else}
				<div class="divide-y divide-border/60">
					{#each dashboard.recentRuns as run (run.id)}
						<div class="flex items-center justify-between py-2.5 text-xs">
							<div class="min-w-0 flex-1 pr-3">
								<div class="flex items-center gap-2">
									<span class="font-bold text-foreground">PR #{run.pull_number}</span>
									<span class="truncate text-muted-foreground">
										{run.pull_snapshot?.title || `PR #${run.pull_number}`}
									</span>
								</div>
								<div
									class="mt-0.5 flex items-center gap-2 font-mono text-[11px] text-muted-foreground"
								>
									<div class="flex items-center gap-1">
										<GitBranch class="size-3" />
										<span class="max-w-[140px] truncate">{run.branch}</span>
									</div>
									{#if run.pull_url}
										<a
											href={run.pull_url}
											target="_blank"
											rel="noreferrer"
											class="font-medium text-primary hover:underline"
										>
											View PR
										</a>
									{/if}
								</div>
							</div>
							<div class="flex items-center gap-2">
								<Badge
									variant="outline"
									class="text-[10px] capitalize {getStateBadgeClass(run.state)}"
								>
									{run.state.replace('_', ' ')}
								</Badge>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Recent Scheduled Job Executions -->
		<div class="rounded-xl border border-border/80 bg-card/60 p-5 backdrop-blur-xs">
			<div class="flex items-center justify-between pb-3">
				<div class="flex items-center gap-2">
					<History class="size-4 text-primary" />
					<h2 class="text-sm font-semibold tracking-tight">Recent Schedule Executions</h2>
				</div>
				<Button
					variant="ghost"
					size="sm"
					onclick={() => goto('/schedules/jobs')}
					class="text-xs text-muted-foreground hover:text-foreground"
				>
					View All
				</Button>
			</div>

			{#if dashboard.error && dashboard.recentJobs.length === 0}
				<p class="text-sm text-muted-foreground">Recent jobs unavailable.</p>
			{:else if dashboard.recentJobs.length === 0}
				<div class="py-8 text-center text-xs text-muted-foreground">
					No schedule jobs executed yet.
				</div>
			{:else}
				<div class="divide-y divide-border/60">
					{#each dashboard.recentJobs as job (job.id)}
						<div class="flex items-center justify-between py-2.5 text-xs">
							<div class="min-w-0 flex-1 pr-3">
								<div class="font-medium text-foreground">
									{job.name}
								</div>
								<div class="mt-0.5 font-mono text-[11px] text-muted-foreground">
									run: {job.dispatcher_run_id || 'manual'}
								</div>
							</div>
							<div class="flex items-center gap-2">
								{#if job.status === 'success'}
									<Badge
										variant="default"
										class="bg-emerald-500/15 text-[10px] text-emerald-600 dark:text-emerald-400"
									>
										Success
									</Badge>
								{:else if job.status === 'failure'}
									<Badge variant="destructive" class="text-[10px]">Failure</Badge>
								{:else}
									<Badge variant="outline" class="text-[10px] capitalize">
										{job.status}
									</Badge>
								{/if}
								<span class="font-mono text-[10px] text-muted-foreground">
									{new Date(job.created_at).toLocaleTimeString([], {
										hour: '2-digit',
										minute: '2-digit'
									})}
								</span>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>

	<!-- Quick Launch Operations -->
	<div class="rounded-xl border border-border/80 bg-card/60 p-6 backdrop-blur-xs">
		<h2 class="text-lg font-semibold tracking-tight">Quick Operations</h2>
		<p class="mb-4 text-sm text-muted-foreground">
			Direct shortcuts to frequent orchestrator actions
		</p>
		<div class="flex flex-wrap gap-3">
			<Button onclick={() => goto('/projects/runs')} class="gap-2">
				<Workflow class="size-4" />
				Pipeline Runs
			</Button>
			<Button variant="secondary" onclick={() => goto('/projects')} class="gap-2">
				<FolderKanban class="size-4" />
				Manage Projects
			</Button>
			<Button variant="secondary" onclick={() => goto('/settings/connectors')} class="gap-2">
				<KeyRound class="size-4" />
				Manage Connectors
			</Button>
			<Button variant="secondary" onclick={() => goto('/schedules/configs')} class="gap-2">
				<CalendarClock class="size-4" />
				View Schedules
			</Button>
			<Button variant="outline" onclick={() => goto('/schedules/jobs')} class="gap-2">
				<History class="size-4" />
				Job History
			</Button>
		</div>
	</div>
</div>
