<script lang="ts">
	import { untrack } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	type Plan = components['schemas']['WorkPlanRead'];
	type Item = components['schemas']['WorkItemWrite'];
	type EditableItem = Item & {
		keyInput: string;
		keyError: string;
		keyElement: HTMLInputElement | null;
	};
	function editableItem(item: Item): EditableItem {
		return { ...item, keyInput: item.key, keyError: '', keyElement: null };
	}
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
	let mode = $state<components['schemas']['WorkPlanCreate']['state']>('draft');
	const flexible = !initial || ['draft', 'proposed'].includes(initial.state);
	let draft = $derived(initial ? flexible : mode === 'draft');
	let reason = $state('');
	let description = $state(initial?.description ?? '');
	let baseBranch = $state(initial?.base_branch ?? 'main');
	const localTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
	function localSchedule(value?: string | null) {
		if (!value) return '';
		const date = new Date(value);
		return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, -1);
	}
	const initialSchedule = localSchedule(initial?.scheduled_at);
	let scheduledAt = $state(initialSchedule);
	let parents = $state<string[]>(initial?.depends_on ?? []);
	let items = $state<EditableItem[]>(
		initial?.items.map((item) =>
			editableItem({
				key: item.key,
				title: item.title,
				description: item.description,
				acceptance: item.acceptance,
				depends_on: [...item.depends_on]
			})
		) ?? []
	);
	$effect(() => {
		for (const item of items) item.keyElement?.setCustomValidity(item.keyError);
	});
	let saving = $state(false);
	const registrationId = crypto.randomUUID();
	let error = $state('');
	let bulkOpen = $state(false);
	let bulk = $state('');
	const textareaClass = 'min-h-24 w-full rounded-md border bg-background px-3 py-2 text-sm';
	function toggle(values: string[], value: string) {
		return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
	}
	function addItem() {
		let index = items.length + 1;
		while (items.some((item) => item.key === `task-${index}` || item.keyInput === `task-${index}`))
			index++;
		items = [
			...items,
			editableItem({
				key: `task-${index}`,
				title: '',
				description: '',
				acceptance: '',
				depends_on: []
			})
		];
		reconcileKeys();
	}
	function removeItem(removed: EditableItem) {
		items = items.filter((item) => item !== removed);
		for (const item of items) {
			item.depends_on = item.depends_on?.filter((key) => key !== removed.key);
		}
		reconcileKeys();
	}
	function renameItem(item: EditableItem, key: string) {
		item.keyInput = key;
		reconcileKeys();
	}
	function reconcileKeys() {
		for (const item of items) {
			item.keyError = !/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,59}$/.test(item.keyInput)
				? 'Use 1–60 letters, digits, underscores or hyphens, starting with a letter or digit.'
				: items.some((other) => other !== item && other.keyInput === item.keyInput)
					? 'Each task needs a unique key.'
					: '';
		}
		if (items.some((item) => item.keyError)) return;
		// Commit the whole key set together so swaps cannot redirect dependency edges.
		const renamed = new Map(items.map((item) => [item.key, item.keyInput]));
		for (const item of items) {
			item.key = item.keyInput;
			item.depends_on = item.depends_on?.map((parent) => renamed.get(parent) ?? parent);
		}
	}
	function importItems() {
		try {
			const value: unknown = JSON.parse(bulk);
			if (
				!Array.isArray(value) ||
				(!draft && value.length < 1) ||
				value.length > 100 ||
				value.some(
					(item) =>
						!item ||
						typeof item !== 'object' ||
						(draft ? ['key'] : ['key', 'title', 'description', 'acceptance']).some(
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
			items = value.map((item) =>
				editableItem({
					key: item.key,
					title: item.title ?? '',
					description: item.description ?? '',
					acceptance: item.acceptance ?? '',
					depends_on: item.depends_on ?? []
				})
			);
			reconcileKeys();
			bulkOpen = false;
			error = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not import tasks';
		}
	}
	async function save() {
		saving = true;
		error = '';
		try {
			const body = {
				title,
				description,
				base_branch: baseBranch,
				scheduled_at: scheduledAt
					? scheduledAt === initialSchedule
						? initial!.scheduled_at
						: new Date(scheduledAt).toISOString()
					: null,
				depends_on: parents,
				items: items.map((item) => ({
					key: item.key,
					title: item.title,
					description: item.description,
					acceptance: item.acceptance,
					depends_on: item.depends_on
				}))
			};
			const result = editing
				? await api.PUT('/api/v1/projects/{project_id}/work-plans/{plan_id}', {
						params: { path: { project_id: projectId, plan_id: editing.id } },
						body: { ...body, expected_revision: editing.revision, reason }
					})
				: await api.POST('/api/v1/projects/{project_id}/work-plans', {
						params: { path: { project_id: projectId } },
						body: { ...body, state: mode, request_id: registrationId }
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
		Drafts can hold an idea without tasks. Proposals wait for a decision. Ready plans stay on hold.
		Only Start requests execution, respecting the start time and project merge policy. After a lost
		response, retry the same content to recover this plan.
	</p>
	{#if !editing}
		<label class="block space-y-2 text-sm"
			>Save as
			<select class="w-full rounded-md border bg-background p-2" bind:value={mode}>
				<option value="draft">Draft — refine later</option>
				<option value="proposed">Proposed — request a decision</option>
				<option value="paused">Ready — keep on hold</option>
				<option value="active">Start — request execution</option>
			</select>
		</label>
	{:else if editing.state === 'proposed'}
		<p class="text-sm text-muted-foreground">
			Saving changes returns this proposal to Draft for review.
		</p>
	{/if}
	{#if error}<p role="alert" class="text-sm text-destructive">{error}</p>{/if}
	<div class="grid gap-4 sm:grid-cols-2">
		<label class="space-y-2 text-sm"
			>Plan title<Input required maxlength={200} bind:value={title} /></label
		>
		<label class="space-y-2 text-sm">Target branch<Input required bind:value={baseBranch} /></label>
	</div>
	<div class="space-y-2 text-sm">
		<label class="block space-y-2">
			Start no earlier than
			<Input type="datetime-local" step="any" bind:value={scheduledAt} />
		</label>
		<p class="text-muted-foreground">
			Time zone: {localTimezone}. Leave blank to start when ready. Work starts on or after this
			time, subject to dependencies, capacity, and the scheduler interval.
		</p>
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
		{#if flexible}<Button type="button" variant="outline" onclick={() => (bulkOpen = !bulkOpen)}
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
	{#each items as item, index (item)}
		<fieldset class="space-y-4 rounded-lg border p-4">
			<legend class="px-1 text-sm font-medium">Task {index + 1}</legend>
			<div class="grid gap-4 sm:grid-cols-[10rem_1fr]">
				<label class="space-y-2 text-sm"
					>Key<Input
						required
						readonly={!flexible}
						bind:ref={item.keyElement}
						value={item.keyInput}
						oninput={(event) => renameItem(item, event.currentTarget.value)}
					/></label
				>
				<label class="space-y-2 text-sm"
					>Title<Input required={!draft} maxlength={200} bind:value={item.title} /></label
				>
			</div>
			<label class="block space-y-2 text-sm"
				>Specification<textarea
					required={!draft}
					class={textareaClass}
					bind:value={item.description}></textarea></label
			>
			<label class="block space-y-2 text-sm"
				>Acceptance criteria<textarea
					required={!draft}
					class={textareaClass}
					bind:value={item.acceptance}></textarea></label
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
			{#if flexible && (draft || items.length > 1)}<Button
					type="button"
					variant="ghost"
					onclick={() => removeItem(item)}>Remove task</Button
				>{/if}
		</fieldset>
	{/each}
	{#if editing}<label class="block space-y-2 text-sm"
			>Change reason (optional)
			<Input maxlength={4000} bind:value={reason} />
		</label>{/if}
	<div class="flex flex-wrap gap-3">
		{#if flexible}<Button
				type="button"
				variant="outline"
				disabled={items.length >= 100 || saving}
				onclick={addItem}>Add task</Button
			>{/if}
		<Button type="submit" disabled={saving}
			>{saving
				? 'Saving…'
				: editing
					? 'Save plan'
					: mode === 'draft'
						? 'Save draft'
						: mode === 'proposed'
							? 'Submit proposal'
							: mode === 'paused'
								? 'Save ready plan'
								: scheduledAt
									? 'Add and schedule'
									: 'Add and start'}</Button
		>
		<Button type="button" variant="ghost" disabled={saving} onclick={oncancel}>Cancel</Button>
	</div>
</form>
