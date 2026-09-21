<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogFooter,
		DialogDescription
	} from '$lib/components/ui/dialog';
	import { Activity, Sparkles, CalendarClock } from '@lucide/svelte';

	type Project = components['schemas']['ProjectRead'];
	let { project: schedulingProject, onclose }: { project: Project; onclose: () => void } = $props();
	let isScheduling = $state(false);
	let scheduleName = $state('');
	let scheduleDescription = $state('');
	let scheduleTaskType = $state<'pipeline.dispatch_project' | 'pipeline.observe_project'>(
		'pipeline.dispatch_project'
	);
	let scheduleObservationPulls = $state('1');
	let scheduleTriggerType = $state<'interval' | 'cron'>('interval');
	let scheduleIntervalSeconds = $state('300');
	let scheduleCronExpression = $state('*/5 * * * *');
	onMount(() => {
		scheduleName = `Dispatch ${schedulingProject.name}`;
		scheduleDescription = `Automated run dispatcher & progress tracker for ${schedulingProject.name}`;
		scheduleTaskType = 'pipeline.dispatch_project';
		scheduleObservationPulls = '1';
		scheduleTriggerType = 'interval';
		scheduleIntervalSeconds = '300';
		scheduleCronExpression = '*/5 * * * *';
	});

	function onTaskTypeChange(type: 'pipeline.dispatch_project' | 'pipeline.observe_project') {
		scheduleTaskType = type;
		if (schedulingProject) {
			if (type === 'pipeline.dispatch_project') {
				scheduleName = `Dispatch ${schedulingProject.name}`;
				scheduleDescription = `Automated run dispatcher & progress tracker for ${schedulingProject.name}`;
			} else {
				scheduleName = `Observe ${schedulingProject.name}`;
				scheduleDescription = `CI observation for ${schedulingProject.name}`;
			}
		}
	}

	async function handleCreateQuickSchedule(e: SubmitEvent) {
		e.preventDefault();
		if (!schedulingProject) return;

		let payload: Record<string, unknown> = {
			project_id: schedulingProject.id
		};

		if (scheduleTaskType === 'pipeline.observe_project') {
			const pulls = scheduleObservationPulls
				.split(',')
				.map((p) => parseInt(p.trim(), 10))
				.filter((n) => !isNaN(n) && n > 0);

			if (pulls.length === 0) {
				toast.error('Please specify at least one valid pull request number');
				return;
			}
			payload = {
				project_id: schedulingProject.id,
				pull_numbers: pulls
			};
		}

		isScheduling = true;
		try {
			const res = await api.POST('/api/v1/schedule_configs', {
				body: {
					name: scheduleName.trim(),
					description: scheduleDescription.trim() || null,
					task_func: scheduleTaskType,
					cron_expression: scheduleTriggerType === 'cron' ? scheduleCronExpression.trim() : null,
					interval_seconds:
						scheduleTriggerType === 'interval' ? Number(scheduleIntervalSeconds) : null,
					payload,
					enabled: true
				}
			});

			if (res.error) {
				toast.error('Failed to create schedule');
			} else {
				toast.success(`Schedule created for ${schedulingProject.name}!`);
				onclose();
			}
		} catch {
			toast.error('Error creating schedule');
		} finally {
			isScheduling = false;
		}
	}
</script>

<!-- Quick Schedule Dialog -->
<Dialog
	open={true}
	onOpenChange={(open) => {
		if (!open) onclose();
	}}
