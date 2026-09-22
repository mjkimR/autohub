<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { allPages, responseData } from '$lib/api/pagination';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import WorkPlanForm from './WorkPlanForm.svelte';
	type Plan = components['schemas']['WorkPlanRead'];
	let { project }: { project: components['schemas']['ProjectRead'] } = $props();
	let plans = $state<Plan[]>([]);
	let loading = $state(true);
	let error = $state('');
	let busy = $state('');
	let creating = $state(false);
	let editing = $state<Plan | undefined>();
	async function load() {
		try {
			plans = await allPages(async (offset, limit) =>
				responseData(
					await api.GET('/api/v1/projects/{project_id}/work-plans', {
						params: { path: { project_id: project.id }, query: { offset, limit } }
					}),
					'Could not load plans'
				)
			);
			error = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load plans';
		} finally {
			loading = false;
		}
	}
	async function control(plan: Plan, action: 'pause' | 'resume' | 'revoke') {
		if (
			action === 'revoke' &&
			!confirm(
				'Revoke all unstarted tasks? Started tasks will continue, including merges. This plan cannot be resumed.'
			)
		)
			return;
		busy = plan.id;
		try {
			const result = await api.POST('/api/v1/projects/{project_id}/work-plans/{plan_id}/control', {
				params: { path: { project_id: project.id, plan_id: plan.id } },
				body: { action, expected_revision: plan.revision }
			});
			if (!result.data) throw new Error(apiErrorMessage(result.error, 'Could not update plan'));
			await load();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not update plan';
		} finally {
			busy = '';
		}
	}
	function waitingReason(plan: Plan, item: Plan['items'][number]) {
		if (item.state !== 'waiting') return item.detail;
		if (plan.state === 'paused') return 'Plan paused';
		if (!project.enabled) return 'Project disabled';
		const parents = plan.depends_on
			.map((id) => plans.find((parent) => parent.id === id))
			.filter((parent) => !parent || parent.state !== 'completed');
		if (parents.length)
			return (
				'Waiting for plans: ' +
				parents.map((parent) => parent?.title ?? 'Unavailable plan').join(', ')
			);
		const tasks = item.depends_on.filter(
			(key) => plan.items.find((other) => other.key === key)?.state !== 'succeeded'
		);
		return tasks.length
			? 'Waiting for tasks: ' + tasks.join(', ')
			: (item.detail ?? 'Ready; waiting for the next execution slot');
	}
	function saved() {
		creating = false;
		editing = undefined;
		void load();
	}
	onMount(() => {
		void load();
		const timer = setInterval(() => {
			if (!creating && !editing && !busy) void load();
		}, 15000);
		return () => clearInterval(timer);
	});
</script>

