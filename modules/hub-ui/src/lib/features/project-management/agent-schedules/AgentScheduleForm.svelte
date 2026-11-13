<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { Textarea } from '$lib/components/ui/textarea';
	import { displayLabel } from '$lib/labels';

	type AICatalog = components['schemas']['AICatalogRead'];
	type AgentSchedule = components['schemas']['AgentScheduleRead'];
	type AgentScheduleWrite = components['schemas']['AgentScheduleWrite'];
	type WorkType = AgentScheduleWrite['work_type'];

	let {
		projectId,
		catalogs,
		schedule,
		onsaved,
		oncancel
	}: {
		projectId: string;
		/** Catalogs that can run scheduled sessions. */
		catalogs: AICatalog[];
		/** The schedule to edit; null creates one. */
		schedule: AgentSchedule | null;
		onsaved: () => void;
		oncancel: () => void;
	} = $props();

	let saving = $state(false);
	let catalogId = $state('');
	let workType = $state<WorkType>('task');
	let title = $state('');
	let prompt = $state('');
	let startingBranch = $state('main');
	let enabled = $state(true);
	let triggerKind = $state<'cron' | 'interval'>('cron');
	let cronExpression = $state('0 9 * * 1');
	let intervalMinutes = $state('60');

	const selectedCatalog = $derived(catalogs.find((c) => c.id === catalogId) ?? null);
	const workTypes = $derived((selectedCatalog?.session_work_types ?? []) as WorkType[]);

	$effect(() => {
		// Keep the work type within what the chosen catalog supports.
		if (workTypes.length > 0 && !workTypes.includes(workType)) workType = workTypes[0];
	});

	onMount(() => {
		if (!schedule) {
			catalogId = catalogs[0]?.id ?? '';
			return;
		}
		catalogId = schedule.ai_catalog_id;
		workType = schedule.work_type as WorkType;
		title = schedule.title;
		prompt = schedule.prompt;
		startingBranch = schedule.starting_branch;
		enabled = schedule.enabled;
		triggerKind = schedule.cron_expression ? 'cron' : 'interval';
		cronExpression = schedule.cron_expression ?? '0 9 * * 1';
		intervalMinutes = String((schedule.interval_seconds ?? 3600) / 60);
	});

	async function save(event: SubmitEvent) {
		event.preventDefault();
		const body: AgentScheduleWrite = {
			ai_catalog_id: catalogId,
			work_type: workType,
			title: title.trim(),
			prompt: prompt.trim(),
			starting_branch: startingBranch.trim() || 'main',
			enabled,
			cron_expression: triggerKind === 'cron' ? cronExpression.trim() : null,
			interval_seconds: triggerKind === 'interval' ? Math.round(Number(intervalMinutes) * 60) : null
		};
		saving = true;
		try {
			const res = schedule
				? await api.PUT('/api/v1/projects/{project_id}/agent-schedules/{schedule_id}', {
						params: { path: { project_id: projectId, schedule_id: schedule.id } },
						body
					})
				: await api.POST('/api/v1/projects/{project_id}/agent-schedules', {
						params: { path: { project_id: projectId } },
						body
					});
			if (res.error) {
				toast.error(apiErrorMessage(res.error, 'Failed to save agent schedule'));
				return;
			}
			toast.success(schedule ? 'Agent schedule updated' : 'Agent schedule created');
			onsaved();
		} catch {
			toast.error('Failed to save agent schedule. Please retry.');
		} finally {
			saving = false;
		}
	}
</script>

<form
	onsubmit={save}
	aria-label={schedule ? `Edit ${schedule.title}` : 'New agent schedule'}
	class="space-y-3 rounded-lg border bg-muted/30 p-4"
>
	<div class="grid gap-3 sm:grid-cols-2">
		<div class="space-y-1.5">
			<label for="asCatalog" class="text-xs font-semibold text-muted-foreground uppercase"
				>AI Catalog</label
			>
			<NativeSelect id="asCatalog" bind:value={catalogId} required class="w-full">
				{#each catalogs as catalog (catalog.id)}
					<option value={catalog.id}>{catalog.name} ({catalog.kind})</option>
				{/each}
			</NativeSelect>
		</div>
		<div class="space-y-1.5">
			<label for="asWorkType" class="text-xs font-semibold text-muted-foreground uppercase"
				>Work type</label
			>
			<NativeSelect id="asWorkType" bind:value={workType} class="w-full">
				{#each workTypes as item (item)}
					<option value={item}>{displayLabel(item)}</option>
				{/each}
			</NativeSelect>
		</div>
	</div>
	<div class="space-y-1.5">
		<label for="asTitle" class="text-xs font-semibold text-muted-foreground uppercase">Title</label>
		<Input id="asTitle" bind:value={title} required maxlength={200} placeholder="Weekly hygiene" />
	</div>
	<div class="space-y-1.5">
		<label for="asPrompt" class="text-xs font-semibold text-muted-foreground uppercase"
			>Prompt</label
		>
		<Textarea
			id="asPrompt"
			bind:value={prompt}
			required
			rows={5}
			class="min-h-28"
			placeholder="What the agent should do each run. The delivery contract for the work type is appended by the hub."
		/>
	</div>
	<div class="grid gap-3 sm:grid-cols-3">
		<div class="space-y-1.5">
			<label for="asBranch" class="text-xs font-semibold text-muted-foreground uppercase"
				>Starting branch</label
			>
			<Input id="asBranch" bind:value={startingBranch} required maxlength={255} />
		</div>
		<div class="space-y-1.5">
			<label for="asTriggerKind" class="text-xs font-semibold text-muted-foreground uppercase"
				>Trigger</label
			>
			<NativeSelect id="asTriggerKind" bind:value={triggerKind} class="w-full">
				<option value="cron">Cron</option>
				<option value="interval">Interval</option>
			</NativeSelect>
		</div>
		{#if triggerKind === 'cron'}
			<div class="space-y-1.5">
				<label for="asCron" class="text-xs font-semibold text-muted-foreground uppercase"
					>Cron expression</label
				>
				<Input id="asCron" bind:value={cronExpression} required placeholder="0 9 * * 1" />
			</div>
		{:else}
			<div class="space-y-1.5">
				<label for="asInterval" class="text-xs font-semibold text-muted-foreground uppercase"
					>Every (minutes)</label
				>
				<Input
					id="asInterval"
					type="number"
					min="1"
					step="any"
					bind:value={intervalMinutes}
					required
				/>
			</div>
		{/if}
	</div>
	<label class="flex items-center justify-between gap-3 text-sm">
		<span class="font-medium text-foreground">Enabled</span>
		<input
			type="checkbox"
			bind:checked={enabled}
			class="size-4 rounded border-border text-primary focus:ring-primary"
		/>
	</label>
	<div class="flex justify-end gap-2">
		<Button type="button" variant="outline" size="sm" onclick={oncancel}>Cancel</Button>
		<Button type="submit" size="sm" disabled={saving || !catalogId}
			>{saving ? 'Saving…' : schedule ? 'Save changes' : 'Create schedule'}</Button
		>
	</div>
</form>
