<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { noticeSelection, clearNoticeReturn } from '$lib/features/auth/login/notice-return';
	import { api, type components } from '$lib/api';
	import { responseData } from '$lib/api/pagination';
	import { Button } from '$lib/components/ui/button';
	import RunDecisionsDialog from './RunDecisionsDialog.svelte';
	type Entry = components['schemas']['DecisionEntryRead'];
	type Run = components['schemas']['PipelineRunRead'];
	type Kind = Entry['kind'];
	const kinds: Kind[] = [
		'run-question',
		'native-hub-question',
		'native-worker-question',
		'native-workflow',
		'native-proposal',
		'native-integration'
	];
	let items = $state<Entry[]>([]);
	let kind = $state<Kind | ''>('');
	let questionState = $state<'' | 'open' | 'answered'>('');
	let projectId = $state('');
	let projects = $state<{ id: string; name: string }[]>([]);
	let cursor = $state<string | undefined>();
	let previous = $state<(string | undefined)[]>([]);
	let next = $state<string | null>(null);
	let busy = $state(false);
	let error = $state('');
	let landing = $state(false);
	let noticeError = $state('');
	let selected = $state<{ entry: Entry; run: Run } | null>(null);
	let origin = $state('');
	let originIndex = $state(0);
	let rows: HTMLDivElement;
	let generation = 0;
	async function load(reset = false) {
		if (reset) {
			cursor = undefined;
			previous = [];
		}
		const own = ++generation;
		busy = true;
		error = '';
		try {
			const data = responseData(
				await api.GET('/api/v1/pipeline-runs/decisions', {
					params: {
						query: {
							project_id: projectId || undefined,
							kind: kind || undefined,
							question_state: questionState || undefined,
							cursor,
							limit: 20
						}
					}
				}),
				'Unable to load observed pending decisions'
			);
			if (own !== generation) return;
			items = data.items;
			next = data.next_cursor;
		} catch (e) {
			if (own === generation) {
				error = e instanceof Error ? e.message : 'Unable to load decisions';
				items = [];
			}
		} finally {
			if (own === generation) busy = false;
		}
	}
	async function review(entry: Entry, index: number) {
		if (busy) return;
		busy = true;
		error = '';
		origin = entry.key;
		originIndex = index;
		try {
			const run = responseData(
				await api.GET('/api/v1/pipeline-runs/{run_id}', {
					params: { path: { run_id: entry.run_id } }
				}),
				'Owner unavailable'
			);
			selected = { entry, run };
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unable to open owner';
		} finally {
			busy = false;
		}
	}
	async function close() {
		selected = null;
		await load();
		await tick();
		const buttons = [...rows.querySelectorAll<HTMLButtonElement>('button[data-key]')];
		(
			buttons.find((b) => b.dataset.key === origin) ??
			buttons[Math.min(originIndex, buttons.length - 1)]
		)?.focus();
	}
	async function openNotice() {
		const url = new URL(window.location.href);
		if (!url.searchParams.has('decision_key') && !url.searchParams.has('decision_fingerprint'))
			return;
		const selection = noticeSelection(url);
		if (!selection) {
			noticeError = 'This decision link is malformed. Open the current inbox.';
			return;
		}
		landing = true;
		noticeError = '';
		try {
			const entry = responseData(
				await api.GET('/api/v1/pipeline-runs/decisions/selection', {
					params: { query: selection }
				}),
				'This decision is unavailable or changed'
			);
			const run = responseData(
				await api.POST('/api/v1/pipeline-runs/decisions/review', { body: selection }),
				'Decision inspection failed; retry review explicitly'
			);
			selected = { entry, run };
		} catch (e) {
			noticeError = e instanceof Error ? e.message : 'Decision unavailable';
		} finally {
			landing = false;
		}
	}
	function openInbox() {
		clearNoticeReturn();
		noticeError = '';
		const url = new URL(window.location.href);
		url.searchParams.delete('decision_key');
		url.searchParams.delete('decision_fingerprint');
		window.history.replaceState(window.history.state, '', url);
		void load(true);
	}
	onMount(() => {
		void load().then(openNotice);
		void api.GET('/api/v1/projects', { params: { query: { limit: 100 } } }).then((result) => {
			if (result.data) projects = result.data.items;
		});
	});
</script>

