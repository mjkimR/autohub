<script lang="ts">
	import type { components } from '$lib/api';
	import RunStateBadge from './RunStateBadge.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { TableRow, TableCell } from '$lib/components/ui/table';
	import {
		GitPullRequest,
		GitBranch,
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
		onhistory,
		ondecisions
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
		ondecisions: (run: PipelineRun) => void;
	} = $props();
</script>

<TableRow
	class="grid min-w-0 gap-1 p-3 md:table-row md:p-0 [&>td]:min-w-0 [&>td]:whitespace-normal"
>
	<TableCell>
		<div class="space-y-1">
			<div class="flex items-center gap-1.5">
				<Badge variant="info" class="font-mono text-xs">
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
			<div class="text-sm font-medium text-foreground md:line-clamp-1 md:text-xs">
				{run.pull_snapshot?.title || 'No title'}
			</div>
		</div>
	</TableCell>

	<TableCell>
		<div class="flex flex-col gap-0.5">
			<span class="text-sm font-semibold text-foreground">{projectName}</span>
			<span class="font-mono text-xs text-muted-foreground">run rev {run.revision}</span>
		</div>
	</TableCell>

	<TableCell>
		<RunStateBadge state={run.state} />
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
				<span class="text-xs text-muted-foreground/60">No PR yet</span>
			{/if}
		</div>
	</TableCell>

	<TableCell>
		{#if run.lease_owner}
			<div class="space-y-0.5 text-xs">
				<div class="flex items-center gap-1 text-foreground">
					<ShieldCheck class="size-3 text-success" />
					<span class="truncate">{run.lease_owner}</span>
				</div>
				{#if run.lease_expires_at}
					<div class="font-mono text-xs text-muted-foreground">
						expires {new Date(run.lease_expires_at).toLocaleTimeString()}
					</div>
				{/if}
			</div>
		{:else}
			<span class="text-xs text-muted-foreground">Idle (unleased)</span>
		{/if}
	</TableCell>

	<TableCell class="text-xs text-muted-foreground"
		><span class="mr-1 md:hidden">Created:</span>
		{new Date(run.created_at).toLocaleString()}
	</TableCell>

	<TableCell class="text-right">
		<div class="flex flex-wrap items-center gap-2 md:justify-end md:gap-1">
			<Button variant="outline" size="sm" onclick={() => ondecisions(run)}>Decisions</Button>
			{#if run.state !== 'completed' && run.state !== 'failed' && run.state !== 'canceled'}
				{#if run.state === 'paused' || run.state === 'blocked'}
					<Button
						variant="ghost"
						size="icon"
						onclick={() => onresume(run)}
						disabled={operating}
						class="size-11 md:size-8"
						title="Resume Run"
						aria-label="Resume Run"
					>
						<Play class="size-4 text-warning" />
					</Button>
				{:else}
					<Button
						variant="subtle"
						size="icon"
						onclick={() => onpause(run.id)}
						disabled={operating}
						class="size-11 md:size-8"
						title="Pause Run"
						aria-label="Pause Run"
					>
						<Pause class="size-4 group-hover/button:text-warning" />
					</Button>
				{/if}

				{#if !run.pull_number}
					<Button
						variant="subtle"
						size="icon"
						onclick={() => onattach(run)}
						class="size-11 md:size-8"
						title="Attach Pull Request"
						aria-label="Attach Pull Request"
					>
						<Link2 class="size-4 group-hover/button:text-primary" />
					</Button>
				{/if}

				<Button
					variant="subtle"
					size="icon"
					onclick={() => onadvance(run.id)}
					disabled={operating}
					class="size-11 md:size-8"
					title="Advance / Sync Run Status"
					aria-label="Advance Run"
				>
					<RefreshCw
						class="size-4 group-hover/button:text-success {operating ? 'animate-spin' : ''}"
					/>
				</Button>

				<Button
					variant="subtle"
					size="icon"
					onclick={() => oncancel(run.id)}
					disabled={operating}
					class="size-11 md:size-8"
					title="Cancel Run"
					aria-label="Cancel Run"
				>
					<XCircle class="size-4 group-hover/button:text-destructive" />
				</Button>
			{/if}

			<Button
				variant="subtle"
				size="icon"
				onclick={() => onhistory(run)}
				class="min-h-11 w-auto md:size-8 md:min-h-0"
				title="View Attempt History"
				aria-label="View Attempt History"
			>
				<History class="ml-3 size-4 md:ml-0" /><span class="mr-3 ml-2 md:hidden"
					>Attempts &amp; errors</span
				>
			</Button>
		</div>
	</TableCell>
</TableRow>
