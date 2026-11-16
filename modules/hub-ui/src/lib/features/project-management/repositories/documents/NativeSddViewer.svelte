<script lang="ts">
	import { onDestroy, untrack, type Snippet } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import { NativeSelect } from '$lib/components/ui/native-select';
	import type { RepositoryDataSource } from '../data-source';
	import type { DocumentSection } from './model';
	import { DocumentViewerState } from './viewer-state.svelte';
	import DocumentList from './DocumentList.svelte';
	import MilestoneList from './MilestoneList.svelte';
	import DocumentPreview from './DocumentPreview.svelte';
	let {
		dataSource,
		branch,
		initialPath = '',
		onselectpath,
		unitActions
	}: {
		dataSource: RepositoryDataSource;
		branch: string;
		initialPath?: string;
		onselectpath: (path: string) => void;
		unitActions?: Snippet<[string]>;
	} = $props();
	const state = new DocumentViewerState((path) => onselectpath(path));
	const sections: { id: DocumentSection; label: string }[] = [
		{ id: 'documents', label: 'Documents' },
		{ id: 'proposals', label: 'Proposals' },
		{ id: 'specs', label: 'Specs' },
		{ id: 'roadmap', label: 'Roadmap' },
		{ id: 'handbook', label: 'Handbook' },
		{ id: 'files', label: 'Files' }
	];
	$effect(() => {
		const source = dataSource,
			ref = branch;
		untrack(() => state.configure(source, ref, initialPath));
	});
	$effect(() => {
		const path = initialPath;
		if (path)
			untrack(() => {
				if (path !== state.blob?.path && path !== state.requestedPath) void state.open(path);
			});
	});
	onDestroy(() => state.destroy());
	const open = (path: string, fragment = '') => {
		void state.open(path, fragment);
	};
	const parent = () =>
		state.directoryTo((state.blob?.path || state.directory).split('/').slice(0, -1).join('/'));
</script>

<section aria-label="SDD repository documents" class="space-y-5">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<nav aria-label="SDD document sections" class="flex flex-wrap gap-2">
			{#each sections as section (section.id)}<Button
					variant={state.section === section.id ? 'secondary' : 'ghost'}
					size="sm"
					aria-pressed={state.section === section.id}
					onclick={() => state.changeSection(section.id)}>{section.label}</Button
				>{/each}
		</nav>
		<p class="text-xs text-muted-foreground">
			Browsing branch: <span class="font-mono">{branch}</span>
		</p>
	</div>
	{#if state.loading}<p role="status" class="text-sm text-muted-foreground">
			Loading {state.section} on {branch}…
		</p>{/if}
	{#if state.error || state.listing.errors.length}
		<div role="alert" class="space-y-2 rounded-lg border p-3 text-sm">
			<p class="font-medium">Document listing incomplete</p>
			{#if state.error}<p>{state.error}</p>{/if}{#each state.listing.errors as error (error)}<p
					class="break-words"
				>
					{error}
				</p>{/each}
			<Button variant="outline" size="sm" onclick={() => state.retry()}>Retry documents</Button>
		</div>
	{/if}
	{#if state.section === 'handbook' && !state.loading && !state.error}
		{#if state.manifest}
			<div class="flex flex-wrap items-center gap-3">
				<p class="text-sm">Handbook release: {state.manifest.tag}</p>
				<label class="text-sm"
					>Handbook language<NativeSelect
						value={state.language}
						onchange={(event) => state.chooseLanguage(event.currentTarget.value)}
						>{#each state.manifest.langs as lang (lang)}<option value={lang}>{lang}</option
							>{/each}</NativeSelect
					></label
				><Button variant="ghost" size="sm" onclick={() => state.chooseLanguage(state.language)}
					>Handbook home</Button
				>
			</div>
		{:else}<p class="text-sm text-muted-foreground">
				No release handbook on this branch. Choose Documents or Files to browse the repository.
			</p>{/if}
	{/if}
	<div class="grid min-w-0 gap-6 lg:grid-cols-3 xl:grid-cols-4">
		<div class="min-w-0 space-y-4">
			{#if ['documents', 'proposals', 'specs'].includes(state.section)}<DocumentList
					documents={state.listing.documents}
					bind:query={state.query}
					selectedPath={state.blob?.path}
					loading={state.loading}
					onopen={open}
				/>
			{:else if state.section === 'roadmap'}<MilestoneList
					documents={state.listing.documents}
					onopen={open}
				/>
			{:else if state.section === 'files'}
				<p class="font-mono text-xs break-all text-muted-foreground">/{state.directory}</p>
				{#if state.directory}<Button variant="ghost" size="sm" onclick={() => parent()}
						>Parent directory</Button
					>{/if}
				{#if !state.loading && !state.files.length && !state.error}<p
						class="text-sm text-muted-foreground"
					>
						Empty directory. Choose another section or return to the parent.
					</p>{/if}
				<ul class="space-y-2" aria-label="Repository files">
					{#each state.files as file (file.path)}<li>
							<Button
								variant="ghost"
								size="sm"
								onclick={() =>
									file.type === 'dir' ? state.directoryTo(file.path) : open(file.path)}
								>{file.name}{file.type === 'dir' ? '/' : ''}</Button
							>
						</li>{/each}
				</ul>
			{/if}
		</div>
		<div class="min-w-0 space-y-4 lg:col-span-2">
			{#if state.reading}<p role="status" class="text-sm text-muted-foreground">
					Loading {state.requestedPath || 'document reference'} on {branch}…
				</p>{/if}
			{#if state.readError}<div role="alert" class="space-y-2 text-sm">
					<p class="break-words">{state.readError}</p>
					<Button variant="outline" size="sm" onclick={() => state.retryRead()}
						>Retry document</Button
					>
				</div>{/if}
			{#if state.blob}
				{#key state.blob.path}<DocumentPreview
						blob={state.blob}
						fragment={state.fragment}
						onopen={open}
						onreference={(id) => state.reference(id)}
						ondirectory={(path) => state.directoryTo(path)}
						onback={state.section === 'files'
							? () => {
									void parent();
								}
							: undefined}
					/>{/key}
			{:else if !state.reading && !state.readError && !state.loading && state.section !== 'handbook'}<p
					class="text-sm text-muted-foreground"
				>
					Select a document to inspect it. Reading does not start work.
				</p>{/if}
		</div>
		{#if state.blob && unitActions}<aside class="min-w-0 lg:col-span-3 xl:col-span-1">
				{@render unitActions(state.blob.path)}
			</aside>{/if}
	</div>
</section>
