<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import type { components } from '$lib/api/schema';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { toast } from 'svelte-sonner';
	import IssuedKeyNotice from './IssuedKeyNotice.svelte';

	type Machine = components['schemas']['MachineRead'];
	type Key = components['schemas']['KeyRead'];
	type Issued = components['schemas']['KeyIssued'];
	let { machine }: { machine: Machine } = $props();

	let keys = $state<Key[]>([]);
	let loading = $state(true);
	let label = $state('');
	let expiresAt = $state('');
	let busy = $state(false);
	let issued = $state<Issued | null>(null);
	let confirmRevoke = $state('');
	const mcp = $derived((machine.scopes ?? []).some((scope) => scope.startsWith('autohub:mcp:')));

	onMount(() => {
		void load();
	});

	async function load() {
		loading = true;
		try {
			const { data } = await api.GET('/api/v1/machines/{machine_id}/keys', {
				params: { path: { machine_id: machine.id }, query: { limit: 100 } }
			});
			if (!data) throw new Error('Unable to load keys');
			keys = data;
		} catch {
			toast.error('Could not load keys');
		} finally {
			loading = false;
		}
	}

	function status(key: Key) {
		if (key.revoked_at) return 'Revoked';
		if (key.expires_at && new Date(key.expires_at) <= new Date()) return 'Expired';
		return 'Active';
	}

	async function issue() {
		busy = true;
		try {
			const { data } = await api.POST('/api/v1/machines/{machine_id}/keys', {
				params: { path: { machine_id: machine.id } },
				body: {
					label: label.trim(),
					expires_at: expiresAt ? new Date(expiresAt).toISOString() : null
				}
			});
			if (!data) {
				toast.error('Could not issue a key');
				return;
			}
			issued = data;
			label = '';
			expiresAt = '';
			await load();
		} catch {
			toast.error('Could not reach the server');
		} finally {
			busy = false;
		}
	}

	async function revoke(key: Key) {
		busy = true;
		try {
			const { data } = await api.DELETE('/api/v1/machines/{machine_id}/keys/{key_id}', {
				params: { path: { machine_id: machine.id, key_id: key.id } }
			});
			if (!data) toast.error('Could not revoke the key');
			else toast.success('Key revoked');
			confirmRevoke = '';
			await load();
		} catch {
			toast.error('Could not reach the server');
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-4 bg-muted/30 p-4">
	{#if issued}
		<IssuedKeyNotice {issued} {mcp} ondismiss={() => (issued = null)} />
	{/if}
	{#if loading}
		<p role="status" class="text-sm">Loading keys…</p>
	{:else}
		<table class="w-full text-left text-sm">
			<thead
				><tr
					><th class="p-2">Label</th><th class="p-2">Created</th><th class="p-2">Expires</th><th
						class="p-2">Status</th
					><th class="p-2">Actions</th></tr
				></thead
			>
			<tbody>
				{#each keys as key (key.id)}
					<tr class="border-t border-border">
						<td class="p-2">{key.label}</td>
						<td class="p-2">{new Date(key.created_at).toLocaleString()}</td>
						<td class="p-2"
							>{key.expires_at ? new Date(key.expires_at).toLocaleString() : 'Never'}</td
						>
						<td class="p-2">{status(key)}</td>
						<td class="flex gap-2 p-2">
							{#if !key.revoked_at}
								{#if confirmRevoke === key.id}
									<Button
										size="sm"
										variant="destructive"
										disabled={busy}
										onclick={() => revoke(key)}>Confirm revoke</Button
									>
									<Button
										size="sm"
										variant="outline"
										disabled={busy}
										onclick={() => (confirmRevoke = '')}>Cancel</Button
									>
								{:else}
									<Button
										size="sm"
										variant="outline"
										disabled={busy}
										onclick={() => (confirmRevoke = key.id)}>Revoke</Button
									>
								{/if}
							{/if}
						</td>
					</tr>
				{:else}
					<tr><td colspan="5" class="p-2 text-muted-foreground">No keys issued.</td></tr>
				{/each}
			</tbody>
		</table>
	{/if}
	<form
		class="flex flex-wrap items-end gap-3"
		onsubmit={(event) => {
			event.preventDefault();
			void issue();
		}}
	>
		<div class="space-y-1">
			<label class="block text-sm" for="key-label-{machine.id}">Key label</label>
			<Input
				id="key-label-{machine.id}"
				bind:value={label}
				required
				maxlength={100}
				disabled={busy}
			/>
		</div>
		<div class="space-y-1">
			<label class="block text-sm" for="key-expires-{machine.id}">Expires (optional)</label>
			<Input
				id="key-expires-{machine.id}"
				type="datetime-local"
				bind:value={expiresAt}
				disabled={busy}
			/>
		</div>
		<Button type="submit" disabled={busy || !machine.is_active || !label.trim()}>Issue key</Button>
	</form>
	{#if !machine.is_active}
		<p class="text-sm text-muted-foreground">Activate the machine before issuing keys.</p>
	{/if}
</div>
