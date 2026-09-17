<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { toast } from 'svelte-sonner';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import {
		Dialog,
		DialogContent,
		DialogDescription,
		DialogFooter,
		DialogHeader,
		DialogTitle
	} from '$lib/components/ui/dialog';

	type Project = components['schemas']['ProjectRead'];
	type AICatalog = components['schemas']['AICatalogRead'];
	type AgentSchedule = components['schemas']['AgentScheduleRead'];
	type AgentScheduleWrite = components['schemas']['AgentScheduleWrite'];
	type WorkType = AgentScheduleWrite['work_type'];

	let {
		project,
		catalogs,
		onclose
	}: { project: Project; catalogs: AICatalog[]; onclose: () => void } = $props();

	let open = $state(true);
	let loading = $state(true);
	let saving = $state(false);
	let schedules = $state<AgentSchedule[]>([]);
	let editing = $state<AgentSchedule | null>(null);
	let formOpen = $state(false);

	// Form state
	let catalogId = $state('');
	let workType = $state<WorkType>('task');
	let title = $state('');
	let prompt = $state('');
	let startingBranch = $state('main');
	let enabled = $state(true);
	let triggerKind = $state<'cron' | 'interval'>('cron');
	let cronExpression = $state('0 9 * * 1');
	let intervalMinutes = $state('60');

	/** Catalogs whose sessions the hub can schedule; a catalog lists the work types it supports. */
	const sessionCatalogs = $derived(catalogs.filter((c) => (c.session_work_types ?? []).length > 0));
	const selectedCatalog = $derived(sessionCatalogs.find((c) => c.id === catalogId) ?? null);
	const workTypes = $derived((selectedCatalog?.session_work_types ?? []) as WorkType[]);

	$effect(() => {
		if (!open) onclose();
	});

	$effect(() => {
		// Keep the work type within what the chosen catalog supports.
		if (workTypes.length > 0 && !workTypes.includes(workType)) workType = workTypes[0];
	});

	/** The hub's error detail: a message, or a list of field errors for a request that failed validation. */
	function detail(error: unknown, fallback: string): string {
		const value = (error as { detail?: unknown } | undefined)?.detail;
		if (typeof value === 'string') return value;
		if (Array.isArray(value)) {
			const messages = value
				.map((item) => (item as { msg?: string })?.msg)
				.filter((msg): msg is string => typeof msg === 'string');
			if (messages.length > 0) return messages.join('; ');
		}
		return fallback;
	}

	async function load() {
		loading = true;
		try {
			const res = await api.GET('/api/v1/projects/{project_id}/agent-schedules', {
				params: { path: { project_id: project.id } }
			});
			if (res.error) toast.error(detail(res.error, 'Failed to load agent schedules'));
			schedules = res.data?.items ?? [];
		} catch {
			toast.error('Failed to load agent schedules');
		} finally {
			loading = false;
		}
	}

	function startCreate() {
		editing = null;
		catalogId = sessionCatalogs[0]?.id ?? '';
		workType = 'task';
		title = '';
		prompt = '';
		startingBranch = 'main';
		enabled = true;
		triggerKind = 'cron';
		cronExpression = '0 9 * * 1';
		intervalMinutes = '60';
		formOpen = true;
	}

	function startEdit(schedule: AgentSchedule) {
		editing = schedule;
		catalogId = schedule.ai_catalog_id;
		workType = schedule.work_type as WorkType;
		title = schedule.title;
		prompt = schedule.prompt;
		startingBranch = schedule.starting_branch;
		enabled = schedule.enabled;
		triggerKind = schedule.cron_expression ? 'cron' : 'interval';
		cronExpression = schedule.cron_expression ?? '0 9 * * 1';
		intervalMinutes = String((schedule.interval_seconds ?? 3600) / 60);
		formOpen = true;
	}

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
			const res = editing
				? await api.PUT('/api/v1/projects/{project_id}/agent-schedules/{schedule_id}', {
						params: { path: { project_id: project.id, schedule_id: editing.id } },
						body
					})
				: await api.POST('/api/v1/projects/{project_id}/agent-schedules', {
						params: { path: { project_id: project.id } },
						body
					});
			if (res.error) {
				toast.error(detail(res.error, 'Failed to save agent schedule'));
				return;
			}
			toast.success(editing ? 'Agent schedule updated' : 'Agent schedule created');
			formOpen = false;
			await load();
		} finally {
			saving = false;
		}
	}

	async function remove(schedule: AgentSchedule) {
		if (!confirm(`Delete "${schedule.title}"? Its scheduler entry is removed with it.`)) return;
		const res = await api.DELETE('/api/v1/projects/{project_id}/agent-schedules/{schedule_id}', {
			params: { path: { project_id: project.id, schedule_id: schedule.id } }
		});
		if (res.error) {
			toast.error(detail(res.error, 'Failed to delete agent schedule'));
			return;
		}
		toast.success('Agent schedule deleted');
		await load();
	}

	async function runNow(schedule: AgentSchedule) {
		const res = await api.POST(
			'/api/v1/projects/{project_id}/agent-schedules/{schedule_id}/run-now',
			{
				params: { path: { project_id: project.id, schedule_id: schedule.id } }
			}
		);
		if (res.error) {
			toast.error(detail(res.error, 'Failed to queue the agent schedule'));
			return;
		}
		toast.success('Queued for the next dispatcher tick');
		await load();
	}

	function trigger(schedule: AgentSchedule): string {
		if (schedule.cron_expression) return `cron ${schedule.cron_expression}`;
		const minutes = (schedule.interval_seconds ?? 0) / 60;
		return `every ${Number.isInteger(minutes) ? minutes : minutes.toFixed(1)} min`;
	}

	function when(value: string | null | undefined, fallback: string): string {
		return value ? new Date(value).toLocaleString() : fallback;
	}

	/** An entry without a due time runs on the next tick, unless the entry itself is paused. */
	function nextRun(schedule: AgentSchedule): string {
		return when(schedule.next_run_at, schedule.enabled && project.enabled ? 'due now' : 'paused');
	}

	onMount(load);
