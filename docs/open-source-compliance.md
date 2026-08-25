# 开放、开源与合规计划

## 开放范围

- ChronosFix 核心编排代码。
- 9 个核心 Skill 的输入输出 Schema 和实现。
- Agent Identity 清单与 AgentTeams 编排草案。
- checkout-timeout 样例故障数据。
- 自动化测试、反事实实验、故障基因生成和补丁竞赛评测脚本。
- MCP 适配器契约示例。

## 暂不开放范围

- 企业真实日志、Trace、配置、代码仓库和工单。
- 任何密钥、Token、个人信息、客户数据。
- 闭源模型调用密钥和私有评测集。

## 许可证

计划采用 Apache-2.0。第三方依赖目前仅使用 Python 标准库；复赛接入 AgentTeams、MCP、CI 或云产品时，将补充依赖版本和许可证清单。

## 数据与隐私

当前复赛包使用合成故障数据，不包含真实个人信息或企业生产数据。后续接入真实数据时，默认进行字段脱敏、最小权限授权和审计记录。

## 复现方式

评审可在本地运行：

```powershell
python demo.py --approve --output evidence
```

然后查看：

- `evidence/proof-report.md`
- `evidence/proof-bundle.json`
- `evidence/trace.jsonl`
