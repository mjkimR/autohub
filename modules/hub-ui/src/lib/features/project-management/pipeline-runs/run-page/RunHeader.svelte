<script lang="ts">
	import type { components } from '$lib/api';
	import { Badge } from '$lib/components/ui/badge';
	import { ChevronRight, CircleHelp, ExternalLink, MessageSquare } from '@lucide/svelte';
	import RunStateBadge from '../RunStateBadge.svelte';
	import { decisionWait, decisionWaitLabel, type RunDecisions } from '../run-actions';

	type Run = components['schemas']['PipelineRunRead'];
	let { run, projectName, decisions }: { run: Run; projectName: string; decisions: RunDecisions } =
		$props();

	let waiting = $derived(
		decisions.status === 'known' ? decisionWaitLabel(decisionWait(decisions.entries)) : null
	);
	let runsHref = $derived(`/projects/${run.project_id}?tab=runs`);
	let prLabel = $derived(run.pull_number ? `PR #${run.pull_number}` : 'No PR yet');
	let reasonLabel = $derived(
		run.state === 'failed' ? 'Failure reason' : run.state === 'canceled' ? 'Reason' : 'Wait reason'
	);
	const time = (value: string) => new Date(value).toLocaleString();
</script>

<nav aria-label="Breadcrumb" class="text-sm text-muted-foreground">
	<ol class="flex flex-wrap items-center gap-1">
		<li><a href="/projects" class="hover:text-foreground">Projects</a></li>
		<li aria-hidden="true"><ChevronRight class="size-3.5" /></li>
		<li>
			<a href={`/projects/${run.project_id}`} class="hover:text-foreground">{projectName}</a>
		</li>
		<li aria-hidden="true"><ChevronRight class="size-3.5" /></li>
		<li><a href={runsHref} class="hover:text-foreground">Runs</a></li>
		<li aria-hidden="true"><ChevronRight class="size-3.5" /></li>
		<li aria-current="page" class="font-medium text-foreground">{prLabel}</li>
	</ol>
</nav>

<header class="space-y-3">
	<div class="flex flex-wrap items-center gap-2">
		<RunStateBadge state={run.state} />
		{#if waiting}
			<Badge variant="attention"><MessageSquare aria-hidden="true" />{waiting}</Badge>
		{/if}
		{#if run.sdd_snapshot}<Badge variant="outline">SDD</Badge>{/if}
	</div>
	<h1 class="text-2xl font-semibold tracking-tight text-balance break-words sm:text-3xl">
		{run.pull_snapshot?.title || prLabel}
	</h1>
	<dl class="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
		<div class="min-w-0">
			<dt class="text-xs text-muted-foreground">Pull request</dt>
			<dd>
				{#if run.pull_url}
					<a
						href={run.pull_url}
						target="_blank"
						rel="noreferrer"
						class="inline-flex items-center gap-1 font-medium underline-offset-4 hover:underline"
						>{prLabel}<ExternalLink aria-hidden="true" class="size-3.5" /></a
					>
				{:else}<span class="text-muted-foreground">{prLabel}</span>{/if}
			</dd>
		</div>
		<div class="min-w-0">
			<dt class="text-xs text-muted-foreground">Branch</dt>
			<dd class="truncate font-mono text-xs leading-5" title={run.branch}>{run.branch}</dd>
		</div>
		<div class="min-w-0">
			<dt class="text-xs text-muted-foreground">Lease</dt>
			<dd>
				{#if run.lease_owner}
					<span class="break-all">{run.lease_owner}</span>
					{#if run.lease_expires_at}<span class="text-muted-foreground">
							· until {new Date(run.lease_expires_at).toLocaleTimeString()}</span
						>{/if}
				{:else}<span class="text-muted-foreground">Idle (unleased)</span>{/if}
			</dd>
		</div>
		<div class="min-w-0">
			<dt class="text-xs text-muted-foreground">Updated</dt>
			<dd>
				{time(run.updated_at)}
				<span class="text-muted-foreground">· revision {run.revision}</span>
			</dd>
		</div>
	</dl>
	{#if run.pause_reason}
		<div class="flex max-w-prose gap-2 rounded-lg border bg-muted/40 p-3 text-sm">
			<CircleHelp aria-hidden="true" class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
			<div class="min-w-0">
				<p class="text-xs text-muted-foreground">{reasonLabel}</p>
				<p class="break-words whitespace-pre-wrap">{run.pause_reason}</p>
			</div>
		</div>
	{/if}
	<p class="font-mono text-xs break-all text-muted-foreground">
		Run {run.id} · created {time(run.created_at)}{run.next_action_at
			? ` · next check ${time(run.next_action_at)}`
			: ''}
	</p>
</header>
