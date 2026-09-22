<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { session } from '$lib/stores/session.svelte';
	import { apiBaseUrl } from '$lib/config';
	import { Button } from '$lib/components/ui/button';

	let enabled = $state(false);
	let busy = $state(false);
	let message = $state('');

	onMount(() => {
		void initialize();
	});

	async function initialize() {
		const url = new URL(window.location.href);
		const outcome = url.searchParams.get('google');
		if (outcome) {
			url.searchParams.delete('google');
			window.history.replaceState(window.history.state, '', url);
			if (outcome === 'complete') {
				busy = true;
				try {
					const { data } = await api.POST('/api/v1/auth/google/exchange');
					if (!data) throw new Error('Exchange failed');
					session.rememberEmail(data.email);
					if (data.status === 'approved' && data.tokens) {
						session.setTokens(data.tokens);
						return;
					}
					message =
						data.status === 'pending'
							? 'Your account is awaiting administrator approval. Sign in again after approval.'
							: data.status === 'rejected'
								? 'Your access request was declined. Contact the administrator.'
								: 'Your account is suspended. Contact the administrator.';
				} catch {
					message = 'Google sign-in expired or failed. Please try again.';
				} finally {
					busy = false;
				}
			} else {
				message =
					outcome === 'existing_account'
						? 'This email belongs to an existing account. Use its password login. Google accounts are not linked automatically.'
						: 'Google sign-in was cancelled or failed. Please try again.';
			}
		}
		try {
			const { data } = await api.GET('/api/v1/auth/google/options');
			enabled = data?.enabled ?? false;
		} catch {
			enabled = false;
		}
	}
</script>

{#if message}
	<p role="status" class="mb-4 rounded-lg border border-border bg-muted p-3 text-sm">{message}</p>
{/if}
{#if busy}
	<p role="status" class="mb-4 text-sm text-muted-foreground">Completing Google sign-in…</p>
{:else if enabled}
	<Button variant="outline" class="mb-4 w-full" href={`${apiBaseUrl()}/api/v1/auth/google/start`}>
		Continue with Google
	</Button>
	<p class="mb-5 text-center text-xs text-muted-foreground">
		New accounts require administrator approval.
	</p>
{/if}
