# AgentTeams / 云 Skill 真实接入状态

更新时间：2026-08-25

## 已验证

- WSL2 Ubuntu 22.04 可用，Docker Engine 29.1.3 已安装并可启动。
- 官方 AgentTeams 源码固定为 `v1.2.3` / commit `223ddc2b8073e4c8b93bcbb15e1d717f196c04d9`。
- 正式资源清单使用 `agentteams.io/v1beta1`，包含 Manager、8 个 Worker、1 个 Team 和 1 个 Human。
- Team 使用 `workerMembers`，且恰好一个 `team_leader`。
- 官方云 Skill 固定为 `alibabacloud-sls-query` / upstream commit `4dc1013ec2564f85fd07e5b5945b2d34ceca7eff`。
- 本地 SLS Adapter 已实现 GetIndex + GetLogsV2 只读计划、24 小时时间窗、RAM 权限边界、User-Agent 和凭据隔离测试。

## 尚未声称完成

- AgentTeams 官方安装器尚未执行。安装器会创建并管理专用容器、卷与管理员配置，需获得用户对这一外部状态变更的明确授权。
- 未配置真实模型 API Key，因此尚无 Manager/Worker 的真实推理协作记录。
- 未配置阿里云 SLS Project、Logstore 和只读 RAM Profile，因此当前云 Skill 证据为 `dry-run`，不是云端查询成功证据。

## 证据等级

| 项目 | 当前等级 |
|---|---|
| 本地 ChronosFix 工程流水线 | measured / tested |
| AgentTeams v1beta1 资源清单 | offline-validated |
| AgentTeams Controller / Matrix 执行 | pending explicit install authorization |
| alibabacloud-sls-query 契约与权限 | interface-tested |
| SLS 真实查询 | pending credentials and target Logstore |
