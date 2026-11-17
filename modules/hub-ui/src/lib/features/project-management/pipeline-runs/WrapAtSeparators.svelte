<script lang="ts">
	/**
	 * Paths, branches and IDs wrap only after a separator (`/`, `-`, `_`, `.`), so a narrow column
	 * never splits a token mid-word. Pair it with `break-words` for a final fallback.
	 */
	let { text }: { text: string } = $props();
	let parts = $derived(text.split(/(?<=[/_.-])/));
</script>

{#each parts as part, index (index)}{part}{#if index < parts.length - 1}<wbr />{/if}{/each}
