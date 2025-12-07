module.exports = {
  root: true,
  env: { browser: true, es2022: true, node: false },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
    'plugin:jsx-a11y/recommended',
    'plugin:import/recommended',
    'prettier',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  settings: { react: { version: 'detect' } },
  rules: {
    'react/prop-types': 'off',
    'import/no-unresolved': 'off', // Vite handles path aliases; toggle if you add tsconfig paths
  },
  ignorePatterns: ['dist/', 'build/', 'node_modules/'],
};
