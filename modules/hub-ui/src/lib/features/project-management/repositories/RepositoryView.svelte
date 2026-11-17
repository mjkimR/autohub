<script lang="ts">
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { untrack, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { RepositorySelection } from './repository-selection.svelte';
	import { page } from '$app/state';
	import { GitBranch, FolderGit2, Sparkles, RefreshCw, Layers } from '@lucide/svelte';
	import NativeSddViewer from './documents/NativeSddViewer.svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { readableLoadError } from '../pipeline-runs/load-errors';
	import { Button } from '$lib/components/ui/button';
	import FileTreeTable from './FileTreeTable.svelte';
	import FileBlobViewer from './FileBlobViewer.svelte';
	import SddUnitActions from './SddUnitActions.svelte';
	import SddStartOutcome from './SddStartOutcome.svelte';
	import SddUnitJump from './SddUnitJump.svelte';
	import { sddStarts } from './sdd-starts.svelte';
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
	const documentSource = $derived(repositoryDataSource(project.id));
	const starts = $derived(sddStarts(project.id));
	const requestedPath = $derived(page.url.searchParams.get('path') || '');
	const selection = new RepositorySelection();
	const requestedUnit = $derived(page.url.searchParams.get('unit') || '');
	const requestedRef = $derived(page.url.searchParams.get('ref') || '');
	const selectionUnit = $derived(requestedPath ? '' : requestedUnit);
	$effect(() => {
		const id = project.id,
			sdd = isSdd,
			unit = selectionUnit,
			ref = requestedRef;
		++readVersion;
		tree = activeBlob = readmeBlob = null;
		currentPath = '';
		error = '';
		untrack(() => {
			if (project.github) void selection.select(id, sdd, unit, ref);
		});
	});
	$effect(() => {
		info = selection.info;
		currentRef = selection.ref;
		loading = selection.status === 'loading';
		if (selection.status === 'ready') untrack(() => void loadTree('', selection.ref));
	});
	$effect(() => {
		void project.id;
		userSelectedMode = null;
	});
	$effect(() => {
		const status = selection.status,
			path = requestedPath,
			ref = currentRef,
			mode = viewerMode;
		if (status === 'ready' && mode === 'default')
			untrack(() => {
				if (path && (activeBlob?.path !== path || activeBlob.ref !== ref))
					void openFile({
						name: path.split('/').pop() || path,
						path,
						type: 'file',
						size: 0,
						sha: ''
					});
				else if (!path && activeBlob) void loadTree('', ref);
			});
	});
	onDestroy(() => selection.destroy());
	function selectDocument(path: string) {
		if (!path || path === requestedPath) return;
		const url = new URL(page.url);
		url.searchParams.set('path', path);
		url.searchParams.set('ref', currentRef);
		url.searchParams.delete('unit');
		void goto(`${url.pathname}${url.search}`, { noScroll: true, keepFocus: true });
	}
	function clearDocument() {
		if (!requestedPath && !requestedUnit) return;
		const url = new URL(page.url);
		url.searchParams.delete('path');
		url.searchParams.delete('unit');
		void goto(`${url.pathname}${url.search}`, { noScroll: true, keepFocus: true });
	}
	function retrySelection() {
		void selection.select(project.id, isSdd, selectionUnit, requestedRef);
	}
	function browse() {
		const url = new URL(page.url);
		url.searchParams.delete('unit');
		url.searchParams.delete('path');
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
			error = readableLoadError(err, "Couldn't load this directory.");
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
				selectDocument(item.path);
			}
		} catch (err) {
			if (version !== readVersion || projectId !== project.id) return;
			error = readableLoadError(err, "Couldn't load this file.");
		} finally {
			if (version === readVersion && projectId === project.id) loading = false;
		}
	}

	async function refreshSdd() {
		await selection.select(
			project.id,
			isSdd,
			requestedPath ? '' : requestedUnit,
			requestedRef || currentRef
		);
		viewerRevision++;
	}

	function handleBranchChange(newRef: string) {
		if (isSdd || requestedUnit || requestedRef) {
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
			{#if requestedUnit}
				<p role="alert" class="mt-2 text-sm">
					Unit unavailable: no repository is connected for the requested subject.
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
			<div class="flex flex-wrap items-center gap-2">
				{#if isSdd}
					<div
						class="flex rounded-lg border p-0.5"
						role="group"
						aria-label="Repository viewer mode"
					>
						<Button
							size="sm"
							variant={viewerMode === 'sdd' ? 'secondary' : 'ghost'}
							aria-pressed={viewerMode === 'sdd'}
							onclick={() => (userSelectedMode = 'sdd')}
							><Sparkles aria-hidden="true" />SDD View</Button
						>
						<Button
							size="sm"
							variant={viewerMode === 'default' ? 'secondary' : 'ghost'}
							aria-pressed={viewerMode === 'default'}
							onclick={() => (userSelectedMode = 'default')}
							><Layers aria-hidden="true" />Git Browser</Button
						>
					</div>
				{/if}

				<Button
					variant="outline"
					size="sm"
					disabled={loading}
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

		{#if isSdd}<SddStartOutcome
				state={starts}
				projectId={project.id}
				repository={project.github.repository}
			/>{/if}
		{#if selection.status === 'loading' && !requestedUnit}<p
				role="status"
				class="text-sm text-muted-foreground"
			>
				Loading repository…
			</p>{/if}
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
			<!-- Native SDD Viewer: only a ready selection has a workspace; other states show their message above. -->
			{#if selection.status === 'ready'}<section class="rounded-xl border bg-card p-4 shadow-xs">
					{#key `${project.id}-${currentRef}-${viewerRevision}`}
						<NativeSddViewer
							dataSource={documentSource}
							branch={currentRef || 'main'}
							initialPath={requestedPath ||
								(requestedUnit && selection.unit
									? `${selection.unit}/${selection.unit.startsWith('specs/') ? 'spec.md' : 'proposal.md'}`
									: '')}
							onselectpath={selectDocument}
							onclearpath={clearDocument}
							unitActions={isSdd ? unitActions : undefined}
							unitJump={isSdd ? unitJump : undefined}
						/>
					{/key}
				</section>{/if}
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

{#snippet unitActions(path: string)}
	<SddUnitActions
		projectId={project.id}
		repository={project.github?.repository || ''}
		{path}
		branch={currentRef}
	/>
{/snippet}

{#snippet unitJump(path: string)}<SddUnitJump {path} />{/snippet}
