<script lang="ts">
	import type { DashboardState } from './dashboard.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Activity, AlertCircle, CalendarClock, CheckCircle2 } from '@lucide/svelte';

	let {
		healthStatus,
		dbStatus,
		triggerStatus,
		lastTickAt
	}: Pick<DashboardState, 'healthStatus' | 'dbStatus' | 'triggerStatus' | 'lastTickAt'> = $props();
</script>

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
		{#if healthStatus === 'online'}
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
		{#if dbStatus === 'connected'}
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
					{lastTickAt
						? `Last tick ${new Date(lastTickAt).toLocaleTimeString()}`
						: 'No tick recorded'}
				</p>
			</div>
		</div>
		{#if triggerStatus === 'ok'}
			<Badge
				variant="default"
				class="gap-1.5 bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/20 dark:text-emerald-400"
			>
				<CheckCircle2 class="size-3.5" />
				Firing
			</Badge>
		{:else if triggerStatus === 'stale'}
			<Badge variant="destructive" class="gap-1.5">
				<AlertCircle class="size-3.5" />
				Stopped
			</Badge>
		{:else}
			<Badge variant="secondary" class="gap-1.5">
				{triggerStatus === 'never' ? 'Never fired' : 'Unknown'}
			</Badge>
		{/if}
	</div>
</div>
