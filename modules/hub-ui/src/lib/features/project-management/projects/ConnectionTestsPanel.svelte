<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import { toast } from 'svelte-sonner';
	type Test = components['schemas']['ConnectionTestRead'];
	let {
		project,
		catalogs
	}: {
		project: components['schemas']['ProjectRead'];
		catalogs: components['schemas']['AICatalogRead'][];
	} = $props();
	let catalogId = $state('');
	let choices = $state<components['schemas']['ConnectionTestOption'][]>([]);
	let selected = $derived(choices.find((catalog) => catalog.ai_catalog_id === catalogId));
	$effect(() => {
		if (!catalogId && choices.length) {
			const preferred =
				project.github?.ai_catalog_id ?? catalogs.find((item) => item.key === 'personal-codex')?.id;
			catalogId =
				choices.find((item) => item.ai_catalog_id === preferred)?.ai_catalog_id ??
				choices[0].ai_catalog_id;
		}
	});
	let tests = $state<Test[]>([]);
	let loading = $state(true);
	let busy = $state(false);
	let error = $state('');
	let requestId = $state<string | null>(null);
	const outcomes: Record<string, string> = {
		running: 'Running',
		succeeded: 'Verified',
		failed: 'Failed',
		timed_out: 'Not verified — timed out',
		canceled: 'Canceled'
	};
	let active = $derived(tests.some((test) => test.status === 'running'));
	async function load() {
		try {
			const params = { path: { project_id: project.id } };
			const [res, config] = await Promise.all([
				api.GET('/api/v1/projects/{project_id}/connection-tests', { params }),
				api.GET('/api/v1/projects/{project_id}/connection-tests/options', { params })
			]);
			if (!res.data || !config.data)
				throw new Error('Could not load connection tests and requirements');
			tests = res.data;
			if (requestId && tests.some((test) => test.id === requestId)) requestId = null;
			choices = config.data;
			error = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load connection tests';
		} finally {
			loading = false;
		}
	}
	async function start() {
		busy = true;
		requestId ??= crypto.randomUUID();
		try {
			const res = await api.POST('/api/v1/projects/{project_id}/connection-tests', {
				params: { path: { project_id: project.id } },
				body: { request_id: requestId, ai_catalog_id: catalogId }
			});
			if (!res.data) {
				if (res.response.status >= 400 && res.response.status < 500) requestId = null;
				throw new Error(apiErrorMessage(res.error, 'Could not start connection test'));
			}
			requestId = null;
			await load();
			toast.success('Connection test queued. The scheduler will continue it.');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Could not start connection test');
		} finally {
			busy = false;
		}
	}
	async function act(test: Test, action: 'advance' | 'cancel') {
		busy = true;
		try {
			const params = { path: { project_id: project.id, test_id: test.id } };
			const res =
				action === 'cancel'
					? await api.POST('/api/v1/projects/{project_id}/connection-tests/{test_id}/cancel', {
							params
						})
					: await api.POST('/api/v1/projects/{project_id}/connection-tests/{test_id}/advance', {
							params
						});
			if (!res.data)
				throw new Error(apiErrorMessage(res.error, 'Could not update connection test'));
			await load();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Could not update connection test');
		} finally {
			busy = false;
		}
	}
	function evidence(test: Test, key: string): string | null {
		const value = test.evidence[key];
		return typeof value === 'string' ? value : null;
	}
	function evidenceLink(
		test: Test,
		key: string,
		origin: string | null | undefined
	): string | undefined {
		const value = evidence(test, key);
		if (!value || !origin) return undefined;
		try {
			const url = new URL(value);
			return url.origin === origin && !url.username && !url.password ? value : undefined;
		} catch {
			return undefined;
		}
	}
	function metadata(test: Test) {
		return (
			test.test_spec?.evidence ?? [
				{ key: 'pull_url', label: 'Test PR', origin: 'https://github.com' },
				{ key: 'ci_url', label: 'CI run', origin: 'https://github.com' }
			]
		);
	}
	onMount(() => {
		void load();
		const timer = setInterval(() => {
			void load();
		}, 10000);
		return () => clearInterval(timer);
	});
</script>

