<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	let {
		offset,
		limit,
		total,
		loading,
		onpage
	}: {
		offset: number;
		limit: number;
		total: number;
		loading: boolean;
		onpage: (offset: number) => void;
	} = $props();
</script>

<nav aria-label="List pagination" class="flex flex-wrap items-center justify-between gap-3 text-sm">
	<span aria-live="polite"
		>{total === 0 ? 0 : offset + 1}–{Math.min(offset + limit, total)} of {total}</span
	>
	<div class="flex flex-wrap gap-2 [&_button]:min-h-11 sm:[&_button]:min-h-0">
		<Button
			variant="outline"
			disabled={loading || offset === 0}
			onclick={() => onpage(Math.max(0, offset - limit))}>Previous page</Button
		>
		<Button
			variant="outline"
			disabled={loading || offset + limit >= total}
			onclick={() => onpage(offset + limit)}>Next page</Button
		>
	</div>
</nav>
