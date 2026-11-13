<script lang="ts">
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { Input } from '$lib/components/ui/input';
	let { onchange }: { onchange: (value: string | undefined) => void } = $props();
	let mode = $state('all');
	let key = $state('');
	function change() {
		onchange(mode === 'all' ? undefined : mode === 'null' ? '' : key.trim() || undefined);
	}
</script>

<NativeSelect aria-label="Run group" bind:value={mode} onchange={change}>
	<option value="all">All groups</option>
	<option value="null">(null)</option>
	<option value="key">Specific group</option>
</NativeSelect>
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
