import prettier from 'eslint-config-prettier';
import path from 'node:path';
import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import { defineConfig, includeIgnoreFile } from 'eslint/config';
import globals from 'globals';
import ts from 'typescript-eslint';
import { structure } from '@app-common/eslint-config/structure';

const gitignorePath = path.resolve(import.meta.dirname, '.gitignore');

export default defineConfig(
	{ ignores: ['src/lib/api/generated/**'] },
	includeIgnoreFile(gitignorePath),
	js.configs.recommended,
	ts.configs.recommended,
	svelte.configs.recommended,
	prettier,
	svelte.configs.prettier,
	...structure({
		// shadcn-svelte primitives are generated; authored views and shared components stay checked.
		ignores: [
			'src/lib/components/ui/**',
			'src/lib/features/project-management/repositories/specrig/**'
		]
	}),
	{
		languageOptions: { globals: { ...globals.browser, ...globals.node } },
		rules: {
			'no-undef': 'off'
		}
	},
	{
		files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],
		languageOptions: {
			parserOptions: {
				projectService: true,
				extraFileExtensions: ['.svelte'],
				parser: ts.parser
			}
		}
	},
	{
		files: ['src/lib/components/ui/**'],
		rules: { 'svelte/no-navigation-without-resolve': 'off' }
	},
	{
		rules: {
			'svelte/button-has-type': 'error',
			'svelte/no-navigation-without-resolve': 'off'
		}
	},
	{
		files: ['src/lib/features/project-management/repositories/specrig/**'],
		rules: {
			'@typescript-eslint/no-explicit-any': 'off',
			'@typescript-eslint/no-unused-expressions': 'off',
			'no-empty': 'off',
			'svelte/button-has-type': 'off',
			'svelte/no-at-html-tags': 'off',
			'svelte/require-each-key': 'off',
			'svelte/prefer-writable-derived': 'off'
		}
	}
);
