<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { CircleCheck, RefreshCw } from '@lucide/svelte';
	import LoadError from '$lib/components/shared/LoadError.svelte';
	import { Button } from '$lib/components/ui/button';
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { AttentionState } from './attention.svelte';
	import OwedGroupSection from './OwedGroupSection.svelte';
	import { groupOwedItems } from './owed-kinds';
	import { useOwedCounts } from './owed-counts.svelte';
	import { attentionHref, type OwedKind } from './owed-links';

	const attention = new AttentionState();
	// `?project=<id>` is the filter, so project screens can link to their own slice of the landing.
	const urlProject = $derived(page.url.searchParams.get('project') ?? '');
	attention.projectId = untrack(() => urlProject);
	$effect(() => {
		const project = urlProject;
		untrack(() => attention.setProject(project));
	});

	function chooseProject(projectId: string) {
		attention.setProject(projectId);
		void goto(attentionHref(projectId), { replaceState: true, keepFocus: true, noScroll: true });
	}
	const counts = useOwedCounts();

	const groups = $derived(groupOwedItems(attention.items));
	const owedGroups = $derived(groups.filter((group) => !group.quiet));
	const quietGroups = $derived(groups.filter((group) => group.quiet));
	// Shell counts cover all visible projects, so they size groups only while no project is chosen.
	const known = $derived(
		!attention.projectId && counts?.value.status === 'known' ? counts.value : null
	);
	const empty = $derived(attention.loaded && owedGroups.length === 0 && !attention.hasMore);
	const summary = $derived.by(() => {
		if (!known || known.total === 0 || empty) return '';
		return known.total === 1 ? '1 item needs you.' : `${known.total} items need you.`;
	});
	// With every page loaded the rows are the whole answer; counts only size a partial list.
	const groupTotal = (kind: OwedKind) => (attention.hasMore ? known?.byKind[kind] : undefined);
	// Read once per render so every row ages from the same moment.
	const now = $derived(attention.loaded ? Date.now() : 0);

	function refresh() {
		void attention.load();
		void counts?.refresh();
	}

	onMount(() => {
		// One fresh counts read past the navigation throttle so groups and summary agree with the
		// rows; the store stays single-flight, so a shell read already in flight is reused.
		void counts?.refresh();
		void attention.load();
		void attention.loadProjects();
	});
</script>

{#snippet skeletonRows()}
	<ul aria-hidden="true" class="divide-y divide-border/70 rounded-xl border border-border bg-card">
		{#each [0, 1, 2] as row (row)}
			<li class="flex items-center justify-between gap-6 px-4 py-4">
				<div class="w-full max-w-md space-y-2">
					<div class="h-3.5 w-3/4 rounded bg-muted"></div>
					<div class="h-3 w-1/2 rounded bg-muted"></div>
				</div>
				<div class="h-8 w-24 shrink-0 rounded-md bg-muted"></div>
			</li>
		{/each}
	</ul>
{/snippet}

<div class="space-y-6" aria-busy={attention.loading}>
	<header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
		<div class="space-y-1">
			<h1 class="text-2xl font-semibold tracking-tight">Attention</h1>
			<p class="text-sm text-muted-foreground">
				Work waiting for you across projects, most consequential first.
				{#if summary}<span class="font-medium text-foreground" data-owed-summary>{summary}</span
					>{/if}
			</p>
		</div>
		<div class="flex flex-wrap items-end gap-3">
			<label class="text-sm font-medium"
				>Project<NativeSelect
					class="mt-1 flex"
					value={attention.projectId}
					onchange={(event) => chooseProject(event.currentTarget.value)}
					><option value="">All projects</option
					>{#each attention.projects as project (project.id)}<option value={project.id}
							>{project.name}</option
						>{/each}</NativeSelect
				></label
			>
			<Button variant="outline" disabled={attention.loading} onclick={refresh}>
				<RefreshCw
					aria-hidden="true"
					class={['size-4', attention.loading && 'animate-spin motion-reduce:animate-none']}
				/>
				Refresh
			</Button>
		</div>
	</header>

	{#if attention.error}
		<div class="space-y-1.5">
			<LoadError
				message={attention.error}
				retry={() => (attention.loaded ? refresh() : attention.load())}
			/>
			<p class="text-xs text-muted-foreground" data-owed-error-note>
				{attention.loaded
					? 'Showing the last loaded items; they may have changed.'
					: 'What needs you is unknown until this loads; nothing is assumed resolved.'}
			</p>
		</div>
	{/if}

	{#if !attention.loaded}
		{#if attention.loading || !attention.error}
			<div class="space-y-3">
				<p role="status" class="text-sm text-muted-foreground">Loading what needs you…</p>
				{@render skeletonRows()}
			</div>
		{/if}
	{:else}
		{#if empty}
			<section
				aria-labelledby="owed-empty"
				class="flex flex-col items-start gap-3 rounded-xl border border-border bg-card px-5 py-6 sm:flex-row sm:items-center"
				data-owed-empty
			>
				<span
					class="flex size-10 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground"
				>
					<CircleCheck aria-hidden="true" class="size-5" />
				</span>
				<div class="min-w-0 flex-1 space-y-0.5">
					<h2 id="owed-empty" class="text-base font-semibold">
						{attention.projectId ? 'Nothing needs you in this project' : 'Nothing needs you'}
					</h2>
					<p class="text-sm text-muted-foreground">
						No decisions, held PR runs, Work Plans, batches or cleanups are waiting. Automation
						carries on without you.
					</p>
				</div>
				{#if attention.projectId}
					<Button variant="outline" size="sm" onclick={() => chooseProject('')}
						>Show all projects</Button
					>
				{:else}
					<Button variant="link" size="sm" href="/projects/runs">Review PR runs</Button>
				{/if}
			</section>
		{/if}

		{#each owedGroups as group (group.kind)}
			<OwedGroupSection
				{group}
				total={groupTotal(group.kind)}
				projectName={(id) => attention.projectName(id)}
				{now}
			/>
		{/each}

		{#if attention.hasMore}
			<div class="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:gap-4">
				<Button
					variant="outline"
					disabled={attention.loadingMore || attention.loading}
					onclick={() => attention.loadMore()}
				>
					{attention.loadingMore ? 'Loading…' : 'Load more'}
				</Button>
				<p class="text-xs text-muted-foreground">
					Showing the {attention.items.length} longest-waiting items; groups fill in as you load more.
				</p>
			</div>
		{/if}

		{#each quietGroups as group (group.kind)}
			<OwedGroupSection
				{group}
				total={groupTotal(group.kind)}
				projectName={(id) => attention.projectName(id)}
				{now}
			/>
		{/each}
	{/if}
</div>
