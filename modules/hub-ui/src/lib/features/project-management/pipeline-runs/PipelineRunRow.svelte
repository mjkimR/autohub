<script lang="ts">
	import type { components } from '$lib/api';
	import { getStateBadgeClass } from './presentation';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { TableRow, TableCell } from '$lib/components/ui/table';
	import {
		GitPullRequest,
		GitBranch,
		AlertCircle,
		CheckCircle2,
		PauseCircle,
		ExternalLink,
		History,
		ShieldCheck,
		Play,
		Pause,
		XCircle,
		Link2,
		RefreshCw
	} from '@lucide/svelte';

	type PipelineRun = components['schemas']['PipelineRunRead'];

	let {
		run,
		projectName,
		operating,
		onadvance,
		onpause,
		onresume,
		oncancel,
		onattach,
		onhistory
	}: {
		run: PipelineRun;
		projectName: string;
		operating: boolean;
		onadvance: (runId: string) => void;
		onpause: (runId: string) => void;
		onresume: (run: PipelineRun) => void;
		oncancel: (runId: string) => void;
		onattach: (run: PipelineRun) => void;
		onhistory: (run: PipelineRun) => void;
	} = $props();
</script>

<TableRow class="transition-colors hover:bg-muted/40">
	<TableCell>
		<div class="space-y-1">
			<div class="flex items-center gap-1.5">
				<Badge
					variant="outline"
					class="border-primary/30 bg-primary/10 font-mono text-xs text-primary"
				>
					PR #{run.pull_number}
				</Badge>
				{#if run.pull_url}
					<a
						href={run.pull_url}
						target="_blank"
						rel="noreferrer"
						class="text-muted-foreground hover:text-foreground"
						title="Open on GitHub"
					>
						<ExternalLink class="size-3" />
					</a>
				{/if}
			</div>
			<div class="line-clamp-1 text-xs font-medium text-foreground">
				{run.pull_snapshot?.title || 'No title'}
			</div>
		</div>
	</TableCell>

	<TableCell>
		<div class="flex flex-col gap-0.5">
			<span class="text-sm font-semibold text-foreground">{projectName}</span>
			<span class="font-mono text-[10px] text-muted-foreground">run rev {run.revision}</span>
		</div>
	</TableCell>

	<TableCell>
		<Badge variant="outline" class="gap-1.5 font-medium {getStateBadgeClass(run.state)}">
			{#if run.state === 'implementing' || run.state === 'dispatching'}
				<span class="size-1.5 animate-pulse rounded-full bg-current"></span>
			{:else if run.state === 'completed'}
				<CheckCircle2 class="size-3" />
			{:else if run.state === 'failed'}
				<AlertCircle class="size-3" />
			{:else if run.state === 'paused' || run.state === 'blocked'}
				<PauseCircle class="size-3" />
			{/if}
			<span class="capitalize">{run.state.replace('_', ' ')}</span>
		</Badge>
		{#if run.pause_reason}
			<p class="mt-1 max-w-xs text-xs whitespace-normal text-muted-foreground">
				{run.pause_reason}
			</p>
		{/if}
	</TableCell>

	<TableCell>
		<div class="space-y-1 font-mono text-xs">
			<div class="flex items-center gap-1 text-muted-foreground">
				<GitBranch class="size-3 shrink-0" />
				<span class="truncate">{run.branch}</span>
			</div>
			{#if run.pull_url}
				<div class="flex items-center gap-1 text-primary">
					<GitPullRequest class="size-3 shrink-0" />
					<a href={run.pull_url} target="_blank" rel="noreferrer" class="hover:underline">
						PR #{run.pull_number || ''}
					</a>
				</div>
			{:else}
				<span class="text-[11px] text-muted-foreground/60">No PR yet</span>
			{/if}
		</div>
	</TableCell>

	<TableCell>
		{#if run.lease_owner}
			<div class="space-y-0.5 text-xs">
				<div class="flex items-center gap-1 text-foreground">
					<ShieldCheck class="size-3 text-emerald-500" />
					<span class="truncate">{run.lease_owner}</span>
				</div>
				{#if run.lease_expires_at}
					<div class="font-mono text-[10px] text-muted-foreground">
						expires {new Date(run.lease_expires_at).toLocaleTimeString()}
					</div>
				{/if}
			</div>
		{:else}
			<span class="text-xs text-muted-foreground">Idle (unleased)</span>
		{/if}
	</TableCell>

	<TableCell class="text-xs text-muted-foreground">
		{new Date(run.created_at).toLocaleString()}
	</TableCell>

	<TableCell class="text-right">
		<div class="flex items-center justify-end gap-1">
			{#if run.state !== 'completed' && run.state !== 'failed' && run.state !== 'canceled'}
				{#if run.state === 'paused' || run.state === 'blocked'}
					<Button
						variant="ghost"
						size="icon"
						onclick={() => onresume(run)}
						disabled={operating}
						class="size-8 text-amber-500 hover:text-amber-600"
						title="Resume Run"
						aria-label="Resume Run"
					>
						<Play class="size-4" />
					</Button>
				{:else}
					<Button
						variant="ghost"
						size="icon"
						onclick={() => onpause(run.id)}
						disabled={operating}
						class="size-8 text-muted-foreground hover:text-amber-500"
						title="Pause Run"
						aria-label="Pause Run"
					>
						<Pause class="size-4" />
					</Button>
				{/if}

				{#if !run.pull_number}
					<Button
						variant="ghost"
						size="icon"
						onclick={() => onattach(run)}
						class="size-8 text-muted-foreground hover:text-primary"
						title="Attach Pull Request"
						aria-label="Attach Pull Request"
					>
						<Link2 class="size-4" />
					</Button>
				{/if}

				<Button
					variant="ghost"
					size="icon"
					onclick={() => onadvance(run.id)}
					disabled={operating}
					class="size-8 text-muted-foreground hover:text-emerald-500"
					title="Advance / Sync Run Status"
					aria-label="Advance Run"
				>
					<RefreshCw class="size-4 {operating ? 'animate-spin' : ''}" />
				</Button>

				<Button
					variant="ghost"
					size="icon"
					onclick={() => oncancel(run.id)}
					disabled={operating}
					class="size-8 text-muted-foreground hover:text-rose-500"
					title="Cancel Run"
					aria-label="Cancel Run"
				>
					<XCircle class="size-4" />
				</Button>
			{/if}

			<Button
				variant="ghost"
				size="icon"
				onclick={() => onhistory(run)}
				class="size-8 text-muted-foreground hover:text-foreground"
				title="View Attempt History"
				aria-label="View Attempt History"
			>
				<History class="size-4" />
			</Button>
		</div>
	</TableCell>
</TableRow>
