# ChronosFix 创新层设计

ChronosFix 的差异化不在于“有很多 Agent”，而在于让多 Agent 团队围绕软件研发的真实风险形成一套带证明的软件变更链：事故证据、因果证明、对抗验证、PR / 发布审计、经验复用。

```text
事故证据 -> 反事实证明根因 -> 缺陷基因验证补丁 -> RiskGate 审批 -> GitHub PR / 证据护照 -> Skill / 故障资产沉淀
```

## 1. 故障时间机器：从相关性到因果性

传统 AIOps 常见问题是“日志里看起来像什么，就猜什么”。ChronosFix 改为构建反事实平行宇宙：

1. 找到事故前后的代码、依赖、配置、流量、告警证据。
2. 为每个可疑变更生成可证伪假设。
3. 在隔离版本中撤销某个变更并重放故障。
4. 如果撤销后故障显著消失，则按确定性效果分分类为主因；否则将其证伪或标记为放大因子。该分数不是统计学置信区间。

这让根因分析从“经验判断”变成“可回放实验”。

## 2. 缺陷基因实验室：从修一个点到修一类问题

一个补丁通过原始事故样例，并不代表它真的可靠。ChronosFix 会从已证明主因中繁殖同源故障变体：

- nominal：原始复现。
- high-traffic：更高流量压力。
- slow-downstream：下游变慢。
- combined-stress：流量和下游同时加压。
- pool-borderline：容量临界点。
- recovery-spike：恢复窗口流量尖峰。
- downstream-jitter：下游抖动。
- silent-config-drift：隐性配置漂移。

补丁必须在这一组变体中竞赛，按平均失败率、最差失败率、风险、成本综合排名。这样能避免“补丁只对原题有效”的脆弱方案。

## 3. PR 证据护照：让 AI 参与的修复可发布、可追责

ChronosFix 给选中补丁生成 Evidence Passport，包含：

- 需求声明：修复目标是什么，不能违反哪些约束。
- 因果声明：为什么它修的是主因，不是巧合。
- 验证声明：它在哪些变体上通过，最差表现如何。
- 风险声明：风险和成本如何评估，是否需要人工审批。
- 回滚声明：如果发布失败，如何恢复。
- 缺口声明：还有哪些场景没有被覆盖。

这让补丁从“AI 建议”升级为“可进入 PR/变更单的证明材料”。在复赛工程中，A-CFX 已生成 GitHub Issue / PR 草案、checks、diff 和审计事件，证明这条链能落到真实研发协作流。

## 4. Skill 自进化工坊：事故变资产

每次事故结束后，SkillForge 会从处理过程里提炼可复用 Skill 候选：

- ConnectionPoolCapacityGuard：连接池容量守卫。
- CounterfactualConfigReplay：配置变更反事实回放。
- ProofCarryingPatch：带证明补丁生成器。

这些候选不会自动上线，而是进入人工评审、回放评测和版本管理。通过后，它们成为团队下一次事故处理的标准能力。

## 5. 为什么适合“软件研发全流程协同”

ChronosFix 覆盖软件研发中的多个关键节点：

- Issue/告警进入：证据融合。
- 根因定位：时间线与假设竞争。
- 修复生成：补丁候选与回滚声明。
- CI/验证：故障变体竞赛。
- PR/发布审批：RiskGate、GitHub PR 与 Evidence Passport。
- 复盘沉淀：ProofReport 与 SkillForge。

它不是单点工具，而是一条研发协同流水线；不是替代人类发布决策，而是让人类拿到更完整、更可信的证据。

## 6. Repair Cockpit：让评委看见闭环

为了避免创新点只停留在文档里，ChronosFix 增加了一个可交互的 Repair Cockpit 修复驾驶舱：

- 顶部固定显示证据等级、run/trace 身份和 human/quality/release 三态门禁。
- 六步评委动线依次展示事故事实、因果证明、故障族验证、三态门禁、证据护照和评测沉淀。
- 评审可切换 12 个 Golden/Badcase/证据不足场景，并观察无人审批阻断分支。
- 所有业务数字均读取 `data/demo-data.json`，前端不维护一套独立结论。

驾驶舱位于 `repair-cockpit/index.html`，是纯静态站点；因浏览器会限制 `file://` 读取 JSON，应通过 GitHub Pages 或本地 HTTP 服务打开。
