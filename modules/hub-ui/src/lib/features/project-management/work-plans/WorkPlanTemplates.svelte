<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import WorkPlanForm from './WorkPlanForm.svelte';
	import TemplateDefinitionEditor from './TemplateDefinitionEditor.svelte';
	import TemplateOutcome from './TemplateOutcome.svelte';
	import { TemplateIntent, freshPreview, type Template } from './template-intent.svelte';
	type Plan = components['schemas']['WorkPlanRead'];
	type Payload = components['schemas']['WorkPlanCreate'];
	let {
		project,
		plans,
		onclose,
		refresh
	}: {
		project: components['schemas']['ProjectRead'];
		plans: Plan[];
		onclose: () => void;
		refresh: () => Promise<void>;
	} = $props();
	let intent = $state<TemplateIntent | null>(null);
	let items = $state<Template[]>([]);
	let total = $state(0),
		offset = $state(0),
		loading = $state(true),
		error = $state('');
	let editing = $state<Template | undefined>(),
		editor = $state(false);
	let sourceId = $state(''),
		sourceName = $state('');
	let selected = $state<Template | null>(null),
		seed = $state<Payload | undefined>(),
		reviewed = $state<Payload | null>(null);
	let binding = $state<{ repository: string; connector: string } | null>(null),
		confirmed = $state(false);
	let deleting = $state<Template | null>(null),
		deleteConfirmed = $state(false);
	let stalePreview = $state(false);
	async function load(page = offset) {
		loading = true;
		try {
			const { data, error: failure } = await api.GET(
				'/api/v1/projects/{project_id}/work-plan-templates',
				{ params: { path: { project_id: project.id }, query: { offset: page, limit: 20 } } }
			);
			if (!data) throw new Error(apiErrorMessage(failure, 'Could not load templates'));
			items = data.items;
			total = data.total_count;
			offset = page;
			error = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load templates';
			throw e;
		} finally {
			loading = false;
		}
	}
	onMount(() => {
		void (async () => {
			try {
				const me = await api.GET('/api/v1/users/me');
				if (!me.data) throw new Error('Sign in again to manage templates');
				intent = new TemplateIntent(project.id, me.data.id);
				await load(0);
			} catch (e) {
				error = e instanceof Error ? e.message : 'Could not load templates';
				loading = false;
			}
		})();
	});
	async function save(name: string, definition: components['schemas']['TemplateDefinition']) {
		if (!intent) return;
		await intent.submit({
			op: editing ? 'update' : 'create',
			target: editing?.id ?? null,
			body: editing
				? { request_id: crypto.randomUUID(), expected_revision: editing.revision, name, definition }
				: { request_id: crypto.randomUUID(), name, definition }
		});
		if (intent.state === 'recorded') {
			editor = false;
			try {
				await load();
			} catch {
				error = 'Definition recorded; refresh failed.';
			}
		}
	}
	async function extract() {
		const source = plans.find((p) => p.id === sourceId);
		if (!source || !intent) return;
		await intent.submit({
			op: 'from-plan',
			target: source.id,
			body: {
				request_id: crypto.randomUUID(),
				source_plan_id: source.id,
				expected_revision: source.revision,
				name: sourceName
			}
		});
		if (intent.state === 'recorded')
			try {
				await load();
			} catch {
				error = 'Definition recorded; refresh failed.';
			}
	}
	async function use(template: Template) {
		if (intent?.locked) return;
		loading = true;
		stalePreview = false;
		confirmed = false;
		reviewed = null;
		try {
			const response = await api.GET(
				'/api/v1/projects/{project_id}/work-plan-templates/{template_id}',
				{ params: { path: { project_id: project.id, template_id: template.id } } }
			);
			const current = await api.GET('/api/v1/projects/{project_id}', {
				params: { path: { project_id: project.id } }
			});
			if (!response.data || !current.data?.github)
				throw new Error('Template or current repository binding unavailable');
			selected = response.data;
			binding = {
				repository: current.data.github.repository,
				connector: current.data.github.github_connector_id
			};
			seed = freshPreview(response.data);
			error = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Template unavailable';
			selected = null;
			seed = undefined;
		} finally {
			loading = false;
		}
	}
	async function register() {
		if (
			stalePreview ||
			!selected ||
			!reviewed ||
			!binding ||
			!confirmed ||
			!intent ||
			!reviewed.request_id
		)
			return;
		await intent.submit({
			op: 'register',
			target: selected.id,
			body: {
				request_id: reviewed.request_id,
				template_revision: selected.revision,
				template_digest: selected.digest,
				expected_repository: binding.repository,
				expected_connector_id: binding.connector,
				payload: reviewed
			}
		});
		if (intent.state === 'refused') {
			confirmed = false;
			stalePreview = true;
		}
		if (intent.state === 'recorded') {
			selected = null;
			seed = undefined;
			reviewed = null;
			try {
				await refresh();
			} catch {
				error = 'Plan recorded; current Plan refresh failed.';
			}
		}
	}
	async function remove() {
		if (!deleting || !deleteConfirmed || !intent) return;
		await intent.submit({
			op: 'delete',
			target: deleting.id,
			body: { request_id: crypto.randomUUID(), expected_revision: deleting.revision }
		});
		if (intent.state === 'recorded') {
			deleting = null;
			deleteConfirmed = false;
			try {
				await load();
			} catch {
				error = 'Deletion recorded; refresh failed.';
			}
		}
	}
