<script lang="ts">
	import { onMount } from 'svelte';
	import { GitBranch, FolderGit2, Sparkles, RefreshCw, Layers } from '@lucide/svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import FileTreeTable from './FileTreeTable.svelte';
	import FileBlobViewer from './FileBlobViewer.svelte';
	import CustomViewerHost from './CustomViewerHost.svelte';
	import type {
		RepoBlob,
		RepoInfo,
		RepoItem,
		RepoTree,
		ViewerMode,
		CustomViewerConfig
	} from './types';

	let { project }: { project: components['schemas']['ProjectRead'] } = $props();

	let info = $state<RepoInfo | null>(null);
	let currentRef = $state<string>('');
	let currentPath = $state<string>('');
	let tree = $state<RepoTree | null>(null);
	let activeBlob = $state<RepoBlob | null>(null);
	let readmeBlob = $state<RepoBlob | null>(null);

	let viewerMode = $state<ViewerMode>('default');
	let loading = $state(true);
	let error = $state('');

	// Check if the project has a custom viewer configuration in its metadata/automation
	let customViewerConfig = $derived.by<CustomViewerConfig | null>(() => {
		const auto = (project.github?.automation || {}) as Record<string, unknown>;
		if (auto.viewer && typeof auto.viewer === 'object') {
			const v = auto.viewer as Record<string, unknown>;
			if (typeof v.tagName === 'string' && typeof v.scriptUrl === 'string') {
				return {
					tagName: v.tagName,
					scriptUrl: v.scriptUrl,
					version: typeof v.version === 'string' ? v.version : undefined
				};
			}
		}
		// Default specrig viewer preset if repo has specrig indication
		return {
			tagName: 'specrig-repo-viewer',
			scriptUrl: '/plugins/specrig/viewer.js',
			version: '1.0.0'
		};
	});

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
				<div class="flex rounded-lg border bg-muted/40 p-0.5 text-xs">
					<button
						type="button"
						onclick={() => (viewerMode = 'default')}
						class={`flex items-center gap-1.5 rounded-md px-3 py-1 font-medium transition-colors ${viewerMode === 'default' ? 'bg-background text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'}`}
					>
						<Layers class="h-3.5 w-3.5" />
						Default View
					</button>

					<button
						type="button"
						onclick={() => (viewerMode = 'custom')}
						class={`flex items-center gap-1.5 rounded-md px-3 py-1 font-medium transition-colors ${viewerMode === 'custom' ? 'bg-primary text-primary-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'}`}
					>
						<Sparkles class="h-3.5 w-3.5 text-amber-300 dark:text-amber-400" />
						Custom Specrig View
					</button>
				</div>

				<Button
					variant="outline"
					size="sm"
					class="h-8 gap-1.5 text-xs"
					onclick={() =>
						activeBlob
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

		{#if loading && !tree && !activeBlob}
			<div class="flex items-center justify-center py-20 text-sm text-muted-foreground">
				Loading repository…
			</div>
		{:else if viewerMode === 'custom' && customViewerConfig}
			<!-- Custom Web Component Slot -->
			<section class="rounded-xl border bg-card p-6 shadow-xs">
				<CustomViewerHost
					config={customViewerConfig}
					projectId={project.id}
					apiBase={`/api/v1/projects/${project.id}/repository`}
					ref={currentRef}
				/>
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
