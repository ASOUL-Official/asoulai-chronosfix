# AgentTeams Runtime 接入状态与验证路径

## 当前结论

ChronosFix 已完成 AgentTeams **正式资源层**接入，但尚未完成 **Controller 运行层**接入。

| 层级 | 当前状态 | 证据 |
|---|---|---|
| 资源规范 | 使用 `agentteams.io/v1beta1` | `agentteams/runtime/chronosfix-resources.yaml` |
| 角色拓扑 | 1 Manager、8 Worker、1 Team、1 Human；Team 恰好一个 `team_leader` | `evidence/agentteams-manifest-validation.json` |
| Worker Skill | 9 个独立可发现 Skill + `chronosfix-local-engine` 离线聚合 fallback | `agentteams/skills/*/SKILL.md`、`coordination.json` skill registry |
| 本地协同证据 | 生成 AgentTeams-compatible transcript | `agentteams/run_chronosfix_team.py`、`evidence/agentteams-run.json` |
| Controller / Matrix | **未安装、未执行** | 无真实 Controller 日志或 Matrix 记录 |
| Manager/Worker 模型推理 | **未执行** | 尚未配置模型 API Key |

因此，当前提交可证明“角色、任务、上下文、权限和状态如何映射到 AgentTeams 正式资源”，不能声称已经在 AgentTeams Controller 中完成真实多 Agent 推理。

## 固定版本与离线校验

- 官方 AgentTeams 源码版本：`v1.2.3`。
- 固定 commit：`223ddc2b8073e4c8b93bcbb15e1d717f196c04d9`。
- 资源 apiVersion：`agentteams.io/v1beta1`。
- Team 成员字段：`workerMembers`。
- Team Leader：`chronosfix-incident-commander`，恰好一个。
- 依赖锁：`agentteams/runtime/dependency-lock.json`。

离线验证命令：

```powershell
python agentteams/runtime/validate_resources.py agentteams/runtime/chronosfix-resources.yaml
```

验证器需要 PyYAML；核心 ChronosFix 流水线仍只使用 Python 标准库。当前校验结果已经固化到 `evidence/agentteams-manifest-validation.json`。

## 本地兼容入口

```powershell
python agentteams/run_chronosfix_team.py --approve --approver "AsoulAI Release Owner" --approval-reason "Semifinal evidence review" --output output/agentteams-latest
```

该命令运行 ChronosFix 本地确定性内核，并输出：

- 角色与任务状态；
- Incident State 上下文摘要；
- `run_id`、`trace_id`；
- `quality_gate` 与 `release_decision`；
- Trace、Metrics、报告和 run manifest 路径。

输出中的 `execution_mode` 为 `local-deterministic-engine`，`agentteams_runtime_executed` 为 false。

## 真实 Controller 验证还需要什么

真实运行会创建或管理容器、卷、管理员配置、Matrix 协作空间，并需要模型凭据，因此不能仅凭代码仓库自动视为已授权完成。完成真实接入至少需要：

1. 获得安装 AgentTeams Controller 的外部状态变更授权。
2. 配置可用模型 API Key 或兼容模型网关。
3. 启动 Controller 并应用 `chronosfix-resources.yaml`。
4. 在 Matrix/Controller 中发起一个合成事故任务。
5. 保存 Team Active 状态、Worker 状态、协作记录、Controller 日志和最终产物。
6. 对照本地 run manifest，验证相同门禁边界没有被 Runtime 改写。

仓库提供两个真实运行入口：

```bash
# WSL2 / Linux；默认使用官方 v1.2.3、Qwen、隔离端口和本地数据目录
export AGENTTEAMS_LLM_API_KEY='在本机 shell 设置，不要提交到仓库'
bash agentteams/runtime/install_official_local.sh
bash agentteams/runtime/apply_resources.sh
bash agentteams/runtime/verify_official_runtime.sh
```

`install_official_local.sh` 从固定 commit 的官方安装器启动 embedded Controller/Matrix，默认使用 `28080/28001/28088/28888/23000` 端口，避免覆盖其他部署。它在缺少模型 key、Docker 不可用或下载失败时退出，不会伪造成功。`verify_official_runtime.sh` 只保存 Controller 状态和 `agt get` 资源 JSON，不保存模型 key、管理员密码或云凭据。

真实运行仍需要：模型 API key、可拉取官方镜像的网络，以及（若启用 SLS Skill）本机 Aliyun CLI Profile 和精确 Project/Logstore。执行成功后，才可以把 `evidence/agentteams-official-runtime/` 作为 Controller 证据加入发布清单；在此之前，发布清单的 truth boundary 仍保持 `agentteams_controller_executed: false`。

## 答辩口径

可说：

> 我们已把 ChronosFix 映射为 AgentTeams v1beta1 的 Manager、8 个 Worker、Team 和 Human 正式资源，并完成离线结构验证；当前可执行证据来自本地确定性 Worker engine。Controller 与 Matrix 尚未安装，因此我们把 transcript 明确标记为 compatible mapping evidence，而非真实 Runtime 证据。

不可说：

- “已经在 AgentTeams 上完成端到端运行”；
- “已经产生真实 Matrix 多 Agent 对话”；
- “AgentTeams 已经接入生产环境”。
