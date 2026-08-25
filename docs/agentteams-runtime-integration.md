# 真实 AgentTeams Runtime 接入判断

结论：**可以接真实 AgentTeams runtime，但不建议在复赛提交前强行全量接入。**

根据公开资料，HiClaw 已更名为 AgentTeams，并且不只是概念框架，而是有真实控制面与 runtime：支持 Manager、Worker、Human、Team、Matrix 协作房间、controller、Helm / Kubernetes、对象存储和多 Worker runtime。它适合决赛阶段做“真实框架接入证明”。

## 为什么现在不强接

1. **环境成本高**
   AgentTeams 真实 runtime 需要容器 / Kubernetes / Matrix / 存储 / 网关等环境，比当前 Python 标准库 Demo 重很多。

2. **复赛风险高**
   复赛重点是 Demo 可运行性和工程验证。当前本地确定性实现稳定、可复现、无外部依赖；如果临时接 runtime，最容易在安装、网络、镜像、端口和凭证上翻车。

3. **评审重点不是“堆组件”**
   官方要求强调设计理念、接口契约、必要性、权限边界、端到端证据和迁移成本。当前材料已经把 AgentTeams 的 Manager / Worker / Shared State / Trace 映射讲清楚。

## 决赛接入路线

| 阶段 | 目标 | 交付物 |
|---|---|---|
| P0：当前复赛 | 等价 AgentTeams 风格入口 | `agentteams/chronosfix-team.yaml`、`agentteams-run.json` |
| P1：轻量真实接入 | 把 A-CFX AgentSpec 转为 AgentTeams Team / Worker 声明 | `agentteams/runtime/` 下的 Team/Worker YAML |
| P2：本地 runtime 演示 | 真实 Manager 创建 Worker，执行一个场景，输出 Matrix/Trace 截图 | runtime 运行记录、截图、导出日志 |
| P3：生产化 | 接 Nacos/Higress/RocketMQ/PolarDB/AgentLoop | Helm values、网关策略、事件模型、数据表 |

## 需要你提供/确认的东西

如果要进入 P1/P2，需要确认：

- 机器是否能稳定运行 Docker Desktop 或 WSL2 Docker。
- 是否允许下载 AgentTeams 镜像和安装脚本。
- 是否有可用模型 API Key / 兼容模型网关。
- 是否愿意为决赛准备一个独立演示环境，避免影响现在稳定提交包。

## 答辩话术

当前复赛版没有假装已经部署真实 AgentTeams runtime，而是做了可验证等价实现，并给出迁移边界：Manager 对应 Incident Commander，Workers 对应 7 个职能 Agent，Incident State 对应共享上下文，trace/run-log/agentteams-run 对应状态追踪。决赛阶段可把这些 YAML 与状态 Schema 映射到真实 AgentTeams Team / Worker / Human / Matrix Room。
