import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, expect, test, vi } from 'vitest';
import CustomViewerHost from './CustomViewerHost.svelte';

const { loadViewer } = vi.hoisted(() => ({ loadViewer: vi.fn() }));
vi.mock('./viewer-loader', () => ({ loadViewer }));
afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});
const config = {
	id: 'test',
	label: 'Test renderer',
	tagName: 'test-repo-viewer',
	scriptUrl: '/plugins/test.js',
	version: 'test',
	initialPath: 'docs/'
};

if (!customElements.get(config.tagName))
	customElements.define(config.tagName, class extends HTMLElement {});

test('mounts a host data source and updates the branch without exposing tokens', async () => {
	loadViewer.mockResolvedValue(config);
	const props = {
		config,
		projectId: 'p1',
		apiBase: '/api/v1/projects/p1/repository',
		ref: 'main',
		onfallback: vi.fn()
	};
	const { container, rerender } = render(CustomViewerHost, props);
	await waitFor(() =>
		expect(container.querySelector(config.tagName)?.getAttribute('branch')).toBe('main')
	);
	const viewer = container.querySelector(config.tagName) as HTMLElement & { dataSource: object };
	expect(viewer.dataSource).toHaveProperty('blob');
	expect(viewer.getAttribute('auth-token')).toBeNull();
	await rerender({
		...props,
		ref: 'feature/a',
		projectId: 'p2',
		apiBase: '/api/v1/projects/p2/repository'
	});
	await waitFor(() =>
		expect(container.querySelector(config.tagName)?.getAttribute('branch')).toBe('feature/a')
	);
	expect(container.querySelector(config.tagName)?.getAttribute('repo-id')).toBe('p2');
});

test('a broken bundle offers a working Git browser fallback', async () => {
	loadViewer.mockRejectedValue(new Error('Bundle unavailable'));
	const onfallback = vi.fn();
	render(CustomViewerHost, { config, projectId: 'p1', apiBase: '/api', ref: 'main', onfallback });
	await screen.findByRole('alert');
	await fireEvent.click(screen.getByRole('button', { name: 'Use Git browser' }));
	expect(onfallback).toHaveBeenCalledOnce();
});
