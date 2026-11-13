<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import { ArrowLeft, FolderGit2, RefreshCw } from '@lucide/svelte';
	import RunHeader from './RunHeader.svelte';
	import RunNextStep from './RunNextStep.svelte';
	import RunActions from '../RunActions.svelte';
	import RunDecisions from '../RunDecisions.svelte';
	import RunAttempts from '../RunAttempts.svelte';
	import AttachPullRequestDialog from '../AttachPullRequestDialog.svelte';
	import { advanceRun, cancelRun, pauseRun, resumeRun } from '../run-operations';
	import {
		decisionsFor,
		loadPendingDecisions,
		type RunDecisions as Decisions
	} from '../run-actions';
	import { runHref } from '../run-links';

	type Run = components['schemas']['PipelineRunRead'];
	/** The PR run's home: identity and state, the next action, decisions and attempts. */
	let { projectId, runId }: { projectId: string; runId: string } = $props();

	let run = $state<Run | null>(null);
	let projectName = $state('');
	let decisions = $state<Decisions>({ status: 'unknown' });
	let status = $state<'loading' | 'ready' | 'not-found'>('loading');
	let error = $state('');
	let refreshing = $state(false);
	let operating = $state(false);
	let attaching = $state(false);
	// A header action that changed the run remounts both sections. A plain Refresh only remounts
	// attempts: the Decisions section keeps its draft and notices and has its own refresh.
	let decisionsGeneration = $state(0);
	let attemptsGeneration = $state(0);

	async function loadRun() {
		const res = await api.GET('/api/v1/pipeline-runs/{run_id}', {
			params: { path: { run_id: runId } }
		});
		if (!res.data) {
			const notFound = res.response?.status === 404;
			if (notFound && !run) status = 'not-found';
			throw new Error(
				apiErrorMessage(res.error, notFound ? 'PR run not found' : 'Could not load the PR run')
			);
		}
		if (res.data.project_id !== projectId) {
			await goto(runHref(res.data.id, res.data.project_id) + window.location.hash, {
				replaceState: true
			});
			return;
		}
		run = res.data;
	}

	async function loadDecisions() {
		try {
			const page = await loadPendingDecisions(projectId, 5);
			decisions = decisionsFor(runId, page);
		} catch {
			decisions = { status: 'unknown' };
		}
	}

	async function loadProjectName() {
		const res = await api.GET('/api/v1/projects/{project_id}', {
			params: { path: { project_id: projectId } }
		});
		projectName = res.data?.name ?? 'Project';
	}

	async function refresh(remount: 'all' | 'attempts' | 'none' = 'none') {
		refreshing = true;
		try {
			await Promise.all([loadRun(), loadDecisions()]);
			error = '';
			if (remount !== 'none') attemptsGeneration += 1;
			if (remount === 'all') decisionsGeneration += 1;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load the PR run';
		} finally {
			refreshing = false;
		}
	}

	async function operate(action: () => Promise<boolean>) {
		operating = true;
		try {
			if (await action()) await refresh('all');
		} finally {
			operating = false;
		}
	}

	onMount(() => {
		void Promise.all([refresh(), loadProjectName().catch(() => (projectName = 'Project'))]).then(
			async () => {
				if (status !== 'not-found') status = 'ready';
				await tick();
				// Section links (`#decisions`, `#attempts`, `#next-step`) land after the content renders.
				const hash = window.location.hash.slice(1);
				if (!hash) return;
				const target = document.getElementById(hash);
				target?.scrollIntoView?.();
				target?.focus({ preventScroll: true });
			}
		);
	});
</script>

<svelte:head
	><title>{run ? `PR #${run.pull_number} · ${projectName || 'PR run'}` : 'PR run'} · AutoHub</title
	></svelte:head
>

