<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	let { onchange }: { onchange: (value: string | undefined) => void } = $props();
	let mode = $state('all');
	let key = $state('');
	function change() {
		onchange(mode === 'all' ? undefined : mode === 'null' ? '' : key.trim() || undefined);
	}
</script>

<select
	aria-label="Run group"
	bind:value={mode}
	onchange={change}
	class="h-11 rounded-md border border-input bg-background px-3 py-2 text-sm"
>
	<option value="all">All groups</option>
	<option value="null">(null)</option>
	<option value="key">Specific group</option>
</select>
{#if mode === 'key'}
	<Input
		aria-label="Run group key"
		placeholder="Enter exact group key"
		maxlength={100}
		bind:value={key}
		oninput={change}
		class="w-48"
	/>
{/if}
