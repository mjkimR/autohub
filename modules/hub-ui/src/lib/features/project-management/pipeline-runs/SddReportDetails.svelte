<script lang="ts">
	let { report }: { report: Record<string, unknown> } = $props();
	let findings = $derived(
		Array.isArray(report.findings) ? (report.findings as Record<string, unknown>[]) : []
	);
	let notes = $derived([
		['Assumptions', report.assumptions],
		['Unverified areas', report.unverified_areas]
	] as const);
</script>

{#if findings.length}
	<ul class="mt-3 space-y-3" aria-label="Review findings">
		{#each findings as finding, index (index)}
			<li class="space-y-1 border-l-2 pl-3 text-xs">
				<p class="font-medium">
					{String(finding.severity || '')}
					{String(finding.issue || 'Finding')} · {String(finding.resolution || 'open')}
				</p>
				{#each ['evidence', 'failure_condition', 'suggested_action', 'waiver'] as field (field)}
					{#if finding[field]}<p class="break-words whitespace-pre-wrap text-muted-foreground">
							{field.replaceAll('_', ' ')}: {String(finding[field])}
						</p>{/if}
				{/each}
			</li>
		{/each}
	</ul>
{/if}
{#each notes as [label, values] (label)}
	{#if Array.isArray(values) && values.length}
		<div class="mt-3 text-xs">
			<p class="font-medium">{label}</p>
			<ul class="list-inside list-disc text-muted-foreground">
				{#each values as value, index (index)}<li class="break-words whitespace-pre-wrap">
						{String(value)}
					</li>{/each}
			</ul>
		</div>
	{/if}
{/each}
