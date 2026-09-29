<script lang="ts">
	import './layout.css';
	import { onMount } from 'svelte';
	import { refreshSession } from '$lib/api/client';
	import favicon from '$lib/assets/favicon.svg';
	import AppShell from '$lib/components/shared/AppShell.svelte';
	import LoginView from '$lib/features/auth/login/LoginView.svelte';
	import { session } from '$lib/stores/session.svelte';
	import { ModeWatcher } from 'mode-watcher';
	import { Toaster } from 'svelte-sonner';

	let { children } = $props();
	let checking = $state(true);
	onMount(async () => {
		if (!new URL(location.href).searchParams.has('google')) await refreshSession();
		checking = false;
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<ModeWatcher />
<Toaster richColors position="top-right" />

{#if checking}
	<p class="p-6 text-muted-foreground">Restoring session…</p>
{:else if session.isAuthenticated}
	<AppShell>{@render children()}</AppShell>
{:else}
	<LoginView />
{/if}
