<script lang="ts">
	import type { components } from '$lib/api';
	let { outcome }: { outcome: components['schemas']['DecisionRequestRead'] } = $props();
	const original = $derived(outcome.result ?? {});
	const settings = $derived(
		original.settings as components['schemas']['SubscriptionSettings'] | undefined
	);
</script>

<section aria-label="Original command result" class="space-y-1 text-xs">
	<p>Original receipt: {outcome.record_state}</p>
	{#if outcome.record_state === 'recorded'}
		<p>
			Original destination generation: {String(original.destination_generation ?? 'unavailable')}
		</p>
		{#if outcome.operation === 'subscription'}
			<p>Original saved revision: {String(original.revision ?? 'unavailable')}</p>
			{#if settings}
				<p>Original subscription: {settings.enabled ? 'enabled' : 'disabled'} · {settings.mode}</p>
				<p>
					Original project scope: {settings.project_scope === 'all'
						? 'All current and future projects'
						: (settings.project_ids ?? []).join(', ')}
				</p>
				<p>Original decision kinds: {(settings.kinds ?? []).join(', ')}</p>
				<p>Original review origin: {settings.review_origin}</p>
			{/if}
		{:else}
			<p>Original resend notice: {String(original.notice_id ?? 'unavailable')}</p>
			<p>Original resend attempt: {String(original.attempt_id ?? 'unavailable')}</p>
		{/if}
	{:else}
		<p>No original command result is proven. Current settings do not settle this request.</p>
	{/if}
</section>
<section aria-label="Current command observation" class="space-y-1 text-xs">
	<p>
		Current subscription revision: {outcome.current.revision} · destination generation {outcome
			.current.destination_generation}
	</p>
	<p>
		Current subscription: {outcome.current.settings.enabled ? 'enabled' : 'disabled'} · {outcome
			.current.settings.mode}
	</p>
	<p>Current review origin: {outcome.current.settings.review_origin}</p>
	<p>
		Current project scope: {outcome.current.settings.project_scope === 'all'
			? 'All current and future projects'
			: (outcome.current.settings.project_ids ?? []).join(', ')}
	</p>
	<p>Current decision kinds: {(outcome.current.settings.kinds ?? []).join(', ')}</p>
	<p>Current settings observed {new Date(outcome.current.observed_at).toLocaleString()}</p>
	{#if outcome.operation === 'resend'}
		<p>
			Current attempt outcome: {outcome.attempt?.state ?? 'Detailed attempt history unavailable'};
			this is separate from original admission.
		</p>
	{/if}
</section>
