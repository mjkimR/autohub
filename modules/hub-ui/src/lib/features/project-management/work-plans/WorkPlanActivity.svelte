<script lang="ts">
	import { untrack } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import WorkPlanChanges from './WorkPlanChanges.svelte';

	let { projectId, planId, revision }: { projectId: string; planId: string; revision: number } =
		$props();
	type Activity = components['schemas']['PlanActivityRead'];
	let open = $state(false);
	let commentsOnly = $state(false);
	let entries = $state<Activity[]>([]);
	let total = $state(0);
	let loading = $state(false);
	let saving = $state(false);
	let error = $state('');
	let body = $state('');
	let requestId = crypto.randomUUID();
	let submittedBody: string | undefined;
	let generation = 0;
	let nextOffset = $state(0);
	async function load(more = false) {
		const current = ++generation;
		loading = true;
		try {
			const result = await api.GET('/api/v1/projects/{project_id}/work-plans/{plan_id}/activity', {
				params: {
					path: { project_id: projectId, plan_id: planId },
					query: { offset: more ? nextOffset : 0, limit: 25, comments_only: commentsOnly }
				}
			});
			if (!result.data) throw new Error(apiErrorMessage(result.error, 'Could not load activity'));
			if (current !== generation) return;
			nextOffset = (more ? nextOffset : 0) + result.data.items.length;
			entries = more
				? [...new Map([...entries, ...result.data.items].map((row) => [row.id, row])).values()]
				: result.data.items;
			total = result.data.total_count;
			error = '';
		} catch (e) {
			if (current === generation)
				error = e instanceof Error ? e.message : 'Could not load activity';
		} finally {
			if (current === generation) loading = false;
		}
	}
	$effect(() => {
		if (open) {
			void revision;
			void commentsOnly;
			untrack(() => {
				void load();
			});
		}
	});
	async function comment() {
		saving = true;
		error = '';
		if (submittedBody !== undefined && submittedBody !== body) requestId = crypto.randomUUID();
		submittedBody = body;
		try {
			const result = await api.POST('/api/v1/projects/{project_id}/work-plans/{plan_id}/comments', {
				params: { path: { project_id: projectId, plan_id: planId } },
				body: { request_id: requestId, body }
			});
			if (!result.data) throw new Error(apiErrorMessage(result.error, 'Could not save comment'));
			body = '';
			submittedBody = undefined;
			requestId = crypto.randomUUID();
			await load();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not save comment';
		} finally {
			saving = false;
		}
	}
</script>

<details class="rounded-lg border p-4" bind:open>
	<summary class="cursor-pointer text-sm font-medium">Activity and comments</summary>
	{#if open}
		<div class="mt-4 space-y-4">
			<div class="flex flex-wrap items-center gap-4">
				<label class="flex items-center gap-2 text-sm"
					><input type="checkbox" bind:checked={commentsOnly} />Comments only</label
				>
				<Button variant="ghost" disabled={loading} onclick={() => load()}>Refresh activity</Button>
			</div>
			{#if error}<p role="alert" class="text-sm text-destructive">{error}</p>{/if}
			<form
				class="space-y-2"
				onsubmit={(event) => {
					event.preventDefault();
					void comment();
				}}
			>
				<label class="block space-y-2 text-sm"
					>Comment
					<textarea
						class="min-h-20 w-full rounded-md border bg-background p-2"
						required
						maxlength={8000}
						disabled={saving}
						bind:value={body}></textarea>
				</label>
				<p class="text-xs text-muted-foreground">
					Comments add context. They do not change the specification or start work. Use Run
					decisions for execution questions.
				</p>
				<Button type="submit" disabled={saving || !body.trim()}
					>{saving ? 'Saving…' : 'Add comment'}</Button
				>
			</form>
			{#if loading}<p class="text-sm text-muted-foreground">Loading activity…</p>{/if}
			{#if !loading && !entries.length}<p class="text-sm text-muted-foreground">
					No activity yet.
				</p>{/if}
			<ol class="space-y-3">
				{#each entries as entry (entry.id)}
					<li class="space-y-2 border-l-2 pl-4 text-sm">
						<p class="text-muted-foreground">
							{entry.kind} · {entry.actor} · {new Date(entry.created_at).toLocaleString()} · revision
							{entry.revision}
						</p>
						{#if entry.body}<p class="whitespace-pre-wrap">{entry.body}</p>{/if}
						{#if Object.keys(entry.changes).length}
							<WorkPlanChanges changes={entry.changes} />
						{/if}
					</li>
				{/each}
			</ol>
			{#if nextOffset < total}<Button
					variant="outline"
					disabled={loading}
					onclick={() => load(true)}>Load more activity</Button
				>{/if}
		</div>
	{/if}
</details>