</script>

<Dialog bind:open>
	<DialogContent class="sm:max-w-3xl">
		<DialogHeader>
			<DialogTitle>{project.name} agent schedules</DialogTitle>
			<DialogDescription>
				Recurring agent sessions this project owns. Each one drives a scheduler entry derived from
				the project; task sessions open pull requests the pipeline adopts, report sessions store
				their final message.
			</DialogDescription>
		</DialogHeader>

		{#if formOpen}
			<form onsubmit={save} class="space-y-3 rounded-md border border-border/80 p-4">
				<div class="grid gap-3 sm:grid-cols-2">
					<div class="space-y-1.5">
						<label for="asCatalog" class="text-xs font-semibold text-muted-foreground uppercase"
							>AI Catalog</label
						>
						<select
							id="asCatalog"
							bind:value={catalogId}
							required
							class="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs"
						>
							{#each sessionCatalogs as catalog (catalog.id)}
								<option value={catalog.id}>{catalog.name} ({catalog.kind})</option>
							{/each}
						</select>
					</div>
					<div class="space-y-1.5">
						<label for="asWorkType" class="text-xs font-semibold text-muted-foreground uppercase"
							>Work type</label
						>
						<select
							id="asWorkType"
							bind:value={workType}
							class="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs"
						>
							{#each workTypes as item (item)}
								<option value={item}>{item}</option>
							{/each}
						</select>
					</div>
				</div>
				<div class="space-y-1.5">
					<label for="asTitle" class="text-xs font-semibold text-muted-foreground uppercase"
						>Title</label
					>
					<Input
						id="asTitle"
						bind:value={title}
						required
						maxlength={200}
						placeholder="Weekly hygiene"
					/>
				</div>
				<div class="space-y-1.5">
					<label for="asPrompt" class="text-xs font-semibold text-muted-foreground uppercase"
						>Prompt</label
					>
					<textarea
						id="asPrompt"
						bind:value={prompt}
						required
						rows="5"
						class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs"
						placeholder="What the agent should do each run. The delivery contract for the work type is appended by the hub."
					></textarea>
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
						<select
							id="asTriggerKind"
							bind:value={triggerKind}
							class="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs"
						>
							<option value="cron">Cron</option>
							<option value="interval">Interval</option>
						</select>
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
					<Button type="button" variant="outline" size="sm" onclick={() => (formOpen = false)}
						>Cancel</Button
					>
					<Button type="submit" size="sm" disabled={saving || !catalogId}
						>{saving ? 'Saving…' : editing ? 'Save changes' : 'Create schedule'}</Button
					>
				</div>
			</form>
		{:else if loading}
			<p class="text-sm text-muted-foreground">Loading agent schedules…</p>
		{:else if schedules.length === 0}
			<p class="text-sm text-muted-foreground">
				No agent schedules yet.
				{#if sessionCatalogs.length === 0}
					No catalog can run scheduled sessions; add a Jules catalog with a connector first.
				{/if}
			</p>
		{:else}
			<ul class="max-h-96 space-y-2 overflow-y-auto">
				{#each schedules as item (item.id)}
					<li class="rounded-md border border-border/80 p-3 text-sm">
						<div class="flex items-start justify-between gap-3">
							<div>
								<span class="font-medium">{item.title}</span>
								<p class="mt-0.5 text-xs text-muted-foreground">
									{trigger(item)} · next {nextRun(item)}
									{#if item.last_run_at}
										· last {when(item.last_run_at, 'never')}{/if}
								</p>
							</div>
							<span class="flex shrink-0 gap-1">
								<Badge variant="outline">{item.work_type}</Badge>
								<Badge variant={item.enabled ? 'secondary' : 'destructive'}
									>{item.enabled ? 'enabled' : 'disabled'}</Badge
								>
							</span>
						</div>
						{#if (item.recent_sessions ?? []).length > 0}
							<ul class="mt-2 space-y-1 text-xs text-muted-foreground">
								{#each item.recent_sessions ?? [] as session (session.id)}
									<li class="flex flex-wrap items-center gap-2">
										<span>{new Date(session.created_at).toLocaleString()}</span>
										<Badge variant="outline" class="text-[10px]"
											>{session.state.replaceAll('_', ' ')}</Badge
										>
										{#if session.pull_request_url}
											<a
												class="text-primary underline"
												href={session.pull_request_url}
												target="_blank"
												rel="noreferrer">Pull request</a
											>
										{/if}
										{#if session.result_summary}
											<span class="truncate">{session.result_summary.slice(0, 80)}</span>
										{/if}
									</li>
								{/each}
							</ul>
						{/if}
						<div class="mt-2 flex gap-2">
							<Button type="button" variant="outline" size="sm" onclick={() => startEdit(item)}
								>Edit</Button
							>
							<Button
								type="button"
								variant="outline"
								size="sm"
								disabled={!item.enabled}
								onclick={() => runNow(item)}>Run now</Button
							>
							<Button type="button" variant="ghost" size="sm" onclick={() => remove(item)}
								>Delete</Button
							>
						</div>
					</li>
				{/each}
			</ul>
		{/if}

		{#if !formOpen}
			<DialogFooter class="items-center gap-2 sm:justify-between">
				<span class="text-xs text-muted-foreground">
					{schedules.length}
					{schedules.length === 1 ? 'schedule' : 'schedules'}
				</span>
				<div class="flex gap-2">
					<Button
						type="button"
						size="sm"
						disabled={sessionCatalogs.length === 0 || !project.github}
						onclick={startCreate}>New schedule</Button
					>
					<Button type="button" variant="outline" size="sm" onclick={() => (open = false)}
						>Close</Button
					>
				</div>
			</DialogFooter>
		{/if}
	</DialogContent>
</Dialog>
