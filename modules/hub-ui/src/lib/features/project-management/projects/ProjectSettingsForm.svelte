<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { GitBranch } from '@lucide/svelte';
	type Project = components['schemas']['ProjectRead'];
	let {
		project,
		connectors,
		catalogs,
		section = 'all',
		onsaved
	}: {
		project: Project;
		connectors: components['schemas']['ConnectorRead'][];
		catalogs: components['schemas']['AICatalogRead'][];
		section?: 'all' | 'general' | 'connection' | 'automation';
		onsaved: () => void;
	} = $props();
	let githubConnectors = $derived(connectors.filter((c) => c.provider === 'github'));
	let pipelineCatalogs = $derived(catalogs.filter((c) => c.pipeline_delivery));
	// Edit / Settings dialog
	let isUpdating = $state(false);
	let editName = $state('');
	let editEnabled = $state(true);
	let hasGithub = $state(false);
	let githubRepo = $state('');
	let githubConnectorId = $state('');
	let githubWorkflow = $state('ci.yml');
	let githubRequiredJobs = $state('lint, test');
	let autoMerge = $state(true);
	let mergeMethod = $state<'squash' | 'merge' | 'rebase'>('squash');
	let autoFixCi = $state(true);
	let autoFixConflicts = $state(true);
	let autoEnrollOnTrigger = $state(true);
	let autoEnrollSessions = $state(true);
	let dispatchIntervalSeconds = $state('60');
	// Empty leaves only the AI catalog's limits.
	let maxInFlightRuns = $state('');
	let aiCatalogId = $state('');

	function initialize(project: Project) {
		editName = project.name;
		editEnabled = project.enabled;
		if (project.github) {
			hasGithub = true;
			githubRepo = project.github.repository;
			githubConnectorId = project.github.github_connector_id;
			githubWorkflow = project.github.verification.workflow;
			githubRequiredJobs = project.github.verification.required_jobs.join(', ');
			autoMerge = project.github.automation?.auto_merge ?? true;
			mergeMethod = project.github.automation?.merge_method ?? 'squash';
			autoFixCi = project.github.automation?.auto_fix_ci ?? true;
			autoFixConflicts = project.github.automation?.auto_fix_conflicts ?? true;
			autoEnrollOnTrigger = project.github.automation?.auto_enroll_on_trigger ?? true;
			autoEnrollSessions = project.github.automation?.auto_enroll_sessions ?? true;
			dispatchIntervalSeconds = String(project.github.automation?.dispatch_interval_seconds ?? 60);
			maxInFlightRuns = String(project.github.automation?.max_in_flight_runs ?? '');
			aiCatalogId = project.github.ai_catalog_id ?? '';
		} else {
			hasGithub = false;
			githubRepo = '';
			githubConnectorId = githubConnectors[0]?.id || '';
			githubWorkflow = 'ci.yml';
			githubRequiredJobs = 'lint, test';
			autoMerge = true;
			mergeMethod = 'squash';
			autoFixCi = true;
			autoFixConflicts = true;
			autoEnrollOnTrigger = true;
			autoEnrollSessions = true;
			dispatchIntervalSeconds = '60';
			maxInFlightRuns = '';
			aiCatalogId = '';
		}
	}

	async function handleUpdateProject(e: SubmitEvent) {
		e.preventDefault();

		isUpdating = true;
		try {
			const jobs = githubRequiredJobs
				.split(',')
				.map((j) => j.trim())
				.filter(Boolean);

			const body: components['schemas']['ProjectUpdate'] = {
				name: editName.trim(),
				enabled: editEnabled,
				expected_revision: project.revision,
				github: hasGithub
					? {
							...project.github,
							repository: githubRepo.trim(),
							github_connector_id: githubConnectorId,
							ai_catalog_id: aiCatalogId || null,
							verification: {
								...project.github?.verification,
								workflow: githubWorkflow.trim(),
								required_jobs: jobs,
								event: project.github?.verification.event ?? 'pull_request'
							},
							automation: {
								...project.github?.automation,
								auto_merge: autoMerge,
								merge_method: mergeMethod,
								auto_fix_ci: autoFixCi,
								auto_fix_conflicts: autoFixConflicts,
								auto_enroll_on_trigger: autoEnrollOnTrigger,
								auto_enroll_sessions: autoEnrollSessions,
								dispatch_interval_seconds: Number(dispatchIntervalSeconds),
								max_in_flight_runs: String(maxInFlightRuns).trim() ? Number(maxInFlightRuns) : null
							}
						}
					: null
			};

			const res = await api.PUT('/api/v1/projects/{project_id}', {
				params: { path: { project_id: project.id } },
				body
			});

			if (res.error) {
				const detail = apiErrorMessage(res.error, 'Failed to update project');
				toast.error(detail);
			} else {
				toast.success('Project configuration updated');
				onsaved();
			}
		} catch {
			toast.error('Failed to update project settings');
		} finally {
			isUpdating = false;
		}
	}

	onMount(() => initialize(project));
