<script lang="ts">
	import { untrack } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	type Plan = components['schemas']['WorkPlanRead'];
	type Item = components['schemas']['WorkItemWrite'];
	let {
		projectId,
		plans,
		editing,
		onsaved,
		oncancel
	}: {
		projectId: string;
		plans: Plan[];
		editing?: Plan;
		onsaved: () => void;
		oncancel: () => void;
	} = $props();
	const initial = untrack(() => editing);
	let title = $state(initial?.title ?? '');
	let description = $state(initial?.description ?? '');
	let baseBranch = $state(initial?.base_branch ?? 'main');
	let parents = $state<string[]>(initial?.depends_on ?? []);
	let items = $state<Item[]>(
		initial?.items.map((item) => ({
			key: item.key,
			title: item.title,
			description: item.description,
			acceptance: item.acceptance,
			depends_on: [...item.depends_on]
		})) ?? [{ key: 'task-1', title: '', description: '', acceptance: '', depends_on: [] }]
	);
	let saving = $state(false);
	let error = $state('');
	let bulkOpen = $state(false);
	let bulk = $state('');
	const textareaClass = 'min-h-24 w-full rounded-md border bg-background px-3 py-2 text-sm';
	function toggle(values: string[], value: string) {
		return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
	}
	function addItem() {
		let index = items.length + 1;
		while (items.some((item) => item.key === `task-${index}`)) index++;
		items = [
			...items,
			{ key: `task-${index}`, title: '', description: '', acceptance: '', depends_on: [] }
		];
	}
	function removeItem(key: string) {
		items = items
			.filter((item) => item.key !== key)
			.map((item) => ({ ...item, depends_on: item.depends_on?.filter((id) => id !== key) }));
	}
	function importItems() {
		try {
			const value: unknown = JSON.parse(bulk);
			if (
				!Array.isArray(value) ||
				value.length < 1 ||
				value.length > 100 ||
				value.some(
					(item) =>
						!item ||
						typeof item !== 'object' ||
						['key', 'title', 'description', 'acceptance'].some(
							(key) => typeof item[key] !== 'string'
						) ||
						(item.depends_on !== undefined &&
							(!Array.isArray(item.depends_on) ||
								item.depends_on.some((key: unknown) => typeof key !== 'string')))
				)
			)
				throw new Error(
					'Use an array of 1–100 tasks with key, title, description, acceptance, and optional depends_on.'
				);
			items = value.map((item) => ({
				key: item.key,
				title: item.title,
				description: item.description,
				acceptance: item.acceptance,
				depends_on: item.depends_on ?? []
			}));
			bulkOpen = false;
			error = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not import tasks';
		}
	}
	async function save() {
		saving = true;
		error = '';
		const body = { title, description, base_branch: baseBranch, depends_on: parents, items };
		try {
			const result = editing
				? await api.PUT('/api/v1/projects/{project_id}/work-plans/{plan_id}', {
						params: { path: { project_id: projectId, plan_id: editing.id } },
						body: { ...body, expected_revision: editing.revision }
					})
				: await api.POST('/api/v1/projects/{project_id}/work-plans', {
						params: { path: { project_id: projectId } },
						body
					});
			if (!result.data) throw new Error(apiErrorMessage(result.error, 'Could not save work plan'));
			onsaved();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not save work plan';
		} finally {
			saving = false;
		}
	}
</script>

<form
	class="space-y-6 rounded-xl border bg-card p-6"
	onsubmit={(event) => {
		event.preventDefault();
		void save();
	}}
