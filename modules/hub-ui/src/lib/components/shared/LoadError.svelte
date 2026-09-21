<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	let { message, retry }: { message: string; retry: () => void } = $props();
</script>

<div
	role="alert"
	class="flex items-center justify-between gap-3 rounded-md border border-destructive/40 p-3 text-sm text-destructive"
>
	<span>{message}</span>
	<Button variant="outline" size="sm" onclick={retry}>Retry</Button>
</div>
