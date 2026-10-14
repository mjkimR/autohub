<script lang="ts">
	let { reports, evidenceUrl }: { reports: unknown; evidenceUrl: string | null } = $props();
	const labels: Record<string, string> = {
		'final-report': 'Final report',
		review: 'Code review',
		reverify: 'Reverification'
	};
	let rows = $derived(
		Array.isArray(reports)
			? (reports.filter((r) => r && typeof r === 'object') as Record<string, unknown>[])
			: []
	);
</script>

{#if rows.length}
	<section class="space-y-3" aria-label="Review evidence summaries">
		{#each rows as report (String(report.file))}
			<details open={report.kind === 'final-report'} class="rounded-lg border p-3 text-sm">
				<summary class="cursor-pointer font-medium"
					>{labels[String(report.kind)] || String(report.kind)}
					<span class="ml-1 text-xs text-muted-foreground">{String(report.status)}</span></summary
				>
				<p class="mt-3 leading-relaxed break-words whitespace-pre-wrap">
					{String(report.summary || 'No summary recorded.')}
				</p>
				{#if report.checks && typeof report.checks === 'object'}<dl class="mt-3 space-y-2 text-xs">
						{#each Object.entries(report.checks) as [name, result] (name)}<div>
								<dt class="font-medium">{name}</dt>
								<dd class="break-words whitespace-pre-wrap text-muted-foreground">
									{String(result)}
								</dd>
							</div>{/each}
					</dl>{/if}
				{#if evidenceUrl && /^envelopes\/[a-z][a-z0-9-]*-\d{2}\.ya?ml$/.test(String(report.file))}<a
						class="mt-3 inline-block text-xs underline"
						href={`${evidenceUrl}/${report.file}`}
						target="_blank"
						rel="noreferrer">Read full evidence at this commit</a
					>{/if}
			</details>
		{/each}
		<p class="text-xs text-muted-foreground">
			Summaries come from the inspected commit. Open the full evidence for findings and details.
		</p>
	</section>
{/if}
