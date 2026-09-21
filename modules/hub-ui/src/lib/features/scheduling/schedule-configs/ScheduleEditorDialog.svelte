<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogFooter
	} from '$lib/components/ui/dialog';
	import JsonSchemaForm from '$lib/components/shared/JsonSchemaForm.svelte';
	import { CalendarClock, Clock } from '@lucide/svelte';

	import { createScheduleDraft, scheduleBody, type ScheduleEditor } from './schedule-form';
	let {
		editor,
		taskSpecs,
		onclose,
		onsaved
	}: {
		editor: ScheduleEditor;
		taskSpecs: components['schemas']['TaskSpecResponse'][];
		onclose: () => void;
		onsaved: () => void;
	} = $props();
	let draft = $state(createScheduleDraft());
	let isSubmitting = $state(false);
	let selectedTaskSpec = $derived(taskSpecs.find((spec) => spec.name === draft.taskFunc));
	onMount(() => {
		draft = createScheduleDraft(editor.mode === 'edit' ? editor.config : undefined);
	});

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		if (!draft.name.trim() || !draft.taskFunc) {
			toast.error(
				editor.mode === 'edit' ? 'Schedule name is required' : 'Name and Task Function are required'
			);
			return;
		}
		isSubmitting = true;
		try {
			const body = scheduleBody(draft);
			const result =
				editor.mode === 'edit'
					? await api.PUT('/api/v1/schedule_configs/{schedule_config_id}', {
							params: { path: { schedule_config_id: editor.config.id } },
							body
						})
					: await api.POST('/api/v1/schedule_configs', { body });
			if (result.error) {
				toast.error(
					apiErrorMessage(
						result.error,
						editor.mode === 'edit' ? 'Failed to update schedule' : 'Failed to create schedule'
					)
				);
			} else {
				toast.success(`Schedule ${draft.name} ${editor.mode === 'edit' ? 'updated' : 'created'}!`);
				onclose();
				onsaved();
			}
		} catch {
			toast.error(
				editor.mode === 'edit'
					? 'Error updating schedule configuration'
					: 'Error creating schedule config'
			);
		} finally {
			isSubmitting = false;
		}
	}
</script>

<!-- Create Schedule Dialog -->
<Dialog
	open={true}
	onOpenChange={(open) => {
		if (!open) onclose();
	}}
