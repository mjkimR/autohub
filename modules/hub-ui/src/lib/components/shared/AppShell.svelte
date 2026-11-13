<script lang="ts">
	import { logoutSession } from '$lib/api/client';
	import { toast } from 'svelte-sonner';
	import { session } from '$lib/stores/session.svelte';
	import { api } from '$lib/api';
	import { page } from '$app/state';
	import ThemeToggle from '$lib/components/shared/ThemeToggle.svelte';
	import SidebarLink from '$lib/components/shared/SidebarLink.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import {
		PENDING_DECISION_NAV_MIN_MS,
		PENDING_DECISIONS_UNKNOWN_LABEL,
		PendingDecisions,
		isPendingDecisionUnknown,
		pendingDecisionPhrase,
		pendingDecisionText
	} from '$lib/features/project-management/pipeline-runs/pending-decisions.svelte';
	import SidebarNavGroup from '$lib/components/shared/SidebarNavGroup.svelte';
	import {
		ADMIN_GROUP,
		DECISIONS_HREF,
		NAV_GROUPS,
		activeHref,
		pageLabel
	} from '$lib/components/shared/app-shell-nav';
	import { Server, Menu, LogOut } from '@lucide/svelte';
	import { onMount } from 'svelte';

	let { children } = $props();

	let menuChoice = $state({ url: '', open: false });
	const menuOpen = $derived(menuChoice.url === page.url.href && menuChoice.open);

	let isOnline = $state(false);
	let isAdmin = $state(false);

	async function loadProfile() {
		const generation = session.generation;
		try {
			const { data } = await api.GET('/api/v1/users/me');
			if (generation === session.generation) isAdmin = data?.is_superadmin ?? false;
		} catch {
			isAdmin = false;
		}
	}

	async function checkHealth() {
		try {
			const res = await api.GET('/api/health');
			const data = res.data as { status?: string } | undefined;
			isOnline = data?.status === 'ok';
		} catch {
			isOnline = false;
		}
	}

	// Operator-owed decisions light the shell; zero shows nothing, unknown shows a neutral "?".
	const pending = new PendingDecisions();
	const pendingText = $derived(pendingDecisionText(pending.value));
	const pendingPhrase = $derived(pendingDecisionPhrase(pending.value));
	const pendingUnknown = $derived(isPendingDecisionUnknown(pending.value));

	onMount(() => {
		checkHealth();
		void loadProfile();
		const interval = setInterval(checkHealth, 10000);
		const stopPending = pending.start();
		return () => {
			clearInterval(interval);
			stopPending();
		};
	});

	// Deciding happens on other screens; re-check on navigation, throttled for the shared DB budget.
	let lastPath = page.url.pathname;
	$effect(() => {
		const path = page.url.pathname;
		if (path === lastPath) return;
		lastPath = path;
		pending.refreshIfStale(PENDING_DECISION_NAV_MIN_MS);
	});

	const current = $derived(activeHref(page.url.pathname));
	const currentLabel = $derived(pageLabel(page.url.pathname));
	const groups = $derived(isAdmin ? [...NAV_GROUPS, ADMIN_GROUP] : NAV_GROUPS);
</script>

