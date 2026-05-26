# 代码工坊

面向代码分析、补丁生成和自动化脚本执行的技能包。

## 能力

- 代码分析
- 补丁生成
- 自动化执行

## 工具

### `analyze_request`

输入：

- `request`: 用户需求描述

输出：

- `summary`
- `next_steps`

### `generate_patch`

输入：

- `request`: 需要修改的目标说明
- `context`: 相关上下文

输出：

- `request`
- `context`
- `patch_hint`

## 使用方式

- 先描述目标，再描述约束
- 给出相关上下文和可编辑文件
- 要求输出结构化建议或补丁草案

## 执行说明

- 生产环境优先通过 SCF 执行
- 当 SCF 不可用时，开发环境会回退到本地技能执行
## 示例

```json
{
  "request": "为当前页面补充只读 Markdown 详情"
}
```
