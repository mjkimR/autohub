<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { components } from '$lib/api';
	import { Badge } from '$lib/components/ui/badge';
	import { ChevronRight, CircleCheck, CirclePause, ExternalLink } from '@lucide/svelte';

	let {
		project,
		signals
	}: {
		project: components['schemas']['ProjectRead'];
		/**
		 * Project-level signals shown under the identity line. Reserved for the owed-item exception
		 * strip; nothing renders here until that contract exists.
		 */
		signals?: Snippet;
	} = $props();
</script>

<header class="space-y-3">
	<nav aria-label="Breadcrumb" class="text-sm text-muted-foreground">
		<ol class="flex flex-wrap items-center gap-1">
			<li><a href="/projects" class="hover:text-foreground">Projects</a></li>
			<li aria-hidden="true"><ChevronRight class="size-3.5" /></li>
			<li aria-current="page" class="font-medium text-foreground">{project.name}</li>
		</ol>
	</nav>
	<div class="flex flex-wrap items-center gap-x-3 gap-y-2">
		<h1 class="text-2xl font-semibold tracking-tight break-words sm:text-3xl">{project.name}</h1>
		{#if project.project_type === 'sdd'}<Badge variant="outline">SDD</Badge>{/if}
		{#if project.enabled}
			<Badge variant="secondary"><CircleCheck aria-hidden="true" />Active</Badge>
		{:else}
			<Badge variant="secondary"><CirclePause aria-hidden="true" />Disabled</Badge>
		{/if}
	</div>
	<p class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
		{#if project.github}
			<span class="font-mono">{project.github.repository}</span>
			<a
				class="inline-flex items-center gap-1 font-medium text-foreground underline-offset-4 hover:underline"
				href={`https://github.com/${project.github.repository}`}
				target="_blank"
				rel="noreferrer">Repository<ExternalLink aria-hidden="true" class="size-3.5" /></a
			>
		{:else}
			<span>No repository connected</span>
		{/if}
	</p>
	{@render signals?.()}
</header>