<div class="flex min-h-screen min-w-0 flex-col bg-background text-foreground lg:flex-row">
	<header
		class={[
			'flex items-center gap-3 border-b border-border p-3 lg:hidden',
			pendingText && 'border-t-2 border-t-attention-text'
		]}
		data-pending-rule={pendingText ? 'true' : undefined}
	>
		<Button
			variant="outline"
			aria-controls="primary-navigation"
			aria-expanded={menuOpen}
			onclick={() => (menuChoice = { url: page.url.href, open: !menuOpen })}
			><Menu class="size-4" /> Menu</Button
		>
		<span class="min-w-0 flex-1 truncate text-sm font-semibold">{currentLabel}</span>
		{#if pendingText}
			<a
				href="/decisions"
				aria-label="Decisions: {pendingPhrase}"
				class="inline-flex min-h-11 items-center rounded-lg px-1 outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
			>
				<Badge variant="attention" class="tabular-nums">
					<span aria-hidden="true" class="size-1.5 rounded-full bg-attention-text"></span>
					{pendingText} pending
				</Badge>
			</a>
		{:else if pendingUnknown}
			<a
				href="/decisions"
				aria-label="Decisions: {PENDING_DECISIONS_UNKNOWN_LABEL}"
				title={PENDING_DECISIONS_UNKNOWN_LABEL}
				class="inline-flex min-h-11 items-center rounded-lg px-1 outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
			>
				<Badge variant="outline" data-pending-unknown>?</Badge>
			</a>
		{/if}
		<ThemeToggle />
	</header>
	<!-- Left Sidebar -->
	<aside
		id="primary-navigation"
		class={[
			'w-full shrink-0 flex-col border-b border-sidebar-border bg-sidebar px-4 py-6 text-sidebar-foreground lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-64 lg:border-r lg:border-b-0',
			menuOpen ? 'flex' : 'hidden'
		]}
	>
		<!-- Brand / Logo -->
		<div class="flex items-center gap-3 px-2 pb-6">
			<div
				class="flex size-10 items-center justify-center rounded-xl bg-sidebar-primary text-sidebar-primary-foreground shadow-md"
			>
				<Server class="size-5" />
			</div>
			<div class="font-bold tracking-tight text-sidebar-foreground">Autohub</div>
		</div>

		<!-- Nav Links -->
		<nav class="flex-1 space-y-5 overflow-y-auto py-4" aria-label="Primary navigation">
			{#each groups as group (group.id)}
				<SidebarNavGroup {group} {current}>
					{#snippet link(item)}
						<SidebarLink
							href={item.href}
							label={item.label}
							icon={item.icon}
							active={item.href === current}
						>
							{#snippet trailing()}
								{#if item.href === DECISIONS_HREF && pendingText}
									<Badge variant="attention" class="tabular-nums" data-pending-count>
										<span aria-hidden="true">{pendingText}</span>
										<span class="sr-only">{pendingPhrase}</span>
									</Badge>
								{:else if item.href === DECISIONS_HREF && pendingUnknown}
									<Badge
										variant="outline"
										title={PENDING_DECISIONS_UNKNOWN_LABEL}
										data-pending-unknown
									>
										<span aria-hidden="true">?</span>
										<span class="sr-only">{PENDING_DECISIONS_UNKNOWN_LABEL}</span>
									</Badge>
								{/if}
							{/snippet}
						</SidebarLink>
					{/snippet}
				</SidebarNavGroup>
			{/each}
		</nav>

		<!-- Bottom User & Status Area -->
		<div class="space-y-4 border-t border-sidebar-border pt-4">
			<div class="flex items-center justify-between px-2">
				<div class="flex items-center gap-2 text-xs">
					{#if isOnline}
						<span class="flex size-2 rounded-full bg-success"></span>
						<span class="text-muted-foreground">Core Online</span>
					{:else}
						<span class="flex size-2 rounded-full bg-destructive"></span>
						<span class="text-destructive">Offline</span>
					{/if}
				</div>
				<ThemeToggle />
			</div>

			<div class="flex items-center justify-between rounded-lg bg-sidebar-accent/60 p-2.5">
				<div class="flex flex-col gap-1 text-xs">
					<span class="font-semibold text-sidebar-foreground">API Session</span>
					<div class="flex items-center gap-1.5">
						{#if session.isAuthenticated}
							<span
								class="inline-flex items-center gap-1.5 rounded-full bg-success/15 px-2 py-0.5 text-xs font-medium text-success"
							>
								<span class="size-1.5 rounded-full bg-success"></span>
								Active
							</span>
						{:else}
							<span
								class="inline-flex items-center gap-1.5 rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
							>
								<span class="size-1.5 rounded-full bg-muted-foreground/50"></span>
								No Session
							</span>
						{/if}
					</div>
				</div>
				<Button
					variant="subtle-destructive"
					size="icon"
					onclick={() =>
						logoutSession().catch(() => toast.error('Sign-out failed. Please try again.'))}
					title="Logout"
					aria-label="Logout"
				>
					<LogOut class="size-4" />
				</Button>
			</div>
		</div>
	</aside>

	<!-- Main Content Area -->
	<main class="min-w-0 flex-1">
		<!-- Top Bar -->
		<header
			class={[
				'sticky top-0 z-20 hidden h-16 items-center justify-between border-b border-border/80 bg-background/80 px-8 backdrop-blur-md lg:flex',
				pendingText && 'border-t-2 border-t-attention-text'
			]}
			data-pending-rule={pendingText ? 'true' : undefined}
		>
			<div class="flex items-center gap-2">
				<span class="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
					Autohub
				</span>
				<span class="text-muted-foreground/60">/</span>
				<span class="text-sm font-semibold text-foreground">
					{currentLabel}
				</span>
			</div>
		</header>

		<!-- Page Content Container -->
		<div class="mx-auto max-w-7xl min-w-0 p-3 wrap-anywhere sm:p-6 lg:p-8">
			{@render children()}
		</div>
	</main>
</div>
