<script lang="ts">
	import type { components } from '$lib/api';
	import { Button } from '$lib/components/ui/button';
	import { ArrowRight, ListChecks, Plus } from '@lucide/svelte';
	let { run }: { run: components['schemas']['PipelineRunRead'] } = $props();
	let owner = $derived((run.related_origins ?? []).find((origin) => origin.kind === 'work_plan'));
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
	{#if owner}
		<p class="max-w-prose text-sm">
			This run delivered Work Item <span class="font-medium">{owner.id}</span>
			in the Work Plan <span class="font-medium">{owner.work_plan_id}</span>. Recover or replace it
			from that Work Item.
		</p>
		<div class="flex flex-wrap gap-2">
			<Button href={`${plansHref}#work-item-${owner.id}`}
				><ListChecks aria-hidden="true" />Open Work Item recovery</Button
			>
			<Button variant="outline" href="#attempts">Review attempt errors</Button>
		</div>
	{:else}
		<p class="max-w-prose text-sm">
			No Work Item links to this run. To retry the change, enroll its PR again or register
			replacement work in a Work Plan.
		</p>
		<div class="flex flex-wrap gap-2">
			<Button href={`/projects/${run.project_id}?tab=runs`}
				><Plus aria-hidden="true" />Enroll PR</Button
			>
			<Button variant="outline" href={plansHref}>Work Plans<ArrowRight aria-hidden="true" /></Button
			>
		</div>
	{/if}
</section>
