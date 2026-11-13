<script lang="ts">
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { onMount, untrack } from 'svelte';
	import { api, type components } from '$lib/api';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogDescription
	} from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { decisionNoticeState } from './decision-notices.svelte';
	import DecisionNoticeReceipt from './DecisionNoticeReceipt.svelte';
	let { channelId }: { channelId: string } = $props();
	const notices = untrack(() => decisionNoticeState(channelId));
	type Settings = components['schemas']['SubscriptionSettings'];
	const kinds = [
		'run-question',
		'native-hub-question',
		'native-worker-question',
		'native-workflow',
		'native-proposal',
		'native-integration'
	] as const;
	let form = $state<Settings>({
		enabled: false,
		project_scope: 'selected',
		project_ids: [],
		kinds: [],
		mode: 'immediate',
		review_origin: '',
		trusted_destination: false
	});
	let projects = $state<{ id: string; name: string }[]>([]);
	let confirmed = $state(false);
	let reviewedDuplicate = $state(false);
	let resendId = $state('');
	let loaded = $state('');
	let dialogOpen = $state(false);
	let view = $state<'settings' | 'history'>('settings');
	$effect(() => {
		if (notices.current) {
			const current = JSON.stringify(notices.current);
			if (current !== loaded) {
				form = JSON.parse(JSON.stringify(notices.current.settings));
				form.trusted_destination = false;
				confirmed = false;
				loaded = current;
			}
		}
	});
	$effect(() => {
		JSON.stringify(form);
		confirmed = false;
		reviewedDuplicate = false;
	});
	onMount(() => {
		void notices.load();
		void api.GET('/api/v1/projects', { params: { query: { limit: 100 } } }).then((r) => {
			if (r.data) projects = r.data.items;
		});
	});
	async function save() {
		if (!notices.current || !confirmed) return;
		await notices.save({
			...form,
			trusted_destination: confirmed,
			request_id: crypto.randomUUID(),
			expected_revision: notices.current.revision,
			expected_destination_generation: notices.current.destination_generation
		});
		confirmed = false;
	}
	async function resend() {
		if (!notices.current || !resendId || !reviewedDuplicate) return;
		await notices.resend(resendId, {
			request_id: crypto.randomUUID(),
			expected_revision: notices.current.revision,
			expected_destination_generation: notices.current.destination_generation,
			acknowledge_possible_duplicate: true
		});
		resendId = '';
		reviewedDuplicate = false;
	}
</script>