>
	<DialogContent class="max-h-[90vh] overflow-y-auto sm:max-w-[560px]">
		<DialogHeader>
			<DialogTitle
				>{editor.mode === 'edit'
					? 'Edit Schedule Configuration'
					: 'Configure New Schedule'}</DialogTitle
			>
		</DialogHeader>

		<form onsubmit={handleSubmit} class="space-y-4 py-2">
			<!-- Name & Description -->
			<div class="space-y-2">
				<label
					for={editor.mode === 'edit' ? 'editScName' : 'scName'}
					class="text-xs font-semibold text-muted-foreground uppercase">Schedule Name</label
				>
				<Input
					id={editor.mode === 'edit' ? 'editScName' : 'scName'}
					placeholder="e.g. Daily Data Sync"
					bind:value={draft.name}
					required
				/>
			</div>

			<div class="space-y-2">
				<label
					for={editor.mode === 'edit' ? 'editScDesc' : 'scDesc'}
					class="text-xs font-semibold text-muted-foreground uppercase"
					>Description (optional)</label
				>
				<Input
					id={editor.mode === 'edit' ? 'editScDesc' : 'scDesc'}
					placeholder="Brief summary of what this schedule runs"
					bind:value={draft.description}
				/>
			</div>

			<!-- Task Target Selection -->
			<div class="space-y-2">
				<label
					for={editor.mode === 'edit' ? 'editScTask' : 'scTask'}
					class="text-xs font-semibold text-muted-foreground uppercase">Target Task</label
				>
				{#if editor.mode === 'edit'}
					<Input
						id="editScTask"
						value={draft.taskFunc}
						disabled
						class="bg-muted font-mono text-xs"
					/>
				{:else}
					<select
						id="scTask"
						class="w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-xs focus-visible:ring-1 focus-visible:ring-ring focus-visible:outline-none"
						bind:value={draft.taskFunc}
						required
					>
						<option value="" disabled selected>Select a task function to execute...</option>
						{#each taskSpecs as spec (spec.name)}
							<option value={spec.name}>{spec.name}</option>
						{/each}
					</select>
				{/if}
				{#if selectedTaskSpec?.description}
					<p class="text-[11px] text-muted-foreground italic">{selectedTaskSpec.description}</p>
				{/if}
			</div>

			<!-- Schedule Cadence Type Selection -->
			<div class="space-y-2">
				<span class="text-xs font-semibold text-muted-foreground uppercase">Execution Cadence</span>
				<div class="flex gap-2">
					<Button
						type="button"
						size="sm"
						variant={draft.scheduleType === 'cron' ? 'default' : 'outline'}
						onclick={() => (draft.scheduleType = 'cron')}
						class="flex-1 gap-1.5"
					>
						<CalendarClock class="size-3.5" />
						Cron Expression
					</Button>
					<Button
						type="button"
						size="sm"
						variant={draft.scheduleType === 'interval' ? 'default' : 'outline'}
						onclick={() => (draft.scheduleType = 'interval')}
						class="flex-1 gap-1.5"
					>
						<Clock class="size-3.5" />
						Interval Seconds
					</Button>
				</div>
			</div>

			{#if draft.scheduleType === 'cron'}
				<div class="space-y-1.5">
					<label
						for={editor.mode === 'edit' ? 'editScCron' : 'scCron'}
						class="text-xs font-semibold text-muted-foreground uppercase">Cron Expression</label
					>
					<Input
						id={editor.mode === 'edit' ? 'editScCron' : 'scCron'}
						placeholder="* * * * * (e.g. 0 9 * * 1-5)"
						bind:value={draft.cronExpression}
						class="font-mono text-xs"
						required
					/>
					<p class="text-[11px] text-muted-foreground">Standard 5-field cron syntax</p>
				</div>
			{:else}
				<div class="space-y-1.5">
					<label
						for={editor.mode === 'edit' ? 'editScInterval' : 'scInterval'}
						class="text-xs font-semibold text-muted-foreground uppercase">Interval (Seconds)</label
					>
					<Input
						id={editor.mode === 'edit' ? 'editScInterval' : 'scInterval'}
						type="number"
						min="1"
						bind:value={draft.intervalSeconds}
						class="font-mono text-xs"
						required
					/>
					<p class="text-[11px] text-muted-foreground">Repeats every N seconds</p>
				</div>
			{/if}

			<!-- Dynamic JSON Schema Form for Payload -->
			{#if editor.mode === 'create' ? draft.taskFunc : selectedTaskSpec?.payload_schema}
				<div class="pt-2">
					<JsonSchemaForm schema={selectedTaskSpec?.payload_schema} bind:value={draft.payload} />
				</div>
			{/if}

			{#if editor.mode === 'edit'}
				<!-- Enabled Toggle -->
				<div class="flex items-center justify-between rounded-lg border p-3">
					<div class="space-y-0.5">
						<div class="text-sm font-medium">Active Schedule</div>
						<div class="text-xs text-muted-foreground">
							Whether the dispatcher should execute this schedule
						</div>
					</div>
					<input
						type="checkbox"
						bind:checked={draft.enabled}
						class="size-4 rounded border-gray-300 text-primary focus:ring-primary"
					/>
				</div>
			{/if}
			<DialogFooter class="pt-4">
				<Button
					type="button"
					variant="outline"
					onclick={onclose}
					disabled={editor.mode === 'edit' && isSubmitting}>Cancel</Button
				>
				<Button type="submit" disabled={isSubmitting}>
					{isSubmitting ? 'Saving...' : editor.mode === 'edit' ? 'Save Changes' : 'Create Schedule'}
				</Button>
			</DialogFooter>
		</form>
	</DialogContent>
</Dialog>
