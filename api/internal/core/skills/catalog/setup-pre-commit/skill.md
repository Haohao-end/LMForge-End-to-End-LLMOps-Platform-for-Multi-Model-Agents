# setup-pre-commit

这是一个为仓库配置 pre-commit 相关质量门禁的技能。

## 适用场景

- 用户想自动化 lint / format / typecheck
- 用户要设置 Husky、lint-staged 或 pre-commit hooks
- 用户想让本地提交阶段先拦住明显错误

## 工作方式

1. 先识别仓库用的语言和脚本工具。
2. 选择最少但有效的钩子组合。
3. 把常见检查前移到提交前。
