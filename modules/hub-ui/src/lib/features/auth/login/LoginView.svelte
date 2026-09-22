<script lang="ts">
	import GoogleLogin from './GoogleLogin.svelte';
	import { session } from '$lib/stores/session.svelte';
	import { api } from '$lib/api';
	import { toast } from 'svelte-sonner';
	import { Server, KeyRound, Lock, AlertCircle, Loader2, Mail } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import {
		Card,
		CardHeader,
		CardTitle,
		CardDescription,
		CardContent
	} from '$lib/components/ui/card';
	import ThemeToggle from '$lib/components/shared/ThemeToggle.svelte';

	// The email is remembered between visits; the password is only ever held by this form.
	let email = $state(session.email);
	let password = $state('');
	let isValidating = $state(false);
	let errorMsg = $state<string | null>(null);

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!email.trim() || !password) {
			errorMsg = 'Email and password are required';
			return;
		}

		isValidating = true;
		errorMsg = null;

		try {
			const res = await api.POST('/api/v1/users/login/', {
				body: { username: email.trim(), password, scope: '' },
				// The login endpoint is an OAuth2 password form, not JSON.
				bodySerializer: (body) => new URLSearchParams(body as Record<string, string>),
				headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
			});

			if (res.response?.status === 429) {
				// The backend locks a caller out after repeated failures; the right password is refused too until then.
				const retryAfter = Number(res.response.headers.get('Retry-After'));
				const minutes = Math.ceil((retryAfter || 300) / 60);
				errorMsg = `Too many failed attempts. Try again in ${minutes} minute(s).`;
				toast.error('Temporarily locked out');
			} else if (res.error || !res.data) {
				errorMsg = 'Sign-in failed. Check your email and password.';
				toast.error('Sign-in failed');
			} else {
				session.rememberEmail(email.trim());
				session.setTokens(res.data);
				password = '';
				toast.success('Signed in');
			}
		} catch {
			errorMsg = 'Could not reach server. Verify server is running on port 8389.';
			toast.error('Connection error');
		} finally {
			isValidating = false;
		}
	}
</script>

<div
	class="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background p-6"
>
	<!-- Background glow effects -->
	<div
		class="pointer-events-none absolute -top-40 left-1/4 size-96 rounded-full bg-primary/10 blur-3xl"
	></div>
	<div
		class="pointer-events-none absolute right-1/4 -bottom-40 size-96 rounded-full bg-primary/10 blur-3xl"
	></div>

	<!-- Top right theme toggle -->
	<div class="absolute top-6 right-6">
		<ThemeToggle />
	</div>

	<!-- Login Card -->
	<Card
		class="relative z-10 w-full max-w-md border-border/80 bg-card/80 shadow-xl backdrop-blur-xl"
	>
		<CardHeader class="space-y-3 text-center">
			<div
				class="mx-auto flex size-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/25"
			>
				<Server class="size-7" />
			</div>
			<CardTitle class="text-2xl font-bold tracking-tight">Autohub Manager</CardTitle>
			<CardDescription class="text-sm text-muted-foreground">
				Sign in to access the orchestrator
			</CardDescription>
		</CardHeader>

		<CardContent>
			<GoogleLogin />
			{#if errorMsg}
				<div
					class="mb-5 flex items-center gap-2.5 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm font-medium text-destructive"
				>
					<AlertCircle class="size-4 shrink-0" />
					<span>{errorMsg}</span>
				</div>
			{/if}

			<form onsubmit={handleSubmit} class="space-y-4">
				<div class="space-y-2">
					<label
						for="email"
						class="text-xs font-semibold tracking-wider text-muted-foreground uppercase"
					>
						Email
					</label>
					<div class="relative">
						<Mail class="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
						<Input
							id="email"
							type="email"
							autocomplete="username"
							placeholder="you@example.com"
							bind:value={email}
							class="h-11 pl-10"
							disabled={isValidating}
							required
						/>
					</div>
				</div>
				<div class="space-y-2">
					<label
						for="password"
						class="text-xs font-semibold tracking-wider text-muted-foreground uppercase"
					>
						Password
					</label>
					<div class="relative">
						<KeyRound
							class="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
						/>
						<Input
							id="password"
							type="password"
							autocomplete="current-password"
							placeholder="Enter password"
							bind:value={password}
							class="h-11 pl-10"
							disabled={isValidating}
							required
						/>
					</div>
				</div>

				<Button
					type="submit"
					class="h-11 w-full gap-2 font-semibold shadow-md"
					disabled={isValidating}
				>
					{#if isValidating}
						<Loader2 class="size-4 animate-spin" />
						Signing in...
					{:else}
						<Lock class="size-4" />
						Sign in
					{/if}
				</Button>
			</form>
		</CardContent>
	</Card>

	<footer
		class="mt-8 text-center text-xs font-semibold tracking-widest text-muted-foreground/60 uppercase"
	>
		Autohub Svelte • High Performance Cloud Scheduler UI
	</footer>
</div>