<section class="space-y-5 rounded-xl border bg-card p-6" aria-label="AI connection tests">
	<div class="flex flex-wrap items-start justify-between gap-4">
		<div>
			<h2 class="text-lg font-semibold">AI connection tests</h2>
			<p class="mt-1 text-sm text-muted-foreground">
				Select an AI catalog to verify its execution, test change, and required CI in this
				repository.
			</p>
		</div>
		<Button
			onclick={start}
			disabled={loading ||
				busy ||
				active ||
				!!error ||
				!project.enabled ||
				!project.github ||
				!selected?.ready}>Start PR test</Button
		>
	</div>
	<div class="space-y-2">
		<label for="test-catalog" class="text-sm font-medium">Test AI catalog</label>
		<select
			id="test-catalog"
			bind:value={catalogId}
			disabled={busy || !!requestId}
			class="flex h-10 w-full max-w-md rounded-md border bg-background px-3 text-sm"
		>
			{#each choices as catalog (catalog.ai_catalog_id)}
				<option value={catalog.ai_catalog_id}
					>{catalog.name} · {catalog.kind}{catalog.ready ? '' : ' (setup needed)'}</option
				>
			{/each}
		</select>
		{#if !choices.length}<p class="text-sm text-muted-foreground">
				No supported AI catalog is configured.
			</p>{/if}
		{#if selected}
			<div class="space-y-3 rounded-lg border p-4" aria-label="Test requirements">
				<h3 class="font-semibold">{selected.spec.title}</h3>
				<p class="text-sm text-muted-foreground">{selected.spec.description}</p>
				{#each selected.spec.requirements as requirement (requirement.key)}
					{@const state =
						selected.requirements.find((item) => item.key === requirement.key)?.status ?? 'manual'}
					<div class="text-sm">
						<p class="font-medium">
							{requirement.label}
							<span
								class:text-destructive={state === 'missing'}
								class="font-normal text-muted-foreground"
								>· {state === 'manual' ? 'Confirm once in provider' : state}</span
							>
						</p>
						<p class="mt-1 text-muted-foreground">
							{requirement.description}
							{#if requirement.url?.startsWith('https://') || requirement.url?.startsWith('/settings/')}<a
									class="text-primary underline"
									href={requirement.url}
									target="_blank"
									rel="noreferrer">Open setup</a
								>{/if}
						</p>
					</div>
				{/each}
			</div>
		{/if}
		{#if requestId}<p class="text-xs text-muted-foreground">
				Retry uses the same request and catalog until the result is confirmed.
			</p>{/if}
	</div>
	<p class="rounded-lg bg-muted/50 p-3 text-sm">
		Uses the selected catalog’s quota and concurrency to create an isolated test PR. AutoHub never
		merges test PRs, even with automatic merge enabled. Successful tests close the PR and delete the
		branch.
	</p>
	<p class="text-xs text-muted-foreground">
		Tests continue on scheduler ticks after you leave this page. A test expires after one hour. On
		failure or cancellation, the PR closes and branch deletion waits 24 hours for a possible late
		cloud push.
	</p>
	{#if error}<p role="alert" class="text-sm text-destructive">
			{error} <button type="button" class="underline" onclick={load}>Retry</button>
		</p>{/if}
	{#if loading}<p class="text-sm text-muted-foreground">Loading tests…</p>
	{:else if tests.length === 0}<p class="text-sm text-muted-foreground">
			No PR test has run. A GitHub access check alone does not confirm an AI provider is ready.
		</p>{/if}
	<div class="space-y-3" aria-live="polite">
		{#each tests as test (test.id)}
			<article class="space-y-3 rounded-lg border p-4">
				<div class="flex flex-wrap items-center justify-between gap-2">
					<div>
						<span class="font-semibold"
							>{test.catalog_snapshot?.name ?? 'Legacy Codex'} · {outcomes[test.status]}</span
						><span class="ml-3 text-xs text-muted-foreground"
							>{new Date(test.created_at).toLocaleString()}</span
						>
					</div>
					{#if !test.configuration_current}<span class="text-xs text-amber-600"
							>Configuration changed — retest recommended</span
						>{/if}
				</div>
				{#if test.status === 'running'}<p class="text-sm">
						{test.test_spec?.phases?.[test.phase] ?? test.phase}{test.cancel_requested
							? ' · Cancellation requested'
							: ''}
					</p>{/if}
				{#if test.detail}<p class="text-sm text-muted-foreground">{test.detail}</p>{/if}
				<div class="flex flex-wrap gap-4 text-xs">
					{#each metadata(test).filter((item) => !item.origin) as item (item.key)}
						<span>{item.label}: {evidence(test, item.key) ?? 'pending'}</span>
					{/each}
					<span>Push: {test.evidence.verified_sha ? 'verified' : 'pending'}</span>
					<span>Cleanup: {test.cleanup_status}</span>
				</div>
				{#if test.cleanup_status === 'waiting'}<p class="text-xs text-muted-foreground">
						Cleanup continues for 24 hours to close late PR output and retain isolated branches.
					</p>{/if}
				{#if evidence(test, 'cleanup_warning')}<p class="text-xs text-muted-foreground">
						Provider reconciliation: {evidence(test, 'cleanup_warning')}. GitHub cleanup continues
						independently.
					</p>{/if}
				{#if evidence(test, 'cleanup_error')}<p class="text-xs text-destructive">
						Cleanup: {evidence(test, 'cleanup_error')}
					</p>{/if}
				<div class="flex flex-wrap items-center gap-3">
					{#each metadata(test).filter((item) => item.origin) as item (item.key)}
						{#if evidenceLink(test, item.key, item.origin)}
							<a
								href={evidenceLink(test, item.key, item.origin)}
								target="_blank"
								rel="noreferrer"
								class="text-sm text-primary underline">{item.label}</a
							>
						{/if}
					{/each}
					{#if test.status === 'running' || test.cleanup_status !== 'completed'}
						<Button size="sm" variant="outline" disabled={busy} onclick={() => act(test, 'advance')}
							>Check / continue now</Button
						>
					{/if}
					{#if test.status === 'running'}<Button
							size="sm"
							variant="outline"
							disabled={busy || test.cancel_requested}
							onclick={() => act(test, 'cancel')}>Cancel test</Button
						>{/if}
				</div>
			</article>
		{/each}
	</div>
</section>
