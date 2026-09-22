<script lang="ts">
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import { toast } from 'svelte-sonner';
	let {
		test,
		onresolved
	}: { test: components['schemas']['ConnectionTestRead']; onresolved: () => Promise<void> } =
		$props();
	let reviewing = $state(false);
	let confirmed = $state(false);
	let note = $state('');
	let busy = $state(false);
	let requestId = $state<string | null>(null);
	let reviewedHeads = $state<Record<string, string>>({});
	function candidateHeads(): Record<string, string> {
		const raw = test.evidence.unconfirmed_pulls;
		if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {};
		return Object.fromEntries(
			Object.entries(raw).flatMap(([number, value]) => {
				if (
					!/^\d+$/.test(number) ||
					!value ||
					typeof value !== 'object' ||
					!('sha' in value) ||
					typeof value.sha !== 'string'
				)
					return [];
				return [[number, value.sha]];
			})
		);
	}
	let candidates = $derived(candidateHeads());
	async function resolve() {
		busy = true;
		requestId ??= crypto.randomUUID();
		try {
			const res = await api.POST(
				'/api/v1/projects/{project_id}/connection-tests/{test_id}/resolve-cleanup',
				{
					params: { path: { project_id: test.project_id, test_id: test.id } },
					body: {
						request_id: requestId,
						confirmed_remote_stopped: true,
						note: note.trim(),
						unrelated_pulls: reviewedHeads
					}
				}
			);
			if (!res.data) {
				if (res.response.status >= 400 && res.response.status < 500) requestId = null;
				throw new Error(apiErrorMessage(res.error, 'Could not resolve cleanup'));
			}
			reviewing = false;
			requestId = null;
			confirmed = false;
			await onresolved();
			toast.success('Review recorded. Cleanup will recheck GitHub before completing.');
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Could not resolve cleanup');
		} finally {
			busy = false;
		}
	}
</script>

{#if Object.keys(candidates).length}
	<div class="space-y-2 rounded-lg border border-amber-500/40 p-3 text-sm">
		<p class="font-medium">PR ownership needs review</p>
		<p>
			These PRs share test history. AutoHub blocks their merge but does not mark, close, or delete
			them.
		</p>
		<ul>
			{#each Object.entries(candidates) as [number, sha] (number)}
				<li>
					<a
						class="text-primary underline"
						href={`https://github.com/${test.repository}/pull/${number}`}
						target="_blank"
						rel="noreferrer">PR #{number}</a
					>
					· {sha.slice(0, 12)}
				</li>
			{/each}
		</ul>
	</div>
{/if}
{#if test.cleanup_resolution_available}
	{#if !reviewing}
		<Button
			size="sm"
			variant="outline"
			onclick={() => {
				reviewing = true;
				confirmed = false;
				reviewedHeads = { ...candidates };
			}}>Review cleanup</Button
		>
	{:else}
		<form
			class="space-y-3 rounded-lg border p-4"
			onsubmit={(event) => {
				event.preventDefault();
				void resolve();
			}}
		>
			<p class="text-sm">
				Check the provider's session history first. This records your decision without creating
				another session. Confirmed test PRs remain protected; the 24-hour branch retention still
				applies.
			</p>
			<label class="flex items-start gap-2 text-sm">
				<input type="checkbox" bind:checked={confirmed} required disabled={busy} />
				I verified that no remote test work is running or can resume, and all PRs listed above are unrelated
				work that must remain untouched.
			</label>
			<label class="grid gap-1 text-sm"
				>Review notes
				<textarea
					class="rounded-md border bg-background p-2"
					bind:value={note}
					required
					maxlength="1000"
					disabled={busy}
					placeholder="For example: no session was created; checked the provider history."
				></textarea>
			</label>
			<div class="flex gap-2">
				<Button type="submit" size="sm" disabled={busy || !confirmed || !note.trim()}
					>Confirm review and continue cleanup</Button
				>
				<Button
					type="button"
					size="sm"
					variant="outline"
					disabled={busy}
					onclick={() => (reviewing = false)}>Back</Button
				>
			</div>
		</form>
	{/if}
{/if}
{#if test.evidence.cleanup_resolution}
	<p class="text-xs text-muted-foreground">
		Operator cleanup review recorded. The original test result is unchanged.
	</p>
{/if}
