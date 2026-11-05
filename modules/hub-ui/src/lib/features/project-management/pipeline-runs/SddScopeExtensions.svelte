<script lang="ts">
	let { extensions }: { extensions: unknown } = $props();
	let rows = $derived(
		Array.isArray(extensions)
			? extensions.filter((row): row is Record<string, unknown> => !!row && typeof row === 'object')
			: []
	);
</script>

{#if rows.length}
	<section class="mt-3 space-y-2 text-xs" aria-label="Worker scope extensions">
		<h4 class="font-medium">Additional files reported by the worker</h4>
		<p class="text-muted-foreground">
			Review the additional files, reasons and linked requirements before approving.
		</p>
		<ul class="space-y-3">
			{#each rows as extension, index (index)}
				<li class="space-y-1 border-l-2 pl-3">
					<p class="font-medium break-all"><code>{String(extension.path || '')}</code></p>
					<p class="text-muted-foreground">Task {String(extension.task ?? '')}</p>
					<p class="break-words whitespace-pre-wrap">{String(extension.reason || '')}</p>
					{#if Array.isArray(extension.requirements)}
						<p class="break-words text-muted-foreground">
							Requirements: {extension.requirements.map(String).join(', ')}
						</p>
					{/if}
				</li>
			{/each}
		</ul>
	</section>
{/if}
