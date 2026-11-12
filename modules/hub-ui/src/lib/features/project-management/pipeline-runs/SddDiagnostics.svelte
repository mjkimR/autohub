<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	let { diagnostics, warnings }: { diagnostics?: unknown; warnings?: unknown } = $props();
	const record = (value: unknown): Record<string, unknown> =>
		value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
	let rows = $derived(
		Array.isArray(diagnostics)
			? diagnostics
					.map(record)
					.filter((row) => typeof row.code === 'string' && typeof row.message === 'string')
					.slice(0, 20)
			: []
	);
	let legacyWarnings = $derived(
		Array.isArray(warnings)
			? warnings
					.map(record)
					.filter((row) => !rows.some((item) => item.code === row.code))
					.slice(0, 20)
			: []
	);
	function category(value: unknown) {
		if (value === 'runtime') return 'Runtime setup';
		if (value === 'decision') return 'Operator decision';
		return 'Repository change';
	}
	function retry(value: unknown) {
		if (value === 'after_fix') return 'Reinspect after repair.';
		if (value === 'safe') return 'Reinspection is safe; it does not repeat a decision.';
		return 'No automatic retry is suggested.';
	}
</script>

{#if rows.length || legacyWarnings.length}
	<section class="space-y-3 text-sm" aria-label="Devkit diagnostics">
		<h4 class="font-semibold">Devkit diagnostics</h4>
		{#each rows as diagnostic, index (index)}
			<div
				class="space-y-2 rounded-lg border p-3"
				class:border-destructive={diagnostic.severity === 'error'}
			>
				<div class="flex flex-wrap items-center gap-2 text-xs">
					<Badge variant={diagnostic.severity === 'error' ? 'destructive' : 'outline'}>
						{diagnostic.severity === 'error'
							? 'Error'
							: diagnostic.severity === 'info'
								? 'Info'
								: 'Warning'}
					</Badge>
					<code class="break-all">{String(diagnostic.code)}</code>
					<span class="text-muted-foreground">{category(diagnostic.category)}</span>
				</div>
				<p class="break-words">{String(diagnostic.message)}</p>
				{#if diagnostic.action}<p class="break-words">
						<span class="font-medium">Next step:</span>
						{String(diagnostic.action)}
					</p>{/if}
				{#if Array.isArray(diagnostic.target_files) && diagnostic.target_files.length}
					<p class="text-xs break-all text-muted-foreground">
						Files: {diagnostic.target_files.map(String).join(', ')}
					</p>
				{/if}
				<p class="text-xs text-muted-foreground">{retry(diagnostic.retry)}</p>
			</div>
		{/each}
		{#each legacyWarnings as warning, index (index)}
			<p class="rounded-lg border p-3">
				{String(warning.detail || warning.code || 'Runtime warning')}
			</p>
		{/each}
	</section>
{/if}
