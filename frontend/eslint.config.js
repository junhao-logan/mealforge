import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
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
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      // 页面在 useEffect 里调 reload() 拉数据(setState 在 await 之后)是 React 18 的常规写法;
      // 这条 React Compiler 规则对它一律报错。彻底消除需要换成 React Query / Suspense 取数,
      // 属于单独的重构, 先降为 warn 保留提示, 不阻塞 CI。
      'react-hooks/set-state-in-effect': 'warn',
    },
  },
  {
    // shadcn/ui 组件按官方写法同时导出组件和 variants(如 buttonVariants), 不改源码结构
    files: ['src/components/ui/**/*.{js,jsx}'],
    rules: { 'react-refresh/only-export-components': 'off' },
  },
])
