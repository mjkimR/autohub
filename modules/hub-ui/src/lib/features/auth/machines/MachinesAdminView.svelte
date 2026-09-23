<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import type { components } from '$lib/api/schema';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { toast } from 'svelte-sonner';
	import MachineKeysPanel from './MachineKeysPanel.svelte';
	import { DEFAULT_MACHINE_SCOPES, MACHINE_SCOPES } from './scopes';

	type Machine = components['schemas']['MachineRead'];
	let isAdmin = $state(false);
	let machines = $state<Machine[]>([]);
	let loading = $state(true);
	let failed = $state(false);
	let name = $state('');
	let scopes = $state<string[]>([...DEFAULT_MACHINE_SCOPES]);
	let busy = $state(false);
	let expanded = $state('');

	onMount(() => {
		void initialize();
	});

	async function initialize() {
		try {
			const { data } = await api.GET('/api/v1/users/me');
			isAdmin = data?.is_superadmin ?? false;
			if (isAdmin) await load();
		} catch {
			failed = true;
		} finally {
			loading = false;
		}
	}

	async function load() {
		loading = true;
		failed = false;
		try {
			const { data } = await api.GET('/api/v1/machines', { params: { query: { limit: 100 } } });
			if (!data) throw new Error('Unable to load machines');
			machines = data;
		} catch {
			failed = true;
			toast.error('Could not load machines');
		} finally {
			loading = false;
		}
	}

	function scopeLabel(scope: string) {
		return MACHINE_SCOPES.find((item) => item.value === scope)?.label ?? scope;
	}

	async function create() {
		busy = true;
		try {
			const { data, response } = await api.POST('/api/v1/machines', {
				body: { name: name.trim(), scopes }
			});
			if (!data) {
				toast.error(
					response.status === 409
						? 'A machine with this name already exists'
						: 'Could not create the machine'
				);
				return;
			}
			toast.success('Machine created');
			name = '';
			scopes = [...DEFAULT_MACHINE_SCOPES];
			await load();
			expanded = data.id;
		} catch {
			toast.error('Could not reach the server');
		} finally {
			busy = false;
		}
	}

	async function setActive(machine: Machine, isActive: boolean) {
		busy = true;
		try {
			const { data } = await api.PATCH('/api/v1/machines/{machine_id}', {
				params: { path: { machine_id: machine.id } },
				body: { is_active: isActive }
			});
			if (!data) toast.error('Could not update the machine');
			else toast.success(isActive ? 'Machine activated' : 'Machine deactivated');
			await load();
		} catch {
			toast.error('Could not reach the server');
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-6">
	<div class="flex items-start justify-between gap-4">
		<div>
			<h1 class="text-2xl font-semibold">Machine keys</h1>
			<p class="mt-2 text-sm text-muted-foreground">
				Machines authenticate MCP clients and the external scheduler. Scopes apply to the whole
				installation. Deactivating a machine rejects all of its keys on the next request.
			</p>
		</div>
		{#if isAdmin}<Button variant="outline" disabled={loading || busy} onclick={() => load()}
				>Refresh</Button
			>{/if}
	</div>
	{#if loading && machines.length === 0}
		<p role="status">Loading machines…</p>
	{:else if failed}
		<p role="alert">Could not load machines. Refresh to try again.</p>
	{:else if !isAdmin}
		<p role="alert">Administrator access is required.</p>
	{:else}
		<form
			class="space-y-4 rounded-lg border border-border p-5"
			onsubmit={(event) => {
				event.preventDefault();
				void create();
			}}
		>
			<h2 class="font-semibold">New machine</h2>
			<div class="space-y-1">
				<label class="block text-sm" for="machine-name">Name</label>
				<Input
					id="machine-name"
					bind:value={name}
					required
					maxlength={100}
					pattern="[a-zA-Z0-9][a-zA-Z0-9._\-]*"
					placeholder="personal-mcp"
					disabled={busy}
				/>
				<p class="text-xs text-muted-foreground">Letters, digits, dot, underscore and hyphen.</p>
			</div>
			<fieldset class="space-y-2">
				<legend class="text-sm">Scopes</legend>
				{#each MACHINE_SCOPES as scope (scope.value)}
					<label class="flex items-center gap-2 text-sm">
						<input type="checkbox" value={scope.value} bind:group={scopes} disabled={busy} />
						<span>{scope.label}</span>
						<span class="text-muted-foreground">— {scope.hint}</span>
					</label>
				{/each}
			</fieldset>
			<Button type="submit" disabled={busy || !name.trim() || scopes.length === 0}
				>Create machine</Button
			>
		</form>
		<div class="overflow-x-auto rounded-lg border border-border">
			<table class="w-full text-left text-sm">
				<thead class="bg-muted"
					><tr
						><th class="p-3">Machine</th><th class="p-3">Scopes</th><th class="p-3">Status</th><th
							class="p-3">Actions</th
						></tr
					></thead
				>
				<tbody>
					{#each machines as machine (machine.id)}
						<tr class="border-t border-border">
							<td class="p-3">{machine.name}</td>
							<td class="p-3">{(machine.scopes ?? []).map(scopeLabel).join(', ') || 'None'}</td>
							<td class="p-3">{machine.is_active ? 'Active' : 'Inactive'}</td>
							<td class="flex flex-wrap gap-2 p-3">
								<Button
									size="sm"
									variant="outline"
									aria-expanded={expanded === machine.id}
									onclick={() => (expanded = expanded === machine.id ? '' : machine.id)}
									>{expanded === machine.id ? 'Hide keys' : 'Keys'}</Button
								>
								<Button
									size="sm"
									variant="outline"
									disabled={busy}
									onclick={() => setActive(machine, !machine.is_active)}
									>{machine.is_active ? 'Deactivate' : 'Activate'}</Button
								>
							</td>
						</tr>
						{#if expanded === machine.id}
							<tr class="border-t border-border">
								<td colspan="4" class="p-0">
									<MachineKeysPanel {machine} />
								</td>
							</tr>
						{/if}
					{:else}
						<tr><td colspan="4" class="p-4">No machines yet.</td></tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
