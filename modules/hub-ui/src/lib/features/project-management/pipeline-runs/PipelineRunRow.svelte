<script lang="ts">
	import type { components } from '$lib/api';
	import RunStateBadge from './RunStateBadge.svelte';
	import RunActions from './RunActions.svelte';
	import { decisionWait, decisionWaitLabel, type RunDecisions } from './run-actions';
	import { runHref } from './run-links';
	import { Badge } from '$lib/components/ui/badge';
	import { TableRow, TableCell } from '$lib/components/ui/table';
	import {
		GitPullRequest,
		GitBranch,
		ExternalLink,
		ShieldCheck,
		MessageSquare
	} from '@lucide/svelte';

	type PipelineRun = components['schemas']['PipelineRunRead'];

	let {
		run,
		projectName,
		operating,
		decisions,
		onadvance,
		onpause,
		onresume,
		oncancel,
		onattach
	}: {
		run: PipelineRun;
		projectName: string;
		operating: boolean;
		decisions: RunDecisions;
		onadvance: (runId: string) => void;
		onpause: (runId: string) => void;
		onresume: (run: PipelineRun) => void;
		oncancel: (runId: string) => void;
		onattach: (run: PipelineRun) => void;
	} = $props();

	let waiting = $derived(
		decisions.status === 'known' ? decisionWaitLabel(decisionWait(decisions.entries)) : null
	);
</script>

<TableRow
	data-attention={waiting ? 'true' : undefined}
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
			<a
				href={runHref(run.id, run.project_id)}
				class="block text-sm font-medium text-foreground underline-offset-4 hover:underline md:line-clamp-1 md:text-xs"
			>
				{run.pull_snapshot?.title || 'No title'}
			</a>
		</div>
	</TableCell>

	<TableCell>
		<div class="flex flex-col gap-0.5">
			<span class="text-sm font-semibold text-foreground">{projectName}</span>
			<span class="font-mono text-xs text-muted-foreground">run rev {run.revision}</span>
		</div>
	</TableCell>

	<TableCell>
		<div class="flex flex-col items-start gap-1">
			<RunStateBadge state={run.state} />
			{#if waiting}
				<Badge variant="attention"><MessageSquare aria-hidden="true" />{waiting}</Badge>
			{/if}
		</div>
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
		<RunActions
			{run}
			{decisions}
			{operating}
			href={(section) => runHref(run.id, run.project_id, section)}
			onadvance={() => onadvance(run.id)}
			onpause={() => onpause(run.id)}
			onresume={() => onresume(run)}
			oncancel={() => oncancel(run.id)}
			onattach={() => onattach(run)}
		/>
	</TableCell>
</TableRow>
