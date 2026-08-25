# 原创性与命名边界说明

本项目公开展示统一使用 **AsoulAI ChronosFix（A-CFX）**，而不是单独使用 “Chronos” 或泛化的 “Debug Agent” 命名，目的是降低与 GitHub 上已有 Chronos / debugging-first 类项目的混淆风险。

## 命名边界

- 对外名称：AsoulAI ChronosFix。
- 缩写名称：A-CFX。
- Repo 名称：asoulai-chronosfix。
- Demo 标题：AsoulAI ChronosFix Repair Cockpit。

## 与常见开源方向的区别

| 相邻方向 | 常见定位 | A-CFX 的差异 |
| --- | --- | --- |
| Chronos / debugging-first 类项目 | 模型、推理或调试助手 | A-CFX 是带证明的软件变更基础设施 |
| 自动补丁工具 | 生成修复建议或代码 Patch | A-CFX 要求补丁进入 PR 前携带因果、验证、风险、回滚和缺口证据 |
| AIOps 排障系统 | 面向运维告警和服务自愈 | A-CFX 面向软件研发全流程协同 |

## 独有表达

A-CFX 的独有识别不是“自动修 Bug”，而是一条证明链：

```text
事故证据 -> 反事实证明根因 -> 缺陷基因验证补丁 -> RiskGate 审批 -> GitHub PR / 证据护照 -> Skill / 故障资产沉淀
```

这条链包含四个公开可识别的原创点：

1. **反事实根因证明**：在平行版本中撤销可疑变更并重放事故，把相关性变成因果证据。
2. **故障基因实验室**：从已证明事故繁殖同源变体，逼补丁修一类问题。
3. **PR 证据护照**：补丁必须携带需求、因果、验证、风险、回滚和缺口声明。
4. **Skill 飞轮**：把事故处理经验沉淀为可评测、可复用、可分发的研发质量资产。

## 提交材料中的同步位置

- PPT 全程统一使用 AsoulAI ChronosFix / A-CFX，并把主叙事锁定为带证明的质量资产闭环。
- Repair Cockpit 标题、页脚和证据链接统一使用 A-CFX 标识。
- README、作品简介和本说明保持同一名称与差异化边界。
