<script lang="ts">
	import { NativeSelect } from '$lib/components/ui/native-select';
	import ProjectConnectionCheckDialog from './ProjectConnectionCheckDialog.svelte';
	import { projectTabHref } from './project-tabs';
	import { PaginatedState } from '$lib/state/paginated.svelte';
	import { responseData } from '$lib/api/pagination';
	import ListPagination from '$lib/components/shared/ListPagination.svelte';
	import LoadError from '$lib/components/shared/LoadError.svelte';

	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Badge } from '$lib/components/ui/badge';
	import {
		Table,
		TableHeader,
		TableBody,
		TableRow,
		TableHead,
		TableCell
	} from '$lib/components/ui/table';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogFooter,
		DialogDescription
	} from '$lib/components/ui/dialog';
	import {
		FolderKanban,
		Plus,
		RefreshCw,
		Search,
		CheckCircle2,
		CircleCheck,
		CirclePause,
		AlertCircle,
		CircleDashed,
		GitBranch
	} from '@lucide/svelte';

	type Project = components['schemas']['ProjectRead'];

	const list = new PaginatedState<Project>();
	let projects = $derived(list.items);
	let loading = $derived(list.loading);
	let searchQuery = $state('');

	// Create dialog
	let isCreateOpen = $state(false);
	let isCreating = $state(false);
	let newName = $state('');
	let newProjectType = $state<'general' | 'sdd'>('general');

	let checkingProject = $state<Project | null>(null);

	async function loadProjects(offset = list.offset) {
		const filters = { search: searchQuery.trim() };
		await list.load(
			async (offset, limit) =>
				responseData(
					await api.GET('/api/v1/projects', { params: { query: { ...filters, offset, limit } } }),
					'Failed to load projects'
				),
			offset
		);
	}

	async function handleCreateProject(e: SubmitEvent) {
		e.preventDefault();
		if (!newName.trim()) {
			toast.error('Project name is required');
			return;
		}

		isCreating = true;
		try {
			const res = await api.POST('/api/v1/projects', {
				body: {
					name: newName.trim(),
					project_type: newProjectType,
					enabled: true
				}
			});

			if (res.error) {
				toast.error('Failed to create project');
			} else {
				toast.success(`Project ${newName} created`);
				isCreateOpen = false;
				newName = '';
				newProjectType = 'general';
				loadProjects();
			}
		} catch {
			toast.error('An error occurred creating the project');
		} finally {
			isCreating = false;
		}
	}

	onMount(() => {
		loadProjects();
	});
</script>