>
	<DialogContent class="sm:max-w-[500px]">
		<DialogHeader>
			<div class="flex items-center gap-2">
				<div
					class="flex size-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-500"
				>
					<CalendarClock class="size-4" />
				</div>
				<div>
					<DialogTitle>Create Scheduled Automation</DialogTitle>
					<DialogDescription>
						Automate background execution for <span class="font-semibold text-foreground"
							>{schedulingProject?.name}</span
						>
					</DialogDescription>
				</div>
			</div>
		</DialogHeader>

		<form onsubmit={handleCreateQuickSchedule} class="space-y-4 py-2">
			<!-- Task Selection -->
			<div class="space-y-2">
				<span class="text-xs font-semibold text-muted-foreground uppercase">Automation Task</span>
				<div class="grid grid-cols-2 gap-2">
					<button
						type="button"
						onclick={() => onTaskTypeChange('pipeline.dispatch_project')}
						class="flex flex-col items-start gap-1 rounded-lg border p-3 text-left transition-all {scheduleTaskType ===
						'pipeline.dispatch_project'
							? 'border-primary bg-primary/5 ring-1 ring-primary'
							: 'border-border hover:bg-muted/50'}"
					>
						<div class="flex items-center gap-1.5 text-xs font-semibold text-foreground">
							<Sparkles class="size-3.5 text-primary" />
							Auto-Dispatch
						</div>
						<p class="text-[11px] leading-snug text-muted-foreground">
							Picks actionable tasks, creates runs & progresses CI automatically.
						</p>
					</button>

					<button
						type="button"
						onclick={() => onTaskTypeChange('pipeline.observe_project')}
						class="flex flex-col items-start gap-1 rounded-lg border p-3 text-left transition-all {scheduleTaskType ===
						'pipeline.observe_project'
							? 'border-primary bg-primary/5 ring-1 ring-primary'
							: 'border-border hover:bg-muted/50'}"
					>
						<div class="flex items-center gap-1.5 text-xs font-semibold text-foreground">
							<Activity class="size-3.5 text-primary" />
							Observe CI
						</div>
						<p class="text-[11px] leading-snug text-muted-foreground">
							Polls GitHub Actions jobs for specified PRs and records latest status.
						</p>
					</button>
				</div>
			</div>

			<!-- PR numbers if observe -->
			{#if scheduleTaskType === 'pipeline.observe_project'}
				<div class="space-y-1.5 rounded-lg border border-border/80 bg-muted/20 p-3">
					<label for="schedPulls" class="text-xs font-semibold text-muted-foreground uppercase">
						Pull Request Numbers (comma-separated)
					</label>
					<Input
						id="schedPulls"
						placeholder="e.g. 1, 42, 105"
						bind:value={scheduleObservationPulls}
						required
					/>
					<p class="text-[11px] text-muted-foreground">
						Specify up to 10 active PR numbers to track.
					</p>
				</div>
			{/if}

			<!-- Basic Config -->
			<div class="space-y-3">
				<div class="space-y-1.5">
					<label for="schedName" class="text-xs font-semibold text-muted-foreground uppercase">
						Schedule Name
					</label>
					<Input id="schedName" bind:value={scheduleName} required />
				</div>

				<div class="space-y-1.5">
					<label for="schedDesc" class="text-xs font-semibold text-muted-foreground uppercase">
						Description (optional)
					</label>
					<Input id="schedDesc" bind:value={scheduleDescription} />
				</div>
			</div>

			<!-- Trigger Cadence -->
			<div class="space-y-2">
				<div class="flex items-center justify-between">
					<span class="text-xs font-semibold text-muted-foreground uppercase">Cadence</span>
					<div class="flex rounded-md border border-border bg-muted/50 p-0.5">
						<button
							type="button"
							class="rounded px-2 py-0.5 text-xs font-medium transition-colors {scheduleTriggerType ===
							'interval'
								? 'bg-background text-foreground shadow-xs'
								: 'text-muted-foreground hover:text-foreground'}"
							onclick={() => (scheduleTriggerType = 'interval')}
						>
							Interval
						</button>
						<button
							type="button"
							class="rounded px-2 py-0.5 text-xs font-medium transition-colors {scheduleTriggerType ===
							'cron'
								? 'bg-background text-foreground shadow-xs'
								: 'text-muted-foreground hover:text-foreground'}"
							onclick={() => (scheduleTriggerType = 'cron')}
						>
							Cron
						</button>
					</div>
				</div>

				{#if scheduleTriggerType === 'interval'}
					<div class="space-y-2">
						<div class="flex gap-2">
							<Button
								type="button"
								size="sm"
								variant={scheduleIntervalSeconds === '60' ? 'default' : 'outline'}
								class="flex-1 text-xs"
								onclick={() => (scheduleIntervalSeconds = '60')}
							>
								1m
							</Button>
							<Button
								type="button"
								size="sm"
								variant={scheduleIntervalSeconds === '300' ? 'default' : 'outline'}
								class="flex-1 text-xs"
								onclick={() => (scheduleIntervalSeconds = '300')}
							>
								5m
							</Button>
							<Button
								type="button"
								size="sm"
								variant={scheduleIntervalSeconds === '900' ? 'default' : 'outline'}
								class="flex-1 text-xs"
								onclick={() => (scheduleIntervalSeconds = '900')}
							>
								15m
							</Button>
							<Button
								type="button"
								size="sm"
								variant={scheduleIntervalSeconds === '3600' ? 'default' : 'outline'}
								class="flex-1 text-xs"
								onclick={() => (scheduleIntervalSeconds = '3600')}
							>
								1h
							</Button>
						</div>
						<div class="flex items-center gap-2">
							<Input
								type="number"
								min="10"
								bind:value={scheduleIntervalSeconds}
								placeholder="Custom seconds"
								class="font-mono text-sm"
							/>
							<span class="text-xs whitespace-nowrap text-muted-foreground">seconds</span>
						</div>
					</div>
				{:else}
					<div class="space-y-1">
						<Input
							bind:value={scheduleCronExpression}
							placeholder="*/5 * * * *"
							class="font-mono text-sm"
							required
						/>
						<p class="text-[11px] text-muted-foreground">Standard 5-field cron syntax (UTC).</p>
					</div>
				{/if}
			</div>

			<DialogFooter class="pt-2">
				<Button type="button" variant="outline" onclick={onclose}>Cancel</Button>
				<Button type="submit" disabled={isScheduling}>
					{isScheduling ? 'Creating...' : 'Create Schedule'}
				</Button>
			</DialogFooter>
		</form>
	</DialogContent>
</Dialog>
