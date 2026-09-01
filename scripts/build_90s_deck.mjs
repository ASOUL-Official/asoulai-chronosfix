import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const skillDir = process.env.PRESENTATIONS_SKILL_DIR || "C:/Users/liuzhanxian/.codex/plugins/cache/openai-primary-runtime/presentations/26.826.12353/skills/presentations";
const { importRuntimeModule } = await import(pathToFileURL(path.join(skillDir, "container_tools/runtime_helpers.mjs")).href);
// Template provenance: the input is the imported template-starter.pptx produced by the frame map.
const TEMPLATE_STARTER_BASENAME = "template-starter.pptx";
const input = path.resolve(process.argv[2]);
const output = path.resolve(process.argv[3]);
const qaDir = path.resolve(process.argv[4]);
const sourceLayoutDir = path.resolve(process.argv[5]);
const sourceSlideByOutput = [1, 4, 8, 16, 18, 22];

async function writeBlob(filePath, blob) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, Buffer.from(await blob.arrayBuffer()));
}

async function editSlide(presentation, slideNo, values) {
  const sourceSlideNo = sourceSlideByOutput[slideNo - 1];
  const sourceLayout = JSON.parse(await fs.readFile(path.join(sourceLayoutDir, `source-slide-${String(sourceSlideNo).padStart(2, "0")}.layout.json`), "utf8"));
  const slide = presentation.slides.getItem(slideNo - 1);
  for (const [aid, value] of Object.entries(values)) {
    const sourceElement = sourceLayout.elements.find((element) => element.aid === aid);
    if (!sourceElement) throw new Error(`Unable to map source shape ${aid} on slide ${sourceSlideNo}`);
    const target = slide.shapes.items.find((shape) => String(shape.id) === String(sourceElement.id));
    if (!target) throw new Error(`Unable to resolve inherited shape ${aid} (id ${sourceElement.id}) on output slide ${slideNo}`);
    target.text.set(value);
  }
}

