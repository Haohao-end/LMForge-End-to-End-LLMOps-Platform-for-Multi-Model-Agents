# migrate-to-codex

这是一个把现有代理配置迁移到 Codex 约定的技能。

## 适用场景

- 用户要把 Claude/Cursor/其他 agent 配置迁移到 Codex
- 需要迁移 skills、agents、hooks 或 MCP 配置
- 用户希望保留已有设置并逐步完成迁移

## 工作方式

1. 扫描仓库里的指令文件和配置目录。
2. 识别哪些内容可以自动迁移，哪些需要手工确认。
3. 继续推进直到迁移完成，不要只做一半。
