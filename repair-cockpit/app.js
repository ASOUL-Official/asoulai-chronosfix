const data = {
  metrics: {
    baselineFailureRate: 0.4872,
    baselineP99: 606.96,
    faultVariants: 8,
    evidenceClaims: 12,
    traceSpans: 16,
    qualityAssets: 3,
  },
  timeline: [
    ["09:40", "代码提交", "为订单请求增加关联日志", "git:a91c7e"],
    ["09:55", "依赖升级", "支付客户端升级，重试路径平均延迟增加", "payment-client@2.0"],
    ["10:10", "配置变更", "数据库连接池从 24 调整为 8", "db.pool.maxSize"],
    ["10:15", "流量上涨", "午间活动流量升至 120 RPS", "checkout.rps"],
    ["10:16", "告警触发", "订单创建失败率和 P99 延迟同时升高", "checkout-5xx"],
  ],
  experiments: [
    {
      id: "H-CODE",
      title: "关联日志代码变更导致性能回退",
      baseline: 0.4872,
      counterfactual: 0.4872,
      confidence: 0,
      classification: "证伪",
      explanation: "撤销代码提交后失败率没有改善，因此它不是主因。",
    },
    {
      id: "H-DEPENDENCY",
      title: "支付客户端升级放大请求占用时间",
      baseline: 0.4872,
      counterfactual: 0.3333,
      confidence: 0.3159,
      classification: "放大因素",
      explanation: "回退依赖后失败率下降但没有归零，说明它会放大故障但不是唯一主因。",
    },
    {
      id: "H-POOL",
      title: "连接池缩容造成服务容量不足",
      baseline: 0.4872,
      counterfactual: 0,
      confidence: 1,
      classification: "主因",
      explanation: "恢复连接池后失败率归零，因果置信度达到 100%。",
    },
  ],
  genome: [
    ["nominal", "known", "从事故证据中复现的种子场景"],
    ["high-traffic", "known", "高流量压力下验证容量是否仍足够"],
    ["slow-downstream", "known", "下游服务变慢时验证连接占用影响"],
    ["combined-stress", "known", "流量与下游压力同时出现"],
    ["pool-borderline", "medium", "中等流量下容量接近饱和边界"],
    ["recovery-spike", "high", "恢复窗口出现流量尖峰"],
    ["downstream-jitter", "medium", "中等流量叠加间歇性下游延迟抖动"],
    ["silent-config-drift", "high", "午间峰值前容量配置发生隐性漂移"],
  ],
  patches: [
    {
      id: "P-RESTORE-POOL",
      title: "恢复连接池 24 并增加容量验证门禁",
      score: 0.9195,
      meanFailure: 0.0078,
      worstFailure: 0.0625,
      risk: 0.3,
      cost: 0.15,
      rollback: "恢复 db.pool.maxSize=8 配置快照",
      verdict: "最终选中：分数最高，最差场景仍满足健康阈值。",
    },
    {
      id: "P-ADAPTIVE-GUARD",
      title: "启用自适应连接池下限保护",
      score: 0.845,
      meanFailure: 0,
      worstFailure: 0,
      risk: 0.55,
      cost: 0.45,
      rollback: "关闭 adaptive_min_pool 并恢复配置快照",
      verdict: "技术效果最好，但风险和成本更高，适合复赛增强。",
    },
    {
      id: "P-PIN-DEPENDENCY",
      title: "将支付客户端回退至 1.8",
      score: 0.613,
      meanFailure: 0.2781,
      worstFailure: 0.5,
      risk: 0.3,
      cost: 0.35,
      rollback: "恢复 payment-client 2.0 锁文件",
      verdict: "只能缓解放大因素，不能修复主因。",
    },
    {
      id: "P-ROLLBACK-CODE",
      title: "回滚关联日志提交",
      score: 0.5359,
      meanFailure: 0.4359,
      worstFailure: 0.5,
      risk: 0.15,
      cost: 0.2,
      rollback: "重新部署 a91c7e",
      verdict: "代码变更已被证伪，回滚不能解决故障。",
    },
  ],
  passport: {
    需求声明: [
      "事故 INC-2026-0816-001 要求降低订单创建失败率与 P99 延迟。",
      "修复不得绕过审批，不得丢失回滚点，不得只修单一样例。",
      "修复必须覆盖由同一根因繁殖出的故障基因变体。",
    ],
    因果声明: [
      "连接池缩容造成服务容量不足：反事实撤销后失败率 48.7% → 0.0%，因果置信度 100.0%。",
      "支付客户端升级放大请求占用时间：单独撤销后失败率 33.3%，判定为放大因素。",
    ],
    验证声明: [
      "补丁竞赛总分 0.919。",
      "平均失败率 0.8%，最差失败率 6.2%。",
      "已覆盖健康变体 8/8。",
    ],
    风险声明: [
      "风险分 0.30，成本分 0.15。",
      "审批状态 approved。",
      "RiskGate 会阻断中高风险补丁的无人值守发布。",
    ],
    回滚声明: ["恢复 db.pool.maxSize=8 配置快照。"],
    缺口声明: ["当前合成 Demo 已覆盖核心故障族；复赛需接入真实 CI、日志和历史事故回放集。"],
  },
  skills: [
    {
      name: "ConnectionPoolCapacityGuard",
      desc: "连接池容量守卫：当配置变更与流量上涨同时出现时，生成容量建议和测试门禁。",
      targets: ["电商订单", "支付链路", "网关服务", "连接池治理"],
    },
    {
      name: "CounterfactualConfigReplay",
      desc: "配置变更反事实回放：在隔离环境验证配置变化是否为主因。",
      targets: ["配置中心", "依赖升级", "发布回滚", "性能回退"],
    },
    {
      name: "ProofCarryingPatch",
      desc: "带证明补丁生成器：为 PR、变更单或发布审批生成证据护照。",
      targets: ["代码修复", "配置变更", "依赖升级", "事故复盘"],
    },
  ],
  engineering: [
    {
      label: "AgentTeams 代码包",
      title: "可执行 Manager / Worker 入口",
      proof: "agentteams/run_chronosfix_team.py",
      desc: "运行后生成 agentteams-run.json，验证角色编排、任务拆解、上下文传递、协同执行和状态追踪。",
    },
    {
      label: "样例输入输出",
      title: "合成事故 + 证据化输出",
      proof: "scenario.json → proof-bundle.json",
      desc: "输入包含 Issue、Git、依赖、配置、流量和告警；输出包含根因、补丁、证据护照和 Skill 候选。",
    },
    {
      label: "日志 / Trace / Metrics",
      title: "复赛验收三件套",
      proof: "trace.jsonl / run-log.jsonl / engineering-metrics.json",
      desc: "每个 Agent 与 Skill 调用都有 trace_id、span_id、status、payload 和权限范围记录。",
    },
    {
      label: "异常处理",
      title: "未审批即阻断",
      proof: "RiskGate: blocked-awaiting-human",
      desc: "不传 --approve 时，中风险补丁不会发布；Evidence Passport 会保留缺口声明和回滚契约。",
    },
    {
      label: "GitHub Issue / PR",
      title: "真实研发协作模拟链路",
      proof: "github-issue.md / github-pr.md / github-pr-diff.patch",
      desc: "事故证据进入 Issue，选中补丁生成 PR 草案，并附带 checks、RiskGate 状态、回滚契约和审计事件。",
    },
  ],
  infra: [
    ["AgentTeams", "多 Agent 编排基点", "Manager/Worker、共享状态、人类可见协作和状态追踪。"],
    ["云 Skills", "云资源操作 Skill 层", "接入官方 Skills 门户、HITL、安全检测、Skill 发现与安装。"],
    ["Nacos", "AI 资源治理控制面", "管理 AgentSpec、SkillSpec、Prompt、配置策略和 MCP Endpoint。"],
    ["Higress", "AI 网关与 MCP 入口", "统一鉴权、路由、限流、Fallback、Token 观测和工具调用治理。"],
    ["PolarDB", "长记忆与 RAG 数据层", "存储历史事故、Runbook、Trace、审计日志和向量索引。"],
    ["UnifiedModel", "统一实体关系模型", "把 Incident、Evidence、Trace、Patch、Skill 建成可查询对象图。"],
    ["RocketMQ", "异步事件流转", "驱动 hypothesis.ready、experiment.done、riskgate.waiting 等可靠事件。"],
    ["AgentLoop", "观测评估与审计", "承接 Trace、Log、Metrics、实验评估和行为审计回放。"],
  ],
};

