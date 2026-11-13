<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { NativeSelect } from '$lib/components/ui/native-select';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogFooter,
		DialogDescription
	} from '$lib/components/ui/dialog';
	import { OBSERVATION_TASK, observedPulls } from './owned-schedules';

	type Project = components['schemas']['ProjectRead'];
	type ScheduleConfig = components['schemas']['ScheduleConfigRead'];
	let {
		project,
		schedule = null,
		onclose,
		onsaved
	}: {
		project: Project;
		/** The CI observation schedule to edit; omitted to create one. */
		schedule?: ScheduleConfig | null;
		onclose: () => void;
		onsaved?: () => void;
	} = $props();

	const presets = [
		{ seconds: '60', label: '1 min' },
		{ seconds: '300', label: '5 min' },
		{ seconds: '900', label: '15 min' },
		{ seconds: '3600', label: '1 h' }
	];
	let saving = $state(false);
	let name = $state('');
	let description = $state('');
	let pulls = $state('');
	let triggerType = $state<'interval' | 'cron'>('interval');
	let intervalSeconds = $state('300');
	let cronExpression = $state('*/5 * * * *');
	let enabled = $state(true);

	onMount(() => {
		if (schedule) {
			name = schedule.name;
			description = schedule.description ?? '';
			pulls = observedPulls(schedule).join(', ');
			triggerType = schedule.cron_expression ? 'cron' : 'interval';
			intervalSeconds = String(schedule.interval_seconds ?? 300);
			cronExpression = schedule.cron_expression ?? '*/5 * * * *';
			enabled = schedule.enabled;
		} else {
			name = `Observe ${project.name}`;
			description = `CI observation for ${project.name}`;
		}
	});

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		const numbers = pulls
			.split(',')
			.map((value) => Number.parseInt(value.trim(), 10))
			.filter((n) => !Number.isNaN(n) && n > 0);
		if (numbers.length === 0) {
			toast.error('Enter at least one pull request number');
			return;
		}
		const body = {
			name: name.trim(),
			description: description.trim() || null,
			task_func: OBSERVATION_TASK,
			cron_expression: triggerType === 'cron' ? cronExpression.trim() : null,
			interval_seconds: triggerType === 'interval' ? Number(intervalSeconds) : null,
			payload: { project_id: project.id, pull_numbers: numbers },
			enabled
		};
		saving = true;
		try {
			const res = schedule
				? await api.PUT('/api/v1/schedule_configs/{schedule_config_id}', {
						params: { path: { schedule_config_id: schedule.id } },
						body
					})
				: await api.POST('/api/v1/schedule_configs', { body });
			if (res.error) {
				toast.error(
					apiErrorMessage(
						res.error,
						schedule ? 'Could not save the schedule' : 'Could not create the schedule'
					)
				);
				return;
			}
			toast.success(schedule ? 'CI observation schedule saved' : 'CI observation schedule created');
			onsaved?.();
			onclose();
		} catch {
			toast.error('Request failed. Check your connection and retry.');
		} finally {
			saving = false;
		}
	}
</script>

<Dialog
	open={true}
	onOpenChange={(open) => {
		if (!open) onclose();
	}}
>
	<DialogContent class="sm:max-w-125">
		<DialogHeader>
			<DialogTitle>{schedule ? 'Edit CI observation' : 'New CI observation'}</DialogTitle>
			<DialogDescription>
				Polls GitHub Actions for the listed pull requests of {project.name} and records their latest CI
				status.
			</DialogDescription>
		</DialogHeader>

		<form onsubmit={submit} class="space-y-4">
			<div class="space-y-1.5">
				<label for="schedPulls" class="text-xs font-semibold text-muted-foreground uppercase">
					Pull request numbers
				</label>
				<Input id="schedPulls" placeholder="e.g. 1, 42, 105" bind:value={pulls} required />
				<p class="text-xs text-muted-foreground">Comma-separated; up to 10 open pull requests.</p>
			</div>
			<div class="space-y-1.5">
				<label for="schedName" class="text-xs font-semibold text-muted-foreground uppercase">
					Name
				</label>
				<Input id="schedName" bind:value={name} required />
			</div>
			<div class="space-y-1.5">
				<label for="schedDesc" class="text-xs font-semibold text-muted-foreground uppercase">
					Description (optional)
				</label>
				<Input id="schedDesc" bind:value={description} />
			</div>
			<div class="grid gap-3 sm:grid-cols-2">
				<div class="space-y-1.5">
					<label for="schedTrigger" class="text-xs font-semibold text-muted-foreground uppercase">
						Trigger
					</label>
					<NativeSelect id="schedTrigger" bind:value={triggerType} class="w-full">
						<option value="interval">Interval</option>
						<option value="cron">Cron (UTC)</option>
					</NativeSelect>
				</div>
				{#if triggerType === 'interval'}
					<div class="space-y-1.5">
						<label
							for="schedInterval"
							class="text-xs font-semibold text-muted-foreground uppercase"
						>
							Every (seconds)
						</label>
						<Input
							id="schedInterval"
							type="number"
							min="10"
							bind:value={intervalSeconds}
							class="font-mono"
						/>
					</div>
				{:else}
					<div class="space-y-1.5">
						<label for="schedCron" class="text-xs font-semibold text-muted-foreground uppercase">
							Cron expression
						</label>
						<Input
							id="schedCron"
							bind:value={cronExpression}
							placeholder="*/5 * * * *"
							class="font-mono"
							required
						/>
					</div>
				{/if}
			</div>
			{#if triggerType === 'interval'}
				<div class="flex flex-wrap gap-2" role="group" aria-label="Interval presets">
					{#each presets as preset (preset.seconds)}
						<Button
							type="button"
							size="sm"
							variant={intervalSeconds === preset.seconds ? 'default' : 'outline'}
							aria-pressed={intervalSeconds === preset.seconds}
							onclick={() => (intervalSeconds = preset.seconds)}>{preset.label}</Button
						>
					{/each}
				</div>
			{/if}
			<label class="flex items-center justify-between gap-3 text-sm">
				<span class="font-medium text-foreground">Enabled</span>
				<input
					type="checkbox"
					bind:checked={enabled}
					class="size-4 rounded border-border text-primary focus:ring-primary"
				/>
			</label>
			<DialogFooter>
				<Button type="button" variant="outline" onclick={onclose}>Cancel</Button>
				<Button type="submit" disabled={saving}>
					{saving ? 'Saving…' : schedule ? 'Save changes' : 'Create schedule'}
				</Button>
			</DialogFooter>
		</form>
	</DialogContent>
</Dialog>
