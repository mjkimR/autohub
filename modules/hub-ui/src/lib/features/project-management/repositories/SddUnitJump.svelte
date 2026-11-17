<script lang="ts">
	import { ArrowDown } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import { unitFromPath } from './sdd-unit';
	/** Narrow layouts place the unit panel after the document; this keeps it one step away. */
	let { path }: { path: string } = $props();
	let unit = $derived(unitFromPath(path));
	function jump() {
		const panel = document.getElementById('sdd-unit-panel');
		panel?.scrollIntoView?.({ block: 'start' });
		panel?.focus({ preventScroll: true });
	}
</script>

{#if unit}
	<Button class="xl:hidden" size="sm" variant="outline" onclick={jump}
		><ArrowDown aria-hidden="true" />Work on this unit</Button
	>
{/if}
