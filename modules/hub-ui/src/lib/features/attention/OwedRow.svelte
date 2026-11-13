<script lang="ts">
	import { ArrowRight, CirclePause } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import { catalogHoldText, waitingAge } from './owed-kinds';
	import { owedHref, type OwedItem } from './owed-links';

	let {
		item,
		projectName,
		now
	}: {
		item: OwedItem;
		/** Display name of the subject's project; the link still works without it. */
		projectName: string | undefined;
		/** Clock for the waiting age, shared by every row of one render. */
		now: number;
	} = $props();

	const href = $derived(owedHref(item));
	const projectHref = $derived(`/projects/${encodeURIComponent(item.subject.project_id)}`);
	const subject = $derived(item.subject.title?.trim() || null);
	const hold = $derived(item.context.catalog_hold ?? null);
</script>

<li
	class="flex flex-col gap-3 px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between sm:gap-6"
	data-owed-key={item.key}
>
	<div class="min-w-0 space-y-1">
		<p class="text-sm font-medium text-foreground">{item.cause}</p>
		<p class="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
			{#if subject}
				<span class="max-w-full truncate text-foreground/80" data-owed-subject>{subject}</span>
				<span aria-hidden="true">·</span>
			{/if}
			<a
				href={projectHref}
				class="font-medium text-foreground underline-offset-4 hover:underline"
				data-owed-project>{projectName ?? 'Open project'}</a
			>
			<span aria-hidden="true">·</span>
			<time datetime={item.waiting_since} title={new Date(item.waiting_since).toLocaleString()}
				>Waiting {waitingAge(item.waiting_since, now)}</time
			>
		</p>
		{#if hold}
			<p class="flex items-center gap-1.5 text-xs text-muted-foreground" data-catalog-hold>
				<CirclePause aria-hidden="true" class="size-3.5 shrink-0" />
				<span
					>{catalogHoldText(hold)} ·
					<a href="/settings/ai-catalogs" class="underline underline-offset-4 hover:text-foreground"
						>AI catalogs</a
					></span
				>
			</p>
		{/if}
	</div>
	<Button
		{href}
		variant="outline"
		class="shrink-0 self-start sm:self-center"
		data-owed-action={item.primary_action.name}
	>
		{item.primary_action.label}
		<span class="sr-only">: {subject ?? item.cause}</span>
		<ArrowRight aria-hidden="true" />
	</Button>
</li>