const percent = (value) => `${(value * 100).toFixed(value === 0 ? 0 : 1)}%`;

function renderTimeline() {
  const container = document.querySelector("#timeline-list");
  container.innerHTML = data.timeline
    .map(
      ([time, kind, summary, source]) => `
        <article class="timeline-item">
          <div class="timeline-dot" aria-hidden="true"></div>
          <div>
            <span>${time} · ${source}</span>
            <strong>${kind}</strong>
            <p>${summary}</p>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderExperiments(activeId = "H-POOL") {
  const tabs = document.querySelector("#experiment-tabs");
  tabs.innerHTML = data.experiments
    .map(
      (item) => `
        <button class="tab ${item.id === activeId ? "active" : ""}" data-id="${item.id}" type="button">
          ${item.id.replace("H-", "")}
        </button>
      `,
    )
    .join("");

  const active = data.experiments.find((item) => item.id === activeId) ?? data.experiments[0];
  document.querySelector("#experiment-detail").innerHTML = `
    <article class="cause-card">
      <h3>${active.title}</h3>
      <p>${active.explanation}</p>
      <div class="rate-pair">
        <div>
          <strong>${percent(active.baseline)}</strong>
          <span>基线失败率</span>
        </div>
        <div>
          <strong>${percent(active.counterfactual)}</strong>
          <span>反事实失败率</span>
        </div>
      </div>
    </article>
    <div class="classification">
      <div>
        <strong>${active.classification}</strong>
        <p>因果置信度 ${percent(active.confidence)}</p>
      </div>
    </div>
  `;

  tabs.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => renderExperiments(button.dataset.id));
  });
}

function renderGenome(filter = "all") {
  const grid = document.querySelector("#genome-grid");
  grid.innerHTML = data.genome
    .map(([name, risk, trigger]) => {
      const hidden = filter !== "all" && filter !== risk ? "hidden" : "";
      return `
        <article class="gene ${hidden}">
          <span class="risk-${risk}">${risk}</span>
          <strong>${name}</strong>
          <p>${trigger}</p>
        </article>
      `;
    })
    .join("");

  document.querySelectorAll(".filter").forEach((button) => {
    button.classList.toggle("active", button.dataset.risk === filter);
    button.addEventListener("click", () => renderGenome(button.dataset.risk));
  });
}

function renderPatches(activeId = "P-RESTORE-POOL") {
  const ranking = document.querySelector("#patch-ranking");
  ranking.innerHTML = data.patches
    .map(
      (patch) => `
        <button class="patch-button ${patch.id === activeId ? "active" : ""}" data-id="${patch.id}" type="button">
          <div class="patch-topline">
            <strong>${patch.title}</strong>
            <span>${patch.score.toFixed(4)}</span>
          </div>
          <div class="bar"><span style="width:${Math.round(patch.score * 100)}%"></span></div>
        </button>
      `,
    )
    .join("");

  const patch = data.patches.find((item) => item.id === activeId) ?? data.patches[0];
  document.querySelector("#patch-detail").innerHTML = `
    <h3>${patch.title}</h3>
    <p>${patch.verdict}</p>
    <div class="result-lines">
      <div class="result-line"><span>平均失败率</span><strong>${percent(patch.meanFailure)}</strong></div>
      <div class="result-line"><span>最差失败率</span><strong>${percent(patch.worstFailure)}</strong></div>
      <div class="result-line"><span>风险 / 成本</span><strong>${patch.risk.toFixed(2)} / ${patch.cost.toFixed(2)}</strong></div>
      <div class="result-line"><span>回滚策略</span><strong>${patch.rollback}</strong></div>
    </div>
  `;

  ranking.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => renderPatches(button.dataset.id));
  });
}

function renderPassport() {
  const list = document.querySelector("#passport-list");
  list.innerHTML = Object.entries(data.passport)
    .map(
      ([title, claims]) => `
        <article class="passport-block">
          <h3>${title}</h3>
          <ul>${claims.map((claim) => `<li>${claim}</li>`).join("")}</ul>
        </article>
      `,
    )
    .join("");
}

function renderSkills() {
  const list = document.querySelector("#skill-list");
  list.innerHTML = data.skills
    .map(
      (skill) => `
        <article class="skill-card">
          <h3>${skill.name}</h3>
          <p>${skill.desc}</p>
          <div class="targets">${skill.targets.map((target) => `<span>${target}</span>`).join("")}</div>
        </article>
      `,
    )
    .join("");
}

function renderEngineering() {
  const grid = document.querySelector("#engineering-grid");
  grid.innerHTML = data.engineering
    .map(
      (item) => `
        <article>
          <span>${item.label}</span>
          <strong>${item.title}</strong>
          <p>${item.desc}</p>
          <em>${item.proof}</em>
        </article>
      `,
    )
    .join("");
}

function renderInfra() {
  const grid = document.querySelector("#infra-grid");
  grid.innerHTML = data.infra
    .map(
      ([name, title, desc]) => `
        <article>
          <span>${name}</span>
          <strong>${title}</strong>
          <p>${desc}</p>
        </article>
      `,
    )
    .join("");
}

function hydrateMetrics() {
  document.querySelector("#metric-failure").textContent = percent(data.metrics.baselineFailureRate);
  document.querySelector("#metric-p99").textContent = `${data.metrics.baselineP99.toFixed(2)}ms`;
  document.querySelector("#metric-variants").textContent = data.metrics.faultVariants;
  document.querySelector("#metric-claims").textContent = data.metrics.evidenceClaims;
  document.querySelector("#metric-trace").textContent = data.metrics.traceSpans;
  document.querySelector("#metric-assets").textContent = data.metrics.qualityAssets;
}

hydrateMetrics();
renderTimeline();
renderExperiments();
renderGenome();
renderPatches();
renderPassport();
renderSkills();
renderEngineering();
renderInfra();