const edits = {
  1: {
    "sh/547294r6": "GOAI 世界人工智能开源大赛 · Agent Infra · 方向三",
    "sh/k3yl0zql": "AsoulAI ChronosFix",
    "sh/7qp4be9c": "A-CFX：软件故障时间机器",
    "sh/65g3298r": "90 秒：从事故到可验证补丁",
    "sh/e94v2hon": "真实本地执行 · 现场按钮 · 明确边界",
  },
  2: {
    "sh/jm5gze1g": "P0 · 结果先行",
    "sh/1cj2d8b6": "我们交付的不是答案，而是敢合并的证据",
    "sh/0ba143al": "同一 run_id 绑定事故、因果、补丁、门禁与审计材料。",
    "sh/ql8jytsj": "真实执行",
    "sh/doj29oba": "本地 Controller 拉起真实子进程，失败后切换到不同 Worker 实例。",
    "sh/3ihk3et8": "可审计",
    "sh/ih8ju9sn": "SQLite Matrix 事件日志 + measured duration + DSSE 签名。",
    "sh/5cva1cfq": "可拒答",
    "sh/i94r6xgz": "Badcase 不乱归因：abstain / indeterminate / blocked。",
    "sh/w72947yt": "48.72%",
    "sh/x8vaxsfe": "Demo 基线失败率",
    "sh/v6tsv2xo": "6.25%",
    "sh/g36tgryd": "补丁最坏失败率",
    "sh/p0batw72": "8",
    "sh/oz29krqh": "强制故障变体",
    "sh/2xkrih8b": "14",
    "sh/1wbapc7q": "证据护照声明",
    "sh/fu9sn2p0": "65",
    "sh/et0reh8f": "自动化测试",
    "sh/tsrqlc7u": "一句话：每个发布决定都能回答“谁做的、凭什么、失败怎么办”。",
  },
  3: {
    "sh/pwjqho7u": "现场 · AgentTeams 多 Agent 协同",
    "sh/18byd4zy": "本地 Controller：真的启动 Worker，不读取静态 JSON",
    "sh/g72x4zyd": "Manager 根据证据自由组合 Agent/Skill；本地 Controller 记录 PID、duration_ms、SQLite Matrix，官方 AgentTeams 仍明确标 pending。",
    "sh/6h0fypgb": "Manager",
    "sh/tkby9kzm": "入口路由 | run 状态",
    "sh/id0fu50z": "Commander",
    "sh/o7ydoret": "任务拆解 | 重派",
    "sh/n6pwfmd8": "Timeline",
    "sh/0jydkreh": "事件融合 | 时间线",
    "sh/zipwbmdc": "Hypothesis",
    "sh/kfixwbe1": "假设契约 | 可证伪",
    "sh/svydgb65": "Universe",
    "sh/7u5w765k": "反事实 | 故障基因",
    "sh/kredcr6t": "Patch / Verify",
    "sh/jq5w365o": "补丁竞赛 | 隔离 CI",
    "sh/w3ed8r6x": "Audit / Curate",
    "sh/m9sb2x4v": "门禁审计 | Skill 沉淀",
    "sh/8bat47ml": "一次现场演示",
    "sh/9w3uds36": "Worker #01 超时 → #02 接管，两个 PID、两个 attempt",
    "sh/z61s7il4": "状态可追溯",
    "sh/07atgnmp": "revision + dedup_key 防止重复事件污染状态",
    "sh/q18bad4n": "真值边界",
    "sh/b2hs3il8": "local executed / official AgentTeams pending",
  },
  4: {
    "sh/ylwj2987": "证据链 · 补丁先过隔离 CI",
    "sh/8z2h8bq1": "每次运行不是截图，而是可验证的变更证明",
    "sh/9kby1g7m": "Trace、checks、RiskGate、run-manifest 与 DSSE 共同绑定同一 run_id。",
    "sh/zutgvm94": "Trace",
    "sh/kv2h4rqp": "真实 PID、起止时间、duration_ms、parent span；可导出 OTLP JSON。",
    "sh/ip4zel83": "隔离 CI",
    "sh/3qdg7qpo": "临时 checkout + 允许路径白名单；补丁前测试失败、应用后通过、反向补丁复原。",
    "sh/e1sf65o3": "RiskGate",
    "sh/1ojy10ne": "质量证据不完整、审批过期或工具被拒绝时，发布保持 blocked。",
    "sh/nqlg3a5k": "Run Manifest",
    "sh/2pcfa5oz": "文件 SHA-256、source commit、测试摘要与边界声明全部可复核。",
    "sh/oruhcf65": "Measured 与 derived 分开；没有真实外部调用就不伪造 success_rate。",
    "sh/atczepob": "PR 草案只读取已选 changes、rollback、checks 与 gate。",
    "sh/7qp0zepo": "证明载体：evidence/ + DSSE envelope + local-infra report",
  },
  5: {
    "sh/w7698ju9": "现场按钮 · 失败就停，证据才继续",
    "sh/wrelszu9": "三次点击把复杂边界变成可观察状态",
    "sh/hsn2l4bu": "Worker 失败重派｜新证据插入｜旧审批失效｜Badcase 拒答",
    "sh/je5knut0": "按钮 1",
    "sh/4felwzu5": "timeout/crash → 备份实例；记录两个 PID 与 attempt",
    "sh/6hw3y9sb": "按钮 2",
    "sh/rip4retw": "evidence-insert → 动态任务 + revision 增长 + 重新评估",
    "sh/upg3i18r": "按钮 3",
    "sh/1cr2tg72": "stale-approval → 拒绝旧 revision；必须重新审批",
    "sh/7mpknmp0": "Badcase",
    "sh/to72pw76": "不支持根因 / 来源冲突 → abstain 或 indeterminate",
    "sh/bi94zqp4": "发布结果",
    "sh/md4nipsr": "阻断，不生成 patch / PR",
    "sh/8zm5kzax": "code-regression → abstain",
    "sh/a14nm9s3": "blocked",
    "sh/w36poza9": "queue-backlog → abstain",
    "sh/q5kna5sz": "conflicting-sources → indeterminate",
    "sh/t0zqp8bm": "等待来源级证据",
    "sh/7yh8nytw": "公开事故",
    "sh/h4jqtsby": "Cloudflare 2019 WAF regex：事实与项目推断分栏",
    "sh/f218rits": "只读来源，不冒充生产事故日志",
  },
  6: {
    "sh/ozyhcf25": "交付 · 现在能验收，下一步能迁移",
    "sh/6987itcr": "AsoulAI ChronosFix：把每次修复变成可携带证明的变更",
    "sh/7a18rydc": "代码、Demo、评测、Trace、审计与边界声明可独立复核。",
    "sh/58zqpov6": "本地已执行",
    "sh/il87etcv": "Controller + SQLite Matrix + 隔离补丁 CI + DSSE",
    "sh/43u9snu5": "证据包",
    "sh/p43q1sva": "14 条声明；release identity 由同一 manifest 绑定",
    "sh/436507qx": "现场 Demo",
    "sh/3ixor29c": "repair-cockpit/ · 三个动作按钮 + Badcase 拒答",
    "sh/hgf6pcr6": "真实边界",
    "sh/gf65w7ql": "AgentTeams/Matrix、RocketMQ、PolarDB、Nacos、Higress、Trace 平台待接入",
    "sh/udonux8v": "复赛材料",
    "sh/1cj61w7q": "90 秒 PPTX / 矢量 PDF / ZIP / Git commit",
    "sh/krihkz2d": "人工 baseline",
    "sh/lsrit4jy": "协议已准备，结果留待真实参与者完成后再写入",
    "sh/jq90ru1s": "核心结论",
    "sh/wnihgf2h": "根因可证明｜补丁可验证｜发布可审计｜边界不夸大",
    "sh/xoripkj2": "请现场点击 Demo：失败会重派，证据会改写，旧审批会失效。",
  },
};

