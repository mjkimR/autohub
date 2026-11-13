<script lang="ts">
	import { untrack } from 'svelte';
	import { api } from '$lib/api';
	import { responseData } from '$lib/api/pagination';
	import { Badge } from '$lib/components/ui/badge';
	import { CircleCheck, CircleX } from '@lucide/svelte';
	import { attentionHref } from '$lib/features/attention/owed-links';
	import { NEEDS_YOU_ANCHOR, owedChips, type OwedChip } from './owed-signals';

	let {
		projectId,
		refreshKey = ''
	}: {
		projectId: string;
		/** Any change reloads the counts once, e.g. a section change or a reloaded project. */
		refreshKey?: string;
	} = $props();

	let chips = $state<OwedChip[] | null>(null);
	let error = $state('');
	let sequence = 0;

	async function load() {
		const current = ++sequence;
		try {
			const counts = responseData(
				await api.GET('/api/v1/owed-items/counts', {
					params: { query: { project_id: projectId } }
				}),
				'Needs-you counts are unavailable'
			);
			if (current !== sequence) return;
			chips = owedChips(projectId, counts.by_kind ?? {});
			error = '';
		} catch (e) {
			if (current !== sequence) return;
			error = e instanceof Error ? e.message : 'Needs-you counts are unavailable';
		}
	}

	// One counts read per mount and per refresh key; no polling.
	$effect(() => {
		void refreshKey;
		untrack(() => void load());
	});

	const counted = $derived(chips?.filter((chip) => !chip.quiet) ?? []);
	const quiet = $derived(chips?.filter((chip) => chip.quiet) ?? []);
	const unknownLabel = $derived(`Needs-you counts unavailable: ${error}`);
</script>

<section
	id={NEEDS_YOU_ANCHOR}
	aria-labelledby="needs-you-label"
	class="flex scroll-mt-4 flex-wrap items-center gap-x-2 gap-y-1.5 text-sm"
	data-owed-state={error
		? 'error'
		: chips === null
			? 'loading'
			: chips.length
				? 'populated'
				: 'clear'}
>
	<h2 id="needs-you-label" class="text-xs font-medium text-muted-foreground">Needs you</h2>
	{#if error}
		<!-- An unknown count stays neutral so an outage never reads as operator debt. -->
		<span class="text-muted-foreground" title={unknownLabel} data-owed-unknown>
			<span aria-hidden="true">—</span><span class="sr-only">{unknownLabel}</span>
		</span>
	{:else if chips === null}
		<span role="status" class="text-muted-foreground">Checking…</span>
	{:else if chips.length === 0}
		<span class="inline-flex items-center gap-1 text-muted-foreground"
			><CircleCheck aria-hidden="true" class="size-3.5" />No exceptions</span
		>
	{:else}
		<ul class="contents">
			{#each counted as chip (chip.kind)}
				<li>
					<Badge
						variant="attention"
						class="tabular-nums"
						href={chip.href}
						data-owed-kind={chip.kind}
					>
						<span aria-hidden="true" class="size-1.5 rounded-full bg-attention-text"></span>
						{chip.label}
					</Badge>
				</li>
			{/each}
			{#each quiet as chip (chip.kind)}
				<li>
					<Badge variant="outline" class="tabular-nums" href={chip.href} data-owed-kind={chip.kind}>
						<CircleX aria-hidden="true" class="text-destructive" />
						{chip.label}
					</Badge>
				</li>
			{/each}
		</ul>
		{#if counted.length}
			<a
				class="text-xs font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
				href={attentionHref(projectId)}>View in Attention</a
			>
		{/if}
	{/if}
</section>
