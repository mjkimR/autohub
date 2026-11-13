<script lang="ts">
	import { untrack } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import { Textarea } from '$lib/components/ui/textarea';
	import { Input } from '$lib/components/ui/input';
	import type { components } from '$lib/api';
	import type { Template } from './template-intent.svelte';
	let {
		template,
		disabled,
		save,
		cancel
	}: {
		template?: Template;
		disabled: boolean;
		save: (name: string, definition: components['schemas']['TemplateDefinition']) => void;
		cancel: () => void;
	} = $props();
	const initial = untrack(() => template);
	let name = $state(initial?.name ?? '');
	let title = $state(initial?.definition.title ?? '');
	let description = $state(initial?.definition.description ?? '');
	let branch = $state(initial?.definition.base_branch ?? 'main');
	let items = $state(
		JSON.stringify(
			initial?.definition.items ?? [
				{ key: 'task', title: '', description: '', acceptance: '', depends_on: [] }
			],
			null,
			2
		)
	);
	let error = $state('');
	function submit() {
		try {
			const parsed: unknown = JSON.parse(items);
			if (!Array.isArray(parsed)) throw new Error('Tasks must be an array');
			save(name, { title, description, base_branch: branch, items: parsed });
			error = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Invalid task definition';
		}
	}
</script>

<form
	class="space-y-3 rounded-lg border p-4"
	onsubmit={(e) => {
		e.preventDefault();
		submit();
	}}
>
	<h3>{initial ? 'Edit template' : 'New template'}</h3>
	{#if initial}<p>Template {initial.id} · expected revision {initial.revision}</p>{/if}
	<label class="block space-y-1"
		>Template name<Input required maxlength={200} bind:value={name} /></label
	>
	<label class="block space-y-1"
		>Default Plan title<Input required maxlength={200} bind:value={title} /></label
	>
	<label class="block space-y-1"
		>Candidate target branch<Input required bind:value={branch} /></label
	>
	<label class="block space-y-1">Goal and scope<Textarea bind:value={description} /></label>
	<label class="block space-y-1"
		>Local tasks (JSON: key, title, description, acceptance, depends_on)<Textarea
			class="min-h-48 font-mono"
			bind:value={items}
		/></label
	>
	<p class="text-sm text-muted-foreground">
		Only specification and local task dependencies are saved. Attachments, execution/approval
		history, PR/Issue identities, schedule, group and external Plan dependencies are excluded.
		Saving starts no work.
	</p>
	{#if error}<p role="alert">{error}</p>{/if}
	<Button type="submit" {disabled}>Save definition</Button><Button
		type="button"
		variant="ghost"
		onclick={cancel}>Cancel editor</Button
	>
</form>
