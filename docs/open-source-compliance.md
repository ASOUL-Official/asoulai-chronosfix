# 开放、开源与合规计划

## 开放范围

- ChronosFix 核心编排代码。
- 9 个核心业务 Skill、官方 SLS 只读 Adapter 的输入输出契约与实现。
- Agent Identity、1 Manager / 8 Worker / 1 Team / 1 Human 的 AgentTeams v1beta1 资源声明和离线校验器。
- 12 个 Golden / Badcase / 证据不足合成样例。
- 自动化测试、反事实实验、故障基因生成和补丁竞赛评测脚本。
- MCP 适配器契约示例。

## 暂不开放范围

- 企业真实日志、Trace、配置、代码仓库和工单。
- 任何密钥、Token、个人信息、客户数据。
- 闭源模型调用密钥和私有评测集。

## 许可证

仓库已采用 Apache-2.0。核心流水线只依赖 Python 标准库；完整公开验收的 Schema 校验和 AgentTeams 清单校验分别使用可选依赖 `jsonschema` 与 `PyYAML`。`SBOM.json` 与 `THIRD_PARTY_NOTICES.md` 记录当前依赖、上游资源及许可证边界；后续新增 Runtime、MCP 或云 SDK 时必须同步更新。

## 数据与隐私

当前复赛包使用合成故障数据，不包含真实个人信息或企业生产数据。后续接入真实数据时，默认进行字段脱敏、最小权限授权和审计记录。

## 复现方式

评审可在本地运行：

```powershell
python demo.py --approve --approver "AsoulAI Release Owner" --approval-reason "Semifinal evidence review" --output evidence
```

然后查看：

- `evidence/proof-report.md`
- `evidence/proof-bundle.json`
- `evidence/trace.jsonl`