</script>

<section class="space-y-4 rounded-xl border p-5" aria-label="Work Plan templates">
	<header class="flex flex-wrap justify-between gap-2">
		<h2 class="text-lg font-semibold">Templates</h2>
		<Button variant="ghost" onclick={onclose}>Close Templates</Button>
	</header>
	<p class="text-sm text-muted-foreground">
		Definitions belong to this project. They never copy execution history, attachments or approvals.
		Unresolved request specifications remain in this account/project tab session across
		close/reload; logout or session loss clears local recovery. Reopen durable request history with
		its original ID after that loss.
	</p>
	{#if error}<p role="alert">{error}</p>{/if}
	{#if intent?.storageError}<p role="alert">{intent.error}</p>{/if}
	{#if intent}<TemplateOutcome
			{intent}
			refresh={async () => {
				await intent?.check();
				await load();
				await refresh();
			}}
		/>{/if}
	{#if loading}<p>Loading templates…</p>{/if}
	{#if selected && seed && binding}
		<section class="space-y-3 rounded-lg border p-4">
			<h3>Template source: {selected.name} · revision {selected.revision}</h3>
			<p>Template {selected.id} · digest {selected.digest}</p>
			<p>Current repository {binding.repository} · connector {binding.connector}</p>
			<p>
				Fresh keys are generated from request {seed.request_id}. Group, schedule and external
				dependencies start empty.
			</p>
			<details>
				<summary>Source slot to fresh task keys</summary>
				<ul>
					{#each [...(selected.definition.items ?? [])].sort( (a, b) => (a.key < b.key ? -1 : a.key > b.key ? 1 : 0) ) as slot, index (slot.key)}<li
						>
							{slot.key} → {seed.items?.[index]?.key}
						</li>{/each}
				</ul>
			</details>
			{#if reviewed}
				{#if stalePreview}<p role="alert">
						The reviewed template or binding was refused. Reload current basis for a new request.
					</p>
					<Button variant="outline" disabled={intent?.locked} onclick={() => use(selected!)}
						>Reload for review</Button
					>{/if}
				<h4>Review complete registration</h4>
				<pre class="max-h-96 overflow-auto text-sm whitespace-pre-wrap">{JSON.stringify(
						reviewed,
						null,
						2
					)}</pre>
				<p>
					{reviewed.state === 'active'
						? 'Active creation can start eligible work immediately.'
						: 'Only active creation requests execution; draft stores the specification.'}
				</p>
				<label class="flex gap-2"
					><input
						type="checkbox"
						bind:checked={confirmed}
						disabled={stalePreview || intent?.locked}
					/>I reviewed this source, current binding and complete specification. Private task text
					will be retained in this tab session for request recovery.</label
				>
				<Button disabled={stalePreview || !confirmed || !intent || intent.locked} onclick={register}
					>{reviewed.state === 'active' ? 'Register active work' : 'Save reviewed plan'}</Button
				>
				<Button
					variant="outline"
					disabled={intent?.locked}
					onclick={() => {
						seed = reviewed!;
						reviewed = null;
						confirmed = false;
					}}>Back to editing</Button
				>
			{:else}
				{#key seed.request_id}<WorkPlanForm
						projectId={project.id}
						{plans}
						{seed}
						onsaved={() => {}}
						onreview={(payload) => {
							reviewed = payload;
							confirmed = false;
						}}
						oncancel={() => {
							selected = null;
							seed = undefined;
							confirmed = false;
						}}
					/>{/key}
			{/if}
			<Button
				variant="ghost"
				onclick={() => {
					selected = null;
					seed = undefined;
					reviewed = null;
					confirmed = false;
				}}>Back to Templates</Button
			>
		</section>
	{:else}
		<div class="flex gap-2">
			<Button
				disabled={!intent || intent.locked || loading}
				onclick={() => {
					editing = undefined;
					editor = true;
				}}>New template</Button
			><Button
				variant="outline"
				onclick={() => {
					confirmed = false;
					deleteConfirmed = false;
					void load().catch(() => {});
				}}>Refresh templates</Button
			>
		</div>
		{#if !loading && !items.length}<p>
				No templates on this page. Create a definition or save one from a Plan.
			</p>{/if}
		{#each items as template (template.id)}<article class="space-y-2 rounded-lg border p-3">
				<h3>{template.name} · {template.id} · revision {template.revision}</h3>
				<p>
					{(template.definition.items ?? []).length} local tasks · {template.definition.base_branch}
				</p>
				<Button disabled={!intent || intent.locked || loading} onclick={() => use(template)}
					>Use template</Button
				><Button
					variant="outline"
					disabled={!intent || intent.locked}
					onclick={() => {
						editing = template;
						editor = true;
					}}>Edit template</Button
				><Button
					variant="outline"
					disabled={!intent || intent.locked}
					onclick={() => {
						deleting = template;
						deleteConfirmed = false;
					}}>Delete template</Button
				>
			</article>{/each}
		<div class="flex gap-2">
			<Button
				variant="outline"
				disabled={loading || offset === 0}
				onclick={() => void load(Math.max(0, offset - 20)).catch(() => {})}
				>Previous templates</Button
			><Button
				variant="outline"
				disabled={loading || offset + items.length >= total}
				onclick={() => void load(offset + 20).catch(() => {})}>Next templates</Button
			>
		</div>
		{#if editor}{#key `${editing?.id ?? 'new'}:${editing?.revision ?? 0}`}<TemplateDefinitionEditor
					template={editing}
					disabled={!intent || intent.locked}
					{save}
					cancel={() => {
						editor = false;
						editing = undefined;
					}}
				/>{/key}{/if}
		<section class="space-y-2 rounded-lg border p-3">
			<h3>Save as template</h3>
			<label class="block"
				>Source Plan<select class="w-full rounded border p-2" bind:value={sourceId}
					><option value="">Select a Plan</option>{#each plans as plan (plan.id)}<option
							value={plan.id}>{plan.title} · revision {plan.revision}</option
						>{/each}</select
				></label
			><label class="block">Template name<Input bind:value={sourceName} maxlength={200} /></label>
			<p class="text-sm">
				Save only the source specification and local edges. Attachment, PR/Issue, execution/approval
				history, group, schedule and external Plan dependencies are omitted. No work starts.
			</p>
			<Button
				disabled={!sourceId || !sourceName.trim() || !intent || intent.locked}
				onclick={extract}>Save source definition</Button
			>
		</section>
		{#if deleting}<section class="space-y-2 rounded-lg border p-3">
				<p>
					Delete {deleting.name} revision {deleting.revision}? Derived Plans and original receipts
					stay unchanged.
				</p>
				<label class="flex gap-2"
					><input type="checkbox" bind:checked={deleteConfirmed} />I reviewed this template deletion</label
				><Button disabled={!deleteConfirmed || !intent || intent.locked} onclick={remove}
					>Confirm template deletion</Button
				><Button
					variant="ghost"
					onclick={() => {
						deleting = null;
						deleteConfirmed = false;
					}}>Cancel deletion</Button
				>
			</section>{/if}
	{/if}
</section>
