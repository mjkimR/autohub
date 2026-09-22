<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import type { components } from '$lib/api/schema';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { toast } from 'svelte-sonner';

	type User = components['schemas']['UserReadAdmin'];
	type Action = components['schemas']['UserAccessChange']['action'];
	type Event = components['schemas']['UserAccessEventRead'];
	let me = $state<User | null>(null);
	let users = $state<User[]>([]);
	let loading = $state(true);
	let failed = $state(false);
	let offset = $state(0);
	let last = $state(true);
	let selected = $state<User | null>(null);
	let action = $state<Action>('approve');
	let reason = $state('');
	let saving = $state(false);
	let events = $state<Event[]>([]);
	let historyUser = $state('');

	onMount(() => {
		void initialize();
	});

	async function initialize() {
		try {
			const { data } = await api.GET('/api/v1/users/me');
			me = data ?? null;
			if (me?.is_superadmin) await load();
		} catch {
			failed = true;
		} finally {
			loading = false;
		}
	}

	async function load(nextOffset = offset) {
		loading = true;
		failed = false;
		try {
			const { data } = await api.GET('/api/v1/users/admin/', {
				params: { query: { offset: nextOffset, limit: 50 } }
			});
			if (!data) throw new Error('Unable to load users');
			users = data.items;
			last = data.last ?? data.items.length < 50;
			offset = nextOffset;
		} catch {
			failed = true;
			toast.error('Could not load accounts');
		} finally {
			loading = false;
		}
	}

	function choose(user: User, nextAction: Action) {
		selected = user;
		action = nextAction;
		reason = '';
	}

	async function save() {
		if (!selected) return;
		saving = true;
		try {
			const { data, response } = await api.POST('/api/v1/users/admin/{user_id}/access', {
				params: { path: { user_id: selected.id } },
				body: { action, expected_version: selected.auth_version, reason: reason.trim() || null }
			});
			if (!data) {
				toast.error(
					response.status === 409
						? 'Account changed or this action is protected. Reload and review the account.'
						: 'Could not change account access'
				);
			} else {
				toast.success('Account access updated');
			}
			selected = null;
			events = [];
			historyUser = '';
			await load();
		} catch {
			toast.error('Could not reach the server');
		} finally {
			saving = false;
		}
	}

	async function showHistory(user: User) {
		try {
			const { data } = await api.GET('/api/v1/users/admin/{user_id}/access-events', {
				params: { path: { user_id: user.id } }
			});
			if (!data) throw new Error('Unable to load history');
			events = data;
			historyUser = user.email;
		} catch {
			toast.error('Could not load access history');
		}
	}
</script>

<div class="space-y-6">
	<div class="flex items-start justify-between gap-4">
		<div>
			<h1 class="text-2xl font-semibold">Account approval</h1>
			<p class="mt-2 text-sm text-muted-foreground">
				Approve access requests and manage account access. Approval grants access to all Hub
				projects.
			</p>
		</div>
		{#if me?.is_superadmin}<Button
				variant="outline"
				disabled={loading || saving}
				onclick={() => load()}>Refresh</Button
			>{/if}
	</div>
	{#if loading}
		<p role="status">Loading accounts…</p>
	{:else if failed}
		<p role="alert">Could not load accounts. Refresh to try again.</p>
	{:else if !me?.is_superadmin}
		<p role="alert">Administrator access is required.</p>
	{:else}
		<div class="overflow-x-auto rounded-lg border border-border">
			<table class="w-full text-left text-sm">
				<thead class="bg-muted"
					><tr
						><th class="p-3">Account</th><th class="p-3">Approval</th><th class="p-3">Access</th><th
							class="p-3">Role</th
						><th class="p-3">Actions</th></tr
					></thead
				>
				<tbody>
					{#each users as user (user.id)}
						<tr class="border-t border-border">
							<td class="p-3"
								>{user.email}{#if user.id === me.id}
									(you){/if}</td
							>
							<td class="p-3">{user.approval_status}</td>
							<td class="p-3">{user.is_active ? 'Active' : 'Suspended'}</td>
							<td class="p-3">{user.is_superadmin ? 'Administrator' : 'User'}</td>
							<td class="flex flex-wrap gap-2 p-3">
								{#if user.id !== me.id}
									{#if user.approval_status !== 'approved'}
										<Button size="sm" disabled={saving} onclick={() => choose(user, 'approve')}
											>Approve</Button
										>
									{/if}
									{#if user.approval_status === 'pending'}
										<Button
											size="sm"
											variant="outline"
											disabled={saving}
											onclick={() => choose(user, 'reject')}>Reject</Button
										>
									{/if}
									{#if user.approval_status === 'approved'}
										<Button
											size="sm"
											variant="outline"
											disabled={saving}
											onclick={() => choose(user, user.is_active ? 'suspend' : 'activate')}
											>{user.is_active ? 'Suspend' : 'Activate'}</Button
										>
										<Button
											size="sm"
											variant="outline"
											disabled={saving}
											onclick={() => choose(user, user.is_superadmin ? 'demote' : 'promote')}
											>{user.is_superadmin ? 'Remove admin' : 'Make admin'}</Button
										>
									{/if}
								{/if}
								<Button size="sm" variant="ghost" onclick={() => showHistory(user)}>History</Button>
							</td>
						</tr>
					{:else}
						<tr><td colspan="5" class="p-4">No accounts found.</td></tr>
					{/each}
				</tbody>
			</table>
		</div>
		<div class="flex items-center gap-3">
			<Button variant="outline" disabled={offset === 0 || saving} onclick={() => load(offset - 50)}
				>Previous</Button
			>
			<span class="text-sm">Page {Math.floor(offset / 50) + 1}</span>
			<Button variant="outline" disabled={last || saving} onclick={() => load(offset + 50)}
				>Next</Button
			>
		</div>
	{/if}
	{#if selected}
		<form
			class="space-y-4 rounded-lg border border-border p-5"
			onsubmit={(event) => {
				event.preventDefault();
				void save();
			}}
		>
			<h2 class="font-semibold">Confirm {action}: {selected.email}</h2>
			<p class="text-sm text-muted-foreground">
				This change ends the account's existing sessions. Administrator promotion grants account
				management permissions.
			</p>
			<label class="block text-sm" for="access-reason">Reason (optional)</label>
			<Input id="access-reason" bind:value={reason} maxlength={500} disabled={saving} />
			<div class="flex gap-2">
				<Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Confirm change'}</Button>
				<Button variant="outline" type="button" disabled={saving} onclick={() => (selected = null)}
					>Cancel</Button
				>
			</div>
		</form>
	{/if}
	{#if historyUser}
		<section class="space-y-3 rounded-lg border border-border p-5">
			<h2 class="font-semibold">Recent access changes: {historyUser}</h2>
			<p class="text-xs text-muted-foreground">Showing the latest 50 changes.</p>
			{#each events as event (event.id)}
				<div class="border-t border-border pt-3 text-sm">
					<p>{event.action} · {new Date(event.created_at).toLocaleString()}</p>
					<p class="text-muted-foreground">Actor: {event.actor_id ?? 'Deleted account'}</p>
					{#if event.reason}<p>{event.reason}</p>{/if}
				</div>
			{:else}<p class="text-sm text-muted-foreground">No changes recorded.</p>{/each}
		</section>
	{/if}
</div>