<div class="space-y-5" bind:this={rows}>
	{#if landing}<p role="status">Inspecting the exact decision from this notice…</p>{/if}
	{#if noticeError}<div role="alert">
			<p>{noticeError}</p>
			<Button disabled={landing} onclick={openNotice}>Retry review</Button><Button
				variant="outline"
				onclick={openInbox}>Open inbox</Button
			>
		</div>{/if}
	<div>
		<h1 class="text-2xl font-semibold">Decisions</h1>
		<p class="text-sm text-muted-foreground">
			Observed pending decisions across projects. New or changed subjects may precede this page;
			Refresh restarts the list.
		</p>
	</div>
	<div class="flex flex-wrap items-end gap-3">
		<label class="text-sm"
			>Project<select
				class="mt-1 block rounded border bg-background p-2"
				bind:value={projectId}
				onchange={() => load(true)}
				><option value="">All projects</option>{#each projects as project (project.id)}<option
						value={project.id}>{project.name}</option
					>{/each}</select
			></label
		>
		<label class="text-sm"
			>Kind<select
				class="mt-1 block rounded border bg-background p-2"
				bind:value={kind}
				onchange={() => load(true)}
				><option value="">All kinds</option>{#each kinds as value (value)}<option {value}
						>{value.replaceAll('-', ' ')}</option
					>{/each}</select
			></label
		>
		<label class="text-sm"
			>Question state<select
				class="mt-1 block rounded border bg-background p-2"
				bind:value={questionState}
				onchange={() => load(true)}
				><option value="">All states</option><option value="open">Needs answer</option><option
					value="answered">Answer saved</option
				></select
			></label
		>
		<Button variant="outline" disabled={busy} onclick={() => load(true)}>Refresh</Button>
		<Button
			variant="ghost"
			disabled={busy}
			onclick={() => {
				projectId = '';
				kind = '';
				questionState = '';
				void load(true);
			}}>Clear filters</Button
		>
	</div>
	{#if error}<p role="alert">{error}</p>
		<Button onclick={() => load()}>Retry</Button>{/if}
	{#if busy}<p role="status">Loading observed decisions…</p>{/if}
	{#if !busy && !error && !items.length}<p>No matching observed pending decisions.</p>{/if}
	{#each items as entry, index (entry.key)}
		<article class="flex items-center justify-between gap-4 rounded-lg border p-4">
			<div class="min-w-0 space-y-1">
				<p class="font-medium break-words">{entry.title}</p>
				<p class="text-sm">
					<a class="underline" href={entry.pull_url} target="_blank" rel="noreferrer"
						>PR #{entry.pull_number}</a
					>
					· {entry.run_state.replaceAll('_', ' ')}
				</p>
				<p class="text-sm">
					{projects.find((p) => p.id === entry.project_id)?.name ?? entry.project_id} · {entry.kind.replaceAll(
						'-',
						' '
					)} · {entry.subject_id}
				</p>
				<p class="text-sm">
					{!entry.actionable
						? 'Answer publication pending'
						: entry.question_state === 'answered'
							? 'Answer saved'
							: 'Needs decision'}
				</p>
				<p class="text-xs text-muted-foreground">
					{entry.kind === 'run-question' ? 'Waiting since' : 'First observed waiting'}
					{new Date(entry.waiting_since).toLocaleString()} · Evidence observed {new Date(
						entry.observed_at
					).toLocaleString()}{entry.head_sha ? ` · ${entry.head_sha.slice(0, 8)}` : ''}
				</p>
			</div>
			<Button
				data-key={entry.key}
				disabled={busy || !entry.actionable}
				onclick={() => review(entry, index)}>Review</Button
			>
		</article>
	{/each}
	<div class="flex gap-3">
		<Button
			variant="outline"
			disabled={busy || !previous.length}
			onclick={() => {
				cursor = previous[previous.length - 1];
				previous = previous.slice(0, -1);
				void load();
			}}>Previous</Button
		>
		<Button
			variant="outline"
			disabled={busy || !next}
			onclick={() => {
				previous = [...previous, cursor];
				cursor = next ?? undefined;
				void load();
			}}>Next</Button
		>
	</div>
</div>
{#if selected}<RunDecisionsDialog
		run={selected.run}
		selection={selected.entry}
		onclose={() => void close()}
		onchange={() => void load()}
	/>{/if}
