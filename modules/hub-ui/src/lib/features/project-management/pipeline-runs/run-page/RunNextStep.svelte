<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { allPages, responseData } from '$lib/api/pagination';
	import { Button } from '$lib/components/ui/button';
	import { ArrowRight, ListChecks, Plus } from '@lucide/svelte';

	type Run = components['schemas']['PipelineRunRead'];
	type Plan = components['schemas']['WorkPlanRead'];
	/**
	 * The recovery path of an ended PR run. A run admitted for a Work Item is recovered from that
	 * item; any other run needs replacement work registered by hand. The run carries no Work Item
	 * reference, so the owning item is found from the project's Work Plans.
	 */
	let { run }: { run: Run } = $props();
	let owner = $state<{ plan: Plan; item: Plan['items'][number] } | null>(null);
	let status = $state<'loading' | 'ready' | 'error'>('loading');

	async function findOwner() {
		status = 'loading';
		try {
			const plans = await allPages(async (offset, limit) =>
				responseData(
					await api.GET('/api/v1/projects/{project_id}/work-plans', {
						params: { path: { project_id: run.project_id }, query: { offset, limit } }
					}),
					'Could not load Work Plans'
				)
			);
			owner = null;
			for (const plan of plans) {
				const item = plan.items.find((candidate) => candidate.pipeline_run_id === run.id);
				if (item) owner = { plan, item };
			}
			status = 'ready';
		} catch {
			status = 'error';
		}
	}
	onMount(() => {
		void findOwner();
	});
	let plansHref = $derived(`/projects/${run.project_id}?tab=plans`);
</script>

<section
	id="next-step"
	tabindex="-1"
	aria-labelledby="run-next-step-heading"
	class="scroll-mt-6 space-y-3 rounded-xl border bg-card p-5"
>
	<h2 id="run-next-step-heading" class="text-base font-semibold">Next step</h2>
	<p class="max-w-prose text-sm text-muted-foreground">
		{run.state === 'failed' ? 'This run failed' : 'This run was canceled'} and cannot be resumed. Its
		result, decisions and attempts stay recorded below. Check the attempt errors, then continue the change
		as new work.
	</p>
	{#if status === 'loading'}
		<p role="status" class="text-sm text-muted-foreground">
			Looking for the Work Item this run delivered…
		</p>
	{:else if owner}
		<p class="max-w-prose text-sm">
			This run delivered Work Item <span class="font-medium"
				>{owner.item.key}: {owner.item.title}</span
			>
			in the Work Plan <span class="font-medium">{owner.plan.title}</span>. Recover or replace it
			from that Work Item.
		</p>
		<div class="flex flex-wrap gap-2">
			<Button href={`${plansHref}#work-item-${owner.item.id}`}
				><ListChecks aria-hidden="true" />Open Work Item recovery</Button
			>
			<Button variant="outline" href="#attempts">Review attempt errors</Button>
		</div>
	{:else}
		<p class="max-w-prose text-sm">
			{status === 'error'
				? 'The owning Work Item could not be checked.'
				: 'No Work Item links to this run.'} To retry the change, enroll its PR again or register replacement
			work in a Work Plan.
		</p>
		<div class="flex flex-wrap gap-2">
			<Button href={`/projects/${run.project_id}?tab=runs`}
				><Plus aria-hidden="true" />Enroll PR</Button
			>
			<Button variant="outline" href={plansHref}>Work Plans<ArrowRight aria-hidden="true" /></Button
			>
			{#if status === 'error'}
				<Button variant="ghost" onclick={findOwner}>Check again</Button>
			{/if}
		</div>
	{/if}
</section>
