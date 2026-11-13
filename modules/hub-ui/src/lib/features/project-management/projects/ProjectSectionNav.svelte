<script lang="ts">
	import { projectTabGroups, projectTabHref, type ProjectTab } from './project-tabs';

	let { projectId, tab }: { projectId: string; tab: ProjectTab } = $props();
	let current = $state<HTMLAnchorElement | null>(null);

	// If a group row is narrower than its tabs it scrolls; keep the selected section in view.
	$effect(() => {
		current?.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
	});
</script>

<!-- Narrow screens stack the Work and Setup rows; wider screens set them side by side. -->
<nav aria-label="Project sections" class="flex flex-col sm:flex-row sm:border-b">
	{#each projectTabGroups as group, index (group.id)}
		{#if index > 0}
			<span aria-hidden="true" class="mx-3 my-3 hidden w-px shrink-0 bg-border sm:block"></span>
		{/if}
		<div
			role="group"
			aria-labelledby={`project-tab-group-${group.id}`}
			class="flex min-w-0 items-stretch overflow-x-auto border-b sm:shrink-0 sm:border-b-0"
		>
			<span
				id={`project-tab-group-${group.id}`}
				class="flex w-12 shrink-0 items-center text-xs font-medium text-muted-foreground sm:w-auto sm:pr-1"
				>{group.label}</span
			>
			{#each group.tabs as item (item.id)}
				{#if tab === item.id}
					<a
						bind:this={current}
						href={projectTabHref(projectId, item.id)}
						aria-current="page"
						class="shrink-0 border-b-2 border-primary px-2.5 py-3 text-sm font-medium text-foreground sm:px-3"
						>{item.label}</a
					>
				{:else}
					<a
						href={projectTabHref(projectId, item.id)}
						class="shrink-0 border-b-2 border-transparent px-2.5 py-3 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground sm:px-3"
						>{item.label}</a
					>
				{/if}
			{/each}
		</div>
	{/each}
</nav>