>
	<h2 class="text-xl font-semibold">{editing ? 'Edit plan' : 'Add work plan'}</h2>
	<p class="text-sm text-muted-foreground">
		Adding a plan schedules eligible work immediately. PRs merge according to project policy.
		Dependencies wait for merged results.
	</p>
	{#if error}<p role="alert" class="text-sm text-destructive">{error}</p>{/if}
	<div class="grid gap-4 sm:grid-cols-2">
		<label class="space-y-2 text-sm"
			>Plan title<Input required maxlength={200} bind:value={title} /></label
		>
		<label class="space-y-2 text-sm">Target branch<Input required bind:value={baseBranch} /></label>
	</div>
	<label class="block space-y-2 text-sm"
		>Goal and scope<textarea class={textareaClass} bind:value={description}></textarea></label
	>
	{#if plans.some((plan) => plan.id !== editing?.id)}
		<fieldset class="space-y-2 rounded-lg border p-4">
			<legend class="px-1 text-sm font-medium">Wait for plans</legend>
			{#each plans.filter((plan) => plan.id !== editing?.id) as plan (plan.id)}
				<label class="flex items-center gap-2 text-sm"
					><input
						type="checkbox"
						checked={parents.includes(plan.id)}
						onchange={() => (parents = toggle(parents, plan.id))}
					/>{plan.title} <span class="text-muted-foreground">{plan.state}</span></label
				>
			{/each}
		</fieldset>
	{/if}
	<div class="flex items-center justify-between gap-3">
		<h3 class="font-semibold">Work items ({items.length}/100)</h3>
		{#if !editing}<Button type="button" variant="outline" onclick={() => (bulkOpen = !bulkOpen)}
				>Import task list</Button
			>{/if}
	</div>
	{#if bulkOpen}<div class="space-y-3 rounded-lg border p-4">
			<p class="text-sm text-muted-foreground">
				Paste a JSON array. Each task needs key, title, description, acceptance, and optional
				depends_on (task keys within this plan).
			</p>
			<label class="block text-sm"
				>Task list<textarea
					class={textareaClass + ' mt-2 font-mono'}
					bind:value={bulk}
					placeholder={'[{"key":"a","title":"Schema","description":"Create schema","acceptance":"Tests pass","depends_on":[]}]'}
				></textarea></label
			>
			<Button type="button" variant="outline" onclick={importItems}>Use task list</Button>
		</div>{/if}
	{#each items as item, index (index)}
		<fieldset class="space-y-4 rounded-lg border p-4">
			<legend class="px-1 text-sm font-medium">Task {index + 1}</legend>
			<div class="grid gap-4 sm:grid-cols-[10rem_1fr]">
				<label class="space-y-2 text-sm"
					>Key<Input required readonly={!!editing} bind:value={item.key} /></label
				>
				<label class="space-y-2 text-sm"
					>Title<Input required maxlength={200} bind:value={item.title} /></label
				>
			</div>
			<label class="block space-y-2 text-sm"
				>Specification<textarea required class={textareaClass} bind:value={item.description}
				></textarea></label
			>
			<label class="block space-y-2 text-sm"
				>Acceptance criteria<textarea required class={textareaClass} bind:value={item.acceptance}
				></textarea></label
			>
			{#if items.length > 1}<div class="space-y-2">
					<p class="text-sm font-medium">Wait for tasks in this plan</p>
					{#each items.filter((other) => other !== item) as other, parentIndex (parentIndex)}
						<label class="flex items-center gap-2 text-sm"
							><input
								type="checkbox"
								checked={item.depends_on?.includes(other.key)}
								onchange={() => (item.depends_on = toggle(item.depends_on ?? [], other.key))}
							/>{other.key}: {other.title || 'Untitled task'}</label
						>
					{/each}
				</div>{/if}
			{#if !editing && items.length > 1}<Button
					type="button"
					variant="ghost"
					onclick={() => removeItem(item.key)}>Remove task</Button
				>{/if}
		</fieldset>
	{/each}
	<div class="flex flex-wrap gap-3">
		{#if !editing}<Button
				type="button"
				variant="outline"
				disabled={items.length >= 100 || saving}
				onclick={addItem}>Add task</Button
			>{/if}
		<Button type="submit" disabled={saving}
			>{saving ? 'Saving…' : editing ? 'Save plan' : 'Add and start'}</Button
		>
		<Button type="button" variant="ghost" disabled={saving} onclick={oncancel}>Cancel</Button>
	</div>
</form>