const notes = {
  1: "0:00–0:12 开门见山：ChronosFix 不承诺替研发做判断，而是让每个修复决定携带证据。\n[Sources]\n- Internal: docs/semifinal-reviewer-response.md\n- Internal: evidence/release-manifest.json",
  2: "0:12–0:27 先讲结果：48.72% 到 6.25% 的既有评测口径、8 个强制故障变体、14 条证据声明；Manager 会按证据自由组合 Agent/Skill 并编译为任务 DAG，当前 65 项测试全绿。\n[Sources]\n- Internal: docs/evaluation-corpus-results.md\n- Internal: tests/ (unittest collection: 65)",
  3: "0:27–0:43 现场重点：Controller 用 Popen 启动真实 Worker 子进程。点击失败后，#01 的 PID 结束，#02 接管；事件落 SQLite Matrix。官方 AgentTeams/Matrix 仍写 pending。\n[Sources]\n- Internal: src/chronosfix/runtime/controller.py\n- Internal: src/chronosfix/runtime/store.py\n- Internal: deploy/infra-boundaries.json",
  4: "0:43–0:58 证据重点：补丁先在临时 checkout 中反复验证，再进入 RiskGate；最后用 DSSE + Ed25519 把输入、结果、边界绑定成可验签声明。\n[Sources]\n- Internal: scripts/run_patch_sandbox.py\n- Internal: src/chronosfix/attestation.py\n- Internal: evidence/release-manifest.json",
  5: "0:58–1:13 三个现场动作：重派、动态插证据、旧审批失效。再点 Badcase：系统必须 abstain/indeterminate，而不是生成一个看似完整的 PR。Cloudflare 事故只作为公开只读事实来源。\n[Sources]\n- Internal: repair-cockpit/index.html\n- Internal: src/chronosfix/runtime/controller.py\n- External: https://blog.cloudflare.com/cloudflare-outage/",
  6: "1:13–1:30 收束：本地执行闭环已可复核，官方产品与真实云服务仍明确列为迁移边界；人工 baseline 等真实观察完成后再更新。\n[Sources]\n- Internal: docs/requirements-matrix.md\n- Internal: baseline/human-study-protocol.json\n- Internal: deploy/infra-boundaries.json",
};

const { FileBlob, PresentationFile } = await importRuntimeModule("@oai/artifact-tool");
const presentation = await PresentationFile.importPptx(await FileBlob.load(input));
for (const [slideNo, values] of Object.entries(edits)) {
  await editSlide(presentation, Number(slideNo), values);
  const slide = presentation.slides.getItem(Number(slideNo) - 1);
  slide.speakerNotes.textFrame.setText(notes[slideNo]);
  slide.speakerNotes.setVisible(true);
}

await fs.mkdir(qaDir, { recursive: true });
for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  await writeBlob(path.join(qaDir, `${stem}.png`), await presentation.export({ slide, format: "png", scale: 1 }));
  await fs.writeFile(path.join(qaDir, `${stem}.layout.json`), await (await slide.export({ format: "layout" })).text(), "utf8");
}
await writeBlob(path.join(qaDir, "deck-montage.webp"), await presentation.export({ format: "webp", montage: true, scale: 1 }));
const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(output);
console.log(JSON.stringify({ output, qaDir, slideCount: presentation.slides.items.length }, null, 2));
