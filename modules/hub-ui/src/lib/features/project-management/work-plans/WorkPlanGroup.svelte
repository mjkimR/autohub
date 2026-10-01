<script lang="ts">
	import { untrack } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	let {
		plan,
		onsaved,
		onclose
	}: {
		plan: components['schemas']['WorkPlanRead'];
		onsaved: () => void;
		onclose: () => void;
	} = $props();
	const initial = untrack(() => plan);
	let value = $state(initial.group_key ?? '');
	let saving = $state(false);
	let error = $state('');
	async function save() {
		saving = true;
		error = '';
		try {
			const result = await api.PATCH('/api/v1/projects/{project_id}/work-plans/{plan_id}/group', {
				params: { path: { project_id: plan.project_id, plan_id: plan.id } },
				body: { group_key: value.trim() || null, expected_revision: plan.revision, reason: '' }
			});
			if (!result.data) throw new Error(apiErrorMessage(result.error, 'Could not change group'));
			onsaved();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not change group';
		} finally {
			saving = false;
		}
	}
</script>

<form
	class="space-y-3 rounded-lg border p-4"
	onsubmit={(event) => {
		event.preventDefault();
		void save();
	}}
>
	<h3 class="font-medium">Change group: {plan.title}</h3>
	<p class="text-sm text-muted-foreground">
		Current saved group: {plan.group_key == null ? '(null)' : JSON.stringify(plan.group_key)}
	</p>
	{#if plan.revision !== initial.revision}
		<p role="status" class="text-sm text-muted-foreground">
			The plan has changed. Your input is preserved; review the current saved group before saving.
		</p>
	{/if}
	<label class="block space-y-2 text-sm"
		>Group key<Input maxlength={100} placeholder="(null)" disabled={saving} bind:value /></label
	>
	<p class="text-sm text-muted-foreground">
		Leave blank for (null). Changing the group only updates classification.
	</p>
	{#if error}<p role="alert" class="text-sm text-destructive">{error}</p>{/if}
	<div class="flex gap-2">
		<Button type="submit" disabled={saving}>Save group</Button>
		<Button type="button" variant="outline" disabled={saving} onclick={onclose}>Cancel</Button>
	</div>
</form>
