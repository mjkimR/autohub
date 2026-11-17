<script lang="ts">
	import { CircleAlert, ExternalLink } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import { projectTabHref } from '../projects/project-tabs';
	import type { StartRefusal } from './sdd-starts.svelte';
	/** A definitive start refusal: nothing was published and nothing is retained for retry. */
	let {
		refusal,
		projectId,
		repository = ''
	}: { refusal: StartRefusal; projectId: string; repository?: string } = $props();
	let branchHref = $derived(
		refusal.branch && /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository)
			? `https://github.com/${repository}/tree/${encodeURIComponent(refusal.branch)}`
			: ''
	);
</script>

<div role="alert" class="space-y-2 rounded-lg border border-destructive/40 p-3 text-sm">
	<p class="flex items-center gap-2 font-medium text-destructive">
		<CircleAlert class="size-4 shrink-0" aria-hidden="true" />{refusal.title}
	</p>
	{#if refusal.branch}
		<p>
			The activity branch <code class="break-all">{refusal.branch}</code> already exists with another
			owner or head. Hub did not overwrite it, and this request is closed.
		</p>
	{:else}
		<p class="break-words">{refusal.detail}</p>
	{/if}
	<p class="text-xs text-muted-foreground">
		{refusal.configuration
			? 'Correct the project configuration, then start again.'
			: 'Nothing was published for this request. Resolve the cause before starting again.'}
	</p>
	{#if branchHref || refusal.configuration}
		<div class="flex flex-wrap gap-2">
			{#if branchHref}<Button
					size="sm"
					variant="outline"
					href={branchHref}
					target="_blank"
					rel="noreferrer"
					><ExternalLink aria-hidden="true" />Inspect branch on GitHub<span class="sr-only">
						(opens in a new tab)</span
					></Button
				>{/if}
			{#if refusal.configuration}
				<Button size="sm" variant="outline" href={projectTabHref(projectId, 'connections')}
					>Open Connections</Button
				>
				<Button size="sm" variant="ghost" href={projectTabHref(projectId, 'settings')}
					>Open Settings</Button
				>
			{/if}
		</div>
	{/if}
</div>
