<script lang="ts">
	import { api } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	let { projectId }: { projectId: string } = $props();
	let spec = $state('');
	let pull = $state<number>(1);
	let busy = $state(false);
	let message = $state('');
	let error = $state('');
	let inspected = $state('');
	let runId = $state('');
	const key = () => JSON.stringify([projectId, spec, pull]);
	async function inspect() {
		busy = true;
		error = '';
		message = '';
		inspected = '';
		try {
			const result = await api.POST('/api/v1/projects/{project_id}/specrig/readiness', {
				params: { path: { project_id: projectId } },
				body: { spec_dir: spec, pull_number: pull }
			});
			if (result.error) throw new Error(apiErrorMessage(result.error, 'Unable to inspect spec'));
			if (!result.data?.ready) throw new Error(result.data?.reason || 'Project needs setup');
			inspected = key();
			message = `Ready at commit ${result.data.head_sha?.slice(0, 12)}. ${result.data.cli_version}`;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Inspection failed';
		} finally {
			busy = false;
		}
	}
	async function start() {
		busy = true;
		error = '';
		try {
			const result = await api.POST('/api/v1/projects/{project_id}/runs', {
				params: { path: { project_id: projectId } },
				body: { spec_dir: spec, pull_number: pull, implemented: false }
			});
			if (result.error)
				throw new Error(apiErrorMessage(result.error, 'Unable to start spec execution'));
			runId = result.data?.id || '';
			message = 'Execution registered. Follow its stages and decisions in Pipeline Runs.';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not start execution';
		} finally {
			busy = false;
		}
	}
</script>

<section class="mb-4 space-y-3 rounded-lg border bg-card p-4">
	<h3 class="text-sm font-semibold">Run a specrig spec</h3>
	<p class="text-sm text-muted-foreground">
		Select a bound spec on an existing pull request. Execution checks the PR revision; the
		repository browser may show a different ref.
	</p>
	<div class="flex flex-wrap gap-3">
		<label class="min-w-64 flex-1 text-sm"
			>Spec directory
			<input
				class="mt-1 w-full rounded border bg-background p-2"
				bind:value={spec}
				placeholder="specs/2026-10/20261010-feature"
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
	</div>
	<div class="flex gap-2">
		<Button variant="outline" disabled={busy || !spec || !pull} onclick={inspect}
			>Check readiness</Button
		>
		<Button disabled={busy || inspected !== key() || !!runId} onclick={start}
			>Start execution</Button
		>
	</div>
	{#if message}<p role="status" class="text-sm">{message}</p>{/if}
	{#if error}<p role="alert" class="text-sm text-destructive">{error}</p>{/if}
</section>
