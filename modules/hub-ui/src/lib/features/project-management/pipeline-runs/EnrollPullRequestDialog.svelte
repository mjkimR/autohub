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
		DialogFooter,
		DialogDescription
	} from '$lib/components/ui/dialog';
	import { Sparkles } from '@lucide/svelte';

	let {
		projects,
		pipelineCatalogs,
		initialProjectId,
		onclose,
		onsaved
	}: {
		projects: components['schemas']['ProjectRead'][];
		initialProjectId: string;
		pipelineCatalogs: components['schemas']['AICatalogRead'][];
		onclose: () => void;
		onsaved: () => void;
	} = $props();
	let isAcquiring = $state(false);
	let acquireProjectId = $state('');
	onMount(() => {
		acquireProjectId = initialProjectId;
	});
	let enrollPullNumber = $state<number>(1);
	let enrollImplemented = $state(false);
	let enrollCatalog = $state('');

	async function handleAcquireRunSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!acquireProjectId) {
			toast.error('Please select a project');
			return;
		}
		isAcquiring = true;
		try {
			const res = await api.POST('/api/v1/projects/{project_id}/runs', {
				params: { path: { project_id: acquireProjectId } },
				body: {
					pull_number: Number(enrollPullNumber),
					implemented: enrollImplemented,
					catalog: enrollCatalog || null
				}
			});
			if (res.error) {
				const detail = apiErrorMessage(res.error, 'Failed to enroll pull request');
				toast.error(detail);
			} else if (res.data) {
				toast.success(`Enrolled PR #${res.data.pull_number} into pipeline run!`);
				onclose();
				onsaved();
			}
		} catch {
			toast.error('Error enrolling pull request');
		} finally {
			isAcquiring = false;
		}
	}
</script>

<!-- Enroll PR Dialog -->
<Dialog
	open={true}
	onOpenChange={(open) => {
		if (!open) onclose();
	}}
>
	<DialogContent class="sm:max-w-[450px]">
		<DialogHeader>
			<div class="flex items-center gap-2">
				<div class="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
					<Sparkles class="size-4" />
				</div>
				<div>
					<DialogTitle>Enroll Pull Request</DialogTitle>
					<DialogDescription>
						Register an open GitHub PR to create an active pipeline run.
					</DialogDescription>
				</div>
			</div>
		</DialogHeader>

		<form onsubmit={handleAcquireRunSubmit} class="space-y-4 py-2">
			<div class="space-y-1.5">
				<label for="acquireProject" class="text-xs font-semibold text-muted-foreground uppercase">
					Target Project
				</label>
				<select
					id="acquireProject"
					bind:value={acquireProjectId}
					class="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs focus:ring-1 focus:ring-ring"
					required
				>
					<option value="" disabled>Select a project</option>
					{#each projects as project (project.id)}
						<option value={project.id}>{project.name}</option>
					{/each}
				</select>
			</div>

			<div class="space-y-1.5">
				<label for="enrollPRNum" class="text-xs font-semibold text-muted-foreground uppercase">
					Pull Request Number
				</label>
				<Input
					id="enrollPRNum"
					type="number"
					min="1"
					bind:value={enrollPullNumber}
					placeholder="e.g. 42"
					required
				/>
			</div>

			<div class="space-y-1.5">
				<label for="enrollCatalog" class="text-xs font-semibold text-muted-foreground uppercase">
					AI Catalog
				</label>
				<select
					id="enrollCatalog"
					bind:value={enrollCatalog}
					class="h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs focus:ring-1 focus:ring-ring"
				>
					<option value="">Project default</option>
					{#each pipelineCatalogs as catalog (catalog.id)}
						<option value={catalog.key}>{catalog.name} ({catalog.kind})</option>
					{/each}
				</select>
				<p class="text-xs text-muted-foreground">
					The same choice can be made in a PR body or comment with <code
						>@auto-run:&lt;key or kind&gt;</code
					>.
				</p>
			</div>

			<label class="flex items-center justify-between gap-3 text-sm">
				<span>
					<span class="font-medium text-foreground">Already implemented</span>
					<span class="mt-0.5 block text-xs text-muted-foreground"
						>Skip the implementation request and start at CI observation.</span
					>
				</span>
				<input
					type="checkbox"
					bind:checked={enrollImplemented}
					class="size-4 rounded border-border text-primary focus:ring-primary"
				/>
			</label>

			<DialogFooter class="pt-2">
				<Button type="button" variant="outline" onclick={onclose}>Cancel</Button>
				<Button type="submit" disabled={isAcquiring || !acquireProjectId}>
					{isAcquiring ? 'Enrolling...' : 'Enroll PR'}
				</Button>
			</DialogFooter>
		</form>
	</DialogContent>
</Dialog>