<div class="space-y-2 border-t pt-3">
	<p class="text-xs">
		Decision notices: {notices.current?.settings.enabled ? 'Enabled' : 'Off by default'} · {notices
			.current?.settings.mode === 'digest'
			? '15-minute digest'
			: 'next eligible maintenance pass'}.
	</p>
	{#if notices.current}<p class="text-xs">
			Last loaded {new Date(notices.current.observed_at).toLocaleString()} · channel {notices
				.current.channel_enabled
				? 'enabled'
				: 'disabled'} · warning {notices.current.severity_enabled ? 'allowed' : 'filtered out'}
		</p>{/if}
	<Button
		size="sm"
		variant="outline"
		onclick={() => {
			view = 'settings';
			dialogOpen = true;
		}}>Decision notices</Button
	>
	<Button
		size="sm"
		variant="outline"
		onclick={() => {
			view = 'history';
			dialogOpen = true;
		}}>Notice history</Button
	>
	<Dialog bind:open={dialogOpen}>
		<!-- eslint-disable-next-line shadcn/no-arbitrary-values -- viewport-relative height has no scale equivalent -->
		<DialogContent class="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
			<DialogHeader
				><DialogTitle
					>{view === 'settings'
						? 'Decision notice settings'
						: 'Decision notice delivery history'}</DialogTitle
				><DialogDescription
					>Observed decision metadata goes only to this explicitly trusted global destination.
					Delivery is separate from owner decisions. Unacknowledged request intent is held only in
					this signed-in page session; after a full reload use durable history or reopen the
					original context before reviewing another command.</DialogDescription
				></DialogHeader
			>

			{#if notices.error}<p role="alert">{notices.error}</p>{/if}
			{#if notices.intent}
				<div class="rounded border p-2" role="status">
					<p>
						{notices.status === 'recorded'
							? 'Request recorded'
							: notices.status === 'refused'
								? 'Request refused'
								: 'Outcome unknown'} — {notices.intent.operation} — {notices.intent.body.request_id}
					</p>
					{#if notices.outcome}<DecisionNoticeReceipt outcome={notices.outcome} />{/if}
					<Button
						size="sm"
						variant="outline"
						disabled={notices.busy}
						onclick={() => notices.check()}>Check outcome</Button
					>
					{#if notices.unresolved}<Button
							size="sm"
							variant="outline"
							disabled={notices.busy}
							onclick={() => notices.retry()}>Retry same request</Button
						>
					{:else}<Button
							size="sm"
							variant="outline"
							onclick={() => {
								notices.dismiss();
								confirmed = false;
							}}>Back to review</Button
						>{/if}
				</div>
			{/if}
			<Button
				size="sm"
				variant="outline"
				disabled={notices.busy}
				onclick={() => {
					confirmed = false;
					void notices.load();
				}}>Refresh evidence</Button
			>
			{#if notices.current && view === 'settings'}
				<p class="text-xs">
					Observed {new Date(notices.current.observed_at).toLocaleString()} · Destination {notices
						.current.chat_id} · generation {notices.current.destination_generation} · revision {notices
						.current.revision}
				</p>
				<p class="text-xs">
					Channel {notices.current.channel_enabled ? 'enabled' : 'disabled'} · warning severity {notices
						.current.severity_enabled
						? 'allowed'
						: 'filtered out'}
				</p>
				<fieldset disabled={notices.busy || notices.unresolved} class="space-y-2">
					<label class="flex gap-2"
						><input type="checkbox" bind:checked={form.enabled} />Enable decision notices</label
					>
					<label class="block"
						>Project scope <NativeSelect bind:value={form.project_scope}
							><option value="selected">Selected projects</option><option value="all"
								>All current and future projects</option
							></NativeSelect
						></label
					>
					{#if form.project_scope === 'selected'}
						<label class="block"
							>Projects (first 100 accessible projects)<NativeSelect
								class="flex"
								multiple
								bind:value={form.project_ids}
								>{#each projects as project (project.id)}<option value={project.id}
										>{project.name}</option
									>{/each}</NativeSelect
							></label
						>
					{/if}
					<p>Decision kinds</p>
					{#each kinds as kind (kind)}<label class="mr-3 inline-flex gap-1"
							><input type="checkbox" bind:group={form.kinds} value={kind} />{kind}</label
						>{/each}
					<label class="block"
						>Delivery <NativeSelect bind:value={form.mode}
							><option value="immediate">Immediate — next eligible maintenance pass</option><option
								value="digest">Digest — 15 minutes after first pending entry</option
							></NativeSelect
						></label
					>
					<label class="block"
						>Hub review origin<Input
							bind:value={form.review_origin}
							placeholder="https://hub.example"
						/></label
					>
					<p class="text-xs">
						Messages contain project/run metadata and authenticated review links to {form.review_origin ||
							'the chosen origin'}. Saving or changing filters may include currently observed
						pending work. Disable stops future admissions; an admitted message may finish.
					</p>
					<div class="space-y-1 text-xs">
						<p>
							Messages contain at most 10 entries and 3,500 characters. Omitted entries remain
							pending.
						</p>
						<p>
							Immediate delivery becomes eligible on the next maintenance pass. Digest becomes
							eligible after 15 minutes and a later pass. Neither mode guarantees a delivery
							deadline.
						</p>
						<p>
							Hub sign-in is required to review an exact decision. Question and answer bodies are
							omitted.
						</p>
						<p class="break-all">
							Example review link (illustrative identity only): {form.review_origin ||
								'https://hub.example'}/decisions?decision_key=example&amp;decision_fingerprint={'0'.repeat(
								64
							)}
						</p>
					</div>
					<label class="flex gap-2"
						><input type="checkbox" bind:checked={confirmed} />I reviewed these settings and trust
						this destination for the selected project metadata.</label
					>
					<Button size="sm" disabled={!confirmed} onclick={save}>Save decision subscription</Button>
				</fieldset>
			{/if}
			{#if view === 'history'}
				{#if notices.current}
					<div class="rounded border p-2" aria-label="Current resend basis">
						<p>
							Current destination: {notices.current.chat_id} · destination generation {notices
								.current.destination_generation} · subscription revision {notices.current.revision}
						</p>
						<p>Review origin: {notices.current.settings.review_origin}</p>
						<p>
							Project scope: {notices.current.settings.project_scope === 'all'
								? 'All current and future projects'
								: (notices.current.settings.project_ids ?? []).join(', ')}
						</p>
						<p>Decision kinds: {(notices.current.settings.kinds ?? []).join(', ')}</p>
						<p>
							Channel {notices.current.channel_enabled ? 'enabled' : 'disabled'} · warning {notices
								.current.severity_enabled
								? 'allowed'
								: 'filtered out'} · subscription {notices.current.settings.enabled
								? 'enabled'
								: 'disabled'}
						</p>
						<p>Basis observed {new Date(notices.current.observed_at).toLocaleString()}</p>
					</div>
				{/if}
				<h4 class="font-medium">Decision delivery history</h4>
				{#if notices.history}<p class="text-xs">
						History observed {new Date(notices.history.observed_at).toLocaleString()}
					</p>{/if}
				<p class="text-xs">
					Transport acceptance does not mean the decision was completed. Unknown outcomes are never
					automatically resent. Native evidence is last observed.
				</p>
				{#each notices.history?.items ?? [] as notice (notice.id)}
					<div class="rounded border p-2">
						<p>
							{String(notice.observed.kind ?? 'Decision')} — {notice.state} · {new Date(
								notice.created_at
							).toLocaleString()} · destination generation {notice.destination_generation}
						</p>
						<p class="text-xs break-all">{notice.decision_key} · {notice.fingerprint}</p>
						<p class="text-xs">
							Project: {String(notice.observed.project_name ?? 'unavailable')} · Run: {String(
								notice.observed.run_id ?? 'unavailable'
							)} · observed {String(notice.observed.observed_at ?? 'unavailable')}
						</p>
						<a
							class="underline"
							href={'/decisions?' +
								new URLSearchParams({
									decision_key: notice.decision_key,
									decision_fingerprint: notice.fingerprint
								})}>Open exact decision</a
						>
						<Button
							size="sm"
							variant="outline"
							disabled={notices.busy || notices.unresolved || notice.state === 'sending'}
							onclick={() => {
								resendId = notice.id;
								reviewedDuplicate = false;
							}}>Review send again</Button
						>
					</div>
				{/each}
				{#if notices.history?.has_more}<Button
						size="sm"
						variant="outline"
						disabled={notices.busy}
						onclick={() => notices.load(notices.history?.next_cursor ?? undefined)}
						>Older notices</Button
					>{/if}
				{#each notices.history?.attempts ?? [] as attempt (attempt.id)}
					<p class="text-xs">
						Attempt {attempt.id}: {attempt.state} · {new Date(attempt.created_at).toLocaleString()} ·
						{attempt.outcome_at
							? new Date(attempt.outcome_at).toLocaleString()
							: 'Outcome not confirmed'}
						{attempt.detail ?? ''}
					</p>
				{/each}
				{#if resendId}
					<div class="rounded border p-2">
						<p>
							Send the retained notice again under current settings. It may already have reached
							Telegram.
						</p>
						<label class="flex gap-2"
							><input type="checkbox" bind:checked={reviewedDuplicate} />I reviewed the current
							destination and accept a possible duplicate message.</label
						>
						<Button
							size="sm"
							disabled={!reviewedDuplicate || notices.busy || notices.unresolved}
							onclick={resend}>Send again</Button
						>
						<Button
							size="sm"
							variant="outline"
							onclick={() => {
								resendId = '';
								reviewedDuplicate = false;
							}}>Cancel resend review</Button
						>
					</div>
				{/if}
			{/if}
			<Button
				variant="outline"
				onclick={() => {
					dialogOpen = false;
				}}>Close</Button
			>
		</DialogContent></Dialog
	>
</div>