</script>

<form onsubmit={handleUpdateProject} class="space-y-5 py-2">
	{#if section === 'all' || section === 'general'}
		<!-- Basic Info -->
		<div class="space-y-3">
			<div class="space-y-1.5">
				<label for="editName" class="text-xs font-semibold text-muted-foreground uppercase"
					>Project Name</label
				>
				<Input id="editName" bind:value={editName} required />
			</div>
			<div class="flex items-center gap-2">
				<input
					type="checkbox"
					id="editEnabled"
					bind:checked={editEnabled}
					class="size-4 rounded border-border text-primary focus:ring-primary"
				/>
				<label for="editEnabled" class="text-sm font-medium text-foreground">
					Project Active (enabled for scheduled tasks)
				</label>
			</div>
		</div>
	{/if}
	{#if section !== 'general'}
		<!-- GitHub Section -->
		<div class="space-y-3 rounded-lg border border-border/80 bg-muted/20 p-3.5">
			{#if section !== 'automation'}
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-2">
						<GitBranch class="size-4 text-foreground" />
						<span class="text-sm font-semibold">GitHub Provider</span>
					</div>
					<label class="flex items-center gap-2 text-xs font-medium text-muted-foreground">
						<input
							type="checkbox"
							bind:checked={hasGithub}
							class="size-3.5 rounded border-border text-primary focus:ring-primary"
						/>
						Enable GitHub
					</label>
				</div>
			{/if}
			{#if hasGithub}
				<div class="space-y-3 pt-2">
					{#if section !== 'automation'}
						<div class="space-y-1">
							<label for="ghRepo" class="text-[11px] font-semibold text-muted-foreground uppercase">
								Repository (owner/repo)
							</label>
							<Input
								id="ghRepo"
								placeholder="e.g. acme/my-app"
								bind:value={githubRepo}
								required={hasGithub}
							/>
						</div>

						<div class="space-y-1">
							<label for="ghConn" class="text-[11px] font-semibold text-muted-foreground uppercase">
								GitHub Connector
							</label>
							{#if githubConnectors.length > 0}
								<select
									id="ghConn"
									bind:value={githubConnectorId}
									class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs focus:ring-1 focus:ring-ring"
								>
									{#each githubConnectors as conn (conn.id)}
										<option value={conn.id}>{conn.name} ({conn.id.slice(0, 8)}...)</option>
									{/each}
								</select>
							{:else}
								<Input
									id="ghConn"
									placeholder="Connector UUID"
									bind:value={githubConnectorId}
									required={hasGithub}
								/>
								<span class="text-[11px] text-amber-500"
									>No GitHub connectors found. Please create one in Connectors.</span
								>
							{/if}
						</div>

						<div class="grid grid-cols-2 gap-2">
							<div class="space-y-1">
								<label for="ghWf" class="text-[11px] font-semibold text-muted-foreground uppercase">
									Workflow File
								</label>
								<Input
									id="ghWf"
									placeholder="ci.yml"
									bind:value={githubWorkflow}
									required={hasGithub}
								/>
							</div>
							<div class="space-y-1">
								<label
									for="ghJobs"
									class="text-[11px] font-semibold text-muted-foreground uppercase"
								>
									Required Jobs
								</label>
								<Input
									id="ghJobs"
									placeholder="lint, test"
									bind:value={githubRequiredJobs}
									required={hasGithub}
								/>
							</div>
						</div>
					{/if}
					{#if section === 'all' || section === 'automation'}
						<details
							open={section === 'automation'}
							class="rounded-md border border-border/80 bg-background/50 p-3"
						>
							<summary class="cursor-pointer text-xs font-semibold text-foreground">
								Advanced automation
							</summary>
							<div class="mt-3 space-y-3">
								<label class="flex items-center justify-between gap-3 text-sm">
									<span>
										<span class="font-medium text-foreground"
											>Automatically merge after CI passes</span
										>
										<span class="mt-0.5 block text-xs text-muted-foreground"
											>GitHub branch rules remain the final authority.</span
										>
									</span>
									<input
										type="checkbox"
										bind:checked={autoMerge}
										class="size-4 rounded border-border text-primary focus:ring-primary"
									/>
								</label>

								<div class="grid grid-cols-2 gap-3">
									<div class="space-y-1">
										<label
											for="mergeMethod"
											class="text-[11px] font-semibold text-muted-foreground uppercase"
											>Merge method</label
										>
										<select
											id="mergeMethod"
											bind:value={mergeMethod}
											disabled={!autoMerge}
											class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs disabled:cursor-not-allowed disabled:opacity-50"
										>
											<option value="squash">Squash</option>
											<option value="merge">Create merge commit</option>
											<option value="rebase">Rebase</option>
										</select>
									</div>
									<div class="space-y-1">
										<label
											for="dispatchInterval"
											class="text-[11px] font-semibold text-muted-foreground uppercase"
											>Dispatch interval (seconds)</label
										>
										<Input
											id="dispatchInterval"
											type="number"
											min="30"
											max="3600"
											bind:value={dispatchIntervalSeconds}
										/>
									</div>
									<div class="space-y-1">
										<label
											for="maxInFlightRuns"
											class="text-[11px] font-semibold text-muted-foreground uppercase"
											>Max runs in flight</label
										>
										<Input
											id="maxInFlightRuns"
											type="number"
											min="1"
											max="50"
											placeholder="No project limit"
											bind:value={maxInFlightRuns}
										/>
									</div>
								</div>

								<div class="space-y-1">
									<label
										for="aiCatalog"
										class="text-[11px] font-semibold text-muted-foreground uppercase"
										>AI catalog</label
									>
									<select
										id="aiCatalog"
										bind:value={aiCatalogId}
										class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs"
									>
										<option value="">Default (Personal Codex)</option>
										{#each pipelineCatalogs as catalog (catalog.id)}
											<option value={catalog.id}>{catalog.name} ({catalog.kind})</option>
										{/each}
									</select>
								</div>

								<label class="flex items-center justify-between gap-3 text-sm">
									<span class="font-medium text-foreground">Ask the AI agent to fix failed CI</span>
									<input
										type="checkbox"
										bind:checked={autoFixCi}
										class="size-4 rounded border-border text-primary focus:ring-primary"
									/>
								</label>
								<label class="flex items-center justify-between gap-3 text-sm">
									<span class="font-medium text-foreground"
										>Ask the AI agent to resolve merge conflicts</span
									>
									<input
										type="checkbox"
										bind:checked={autoFixConflicts}
										class="size-4 rounded border-border text-primary focus:ring-primary"
									/>
								</label>
								<label class="flex items-center justify-between gap-3 text-sm">
									<span>
										<span class="font-medium text-foreground">Enroll PRs containing @auto-run</span>
										<span class="mt-0.5 block text-xs text-muted-foreground"
											>Turning this off keeps PR enrollment manual.</span
										>
									</span>
									<input
										type="checkbox"
										bind:checked={autoEnrollOnTrigger}
										class="size-4 rounded border-border text-primary focus:ring-primary"
									/>
								</label>
								<label class="flex items-center justify-between gap-3 text-sm">
									<span>
										<span class="font-medium text-foreground"
											>Adopt PRs opened by agent sessions</span
										>
										<span class="mt-0.5 block text-xs text-muted-foreground"
											>A task session's PR enters the pipeline at CI observation.</span
										>
									</span>
									<input
										type="checkbox"
										bind:checked={autoEnrollSessions}
										class="size-4 rounded border-border text-primary focus:ring-primary"
									/>
								</label>
							</div>
						</details>
					{/if}
				</div>
			{/if}
		</div>
	{/if}
	<div class="flex justify-end pt-2">
		<Button type="submit" disabled={isUpdating}>
			{isUpdating ? 'Saving...' : 'Save Changes'}
		</Button>
	</div>
</form>
