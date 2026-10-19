<script lang="ts">
	import { api } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import SddRunLinks from './SddRunLinks.svelte';
	import { Button } from '$lib/components/ui/button';
	let {
		projectId,
		selectedSpec = '',
		repository = ''
	}: { projectId: string; selectedSpec?: string; repository?: string } = $props();
	$effect(() => {
		if (selectedSpec) spec = selectedSpec;
	});
	let spec = $state('');
	let pull = $state<number>(1);
	let busy = $state(false);
	let message = $state('');
	let error = $state('');
	let inspected = $state('');
	let warnings = $state<string[]>([]);
	let effort = $state<'low' | 'medium' | 'high'>('medium');
	let runtime = $state('');
	let runtimeError = $state('');
	async function checkRuntime() {
		busy = true;
		runtime = '';
		runtimeError = '';
		try {
			const result = await api.GET('/api/v1/projects/{project_id}/sdd/runtime', {
				params: { path: { project_id: projectId } }
			});
			if (result.error)
				throw new Error(apiErrorMessage(result.error, 'Unable to check the runtime'));
			const status = result.data;
			const spec = status.revisions?.['devkit-spec']?.slice(0, 12);
			const summary = `Runtime ${status.isolation ?? 'without a sandbox'}: ${status.ok ? 'ok' : 'unavailable'}${spec ? ` · devkit-spec ${spec}` : ''}`;
			if (status.ok)
				runtime = `${summary} · profile ${status.profile ?? 'default'} · bundles: ${(status.bundles ?? []).join(', ') || 'unknown'}`;
			else runtimeError = `${summary}. ${status.detail ?? ''}`.trim();
		} catch (e) {
			runtimeError = e instanceof Error ? e.message : 'Runtime check failed';
		} finally {
			busy = false;
		}
	}
	let runId = $state('');
	let startedKey = $state('');
	const key = () => JSON.stringify([projectId, spec, pull]);
	async function inspect() {
		const requestedKey = key();
		busy = true;
		error = '';
		message = '';
		inspected = '';
		warnings = [];
		try {
			const result = await api.POST('/api/v1/projects/{project_id}/sdd/readiness', {
				params: { path: { project_id: projectId } },
				body: { spec_dir: spec, pull_number: pull }
			});
			if (result.error) throw new Error(apiErrorMessage(result.error, 'Unable to inspect spec'));
			if (!result.data?.ready) throw new Error(result.data?.reason || 'Project needs setup');
			if (requestedKey !== key()) return;
			inspected = requestedKey;
			message = `Ready at commit ${result.data.head_sha?.slice(0, 12)}. ${result.data.cli_version}`;
			warnings = (result.data.warnings ?? []).map((item) => item.detail);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Inspection failed';
		} finally {
			busy = false;
		}
	}
	async function start() {
		const requestedKey = key();
		busy = true;
		error = '';
		try {
			const result = await api.POST('/api/v1/projects/{project_id}/runs', {
				params: { path: { project_id: projectId } },
				body: {
					spec_dir: spec,
					pull_number: pull,
					implemented: false,
					handoff: false,
					activity_effort: effort
				}
			});
			if (result.error)
				throw new Error(apiErrorMessage(result.error, 'Unable to start spec execution'));
			runId = result.data?.id || '';
			startedKey = requestedKey;
			message = 'Execution registered. Follow its stages and decisions in Pipeline Runs.';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not start execution';
		} finally {
			busy = false;
		}
	}
</script>

<section class="mb-4 space-y-3 rounded-lg border bg-card p-4">
	<h3 class="text-sm font-semibold">Run an SDD spec</h3>
	<p class="text-sm text-muted-foreground">
		Select a bound spec on an existing pull request whose head is the spec's activity branch (<code
			>dev-&lt;slug&gt;</code
		>). Execution checks the PR revision; the repository browser may show a different ref. For a new
		idea, prepare its spec and PR first; Work Plans do not create native SDD runs yet.
	</p>
	<div class="flex flex-wrap gap-3">
		<label class="min-w-64 flex-1 text-sm"
			>Unit directory (spec or proposal)
			<input
				class="mt-1 w-full rounded border bg-background p-2"
				bind:value={spec}
				placeholder="specs/2026-10/20261010-feature or docs/proposals/PROP-feature"
				disabled={busy}
			/>
		</label>
		<label class="text-sm"
			>Pull request
			<input
				class="mt-1 block w-28 rounded border bg-background p-2"
				type="number"
				min="1"
				bind:value={pull}
				disabled={busy}
			/>
		</label>
		<label class="text-sm"
			>Activity effort
			<select
				class="mt-1 block rounded border bg-background p-2"
				bind:value={effort}
				disabled={busy}
				aria-label="Activity effort"
			>
				<option value="low">low</option>
				<option value="medium">medium</option>
				<option value="high">high</option>
			</select>
		</label>
	</div>
	<div class="flex flex-wrap gap-2">
		<Button variant="outline" disabled={busy} onclick={checkRuntime}>Check runtime</Button>
		<Button variant="outline" disabled={busy || !spec || !pull} onclick={inspect}
			>Check readiness</Button
		>
		<Button
			disabled={busy || inspected !== key() || (!!runId && startedKey === key())}
			onclick={start}>Start execution</Button
		>
	</div>
	{#if runId && startedKey === key()}<Button
			variant="outline"
			href={`/projects/runs?run=${runId}&view=decisions`}>Open execution & decisions</Button
		>{/if}
	<SddRunLinks {projectId} {repository} specDir={spec} refresh={runId} />
	{#if runtime}<p role="status" class="text-sm">{runtime}</p>{/if}
	{#if runtimeError}<p role="alert" class="text-sm text-destructive">{runtimeError}</p>{/if}
	{#if message}<p role="status" class="text-sm">{message}</p>{/if}
	{#each warnings as warning, index (index)}<p
			role="status"
			class="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm"
		>
			{warning}
		</p>{/each}
	{#if error}<p role="alert" class="text-sm text-destructive">{error}</p>{/if}
</section>
