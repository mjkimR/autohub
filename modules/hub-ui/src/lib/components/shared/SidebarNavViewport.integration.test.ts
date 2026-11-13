import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import SidebarNavViewport from './SidebarNavViewport.svelte';

const children = createRawSnippet(() => ({
	render: () =>
		'<div><a href="/first">First</a><div><a href="/last" aria-current="page">Last</a></div></div>'
}));
let resize: () => void;
let disconnect: ReturnType<typeof vi.fn>;
let observe: ReturnType<typeof vi.fn>;
beforeEach(() => {
	disconnect = vi.fn();
	observe = vi.fn();
	vi.stubGlobal(
		'ResizeObserver',
		class {
			constructor(callback: () => void) {
				resize = callback;
			}
			observe = observe;
			disconnect = disconnect;
		}
	);
});
afterEach(() => {
	cleanup();
	vi.unstubAllGlobals();
	vi.restoreAllMocks();
});

const cue = (edge: string) => document.querySelector(`[data-navigation-cue="${edge}"]`)!;
const visible = (edge: string) => cue(edge).getAttribute('data-visible') === 'true';
function mount() {
	const view = render(SidebarNavViewport, { children, menuOpen: false, current: null });
	const nav = screen.getByRole('navigation', { name: 'Primary navigation' });
	let height = 100;
	let total = 300;
	Object.defineProperties(nav, {
		clientHeight: { configurable: true, get: () => height },
		scrollHeight: { configurable: true, get: () => total }
	});
	return {
		view,
		nav,
		size: (h: number, t: number) => {
			height = h;
			total = t;
		}
	};
}

test('fit, top, middle, bottom and fractional boundaries show only hidden edges', async () => {
	const { nav, size } = mount();
	resize();
	await waitFor(() => expect(visible('bottom')).toBe(true));
	expect(visible('top')).toBe(false);
	nav.scrollTop = 100;
	await fireEvent.scroll(nav);
	await waitFor(() => expect(visible('top')).toBe(true));
	expect(visible('bottom')).toBe(true);
	nav.scrollTop = 199.5;
	await fireEvent.scroll(nav);
	await waitFor(() => expect(visible('bottom')).toBe(false));
	nav.scrollTop = 0.5;
	await fireEvent.scroll(nav);
	await waitFor(() => expect(visible('top')).toBe(false));
	size(300, 300);
	resize();
	await waitFor(() => expect(visible('bottom')).toBe(false));
});

test('zero-height hidden regions show neither cue, including after content resize', async () => {
	const { nav, size } = mount();
	nav.scrollTop = 50;
	resize();
	await waitFor(() => expect(visible('top')).toBe(true));
	size(0, 300);
	resize();
	await waitFor(() => expect(visible('top')).toBe(false));
	expect(visible('bottom')).toBe(false);
});

test('resize observes viewport and content; decoration cannot focus or intercept links', async () => {
	const { nav } = mount();
	resize();
	await waitFor(() => expect(visible('bottom')).toBe(true));
	expect(observe).toHaveBeenCalledWith(nav);
	expect(observe).toHaveBeenCalledWith(nav.firstElementChild);
	for (const edge of ['top', 'bottom']) {
		expect(cue(edge).getAttribute('aria-hidden')).toBe('true');
		expect(cue(edge).getAttribute('tabindex')).toBeNull();
		expect(cue(edge).classList.contains('pointer-events-none')).toBe(true);
		expect(nav.contains(cue(edge))).toBe(false);
	}
});

test('reveal aligns the displayed active link only within navigation', async () => {
	const { view, nav, size } = mount();
	size(0, 300);
	resize();
	const active = screen.getByRole('link', { name: 'Last' });
	vi.spyOn(active, 'getClientRects').mockReturnValue([new DOMRect()] as unknown as DOMRectList);
	vi.spyOn(nav, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, 10, 200, 100));
	vi.spyOn(active, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, 250, 150, 40));
	const pageScroll = vi.spyOn(window, 'scrollTo');
	size(100, 300);
	await view.rerender({ children, menuOpen: true, current: '/last' });
	await waitFor(() => expect(nav.scrollTop).toBe(184));
	expect(pageScroll).not.toHaveBeenCalled();
	expect(visible('top')).toBe(true);
});

test('explicitly hidden active destination stays collapsed on reveal', async () => {
	const { view, nav } = mount();
	const active = screen.getByRole('link', { name: 'Last' });
	active.parentElement!.hidden = true;
	vi.spyOn(active, 'getClientRects').mockReturnValue([new DOMRect()] as unknown as DOMRectList);
	await view.rerender({ children, menuOpen: true, current: '/last' });
	expect(active.parentElement!.hidden).toBe(true);
	expect(nav.scrollTop).toBe(0);
});

test('without ResizeObserver content, visibility and window resize still update cues', async () => {
	vi.stubGlobal('ResizeObserver', undefined);
	const { nav, size } = mount();
	size(300, 300);
	await fireEvent.resize(window);
	await waitFor(() => expect(visible('bottom')).toBe(false));
	size(100, 400);
	nav.firstElementChild!.append(document.createElement('a'));
	await waitFor(() => expect(visible('bottom')).toBe(true));
	size(500, 400);
	await fireEvent.resize(window);
	await waitFor(() => expect(visible('bottom')).toBe(false));
});

test('unmount disconnects both observers and removes its resize listener', async () => {
	const remove = vi.spyOn(window, 'removeEventListener');
	const mutation = vi.spyOn(MutationObserver.prototype, 'disconnect');
	const { view } = mount();
	await view.unmount();
	expect(disconnect).toHaveBeenCalledOnce();
	expect(mutation).toHaveBeenCalledOnce();
	expect(remove).toHaveBeenCalledWith('resize', expect.any(Function));
	resize(); // queued deliveries after teardown are harmless.
});

test('a late active administrative link receives clearance without snapping later user scroll', async () => {
	const { nav } = mount();
	const old = screen.getByRole('link', { name: 'Last' });
	old.removeAttribute('aria-current');
	const active = document.createElement('a');
	active.href = '/admin';
	active.textContent = 'Administration';
	active.setAttribute('aria-current', 'page');
	vi.spyOn(active, 'getClientRects').mockReturnValue([new DOMRect()] as unknown as DOMRectList);
	vi.spyOn(nav, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, 10, 200, 100));
	vi.spyOn(active, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, 250, 150, 40));
	nav.firstElementChild!.append(active);
	await waitFor(() => expect(nav.scrollTop).toBe(184));
	nav.scrollTop = 0;
	await fireEvent.scroll(nav);
	expect(nav.scrollTop).toBe(0);
});

test('keyboard focus keeps another destination and its ring inside the scrollport', async () => {
	const { nav } = mount();
	const first = screen.getByRole('link', { name: 'First' });
	vi.spyOn(nav, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, 10, 200, 100));
	vi.spyOn(first, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, 2, 150, 40));
	nav.scrollTop = 20;
	await fireEvent.focusIn(first);
	expect(nav.scrollTop).toBe(8);
});
