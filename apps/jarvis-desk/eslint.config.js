// ESLint for jarvis-desk.
//
// Sat op 8/9-2026 efter at et `useMemo` under en betinget return braekkede hele
// visningen med React #310 hos Bjoern. Det vaerste ved den fejl var hvor stille
// den var: tsc var ren, alle 605 tests groenne, buildet lykkedes og releasen gik
// ud — appen var ubrugelig foerst da han aabnede den. Intet i kaeden kiggede paa
// hook-raekkefoelge.
//
// `npm run lint`-scriptet har eksisteret hele tiden og pegede paa en config der
// ikke fandtes.
//
// Regelsaettet er bevidst SMALT. Formaalet er de fejl der ikke kan ses i en
// test og ikke fanges af tsc — ikke at omskrive husets stil. En lint der
// larmer om formatering bliver slaaet fra, og saa er vagten vaek igen.

import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import reactHooks from 'eslint-plugin-react-hooks'

export default tseslint.config(
  {
    ignores: ['dist/**', 'dist-electron/**', 'release/**', 'node_modules/**'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    plugins: { 'react-hooks': reactHooks },
    rules: {
      // ── grunden til at denne fil findes ──────────────────────────────────
      'react-hooks/rules-of-hooks': 'error',
      // Manglende afhaengigheder er en advarsel, ikke en fejl: flere effekter
      // her udelader BEVIDST en afhaengighed (se kommentarerne i
      // SessionContext og CodePanel), og en haard fejl ville tvinge dem til at
      // slaa hele reglen fra.
      'react-hooks/exhaustive-deps': 'warn',

      // ── stoej der ville faa nogen til at slukke for lint'en ──────────────
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/no-empty-object-type': 'off',
      'no-empty': ['error', { allowEmptyCatch: true }],
    },
  },
  {
    // Electron-hovedprocessen og tests koerer i Node, ikke i browseren.
    files: ['electron/**/*.ts', '**/*.test.{ts,tsx}', 'vite.config.ts'],
    languageOptions: {
      globals: {
        process: 'readonly', __dirname: 'readonly', require: 'readonly',
        console: 'readonly', Buffer: 'readonly', module: 'writable',
      },
    },
    rules: {
      // `electron/bridge.ts` baerer @ts-nocheck med vilje.
      '@typescript-eslint/ban-ts-comment': 'off',
    },
  },
  {
    // Build-hooks er CommonJS og koerer i Node under electron-builder.
    files: ['build-hooks/**/*.cjs', '**/*.cjs'],
    languageOptions: {
      sourceType: 'commonjs',
      globals: {
        require: 'readonly', module: 'writable', exports: 'writable',
        __dirname: 'readonly', process: 'readonly', console: 'readonly',
      },
    },
    rules: { '@typescript-eslint/no-require-imports': 'off' },
  },
  {
    // Canvas-tegning skrevet som taette udtryk (`a ? ctx.lineTo(…) : …`). Det
    // er en stil-praeference, ikke en fejl, og at omskrive tegnekoden for at
    // goere en linter glad ville vaere at aendre virkende kode uden grund.
    files: ['src/components/PresenceOrb.tsx'],
    rules: { '@typescript-eslint/no-unused-expressions': 'off' },
  },
)
