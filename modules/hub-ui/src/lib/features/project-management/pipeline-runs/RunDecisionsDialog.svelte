<script lang="ts">
	import { untrack } from 'svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogDescription
	} from '$lib/components/ui/dialog';
	import { ExternalLink } from '@lucide/svelte';
	import type { components } from '$lib/api';
	import RunStateBadge from './RunStateBadge.svelte';
	import RunDecisions from './RunDecisions.svelte';
	import { runHref } from './run-links';
	type Run = components['schemas']['PipelineRunRead'];
	/**
	 * Decision inbox fast path: the PR run page's Decisions section in a dialog, so an exact
	 * selection can be resolved without leaving the inbox.
	 */
	let {
		run,
		onclose,
		onchange,
		selection
	}: {
		run: Run;
		onclose: () => void;
		onchange: () => void;
		selection?: components['schemas']['DecisionEntryRead'];
	} = $props();
	let current = $state(untrack(() => run));
</script>

<Dialog
	open={true}
	onOpenChange={(open) => {
		if (!open) onclose();
	}}
>
	<!-- eslint-disable shadcn/no-arbitrary-values -- viewport-relative height has no scale equivalent -->
	<DialogContent
		class="flex max-h-[calc(100dvh-2rem)] flex-col gap-0 overflow-hidden p-0 sm:max-w-260"
	>
		<!-- eslint-enable shadcn/no-arbitrary-values -->
		<div class="shrink-0 border-b">
			<DialogHeader class="px-5 py-5 sm:px-7">
				<div class="mb-2 flex items-center gap-2 pr-8">
					<Badge variant="outline">PR #{run.pull_number}</Badge>
					<RunStateBadge state={current.state} />
					{#if current.sdd_snapshot}<span class="text-xs text-muted-foreground">SDD</span>{/if}
				</div>
				<DialogTitle class="text-xl leading-snug break-words"
					>{current.pull_snapshot.title}</DialogTitle
				>
				<DialogDescription
					>Review the evidence and choose the next step for this run.</DialogDescription
				>
				<div class="mt-3 flex flex-wrap items-center gap-2">
					<Button variant="outline" size="sm" href={run.pull_url} target="_blank" rel="noreferrer"
						><ExternalLink class="size-3.5" />Inspect pull request</Button
					>
					<Button variant="ghost" size="sm" href={runHref(run.id, run.project_id)}
						>Open run page</Button
					>
				</div>
			</DialogHeader>
		</div>
		<div class="min-h-0 overflow-y-auto px-5 py-5 sm:px-7">
			<RunDecisions {run} {selection} {onchange} onrun={(latest) => (current = latest)} />
		</div>
	</DialogContent>
</Dialog>
