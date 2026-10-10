<script lang="ts">
	import { onMount } from 'svelte';
	import { GitBranch, FolderGit2, Sparkles, RefreshCw, Layers } from '@lucide/svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import FileTreeTable from './FileTreeTable.svelte';
	import FileBlobViewer from './FileBlobViewer.svelte';
	import SpecrigViewer from './specrig/SpecrigViewer.svelte';
	import { repositoryDataSource } from './data-source';
	import type { RepoBlob, RepoInfo, RepoItem, RepoTree } from './types';

	let { project }: { project: components['schemas']['ProjectRead'] } = $props();

	let info = $state<RepoInfo | null>(null);
	let currentRef = $state<string>('');
	let currentPath = $state<string>('');
	let tree = $state<RepoTree | null>(null);
	let activeBlob = $state<RepoBlob | null>(null);
	let readmeBlob = $state<RepoBlob | null>(null);

	let isSpecrig = $derived(project.project_type === 'specrig');
	let userSelectedMode = $state<'default' | 'specrig' | null>(null);
	let viewerMode = $derived(userSelectedMode ?? (isSpecrig ? 'specrig' : 'default'));
	let viewerRevision = $state(0);
	let loading = $state(true);
	let error = $state('');

	let breadcrumbs = $derived.by(() => {
		if (!currentPath) return [];
		const parts = currentPath.split('/').filter(Boolean);
		return parts.map((name, index) => ({
			name,
			path: parts.slice(0, index + 1).join('/')
		}));
	});

	async function loadInfo() {
		try {
			const res = await api.GET('/api/v1/projects/{project_id}/repository/info', {
				params: { path: { project_id: project.id } }
			});
			if (res.error) throw new Error(apiErrorMessage(res.error, 'Could not load repository info'));
			if (res.data) {
				info = res.data;
				if (!currentRef) {
					currentRef = res.data.default_branch;
				}
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load repository info';
		}
	}

	async function loadTree(path: string = '', ref: string = currentRef) {
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
			error = err instanceof Error ? err.message : 'Failed to load directory';
		} finally {
			loading = false;
		}
	}

	async function loadReadme(path: string, ref: string = currentRef) {
		try {
			const res = await api.GET('/api/v1/projects/{project_id}/repository/blob', {
				params: {
					path: { project_id: project.id },
					query: { path, ref }
				}
			});
			if (res.data) {
				readmeBlob = res.data;
			}
		} catch {
			// Ignore readme load failures silently
		}
	}

	async function openFile(item: RepoItem) {
		loading = true;
		error = '';
		try {
			const res = await api.GET('/api/v1/projects/{project_id}/repository/blob', {
				params: {
					path: { project_id: project.id },
					query: { path: item.path, ref: currentRef }
				}
			});
			if (res.error) throw new Error(apiErrorMessage(res.error, 'Could not load file content'));
			if (res.data) {
				activeBlob = res.data;
				currentPath = item.path;
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load file';
		} finally {
			loading = false;
		}
	}

	function handleBranchChange(newRef: string) {
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

	onMount(async () => {
		if (project.github) {
			await loadInfo();
			if (currentRef) {
				await loadTree('', currentRef);
			}
		} else {
			loading = false;
		}
	});
</script>

<div class="space-y-6">
	{#if !project.github}
		<div class="rounded-xl border bg-card p-8 text-center">
			<FolderGit2 class="mx-auto h-10 w-10 text-muted-foreground/60" />
			<h3 class="mt-3 font-semibold text-foreground">No Repository Connected</h3>
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
				<div
					class="flex items-center gap-2 rounded-lg border bg-muted/30 px-3 py-1.5 text-xs font-medium"
				>
					<GitBranch class="h-3.5 w-3.5 text-muted-foreground" />
					{#if info && (info.branches ?? []).length > 0}
						<select
							value={currentRef}
							aria-label="Repository branch"
							onchange={(e) => handleBranchChange(e.currentTarget.value)}
							class="cursor-pointer bg-transparent font-mono text-xs font-semibold text-foreground outline-hidden"
						>
							{#each info.branches ?? [] as branch (branch)}
								<option value={branch}>{branch}</option>
							{/each}
						</select>
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
				{#if isSpecrig}
					<div class="flex rounded-lg border bg-muted/40 p-0.5 text-xs">
						<button
							type="button"
							onclick={() => (userSelectedMode = 'specrig')}
							class={`flex items-center gap-1.5 rounded-md px-3 py-1 font-medium transition-colors ${viewerMode === 'specrig' ? 'bg-primary text-primary-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'}`}
						>
							<Sparkles class="h-3.5 w-3.5 text-amber-300 dark:text-amber-400" />
							Specrig View
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
					class="h-8 gap-1.5 text-xs"
					onclick={() =>
						viewerMode === 'specrig'
							? viewerRevision++
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

		{#if loading && !tree && !activeBlob && viewerMode !== 'specrig'}
			<div class="flex items-center justify-center py-20 text-sm text-muted-foreground">
				Loading repository…
			</div>
		{:else if viewerMode === 'specrig'}
			<!-- Native Specrig Viewer -->
			<section class="rounded-xl border bg-card p-4 shadow-xs">
				{#key viewerRevision}
					<SpecrigViewer
						dataSource={repositoryDataSource(project.id)}
						branch={currentRef || 'main'}
						repoId={project.github?.repository || project.name}
						initialPath="docs/"
					/>
				{/key}
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
