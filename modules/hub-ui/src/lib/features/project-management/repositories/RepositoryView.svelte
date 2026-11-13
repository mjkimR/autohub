<script lang="ts">
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { untrack, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { RepositorySelection, unitDirectory } from './repository-selection.svelte';
	import { page } from '$app/state';
	import { GitBranch, FolderGit2, Sparkles, RefreshCw, Layers } from '@lucide/svelte';
	import { SddViewer } from 'devkit-viewer';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import FileTreeTable from './FileTreeTable.svelte';
	import FileBlobViewer from './FileBlobViewer.svelte';
	import SddExecution from './SddExecution.svelte';
	import SddProposals from './SddProposals.svelte';
	import SddBatch from './SddBatch.svelte';
	import { repositoryDataSource } from './data-source';
	import type { RepoBlob, RepoInfo, RepoItem, RepoTree } from './types';

	let { project }: { project: components['schemas']['ProjectRead'] } = $props();

	let info = $state<RepoInfo | null>(null);
	let currentRef = $state<string>('');
	let currentPath = $state<string>('');
	let tree = $state<RepoTree | null>(null);
	let activeBlob = $state<RepoBlob | null>(null);
	let readmeBlob = $state<RepoBlob | null>(null);

	let isSdd = $derived(project.project_type === 'sdd');
	let selectedSpec = $state('');
	const selection = new RepositorySelection();
	const requestedUnit = $derived(page.url.searchParams.get('unit') || '');
	const requestedRef = $derived(page.url.searchParams.get('ref') || '');
	const requestedBatch = $derived(page.url.searchParams.get('batch') || '');
	$effect(() => {
		const id = project.id,
			sdd = isSdd,
			unit = requestedUnit,
			ref = requestedRef;
		userSelectedMode = null;
		untrack(() => {
			if (project.github) void selection.select(id, sdd, unit, ref);
		});
	});
	$effect(() => {
		info = selection.info;
		currentRef = selection.ref;
		selectedSpec = selection.unit;
		if (selection.status === 'ready') untrack(() => void loadTree('', selection.ref));
	});
	onDestroy(() => selection.destroy());
	function retrySelection() {
		void selection.select(project.id, isSdd, requestedUnit, requestedRef);
	}
	function browse() {
		const url = new URL(page.url);
		url.searchParams.delete('unit');
		if (selection.missingRef) url.searchParams.delete('ref');
		void goto(`${url.pathname}${url.search}`, { noScroll: true, keepFocus: true });
	}

	let userSelectedMode = $state<'default' | 'sdd' | null>(null);
	let viewerMode = $derived(userSelectedMode ?? (isSdd ? 'sdd' : 'default'));
	let viewerRevision = $state(0);
	let loading = $state(true);
	let error = $state('');
	let readVersion = 0;

	let breadcrumbs = $derived.by(() => {
		if (!currentPath) return [];
		const parts = currentPath.split('/').filter(Boolean);
		return parts.map((name, index) => ({
			name,
			path: parts.slice(0, index + 1).join('/')
		}));
	});

	async function loadTree(path: string = '', ref: string = currentRef) {
		const version = ++readVersion,
			projectId = project.id;
		loading = true;
		error = '';
		activeBlob = null;
		readmeBlob = null;
		try {
			const res = await api.GET('/api/v1/projects/{project_id}/repository/tree', {
				params: {
					path: { project_id: project.id },
					query: { path, ref }
				}
			});
			if (version !== readVersion || projectId !== project.id) return;
			if (res.error) throw new Error(apiErrorMessage(res.error, 'Could not load directory tree'));
			if (res.data) {
				tree = res.data;
				currentPath = path;

				// Check for README.md in current directory
				const items = res.data.items ?? [];
				const readmeItem = items.find(
					(i) => i.type === 'file' && i.name.toLowerCase() === 'readme.md'
				);
				if (readmeItem) {
					void loadReadme(readmeItem.path, ref);
				}
			}
		} catch (err) {
			if (version !== readVersion || projectId !== project.id) return;
			error = err instanceof Error ? err.message : 'Failed to load directory';
		} finally {
			if (version === readVersion && projectId === project.id) loading = false;
		}
	}

	async function loadReadme(path: string, ref: string = currentRef) {
		const projectId = project.id,
			version = readVersion;
		try {
			const res = await api.GET('/api/v1/projects/{project_id}/repository/blob', {
				params: {
					path: { project_id: project.id },
					query: { path, ref }
				}
			});
			if (ref !== currentRef || projectId !== project.id || version !== readVersion) return;
			if (res.data) {
				readmeBlob = res.data;
			}
		} catch {
			// Ignore readme load failures silently
		}
	}

	async function openFile(item: RepoItem) {
		const version = ++readVersion,
			projectId = project.id;
		loading = true;
		error = '';
		try {
			const res = await api.GET('/api/v1/projects/{project_id}/repository/blob', {
				params: {
					path: { project_id: project.id },
					query: { path: item.path, ref: currentRef }
				}
			});
			if (version !== readVersion || projectId !== project.id) return;
			if (res.error) throw new Error(apiErrorMessage(res.error, 'Could not load file content'));
			if (res.data) {
				activeBlob = res.data;
				currentPath = item.path;
			}
		} catch (err) {
			if (version !== readVersion || projectId !== project.id) return;
			error = err instanceof Error ? err.message : 'Failed to load file';
		} finally {
			if (version === readVersion && projectId === project.id) loading = false;
		}
	}

	async function refreshSdd() {
		await selection.select(project.id, isSdd, requestedUnit, requestedRef);
		viewerRevision++;
	}

	function handleBranchChange(newRef: string) {
		if (requestedUnit || requestedRef) {
			const url = new URL(page.url);
			url.searchParams.set('ref', newRef);
			void goto(`${url.pathname}${url.search}`, { noScroll: true, keepFocus: true });
			return;
		}
		currentRef = newRef;
		if (activeBlob) {
			void openFile({
				name: activeBlob.path.split('/').pop() || '',
				path: activeBlob.path,
				type: 'file',
				size: activeBlob.size,
				sha: activeBlob.sha
			});
		} else {
			void loadTree(currentPath, newRef);
		}
	}
</script>

<div class="space-y-6">
	{#if !project.github}
		<div class="rounded-xl border bg-card p-8 text-center">
			<FolderGit2 class="mx-auto h-10 w-10 text-muted-foreground/60" />
			<h3 class="mt-3 font-semibold text-foreground">No Repository Connected</h3>
			{#if requestedUnit || requestedBatch}
				<p role="alert" class="mt-2 text-sm">
					{requestedUnit ? 'Unit unavailable' : 'Batch unavailable'}: no repository is connected for
					the requested subject.
				</p>
				<Button variant="outline" size="sm" href={`/projects/${project.id}?tab=repository`}
					>Browse repository</Button
				>
			{/if}
			<p class="mt-1 text-sm text-muted-foreground">
				Connect a GitHub repository in the Connections tab to view and browse source files.
			</p>
		</div>
	{:else}
		<!-- Repository Control Bar -->
		<div
			class="flex flex-wrap items-center justify-between gap-4 rounded-xl border bg-card p-4 shadow-xs"
		>
			<div class="flex flex-wrap items-center gap-3">
				<!-- Branch Selector -->
				<div class="flex items-center gap-2 text-xs font-medium">
					<GitBranch class="h-3.5 w-3.5 text-muted-foreground" />
					{#if info && (info.branches ?? []).length > 0}
						<NativeSelect
							value={currentRef}
							aria-label="Repository branch"
							onchange={(e) => handleBranchChange(e.currentTarget.value)}
						>
							{#each info.branches ?? [] as branch (branch)}
								<option value={branch}>{branch}</option>
							{/each}
						</NativeSelect>
					{:else}
						<span class="font-mono text-xs">{currentRef || 'main'}</span>
					{/if}
				</div>

				<!-- Path Breadcrumbs -->
				<nav class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
					<button
						type="button"
						onclick={() => loadTree('', currentRef)}
						class="text-foreground transition-colors hover:underline"
					>
						{project.github.repository.split('/')[1] || project.github.repository}
					</button>

					{#each breadcrumbs as crumb, i (crumb.path)}
						<span class="text-muted-foreground/50">/</span>
						{#if i === breadcrumbs.length - 1 && activeBlob}
							<span class="font-semibold text-foreground">{crumb.name}</span>
						{:else}
							<button
								type="button"
								onclick={() => loadTree(crumb.path, currentRef)}
								class="hover:text-foreground hover:underline"
							>
								{crumb.name}
							</button>
						{/if}
					{/each}
				</nav>
			</div>

			<!-- View Mode & Action Controls -->
			<div class="flex items-center gap-2">
				{#if isSdd}
					<div class="flex rounded-lg border bg-muted/40 p-0.5 text-xs">
						<button
							type="button"
							onclick={() => (userSelectedMode = 'sdd')}
							class={`flex items-center gap-1.5 rounded-md px-3 py-1 font-medium transition-colors ${viewerMode === 'sdd' ? 'bg-primary text-primary-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'}`}
						>
							<Sparkles
								class="h-3.5 w-3.5 {viewerMode === 'sdd'
									? 'text-primary-foreground'
									: 'text-warning'}"
							/>
							Sdd View
						</button>
						<button
							type="button"
							onclick={() => (userSelectedMode = 'default')}
							class={`flex items-center gap-1.5 rounded-md px-3 py-1 font-medium transition-colors ${viewerMode === 'default' ? 'bg-background text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'}`}
						>
							<Layers class="h-3.5 w-3.5" />
							Git Browser
						</button>
					</div>
				{/if}

				<Button
					variant="outline"
					size="sm"
					class="h-8"
					onclick={() =>
						viewerMode === 'sdd'
							? refreshSdd()
							: activeBlob
								? openFile({
										name: '',
										path: activeBlob.path,
										type: 'file',
										size: activeBlob.size,
										sha: activeBlob.sha
									})
								: loadTree(currentPath, currentRef)}
				>
					<RefreshCw class="h-3.5 w-3.5" />
					Refresh
				</Button>
			</div>
		</div>

		{#if requestedUnit && selection.status === 'loading'}<p role="status">
				Loading requested unit {requestedUnit}…
			</p>{/if}
		{#if selection.status === 'unavailable' || selection.status === 'error'}
			<section role="alert" class="space-y-2 rounded-lg border p-4">
				<h3 class="font-semibold">Unit unavailable</h3>
				<p class="text-sm">{requestedUnit || requestedRef}: {selection.error}</p>
				{#if selection.status === 'error'}<Button
						variant="outline"
						size="sm"
						onclick={retrySelection}>Retry unit</Button
					>{/if}
				<Button variant="outline" size="sm" onclick={browse}>Browse repository</Button>
			</section>
		{/if}
		{#if requestedBatch && !isSdd}<p role="alert">
				Batch unavailable: this project does not support SDD batch selection.
			</p>
			<Button variant="outline" size="sm" href={`/projects/${project.id}?tab=repository`}
				>Browse repository</Button
			>{/if}
		{#if error}
			<div
				role="alert"
				class="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive"
			>
				{error}
				<button
					type="button"
					onclick={() => loadTree(currentPath, currentRef)}
					class="ml-2 font-semibold underline"
				>
					Retry
				</button>
			</div>
		{/if}

		{#if loading && !tree && !activeBlob && viewerMode !== 'sdd'}
			<div class="flex items-center justify-center py-20 text-sm text-muted-foreground">
				Loading repository…
			</div>
		{:else if viewerMode === 'sdd'}
			{#if isSdd && (!requestedUnit || selection.status === 'ready')}{#key project.id}<SddExecution
						projectId={project.id}
						repository={project.github.repository}
						{selectedSpec}
					/><SddProposals
						projectId={project.id}
						repository={project.github?.repository ?? ''}
					/>{/key}{/if}
			{#if isSdd}<SddBatch projectId={project.id} selectedBatchId={requestedBatch} />{/if}
			<!-- Native Sdd Viewer -->
			<section class="rounded-xl border bg-card p-4 shadow-xs">
				{#if selection.status === 'ready'}{#key `${project.id}-${currentRef}-${requestedUnit}-${viewerRevision}`}
						<SddViewer
							dataSource={repositoryDataSource(project.id)}
							branch={currentRef || 'main'}
							repoId={project.github?.repository || project.name}
							initialView={selectedSpec ? 'files' : 'dashboard'}
							initialPath={selectedSpec
								? `${selectedSpec}/${selectedSpec.startsWith('specs/') ? 'spec.md' : 'proposal.md'}`
								: 'docs/'}
							onselectpath={(path) => {
								const unit =
									path.match(/^(specs\/\d{4}-\d{2}\/[^/]+|docs\/proposals\/PROP-[^/]+)/)?.[1] || '';
								selectedSpec = unitDirectory.test(unit) ? unit : '';
							}}
						/>
					{/key}{/if}
			</section>
		{:else if activeBlob}
			<!-- File Content Viewer -->
			<FileBlobViewer
				blob={activeBlob}
				onback={() => {
					const parent = activeBlob?.path.split('/').slice(0, -1).join('/') || '';
					void loadTree(parent, currentRef);
				}}
			/>
		{:else if tree}
			<!-- Directory File List & Readme Preview -->
			<div class="space-y-6">
				<FileTreeTable
					items={tree.items ?? []}
					{currentPath}
					onnavigate={(dir) => loadTree(dir, currentRef)}
					onselect={(file) => openFile(file)}
				/>

				{#if readmeBlob}
					<div class="space-y-2">
						<div
							class="flex items-center gap-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase"
						>
							<span>README.md</span>
						</div>
						<FileBlobViewer blob={readmeBlob} />
					</div>
				{/if}
			</div>
		{/if}
	{/if}
</div>
