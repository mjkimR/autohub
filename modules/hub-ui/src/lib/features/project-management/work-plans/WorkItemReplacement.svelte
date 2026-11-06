<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	type Read = components['schemas']['ReplacementRead'];
	type Item = components['schemas']['WorkItemRead'];
	type Link = components['schemas']['ReplacementLinkRead'];
	type Op = 'link' | 'accept' | 'withdraw';
	type Body = Omit<components['schemas']['ReplacementLinkCommand'], 'replacement_item_id'> &
		Partial<
			components['schemas']['ReplacementLinkCommand'] &
				components['schemas']['ReplacementAcceptCommand'] &
				components['schemas']['ReplacementWithdrawCommand']
		>;
	let {
		projectId,
		planId,
		item,
		items,
		refresh
	}: {
		projectId: string;
		planId: string;
		item: Item;
		items: Item[];
		refresh: () => Promise<void>;
	} = $props();
	let read = $state<Read | null>(null);
	let candidateId = $state('');
	let dependentId = $state('');
	let reason = $state('');
	let busy = $state(false);
	let error = $state('');
	let status = $state('');
	let reviewing = $state<{ op: Op; link: Link | null; basis: Read; acceptanceId?: string } | null>(
		null
	);
	let pending = $state<{
		op: Op;
		linkId: string | null;
		path: { project_id: string; plan_id: string; item_id: string };
		body: Body;
	} | null>(null);
	let confirmed = $state(false);
	const path = $derived({ project_id: projectId, plan_id: planId, item_id: item.id });
	const dependents = $derived(items.filter((i) => i.depends_on.includes(item.key)));
	const storageKey = $derived(`work-item-replacement:${projectId}:${item.id}`);
	onMount(() => {
		const saved = sessionStorage.getItem(storageKey);
		if (saved) {
			try {
				pending = JSON.parse(saved);
				status =
					'Restored unresolved replacement request. Retry its original endpoint and payload.';
			} catch {
				error =
					'Saved request cannot be read. Preserve it and inspect the original decision history.';
			}
		}
	});
	function invalidate() {
		reviewing = null;
		confirmed = false;
	}
	async function load(candidate = false, offset = 0, eventLink: Link | null = null) {
		invalidate();
		busy = true;
		error = '';
		try {
			const response = await api.GET(
				'/api/v1/projects/{project_id}/work-plans/{plan_id}/items/{item_id}/replacement-links',
				{
					params: {
						path,
						query: {
							replacement_item_id: candidate ? candidateId : undefined,
							offset,
							limit: 10,
							event_link_id: eventLink?.id,
							event_offset: eventLink?.events.length ?? 0
						}
					}
				}
			);
			if (!response.data)
				throw new Error(apiErrorMessage(response.error, 'Could not load replacement evidence'));
			if (eventLink && read) {
				read = {
					...response.data,
					links: response.data.links.map((link) =>
						link.id === eventLink.id
							? {
									...link,
									events: [...eventLink.events, ...link.events],
									acceptances: [
										...new Map(
											[
												...eventLink.acceptances.map((a) => ({ ...a, active: false })),
												...link.acceptances
											].map((a) => [a.id, a])
										).values()
									]
								}
							: link
					)
				};
			} else read = response.data;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load replacement evidence';
		} finally {
			busy = false;
		}
	}
	function review(op: Op, link: Link | null = null, acceptanceId?: string) {
		if (!read) return;
		reviewing = JSON.parse(JSON.stringify({ op, link, acceptanceId, basis: read }));
		confirmed = false;
		reason = '';
		dependentId = '';
	}
	async function submit() {
		if (!pending && (!read || !reviewing)) return;
		if (!pending) {
			const r = reviewing!;
			const replacement = r.link?.current_replacement ?? r.basis.candidate;
			if (!replacement) return;
			const body: Body = {
				request_id: crypto.randomUUID(),
				reason: reason.trim(),
				expected_original_revision: r.basis.original.plan_revision,
				expected_replacement_revision: replacement.plan_revision,
				expected_evidence_revision: r.basis.evidence_revision
			};
			if (r.op === 'link') body.replacement_item_id = replacement.item_id;
			if (r.op === 'accept')
				Object.assign(body, {
					dependent_item_id: dependentId,
					original_digest: r.basis.original.digest,
					replacement_digest: replacement.digest,
					merge_sha: replacement.merge_sha,
					execution_id: replacement.execution_id
				});
			if (r.op === 'withdraw') body.acceptance_id = r.acceptanceId ?? null;
			pending = { op: r.op, linkId: r.link?.id ?? null, path: { ...path }, body };
		}
		busy = true;
		error = '';
		const original = pending;
		try {
			sessionStorage.setItem(storageKey, JSON.stringify(original));
			const response =
				original.op === 'link'
					? await api.POST(
							'/api/v1/projects/{project_id}/work-plans/{plan_id}/items/{item_id}/replacement-links',
							{
								params: { path: original.path },
								body: original.body as components['schemas']['ReplacementLinkCommand']
							}
						)
					: original.op === 'accept'
						? await api.POST(
								'/api/v1/projects/{project_id}/work-plans/{plan_id}/items/{item_id}/replacement-links/{link_id}/acceptances',
								{
									params: { path: { ...original.path, link_id: original.linkId! } },
									body: original.body as components['schemas']['ReplacementAcceptCommand']
								}
							)
						: await api.POST(
								'/api/v1/projects/{project_id}/work-plans/{plan_id}/items/{item_id}/replacement-links/{link_id}/withdraw',
								{
									params: { path: { ...original.path, link_id: original.linkId! } },
									body: original.body as components['schemas']['ReplacementWithdrawCommand']
								}
							);
			if (!response.data) {
				const ownerCode =
					response.error && typeof response.error === 'object' && 'code' in response.error
						? response.error.code
						: null;
				if (response.response.status === 409 && ownerCode === 'REPLACEMENT_CONFLICT') {
					sessionStorage.removeItem(storageKey);
					pending = null;
					read = null;
					reviewing = null;
					confirmed = false;
					status = 'Refused. Refresh evidence, review current revisions and confirm a new request.';
				}
				throw new Error(apiErrorMessage(response.error, 'Replacement outcome unknown'));
			}
			read = response.data;
			sessionStorage.removeItem(storageKey);
			pending = null;
			reviewing = null;
			status = `Recorded ${response.data.result?.operation}. Original outcome remains ${response.data.original.item_state}.`;
			try {
				await refresh();
			} catch {
				error = 'Recorded; Plan refresh failed. Refresh evidence before another action.';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Outcome unknown. Retry the same request.';
		} finally {
			busy = false;
		}
	}
</script>

<section class="space-y-3 border-t pt-3" aria-label={`Replacement for ${item.key}`}>
	<Button size="sm" variant="outline" onclick={() => load()} disabled={busy}
		>Inspect replacement evidence</Button
	>
	{#if status}<p role="status">{status}</p>{/if}
	{#if error}<p role="alert">{error}</p>{/if}
	{#if pending}
		<p>
			Outcome unknown for request {pending.body.request_id}. The original request and reviewed
			revisions are retained.
		</p>
		<Button size="sm" onclick={submit} disabled={busy}>Retry same request</Button>
	{/if}
	{#if read}
		<p>
			Original {read.original.key}: {read.original.item_state} · Plan {read.original.plan_state} · {read
				.original.repository} → {read.original.target}
		</p>
		<p>Plan revision {read.original.plan_revision} · Evidence revision {read.evidence_revision}</p>
		<p>
			Linking or replacement merge alone releases no dependency. Acceptance applies to one existing
			local edge. Plan, schedule and capacity holds remain.
		</p>
		{#if !read.links.some((link) => link.active)}
			<label class="block"
				>Replacement Work Item ID<input
					class="block w-full rounded border bg-background p-2"
					bind:value={candidateId}
					oninput={invalidate}
					disabled={busy || !!pending}
				/></label
			>
			<Button
				size="sm"
				variant="outline"
				onclick={() => load(true)}
				disabled={busy || !!pending || !candidateId.trim()}>Review replacement</Button
			>
			{#if read.candidate}
				<div class="space-y-1 rounded border p-3">
					<p>{read.candidate.key}: {read.candidate.title} · {read.candidate.item_state}</p>
					<p>
						Plan {read.candidate.plan_id} · {read.candidate.repository} → {read.candidate.target}
					</p>
					<p class="whitespace-pre-wrap">{read.candidate.description}</p>
					<p class="whitespace-pre-wrap">Acceptance: {read.candidate.acceptance}</p>
					<Button size="sm" onclick={() => review('link')} disabled={busy || !!pending}
						>Link replacement</Button
					>
				</div>
			{/if}
		{/if}
		{#each read.links as link (link.id)}
			<article class="space-y-2 rounded border p-3">
				<p>
					{link.active ? 'Active' : 'Withdrawn'} link to {link.current_replacement.key}: {link
						.current_replacement.item_state} · Plan {link.current_replacement.plan_id}
				</p>
				<p>
					{link.current_replacement.repository} → {link.current_replacement.target} · merge {link
						.current_replacement.merge_sha ?? 'not confirmed'}
				</p>
				<p>Merge completed: {link.current_replacement.completed_at ?? 'not recorded'}</p>
				<p>{link.current_replacement.title}: {link.current_replacement.description}</p>
				<p>Acceptance: {link.current_replacement.acceptance}</p>
				<p>
					Specification digest {link.current_replacement.digest} · Execution {link
						.current_replacement.execution_id ?? 'not recorded'}
				</p>
				{#if link.current_replacement.pull_url}<a
						class="underline"
						href={link.current_replacement.pull_url}>Inspect replacement PR</a
					>{/if}
				<p>{link.actor}: {link.reason}</p>
				{#if link.active}
					<Button
						size="sm"
						onclick={() => review('accept', link)}
						disabled={busy || !!pending || link.current_replacement.item_state !== 'succeeded'}
						>Review edge acceptance</Button
					>
					<Button
						size="sm"
						variant="outline"
						onclick={() => review('withdraw', link)}
						disabled={busy || !!pending || link.acceptances.some((a) => a.consumed)}
						>Withdraw link</Button
					>
				{/if}
				{#each link.acceptances as acceptance (acceptance.id)}
					<p>
						Dependent {items.find((i) => i.id === acceptance.dependent_item_id)?.key ??
							acceptance.dependent_item_id} · {acceptance.consumed
							? 'consumed'
							: acceptance.active
								? 'accepted, not consumed'
								: 'withdrawn'} · {acceptance.actor}: {acceptance.reason}
					</p>
					{#if acceptance.active && !acceptance.consumed && link.active}<Button
							size="sm"
							variant="outline"
							onclick={() => review('withdraw', link, acceptance.id)}
							disabled={busy || !!pending}>Withdraw edge acceptance</Button
						>{/if}
				{/each}
				<details>
					<summary>Replacement history</summary>{#each link.events as event (event.id)}<p>
							{event.kind} · {event.actor}: {event.reason} · {event.created_at} · revision {event.revision}
						</p>{/each}
					{#if link.events.length < link.event_total_count}<Button
							size="sm"
							variant="ghost"
							onclick={() => load(false, read!.history_offset, link)}
							disabled={busy}>Load more replacement events</Button
						>{/if}
				</details>
			</article>
		{/each}
		{#if read.history_offset > 0}<Button
				size="sm"
				variant="ghost"
				onclick={() => load(false, Math.max(0, read!.history_offset - read!.history_limit))}
				disabled={busy}>Previous replacement links</Button
			>{/if}
		{#if read.history_offset + read.history_limit < read.history_total_count}<Button
				size="sm"
				variant="ghost"
				onclick={() => load(false, read!.history_offset + read!.history_limit)}
				disabled={busy}>Next replacement links</Button
			>{/if}
		{#if !read.links.length}<p>No replacement history. Legacy outcomes are unchanged.</p>{/if}
		{#if reviewing && !pending}
			<div class="space-y-2 rounded border p-3" aria-label="Confirm replacement decision">
				<p>
					Confirm {reviewing.op}. Original Item and Plan outcomes stay unchanged. A consumed edge or
					link cannot be withdrawn.
				</p>
				{#if reviewing.op === 'accept'}
					<label class="block"
						>Dependent edge<select
							class="block rounded border bg-background p-2"
							bind:value={dependentId}
							onchange={() => (confirmed = false)}
							disabled={busy}
							><option value="">Choose one existing edge</option
							>{#each dependents as dependent (dependent.id)}<option value={dependent.id}
									>{dependent.key} → {item.key}</option
								>{/each}</select
						></label
					>
					<p>
						Reviewed original digest {read.original.digest}; replacement merge {reviewing.link
							?.current_replacement.merge_sha}.
					</p>
				{/if}
				<label class="block"
					>Replacement reason<textarea
						class="block w-full rounded border bg-background p-2"
						bind:value={reason}
						oninput={() => (confirmed = false)}
						maxlength="500"
						disabled={busy}></textarea></label
				>
				<label
					><input type="checkbox" bind:checked={confirmed} disabled={busy} /> I reviewed both specifications,
					exact target and this edge decision.</label
				>
				<Button
					size="sm"
					onclick={submit}
					disabled={busy ||
						!confirmed ||
						!reason.trim() ||
						(reviewing.op === 'accept' && !dependentId)}>Confirm replacement decision</Button
				>
				<Button size="sm" variant="ghost" onclick={() => (reviewing = null)} disabled={busy}
					>Cancel</Button
				>
			</div>
		{/if}
	{/if}
</section>