<section class="space-y-5">
	<header class="flex flex-wrap items-center justify-between gap-3">
		<div>
			<h2 class="text-xl font-semibold">Work plans</h2>
			<p class="mt-1 text-sm text-muted-foreground">
				Dependencies release after merging. Pausing or revoking affects only tasks that have not
				started.
			</p>
		</div>
		<div class="flex gap-2">
			<Button variant="outline" onclick={load}>Refresh</Button><Button
				disabled={!project.github || creating || !!editing}
				onclick={() => (creating = true)}>Add plan</Button
			>
		</div>
	</header>
	{#if error}<p role="alert" class="rounded-lg border border-destructive/30 p-4 text-sm">
			{error}
		</p>{/if}
	{#if creating || editing}<WorkPlanForm
			projectId={project.id}
			{plans}
			{editing}
			onsaved={saved}
			oncancel={() => {
				creating = false;
				editing = undefined;
			}}
		/>{/if}
	{#if loading}<p class="text-sm text-muted-foreground">Loading plans…</p>
	{:else if !plans.length && !creating}<div
			class="rounded-xl border border-dashed p-8 text-center text-muted-foreground"
		>
			Add a plan with tasks and dependencies to start.
		</div>{/if}
	{#each plans as plan (plan.id)}
		<article class="space-y-4 rounded-xl border bg-card p-5">
			<header class="flex flex-wrap justify-between gap-3">
				<div>
					<h3 class="text-lg font-semibold">{plan.title}</h3>
					<p class="mt-1 text-sm text-muted-foreground">
						{plan.state} · {plan.items.filter((item) => item.state === 'succeeded').length}/{plan
							.items.length} merged · {plan.base_branch}
					</p>
				</div>
				<div class="flex flex-wrap gap-2">
					{#if plan.state === 'active' || plan.state === 'paused'}
						{#if plan.items.every((item) => !item.started_at)}<Button
								variant="outline"
								disabled={!!busy || creating || !!editing}
								onclick={() => (editing = plan)}>Edit</Button
							>{/if}
						<Button
							variant="outline"
							disabled={!!busy}
							onclick={() => control(plan, plan.state === 'paused' ? 'resume' : 'pause')}
							>{plan.state === 'paused' ? 'Resume' : 'Pause'}</Button
						>
						<Button variant="outline" disabled={!!busy} onclick={() => control(plan, 'revoke')}
							>Revoke</Button
						>
					{/if}
				</div>
			</header>
			{#if plan.description}<p class="text-sm whitespace-pre-wrap">{plan.description}</p>{/if}
			{#if plan.depends_on.length}<p class="text-sm">
					Depends on: {plan.depends_on
						.map((id) => plans.find((parent) => parent.id === id)?.title ?? id)
						.join(', ')}
				</p>{/if}
			<div class="flex flex-wrap gap-3 text-sm">
				{#if plan.issue?.issue_url}<a
						class="text-primary underline"
						href={plan.issue.issue_url}
						target="_blank"
						rel="noreferrer">Plan issue ↗</a
					>{/if}
				{#if plan.issue?.pending}<span class="text-muted-foreground">GitHub record pending</span
					>{/if}
			</div>
			{#if plan.issue?.error}<p class="text-sm text-muted-foreground">
					Record sync: {plan.issue.error}. Work continues independently.
				</p>{/if}
			<div class="divide-y rounded-lg border">
				{#each plan.items as item (item.id)}
					<details class="p-4">
						<summary class="cursor-pointer text-sm"
							><span class="font-medium">{item.key}: {item.title}</span><span
								class="ml-3 text-muted-foreground">{item.state}</span
							></summary
						>
						<div class="mt-3 space-y-3 text-sm">
							{#if waitingReason(plan, item)}<p class="text-muted-foreground">
									{waitingReason(plan, item)}
								</p>{/if}
							{#if item.depends_on.length}<p>Depends on: {item.depends_on.join(', ')}</p>{/if}
							<p class="whitespace-pre-wrap">{item.description}</p>
							<p class="whitespace-pre-wrap">
								<strong>Acceptance criteria:</strong>
								{item.acceptance}
							</p>
							<div class="flex flex-wrap gap-3">
								{#if item.pull_url}<a
										class="text-primary underline"
										href={item.pull_url}
										target="_blank"
										rel="noreferrer">Pull request ↗</a
									>{/if}
								{#if item.issue?.issue_url}<a
										class="text-primary underline"
										href={item.issue.issue_url}
										target="_blank"
										rel="noreferrer">Task issue ↗</a
									>{/if}
								{#if item.pipeline_run_id}<a
										class="text-primary underline"
										href={`/projects/${project.id}?tab=runs`}>Execution runs</a
									>{/if}
							</div>
							{#if item.pipeline_run_retired_at}<p class="text-muted-foreground">
									Execution history expired; completion evidence is retained.
								</p>{/if}
							{#if item.issue?.pending}<p class="text-muted-foreground">
									GitHub record pending{item.issue.error ? ': ' + item.issue.error : ''}
								</p>{/if}
						</div>
					</details>
				{/each}
			</div>
		</article>
	{/each}
</section>
