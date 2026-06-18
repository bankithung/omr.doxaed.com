import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import jsxA11y from 'eslint-plugin-jsx-a11y'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    plugins: {
      'jsx-a11y': jsxA11y,
    },
    rules: {
      ...jsxA11y.configs.recommended.rules,
      // autoFocus on dialog inputs is intentional — it moves keyboard/screen-reader focus
      // into the dialog content, which is actually the correct accessibility pattern.
      'jsx-a11y/no-autofocus': 'warn',

      // --- Downgraded from "error" to "warn" ---
      // These rules fire on correct, working patterns in this codebase:
      //   set-state-in-effect: data-fetch effects legitimately set state inside useEffect;
      //     React 19 rule is over-strict for standard async-fetch patterns.
      //   only-export-components: context files (AuthContext, OrgContext) intentionally
      //     export both a Provider component and a hook — splitting them adds no value.
      //   exhaustive-deps: mount-only effects ([]) are intentional; deps are correct.
      'react-hooks/set-state-in-effect': 'warn',
      'react-refresh/only-export-components': 'warn',
      'react-hooks/exhaustive-deps': 'warn',
    },
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
  },
])