<div class="mx-auto w-full max-w-7xl space-y-6">
	{#if status === 'loading'}
		<p role="status" class="text-sm text-muted-foreground">Loading PR run…</p>
	{:else if status === 'not-found' || !run}
		<section class="space-y-3 rounded-xl border bg-card p-6">
			<h1 class="text-xl font-semibold">
				{status === 'not-found' ? 'PR run not found' : 'PR run unavailable'}
			</h1>
			<p class="max-w-prose text-sm text-muted-foreground">
				{status === 'not-found'
					? 'This PR run does not exist or its history has expired. Its Work Item and pull request keep their retained results.'
					: error || 'The PR run could not be loaded.'}
			</p>
			<div class="flex flex-wrap gap-2">
				{#if status !== 'not-found'}<Button onclick={() => refresh()}>Retry</Button>{/if}
				<Button variant="outline" href={`/projects/${projectId}?tab=runs`}
					><ArrowLeft aria-hidden="true" />Back to project runs</Button
				>
			</div>
		</section>
	{:else}
		<RunHeader {run} projectName={projectName || 'Project'} {decisions} />
		<div class="flex flex-wrap items-center justify-between gap-3">
			<RunActions
				{run}
				{decisions}
				{operating}
				layout="page"
				href={(section) => (section ? `#${section}` : runHref(run!.id, run!.project_id))}
				onadvance={() => operate(() => advanceRun(run!.id))}
				onpause={() => operate(() => pauseRun(run!.id))}
				onresume={() => operate(() => resumeRun(run!))}
				oncancel={() => operate(() => cancelRun(run!.id))}
				onattach={() => (attaching = true)}
			/>
			<Button variant="ghost" size="sm" disabled={refreshing} onclick={() => refresh('attempts')}
				><RefreshCw aria-hidden="true" class={refreshing ? 'animate-spin' : ''} />Refresh</Button
			>
		</div>
		{#if error}
			<div
				role="alert"
				class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-destructive/40 p-3 text-sm text-destructive"
			>
				<span>{error}. Showing the last loaded run.</span>
				<Button variant="outline" size="sm" disabled={refreshing} onclick={() => refresh()}
					>Retry</Button
				>
			</div>
		{/if}

		{#if run.state === 'failed' || run.state === 'canceled'}
			{#key run.id}<RunNextStep {run} />{/key}
		{/if}

		{#if run.sdd_snapshot?.spec_dir}
			<p class="flex flex-wrap items-center gap-2 text-sm">
				<FolderGit2 aria-hidden="true" class="size-4 text-muted-foreground" />
				<span class="text-muted-foreground">SDD unit</span>
				<a
					class="font-mono text-xs break-all underline underline-offset-4"
					href={`/projects/${run.project_id}?tab=repository&unit=${encodeURIComponent(String(run.sdd_snapshot.spec_dir))}`}
					>{String(run.sdd_snapshot.spec_dir)}</a
				>
			</p>
		{/if}

		{#key decisionsGeneration}
			<section
				id="decisions"
				tabindex="-1"
				aria-labelledby="run-decisions-heading"
				class="scroll-mt-6 space-y-4 rounded-xl border bg-card p-5 sm:p-6"
			>
				<h2 id="run-decisions-heading" class="text-lg font-semibold">Decisions</h2>
				<RunDecisions {run} onRunPage onchange={() => void refresh()} />
			</section>
		{/key}
		{#key attemptsGeneration}
			<section
				id="attempts"
				tabindex="-1"
				aria-labelledby="run-attempts-heading"
				class="scroll-mt-6 space-y-4 rounded-xl border bg-card p-5 sm:p-6"
			>
				<div>
					<h2 id="run-attempts-heading" class="text-lg font-semibold">Execution attempts</h2>
					<p class="text-sm text-muted-foreground">
						Immutable request snapshots, correlation keys and recorded outcomes.
					</p>
				</div>
				<RunAttempts runId={run.id} />
			</section>
		{/key}
	{/if}
</div>

{#if attaching && run}
	<AttachPullRequestDialog
		{run}
		onclose={() => (attaching = false)}
		onsaved={() => void refresh('all')}
	/>
{/if}
