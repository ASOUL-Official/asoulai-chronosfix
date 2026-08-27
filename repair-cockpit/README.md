# AsoulAI ChronosFix Repair Cockpit

这是 ChronosFix 的复赛评委模式 Demo。页面不在 `app.js` 中维护业务结果，而是读取由工程证据生成的 `data/demo-data.json`。

## 生成最新 Demo 数据

在项目根目录运行：

```powershell
python repair-cockpit/scripts/build_demo_data.py
```

生成器会：

- 从 9 个 Golden 场景执行完整离线流水线；
- 分别执行“具名离线审批”和“无人审批阻断”两个真实 RiskGate 分支；
- 从 3 个评测专用夹具读取 Badcase / 证据不足结果；
- 汇总 `run_id`、`trace_id`、三态门禁、故障族结果、证据护照与评测口径；
- 只把前端需要的字段写入 `repair-cockpit/data/demo-data.json`。

## 本地打开

浏览器通常禁止 `file://` 页面读取相邻 JSON，因此请在项目根目录启动静态服务：

```powershell
python -m http.server 8000 --directory repair-cockpit
```

然后访问：

```text
http://localhost:8000/
```

GitHub Pages 会直接按静态资源方式加载，无需后端。

## 90 秒评委动线

1. 选择 `checkout-timeout`，说明页面读取的是离线运行证据而非前端写死数字。
2. 点击“动态协同”，展示新证据插入任务、Worker 超时重派、去重和 revision 暂停/恢复。
3. 点击“因果证明”，展示主因、放大因素和证伪假设的反事实差异。
4. 点击“故障族验证”，展示补丁竞赛、真实变更字段和强制变体结果。
5. 在“三态门禁”切换“含具名审批 / 无人审批”，观察 `human_approval`、`quality_gate`、`release_decision` 独立变化。
6. 点击“证据护照”，展示 SHA-256、回滚契约以及真实仓库、Issue、PR、评测链接。
7. 点击“评测与沉淀”，展示 9 个 Golden 和 3 个边界样例；再选择 Badcase，说明失败不会进入补丁或发布流程。

### 现场异常注入

右侧“运行时异常注入”控制台是浏览器内的本地控制面模拟，可连续点击并观察 revision、任务图、事件流和三态门禁变化：

- 新证据、重复 evidence：验证动态任务注册与幂等去重；
- Worker 超时、Worker 崩溃：验证 capability 重派与失败 attempt；
- 人工暂停、旧审批失效、人工恢复：验证 checkpoint 和最新 revision 绑定；
- 工具权限拒绝、重试耗尽：验证最小权限与 fail-closed。

这些按钮不会调用真实 AgentTeams、云 API、GitHub 或生产系统；它们用于现场解释控制面契约，真实外部执行状态仍以 `evidence/` 与文档中的边界声明为准。

## 状态边界

- `offline-validated`：核心流水线在确定性合成场景中离线执行并留下证据。
- `dry-run`：GitHub 修复流当前生成本地草案；公开 Issue #1 / PR #2 仅作为真实协作证据。
- `pending`：不宣称已经连接真实 AgentTeams Controller Runtime、阿里云 Skills 或生产云资源。
- 页面中的 `commit=evidence-source` 表示 Demo 数据绑定到证据生成时的源码快照；真实补丁提交仍保持 `local-draft`，避免使用虚构 SHA。

## 静态检查

```powershell
node --check repair-cockpit/app.js
python -m json.tool repair-cockpit/data/demo-data.json > $null
python scripts/validate_release_manifest.py
```