{#snippet status(project: Project)}
	{#if project.enabled}
		<Badge variant="secondary"><CircleCheck aria-hidden="true" />Active</Badge>
	{:else}
		<Badge variant="secondary"><CirclePause aria-hidden="true" />Disabled</Badge>
	{/if}
{/snippet}

<div class="space-y-6">
	<!-- Page Header -->
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-3xl font-bold tracking-tight">Projects</h1>
			<p class="text-sm text-muted-foreground">
				Manage repository connections and verify CI pipelines
			</p>
		</div>
		<div class="flex items-center gap-3">
			<Button variant="outline" size="sm" onclick={() => loadProjects()} disabled={loading}>
				<RefreshCw class="size-4 {loading ? 'animate-spin' : ''}" />
				Refresh
			</Button>
			<Button size="sm" onclick={() => (isCreateOpen = true)}>
				<Plus class="size-4" />
				New Project
			</Button>
		</div>
	</div>

	<!-- Controls & Search -->
	<div class="flex items-center gap-3">
		<div class="relative max-w-sm flex-1">
			<Search class="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
			<Input
				placeholder="Search projects or repositories..."
				bind:value={searchQuery}
				oninput={() => loadProjects(0)}
				class="pl-9"
			/>
		</div>
	</div>

	{#if list.error}
		<LoadError message={list.error} retry={() => loadProjects()} />
	{/if}

	<div
		class="overflow-hidden rounded-xl border border-border/80 bg-card/60 shadow-xs backdrop-blur-xs"
	>
		<Table>
			<TableHeader>
				<TableRow>
					<TableHead class="w-50">Project Name</TableHead>
					<TableHead class="hidden md:table-cell">Providers & Verification</TableHead>
					<TableHead class="w-35">Access check</TableHead>
					<TableHead class="hidden w-25 sm:table-cell">Status</TableHead>
					<TableHead class="hidden w-45 text-right sm:table-cell">Actions</TableHead>
				</TableRow>
			</TableHeader>
			<TableBody>
				{#if loading}
					<TableRow>
						<TableCell colspan={5} class="h-32 text-center text-muted-foreground">
							Loading projects...
						</TableCell>
					</TableRow>
				{:else if list.error}
					<TableRow><TableCell colspan={5}>List unavailable</TableCell></TableRow>
				{:else if projects.length === 0}
					<TableRow>
						<TableCell colspan={5} class="h-32 text-center text-muted-foreground">
							<div class="flex flex-col items-center justify-center gap-2">
								<FolderKanban class="size-8 text-muted-foreground/40" />
								<span>No projects found</span>
							</div>
						</TableCell>
					</TableRow>
				{:else}
					{#each projects as project (project.id)}
						<TableRow>
							<TableCell class="font-semibold text-foreground">
								<div class="flex flex-col gap-0.5">
									<div class="flex items-center gap-1.5">
										<a class="hover:text-primary hover:underline" href={`/projects/${project.id}`}
											>{project.name}</a
										>
										{#if project.project_type === 'sdd'}
											<Badge variant="outline">SDD</Badge>
										{/if}
									</div>
									<span class="font-mono text-xs font-normal text-muted-foreground"
										>rev {project.revision}</span
									>
									<!-- Below md the repository column is hidden; keep the repository with the name. -->
									<span class="font-mono text-xs font-normal text-muted-foreground md:hidden"
										>{project.github?.repository ?? 'No GitHub'}</span
									>
									<!-- Below sm the status column is hidden; keep the status with the name. -->
									<span class="font-normal sm:hidden">{@render status(project)}</span>
								</div>
							</TableCell>
							<TableCell class="hidden text-xs md:table-cell">
								<div class="flex flex-wrap items-center gap-1.5">
									{#if project.github}
										<Badge variant="info" class="font-mono">
											<GitBranch class="size-3" />
											{project.github.repository}
										</Badge>
										<Badge variant="secondary" class="font-mono">
											{project.github.verification.workflow}
										</Badge>
									{:else}
										<span class="text-muted-foreground">No GitHub</span>
									{/if}
								</div>
							</TableCell>
							<TableCell>
								<button
									type="button"
									class="rounded-4xl transition-opacity hover:opacity-80 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
									onclick={() => (checkingProject = project)}
									aria-label={`Open GitHub access check for ${project.name}`}
								>
									{#if !project.last_check}
										<Badge variant="outline"><CircleDashed aria-hidden="true" />Unchecked</Badge>
									{:else if project.last_check.ready}
										<Badge variant="success"><CheckCircle2 aria-hidden="true" />Access OK</Badge>
									{:else}
										<Badge variant="warning"><AlertCircle aria-hidden="true" />Issue</Badge>
									{/if}
								</button>
							</TableCell>
							<TableCell class="hidden sm:table-cell">{@render status(project)}</TableCell>
							<TableCell class="hidden text-right sm:table-cell">
								<!-- Configuration has one home: the project's Setup tabs; on a phone the name opens it. -->
								<div class="flex items-center justify-end gap-3 text-sm">
									<a
										class="font-medium underline-offset-4 hover:underline"
										href={projectTabHref(project.id, 'automation')}
										aria-label={`Automation for ${project.name}`}>Automation</a
									>
									<a
										class="font-medium underline-offset-4 hover:underline"
										href={projectTabHref(project.id, 'settings')}
										aria-label={`Settings for ${project.name}`}>Settings</a
									>
								</div>
							</TableCell>
						</TableRow>
					{/each}
				{/if}
			</TableBody>
		</Table>
	</div>
	{#if !list.error}
		<ListPagination
			offset={list.offset}
			limit={list.limit}
			total={list.total}
			{loading}
			onpage={loadProjects}
		/>
	{/if}

	<!-- Create Project Dialog -->
	<Dialog bind:open={isCreateOpen}>
		<DialogContent class="sm:max-w-106.25">
			<DialogHeader>
				<DialogTitle>Register New Project</DialogTitle>
				<DialogDescription>
					Create a project workspace. You can configure its GitHub connection right after.
				</DialogDescription>
			</DialogHeader>
			<form onsubmit={handleCreateProject} class="space-y-4 py-2">
				<div class="space-y-2">
					<label for="pName" class="text-xs font-semibold text-muted-foreground uppercase"
						>Project Name</label
					>
					<Input id="pName" placeholder="e.g. backend-pipeline" bind:value={newName} required />
				</div>
				<div class="space-y-2">
					<label for="pType" class="text-xs font-semibold text-muted-foreground uppercase"
						>Project Type</label
					>
					<NativeSelect id="pType" bind:value={newProjectType} class="w-full">
						<option value="general">General (Standard Git Repository)</option>
						<option value="sdd">Sdd (Spec-Driven Engineering)</option>
					</NativeSelect>
				</div>
				<DialogFooter class="pt-4">
					<Button type="button" variant="outline" onclick={() => (isCreateOpen = false)}>
						Cancel
					</Button>
					<Button type="submit" disabled={isCreating}>
						{isCreating ? 'Creating...' : 'Create Project'}
					</Button>
				</DialogFooter>
			</form>
		</DialogContent>
	</Dialog>

	{#if checkingProject}
		{#key checkingProject.id}
			<ProjectConnectionCheckDialog
				project={checkingProject}
				onclose={() => (checkingProject = null)}
				onchecked={() => loadProjects()}
			/>
		{/key}
	{/if}
</div>
