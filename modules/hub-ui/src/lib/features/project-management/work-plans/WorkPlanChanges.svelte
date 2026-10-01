<script lang="ts">
	let { changes }: { changes: Record<string, unknown> } = $props();
	const labels: Record<string, string> = {
		title: 'Title',
		description: 'Goal and scope',
		base_branch: 'Target branch',
		scheduled_at: 'Start no earlier than',
		depends_on: 'Plan dependencies',
		items: 'Tasks',
		state: 'Status'
	};
	function pair(value: unknown): { before?: unknown; after?: unknown } {
		return value && typeof value === 'object' ? value : {};
	}
	function text(value: unknown): string {
		if (value === null || value === undefined || value === '') return '—';
		if (Array.isArray(value)) return value.length ? value.map(text).join('\n\n') : 'None';
		if (typeof value === 'object') {
			const item = value as Record<string, unknown>;
			if ('key' in item)
				return `${item.key}: ${item.title || 'Untitled task'}\nSpecification: ${item.description || 'Not yet defined'}\nAcceptance: ${item.acceptance || 'Not yet defined'}\nDepends on: ${text(item.depends_on)}`;
			return JSON.stringify(value, null, 2);
		}
		return String(value);
	}
</script>

<details>
	<summary class="cursor-pointer"
		>Changes: {Object.keys(changes)
			.map((key) => labels[key] ?? key)
			.join(', ')}</summary
	>
	<div class="mt-3 space-y-4">
		{#each Object.entries(changes) as [key, value] (key)}
			<section class="space-y-2">
				<h4 class="font-medium">{labels[key] ?? key}</h4>
				<div class="grid gap-2 sm:grid-cols-2">
					<div class="min-w-0 rounded bg-muted p-3">
						<p class="mb-2 text-xs text-muted-foreground">Before</p>
						<p class="max-h-64 overflow-auto wrap-anywhere whitespace-pre-wrap">
							{text(pair(value).before)}
						</p>
					</div>
					<div class="min-w-0 rounded bg-muted p-3">
						<p class="mb-2 text-xs text-muted-foreground">After</p>
						<p class="max-h-64 overflow-auto wrap-anywhere whitespace-pre-wrap">
							{text(pair(value).after)}
						</p>
					</div>
				</div>
			</section>
		{/each}
	</div>
</details>
