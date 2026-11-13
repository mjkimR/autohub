<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import OwedRow from './OwedRow.svelte';
	import { owedKindCount } from './owed-links';
	import type { OwedGroup } from './owed-kinds';

	let {
		group,
		total,
		projectName,
		now
	}: {
		group: OwedGroup;
		/** Every item of this kind the filters admit, when known; loaded rows can be fewer. */
		total: number | undefined;
		projectName: (id: string) => string | undefined;
		now: number;
	} = $props();

	const count = $derived(Math.max(total ?? 0, group.items.length));
	const partial = $derived(group.items.length < count);
	const headingId = $derived(`owed-${group.kind}`);
</script>

<section aria-labelledby={headingId} class="space-y-2" data-owed-group={group.kind}>
	<div class="flex flex-wrap items-baseline gap-x-2 gap-y-1">
		<h2
			id={headingId}
			class={[
				'text-sm font-semibold tracking-tight',
				group.quiet ? 'text-muted-foreground' : 'text-foreground'
			]}
		>
			{group.label}
		</h2>
		<!-- Attention marks the group once; a quiet kind carries no count weight. -->
		<Badge
			variant={group.quiet ? 'outline' : 'attention'}
			class="tabular-nums"
			data-owed-count={group.quiet ? 'quiet' : 'counted'}
		>
			{#if !group.quiet}<span aria-hidden="true" class="size-1.5 rounded-full bg-attention-text"
				></span>{/if}
			<span aria-hidden="true">{count}</span>
			<span class="sr-only">{owedKindCount(group.kind, count)}</span>
		</Badge>
		{#if partial}
			<span class="text-xs text-muted-foreground">{group.items.length} shown</span>
		{/if}
		{#if group.quiet}
			<span class="w-full text-xs text-muted-foreground sm:w-auto"
				>Not counted as owed. Inspect when convenient.</span
			>
		{/if}
	</div>
	<ul class="divide-y divide-border/70 rounded-xl border border-border bg-card">
		{#each group.items as item (item.key)}
			<OwedRow {item} projectName={projectName(item.subject.project_id)} {now} />
		{/each}
	</ul>
</section>
