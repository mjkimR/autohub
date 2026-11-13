import prettier from 'eslint-config-prettier';
import path from 'node:path';
import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import { plugin as shadcn } from '@shadcn/lint';
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
		ignores: ['src/lib/components/ui/**']
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
		// Design-system lint (warnings): theme tokens and component variants own color and size.
		// Generated shadcn-svelte primitives define those variants and stay out of scope.
		files: ['src/**/*.svelte', 'src/**/*.ts'],
		ignores: ['src/lib/components/ui/**', 'src/lib/api/generated/**'],
		plugins: { shadcn },
		rules: {
			'shadcn/no-restyle': [
				'warn',
				{
					allow: ['layout'],
					contracts: [
						// Clickable cards may add a hover shadow.
						{ pattern: '^Card$', allow: ['layout', 'spacing', 'effects', 'motion'] },
						// Structural slots own their padding and gaps per screen.
						{
							pattern:
								'^(CardHeader|CardContent|CardFooter|DialogContent|DialogHeader|DialogFooter|TabsContent|TableRow)$',
							allow: ['layout', 'spacing']
						},
						// Text slots may resize and reweight their text, never recolor it.
						{
							pattern: '^(CardTitle|CardDescription|DialogTitle|DialogDescription|Badge)$',
							allow: ['layout', 'typography']
						},
						// Inputs may make room for icons and use monospace for identifiers or JSON.
						{ pattern: '^(Input|Textarea)$', allow: ['layout', 'spacing', 'typography'] },
						// Table cells carry content styling (muted or monospace values).
						{
							pattern: '^(TableCell|TableHead)$',
							allow: ['layout', 'spacing', 'typography', 'color']
						}
					]
				}
			],
			'shadcn/no-raw-colors': 'warn',
			'shadcn/no-arbitrary-values': 'warn',
			'shadcn/no-inline-styles': 'warn',
			'shadcn/no-unknown-classes': 'warn',
			'shadcn/require-static-classes': 'warn'
		}
	}
);
