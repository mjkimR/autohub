<script lang="ts">
	import { session } from '$lib/stores/session.svelte';
	import { api } from '$lib/api';
	import { page } from '$app/state';
	import ThemeToggle from '$lib/components/shared/ThemeToggle.svelte';
	import { Button } from '$lib/components/ui/button';
	import {
		Server,
		Menu,
		LayoutDashboard,
		FolderKanban,
		CalendarClock,
		History,
		Settings,
		FileCode,
		LogOut,
		Workflow,
		KeyRound,
		Bot,
		BellRing,
		Webhook
	} from '@lucide/svelte';
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

	onMount(() => {
		checkHealth();
		void loadProfile();
		const interval = setInterval(checkHealth, 10000);
		return () => clearInterval(interval);
	});

	const navSections = [
		{
			label: 'Overview',
			items: [{ href: '/', label: 'Dashboard', icon: LayoutDashboard }]
		},
		{
			label: 'Project management',
			items: [
				{ href: '/projects', label: 'Projects', icon: FolderKanban },
				{ href: '/projects/runs', label: 'Pipeline runs', icon: Workflow }
			]
		},
		{
			label: 'Scheduling',
			items: [
				{ href: '/schedules/configs', label: 'Schedule configs', icon: CalendarClock },
				{ href: '/schedules/jobs', label: 'Schedule jobs', icon: History }
			]
		},
		{
			label: 'Configuration',
			items: [
				{ href: '/settings/connectors', label: 'Connectors', icon: KeyRound },
				{ href: '/settings/ai-catalogs', label: 'AI Catalogs', icon: Bot },
				{ href: '/settings/notifications', label: 'Notifications', icon: BellRing },
				{ href: '/settings/system', label: 'System configs', icon: Settings }
			]
		},
		{
			label: 'Operations',
			items: [
				{ href: '/operations/tasks', label: 'Task specs', icon: FileCode },
				{ href: '/operations/webhooks', label: 'Webhook deliveries', icon: Webhook }
			]
		}
	] as const;

	function isActive(href: string) {
		if (
			href === '/projects' &&
			page.url.pathname.startsWith('/projects/') &&
			page.url.pathname !== '/projects/runs'
		)
			return true;
		return page.url.pathname === href;
	}

	function currentPageLabel() {
		if (page.url.pathname === '/admin/users') return 'Account approval';
		if (page.url.pathname === '/admin/machines') return 'Machine keys';
		for (const section of navSections) {
			for (const item of section.items) {
				if (isActive(item.href)) return item.label;
			}
		}
		return 'Page not found';
	}
</script>

<div class="flex min-h-screen min-w-0 flex-col bg-background text-foreground lg:flex-row">
	<header class="flex items-center gap-3 border-b border-border p-3 lg:hidden">
		<Button
			variant="outline"
			class="min-h-11"
			aria-controls="primary-navigation"
			aria-expanded={menuOpen}
			onclick={() => (menuChoice = { url: page.url.href, open: !menuOpen })}
			><Menu class="size-4" /> Menu</Button
		>
		<span class="min-w-0 flex-1 truncate text-sm font-semibold">{currentPageLabel()}</span>
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
			<div>
				<div class="font-bold tracking-tight text-sidebar-foreground">Autohub</div>
				<div class="text-[11px] font-medium text-muted-foreground">Scheduler Manager</div>
			</div>
		</div>

		<!-- Nav Links -->
		<nav class="flex-1 space-y-5 overflow-y-auto py-4" aria-label="Primary navigation">
			{#each navSections as section (section.label)}
				<div>
					<p
						class="px-3 pb-1.5 text-[10px] font-semibold tracking-wider text-muted-foreground uppercase"
					>
						{section.label}
					</p>
					<div class="space-y-1">
						{#each section.items as item (item.href)}
							<a
								href={item.href}
								aria-current={isActive(item.href) ? 'page' : undefined}
								class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors {isActive(
									item.href
								)
									? 'bg-sidebar-accent font-semibold text-sidebar-accent-foreground shadow-xs'
									: 'text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'}"
							>
								<item.icon class="size-4 shrink-0" />
								<span>{item.label}</span>
							</a>
						{/each}
					</div>
				</div>
			{/each}
			{#if isAdmin}
				<a
					href="/admin/users"
					aria-current={isActive('/admin/users') ? 'page' : undefined}
					class="block rounded-lg px-3 py-2.5 text-sm font-medium hover:bg-sidebar-accent"
					>Account approval</a
				>
				<a
					href="/admin/machines"
					aria-current={isActive('/admin/machines') ? 'page' : undefined}
					class="block rounded-lg px-3 py-2.5 text-sm font-medium hover:bg-sidebar-accent"
					>Machine keys</a
				>
			{/if}
		</nav>

		<!-- Bottom User & Status Area -->
		<div class="space-y-4 border-t border-sidebar-border pt-4">
			<div class="flex items-center justify-between px-2">
				<div class="flex items-center gap-2 text-xs">
					{#if isOnline}
						<span class="flex size-2 rounded-full bg-emerald-500"></span>
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
								class="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400"
							>
								<span class="size-1.5 rounded-full bg-emerald-500"></span>
								Active
							</span>
						{:else}
							<span
								class="inline-flex items-center gap-1.5 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
							>
								<span class="size-1.5 rounded-full bg-muted-foreground/50"></span>
								No Session
							</span>
						{/if}
					</div>
				</div>
				<Button
					variant="ghost"
					size="icon"
					onclick={() => session.logout()}
					class="size-8 text-muted-foreground hover:text-destructive"
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
			class="sticky top-0 z-20 hidden h-16 items-center justify-between border-b border-border/80 bg-background/80 px-8 backdrop-blur-md lg:flex"
		>
			<div class="flex items-center gap-2">
				<span class="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
					Autohub
				</span>
				<span class="text-muted-foreground/60">/</span>
				<span class="text-sm font-semibold text-foreground capitalize">
					{currentPageLabel()}
				</span>
			</div>

			<div class="flex items-center gap-3 text-xs text-muted-foreground">
				<span
					class="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 font-medium text-primary"
				>
					<span class="size-1.5 animate-pulse rounded-full bg-primary"></span>
					Svelte 5 Runes
				</span>
			</div>
		</header>

		<!-- Page Content Container -->
		<div class="mx-auto max-w-7xl min-w-0 p-3 [overflow-wrap:anywhere] sm:p-6 lg:p-8">
			{@render children()}
		</div>
	</main>
</div>
