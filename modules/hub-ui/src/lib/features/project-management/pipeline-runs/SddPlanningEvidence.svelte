<script lang="ts">
	import SddReports from './SddReports.svelte';
	let { progress, evidenceUrl }: { progress: Record<string, unknown>; evidenceUrl: string | null } =
		$props();
	let proposal = $derived((progress.proposal || {}) as Record<string, unknown>);
	let gaps = $derived(Array.isArray(progress.review_gaps) ? progress.review_gaps : []);
</script>

<section class="space-y-3 rounded-xl border bg-card p-4" aria-label="Planning decision evidence">
	<h3 class="text-sm font-semibold">Planning decision evidence</h3>
	<p class="text-xs text-muted-foreground">
		Review the change summary, decisions, assumptions and remaining findings before accepting the
		direction.
	</p>
	<p class="text-sm">
		Recommended effort · Planning <strong
			>{String(proposal.planning_effort || 'unspecified')}</strong
		>
		· Development <strong>{String(proposal.dev_effort || 'unspecified')}</strong>
	</p>
	{#if gaps.length}
		<div class="space-y-2 rounded-lg border border-amber-500/30 p-3 text-sm" role="status">
			<p class="font-medium">Planning review gaps</p>
			{#each gaps as gap, index (index)}<p class="text-xs break-words">{String(gap)}</p>{/each}
			<p class="text-xs text-muted-foreground">
				Request changes if more evidence is needed. These gaps are review guidance.
			</p>
		</div>
	{/if}
	<SddReports reports={progress.reports} {evidenceUrl} />
	{#if !Array.isArray(progress.reports) || !progress.reports.length}<p
			class="text-xs text-muted-foreground"
		>
			No Planning reports have been recorded at this commit.
		</p>{/if}
</section>
