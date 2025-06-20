# Open-Coze 前端项目 (Vue3 + Vite)

这是一个基于 Vue 3 和 Vite 构建的 LLMOps 平台前端项目模板。

## 🛠️ 推荐开发环境

- 编辑器: [VSCode](https://code.visualstudio.com/)
- 插件: [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (请禁用 Vetur)

## ⚙️ TypeScript 支持

TypeScript 默认无法处理 `.vue` 文件的类型信息，因此我们使用 `vue-tsc` 替代 `tsc` 进行类型检查。在编辑器中，需要安装 [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) 插件来支持 `.vue` 文件的类型提示。

## 🔧 自定义配置

查看 [Vite 配置文档](https://vitejs.dev/config/) 了解如何自定义项目配置。

## 🚀 项目初始化

```bash
npm install
```

### 启动开发服务器 (热更新)

```bash
npm run serve
```

### 类型检查 & 生产环境构建

```bash
npm run build
```

### 运行单元测试 (Vitest)

```bash
npm run test:unit
```

### 代码检查 (ESLint)

```bash
npm run lint
```

### 格式化代码

```bash
npm run format
```

## 📦 项目结构

```
src/
├── assets/          # 静态资源
├── components/      # 公共组件
├── composables/     # 组合式函数
├── router/          # 路由配置
├── stores/          # Pinia 状态管理
├── styles/          # 全局样式
├── utils/           # 工具函数
├── views/           # 页面组件
├── App.vue          # 根组件
└── main.ts          # 应用入口
```

## 📌 注意事项

1. 项目使用 Vue 3 的组合式 API (Composition API)
2. 样式方案采用 TailwindCSS
3. 状态管理使用 Pinia
4. 网络请求使用 Axios 封装
5. 支持 TypeScript 类型检查

