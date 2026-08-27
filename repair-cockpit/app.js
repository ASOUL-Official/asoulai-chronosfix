const DATA_URL = "./data/demo-data.json";

const view = {
  data: null,
  scenarioId: null,
  mode: "approved",
  stepIndex: 0,
  demo: {
    events: [],
    revisionDelta: 0,
    attemptDelta: 0,
    taskOverrides: {},
    forcePaused: false,
    staleApproval: false,
    forceQualityFailure: false,
    forceToolDenied: false,
    log: [],
  },
};

const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const percent = (value, digits = 1) =>
  typeof value === "number" ? `${(value * 100).toFixed(digits)}%` : "—";
const milliseconds = (value) =>
  typeof value === "number" ? `${value.toFixed(value >= 100 ? 1 : 2)} ms` : "—";
const shortId = (value, length = 16) => {
  if (!value) return "pending";
  return value.length > length ? `${value.slice(0, length)}…` : value;
};
const list = (values) => (values?.length ? values.join("、") : "—");
const blockerLabel = (blocker) => {
  if (typeof blocker === "string") return blocker;
  if (blocker && typeof blocker === "object") {
    return blocker.message ?? blocker.code ?? JSON.stringify(blocker);
  }
  return String(blocker ?? "unknown blocker");
};

function statusClass(value) {
  const normalized = String(value ?? "").toLowerCase();
  if (["approved", "passed", "success", "correct", "completed", "offline-validated"].includes(normalized)) {
    return "is-pass";
  }
  if (
    normalized.includes("blocked") ||
    ["failed", "failure", "incorrect", "not-approved", "rejected"].includes(normalized)
  ) {
    return "is-block";
  }
  if (["pending", "paused_awaiting_human", "dry-run", "abstain"].includes(normalized)) return "is-pending";
  return "is-neutral";
}

function currentScenario() {
  return view.data.cases.find((item) => item.id === view.scenarioId) ?? view.data.cases[0];
}

function currentMode() {
  const scenario = currentScenario();
  return scenario.modes?.[view.mode] ?? null;
}

function resetDemoState() {
  view.demo = {
    events: [],
    revisionDelta: 0,
    attemptDelta: 0,
    taskOverrides: {},
    forcePaused: false,
    staleApproval: false,
    forceQualityFailure: false,
    forceToolDenied: false,
    log: [],
  };
}

function effectiveMode() {
  const mode = currentMode();
  if (!mode) return null;
  const next = {
    ...mode,
    blockers: [...(mode.blockers ?? [])],
    quality_blockers: [...(mode.quality_blockers ?? [])],
    approval_blockers: [...(mode.approval_blockers ?? [])],
  };
  if (view.demo.forceQualityFailure || view.demo.forceToolDenied) {
    next.quality_gate = "failed";
    next.release_decision = "blocked-quality";
    next.release_ready = false;
    next.quality_blockers.push(
      view.demo.forceToolDenied ? "注入的工具调用被最小权限策略拒绝" : "注入的工具验证失败：重试已耗尽",
    );
    next.blockers.push("quality_gate=failed");
  }
  if (view.demo.forcePaused || view.demo.staleApproval) {
    next.human_approval = "pending";
    next.release_decision = "blocked-awaiting-human";
    next.release_ready = false;
    next.approval_blockers.push(
      view.demo.staleApproval ? "approval_revision_stale：需要绑定最新 revision" : "等待人工 checkpoint",
    );
    next.blockers.push(view.demo.staleApproval ? "approval_revision_stale" : "human_approval=pending");
  }
  return next;
}

function effectiveCoordination(coordination) {
  if (!coordination) return null;
  const tasks = (coordination.tasks ?? []).map((task) => ({
    ...task,
    status: view.demo.taskOverrides[task.task_id] ?? task.status,
  }));
  return {
    ...coordination,
    revision: coordination.revision + view.demo.revisionDelta,
    status: view.demo.forceQualityFailure || view.demo.forceToolDenied
      ? "BLOCKED_RETRY_EXHAUSTED"
      : view.demo.forcePaused || view.demo.staleApproval
        ? "PAUSED_AWAITING_HUMAN"
        : coordination.status,
    tasks,
    attempts: [...(coordination.attempts ?? []), ...Array.from({ length: view.demo.attemptDelta }, (_, index) => ({
      task_id: "injected-worker-check",
      attempt: index + 1,
      worker: "demo-injector",
      status: "FAILED",
      error: "local simulation",
    }))],
    events: [...(coordination.events ?? []), ...view.demo.events],
  };
}

function addDemoEvent(eventType, message, options = {}) {
  const revisionDelta = options.revisionDelta ?? 1;
  view.demo.revisionDelta += revisionDelta;
  const coordination = currentScenario().coordination;
  const revision = (coordination?.revision ?? 0) + view.demo.revisionDelta;
  view.demo.events.push({
    event_type: eventType,
    revision,
    task_id: options.task_id,
    worker: options.worker,
    source: "demo-injector",
    message,
    idempotency_key: `demo-${eventType}-${Date.now()}-${view.demo.events.length}`,
  });
  view.demo.log.unshift({
    eventType,
    revision,
    message,
    timestamp: new Date().toLocaleTimeString("zh-CN", { hour12: false }),
  });
}

function renderInjectionLog() {
  const target = $("#injector-log");
  if (!target) return;
  target.innerHTML = view.demo.log.length
    ? view.demo.log
        .slice(0, 4)
        .map(
          (item) => `
            <div class="inject-log-row">
              <span>r${escapeHtml(item.revision)}</span>
              <strong>${escapeHtml(item.eventType)}</strong>
              <small>${escapeHtml(item.message)} · ${escapeHtml(item.timestamp)}</small>
            </div>
          `,
        )
        .join("")
    : `<span class="inject-empty">尚未注入事件；点击按钮观察共享状态如何改变。</span>`;
}

function applyInjection(type) {
  const scenario = currentScenario();
  if (type === "reset") {
    resetDemoState();
    renderInjectionLog();
    renderScenario();
    return;
  }
  if (scenario.runtime_scope !== "pipeline-and-evaluation" || !scenario.coordination) {
    view.demo.log.unshift({
      eventType: "blocked",
      revision: 0,
      message: "evaluation-only 样例不会进入控制面",
      timestamp: new Date().toLocaleTimeString("zh-CN", { hour12: false }),
    });
    renderInjectionLog();
    return;
  }
  switch (type) {
    case "new-evidence":
      addDemoEvent("evidence_observed", "发现配置漂移证据，动态注册审计任务", {
        task_id: "dynamic-config-audit",
        worker: "timeline-analyst-01",
      });
      view.demo.taskOverrides["dynamic-config-audit"] = "COMPLETED · EVIDENCE-TRIGGERED";
      break;
    case "worker-timeout":
      addDemoEvent("task_failed", "注入 timeline Worker 超时", {
        task_id: "timeline",
        worker: "timeline-analyst-01",
      });
      addDemoEvent("task_reassigned", "按 capability 重派到备用 Worker", {
        task_id: "timeline",
        worker: "timeline-analyst-02",
      });
      view.demo.attemptDelta += 1;
      view.demo.taskOverrides.timeline = "COMPLETED · REASSIGNED";
      break;
    case "duplicate-evidence":
      addDemoEvent("evidence_deduplicated", "重复 evidence 被幂等键拦截；revision 不变", {
        revisionDelta: 0,
        task_id: "dynamic-config-audit",
      });
      break;
    case "pause":
      addDemoEvent("human_pause", "中风险补丁进入人工 checkpoint", { task_id: "risk-gate" });
      view.demo.forcePaused = true;
      break;
    case "stale-approval":
      addDemoEvent("approval_invalidated", "新证据使旧 approval revision 自动失效", { task_id: "risk-gate" });
      view.demo.staleApproval = true;
      view.demo.forcePaused = true;
      break;
    case "resume":
      if (!view.demo.forcePaused && !view.demo.staleApproval) {
        view.demo.log.unshift({
          eventType: "resume_blocked",
          revision: (scenario.coordination?.revision ?? 0) + view.demo.revisionDelta,
          message: "没有暂停中的 checkpoint，恢复请求被忽略",
          timestamp: new Date().toLocaleTimeString("zh-CN", { hour12: false }),
        });
        break;
      }
      if (view.demo.staleApproval) {
        addDemoEvent("approval_rebound", "人工重新确认最新 revision 的审批摘要");
        view.demo.staleApproval = false;
      }
      addDemoEvent("human_resume", "人工确认最新证据后恢复任务", { task_id: "risk-gate" });
      view.demo.forcePaused = false;
      break;
    case "tool-denied":
      addDemoEvent("tool_permission_denied", "只读工具调用被最小权限策略拒绝，系统拒绝继续", {
        task_id: "dynamic-config-audit",
        worker: "timeline-analyst-01",
      });
      view.demo.forceToolDenied = true;
      view.demo.taskOverrides["dynamic-config-audit"] = "BLOCKED · PERMISSION DENIED";
      break;
    case "worker-crash":
      addDemoEvent("worker_crashed", "Worker 进程崩溃，租约失效", {
        task_id: "hypotheses",
        worker: "hypothesis-scientist-01",
      });
      addDemoEvent("task_reassigned", "控制面重新分派到备用 Worker", {
        task_id: "hypotheses",
        worker: "hypothesis-scientist-02",
      });
      view.demo.attemptDelta += 1;
      view.demo.taskOverrides.hypotheses = "COMPLETED · CRASH RECOVERED";
      break;
    case "retry-exhausted":
      addDemoEvent("retry_exhausted", "RiskGate Worker 重试耗尽，系统 fail-closed", {
        task_id: "risk-gate",
        worker: "release-auditor-01",
      });
      view.demo.attemptDelta += 2;
      view.demo.forceQualityFailure = true;
      view.demo.taskOverrides["risk-gate"] = "BLOCKED · RETRY EXHAUSTED";
      break;
    default:
      return;
  }
  renderInjectionLog();
  renderScenario();
}

function renderExternalLinks() {
  $("#external-links").innerHTML = view.data.links
    .map(
      (item) => `
        <a href="${escapeHtml(item.href)}" target="_blank" rel="noreferrer">
          ${escapeHtml(item.label)} <span aria-hidden="true">↗</span>
        </a>
      `,
    )
    .join("");
}

function renderTruthStrip() {
  $("#truth-strip").innerHTML = view.data.truthful_status
    .map(
      (item) => `
        <article class="truth-item">
          <span>${escapeHtml(item.label)}</span>
          <strong class="status-pill ${statusClass(item.value)}">${escapeHtml(item.value)}</strong>
          <small>${escapeHtml(item.detail)}</small>
        </article>
      `,
    )
    .join("");
}

function renderScenarioOptions() {
  const golden = view.data.cases.filter((item) => item.kind === "golden");
  const evaluationOnly = view.data.cases.filter((item) => item.kind !== "golden");
  const options = (items) =>
    items
      .map(
        (item) => `
          <option value="${escapeHtml(item.id)}">
            ${escapeHtml(item.id)} · ${escapeHtml(item.title)}
          </option>
        `,
      )
      .join("");
  $("#scenario-select").innerHTML = `
    <optgroup label="Golden · 完整流水线 ${golden.length} 个">
      ${options(golden)}
    </optgroup>
    <optgroup label="Badcase / 证据不足 · 只进入评测 ${evaluationOnly.length} 个">
      ${options(evaluationOnly)}
    </optgroup>
  `;
  $("#scenario-select").value = view.scenarioId;
}

function renderJudgeSteps() {
  $("#judge-steps").innerHTML = view.data.judge_steps
    .map(
      (item, index) => `
        <button class="${index === view.stepIndex ? "active" : ""}" data-step="${index}" type="button">
          <span>${escapeHtml(item.number)}</span>
          <strong>${escapeHtml(item.label)}</strong>
        </button>
      `,
    )
    .join("");

  $("#judge-steps").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      view.stepIndex = Number(button.dataset.step);
      renderJudgeSteps();
      renderStage();
    });
  });
}

function setStatus(element, value) {
  element.textContent = value;
  element.className = statusClass(value);
}

function renderGateAndIdentity() {
  const scenario = currentScenario();
  const mode = effectiveMode();
  const isPipeline = scenario.runtime_scope === "pipeline-and-evaluation";

  const human = mode?.human_approval ?? "pending";
  const quality = mode?.quality_gate ?? "pending";
  const decision = mode?.release_decision ?? "pending";
  setStatus($("#human-approval"), human);
  setStatus($("#quality-gate"), quality);
  setStatus($("#release-decision"), decision);

  $("#run-id").textContent = mode?.run_id ?? "pending · evaluation-only";
  $("#trace-id").textContent = mode?.trace_id ?? "pending · no pipeline trace";
  const revision = view.data.revision;
  const base = revision.base_commit ? ` · base ${shortId(revision.base_commit, 10)}` : "";
  $("#commit-id").textContent = `${revision.commit} · ${revision.kind}${base}`;
  $("#commit-id").title = revision.base_commit ?? "No patch commit was created by this dry-run.";

  $("#scenario-note").innerHTML = isPipeline
    ? `<strong>Golden · 完整流水线</strong>　${escapeHtml(scenario.incident_id)}　·　合成数据、离线实测`
    : `<strong>${escapeHtml(scenario.kind)} · evaluation-only</strong>　不会进入补丁、RiskGate 或 PR 流程；用于如实暴露系统边界。`;

  $("#decision-switch").querySelectorAll("button").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === view.mode);
    button.disabled = !isPipeline;
  });
}

function metricCard(label, value, note = "") {
  return `
    <article class="metric-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      ${note ? `<small>${escapeHtml(note)}</small>` : ""}
    </article>
  `;
}

function renderIncident(scenario) {
  const baselineMetrics = scenario.baseline_metrics ?? {};
  const baseline = scenario.baseline ?? {};
  const events = scenario.timeline ?? [];
  return `
    <div class="section-head">
      <div>
        <span class="micro-label">${escapeHtml(scenario.incident_id)}</span>
        <h3>${escapeHtml(scenario.title)}</h3>
      </div>
      <span class="case-badge ${scenario.kind === "golden" ? "golden" : "badcase"}">
        ${escapeHtml(scenario.kind)}
      </span>
    </div>
    <div class="metric-row">
      ${metricCard("基线失败率", percent(baselineMetrics.failure_rate), "deterministic synthetic")}
      ${metricCard("基线 P99", milliseconds(baselineMetrics.p99_ms), "simulator output")}
      ${metricCard("流量", `${baseline.traffic_rps ?? "—"} RPS`, "scenario input")}
      ${metricCard("连接池", `${baseline.pool_size ?? "—"}`, "scenario input")}
    </div>
    <div class="timeline compact-scroll">
      ${events
        .map((event, index) => {
          const timestamp = event.timestamp?.slice(11, 16) ?? `T${index + 1}`;
          return `
            <article>
              <span class="timeline-index">${String(index + 1).padStart(2, "0")}</span>
              <div>
                <small>${escapeHtml(timestamp)} · ${escapeHtml(event.source)}</small>
                <strong>${escapeHtml(event.kind)}</strong>
                <p>${escapeHtml(event.summary)}</p>
              </div>
            </article>
          `;
        })
        .join("")}
    </div>
  `;
}

function classificationLabel(value) {
  return {
    "primary-cause": "主因",
    amplifier: "放大因素",
    "not-causal": "已证伪",
  }[value] ?? value;
}

function renderCausal(scenario) {
  const evaluation = scenario.evaluation;
  if (scenario.runtime_scope !== "pipeline-and-evaluation") {
    return `
      <div class="evaluation-focus ${evaluation.expectation_met ? "is-met" : "is-missed"}">
        <span>${escapeHtml(evaluation.case_type)} · ${escapeHtml(evaluation.model_support)}</span>
        <h3>${escapeHtml(scenario.title)}</h3>
        <p>${escapeHtml(evaluation.rationale)}</p>
        <div class="comparison-grid">
          ${metricCard(
            "Ground Truth",
            evaluation.expected_outcome === "abstain"
              ? "应拒答"
              : list(evaluation.expected_primary_causes),
            "expected",
          )}
          ${metricCard("系统观测", list(evaluation.observed_primary_causes), evaluation.status)}
          ${metricCard("是否达成", evaluation.expectation_met ? "YES" : "NO", "kept as failure")}
        </div>
        <div class="boundary-note">
          <strong>已知边界，不包装成成功</strong>
          <p>${escapeHtml(evaluation.boundary_note)}</p>
        </div>
      </div>
    `;
  }

  return `
    <div class="experiment-grid">
      ${scenario.experiments
        .map(
          (item) => `
            <article class="experiment-card ${statusClass(
              item.classification === "primary-cause" ? "passed" : "neutral",
            )}">
              <div class="card-topline">
                <span>${escapeHtml(item.hypothesis_id)}</span>
                <strong>${escapeHtml(classificationLabel(item.classification))}</strong>
              </div>
              <h3>${escapeHtml(item.title)}</h3>
              <div class="rate-flow">
                <span>${percent(item.baseline_failure_rate)}</span>
                <i>→</i>
                <span>${percent(item.counterfactual_failure_rate)}</span>
              </div>
              <p>干预效果分 ${percent(item.intervention_effect_score)}；该值是确定性回放效果分，不是统计学置信区间。</p>
            </article>
          `,
        )
        .join("")}
    </div>
    <div class="scope-note">
      <strong>Ground Truth 对照：</strong>
      期望主因 ${escapeHtml(list(evaluation.expected_primary_causes))}；观测主因
      ${escapeHtml(list(evaluation.observed_primary_causes))}；结果
      <span class="status-pill ${statusClass(evaluation.status)}">${escapeHtml(evaluation.status)}</span>。
    </div>
  `;
}

function renderCoordination(scenario) {
  const coordination = effectiveCoordination(scenario.coordination);
  if (!coordination) {
    return `
      <div class="blocked-stage">
        <span>evaluation-only</span>
        <h3>此样例未进入动态协同控制面</h3>
        <p>边界样例会在生成补丁前停止，避免把未建模根因包装成成功。</p>
      </div>
    `;
  }
  const events = coordination.events ?? [];
  const attempts = coordination.attempts ?? [];
  const tasks = coordination.tasks ?? [];
  const count = (type) => events.filter((event) => event.event_type === type).length;
  const eventLabel = {
    evidence_observed: "新证据触发",
    task_reassigned: "Worker 重派",
    task_failed: "Worker 失败",
    evidence_deduplicated: "证据去重",
    task_deduplicated: "任务幂等回放",
    human_pause: "人工暂停",
    approval_invalidated: "旧审批失效",
    approval_rebound: "审批重新绑定",
    human_resume: "人工恢复",
    tool_permission_denied: "权限拒绝",
    worker_crashed: "Worker 崩溃",
    retry_exhausted: "重试耗尽",
  };
  return `
    <div class="section-head">
      <div>
        <span class="micro-label">AGENTTEAMS MATRIX · LOCAL COMPATIBLE EVIDENCE</span>
        <h3>任务会随着证据变化，而不是按固定剧本走完</h3>
      </div>
      <span class="case-badge golden">REV ${escapeHtml(coordination.revision)}</span>
    </div>
    <div class="metric-row">
      ${metricCard("共享状态 revision", coordination.revision, "每次状态写入递增")}
      ${metricCard("任务 / attempts", `${tasks.length} / ${attempts.length}`, "含失败重派")}
      ${metricCard("Worker 重派", count("task_reassigned"), "timeout -> backup")}
      ${metricCard("去重事件", count("evidence_deduplicated") + count("task_deduplicated"), "幂等保护")}
    </div>
    <div class="coordination-grid">
      <section class="task-board">
        <div class="card-topline"><span>动态任务图</span><strong>${escapeHtml(coordination.status)}</strong></div>
        ${tasks.map((task) => `
          <article class="task-row ${statusClass(task.status)}">
            <span>${escapeHtml(task.task_id)}</span>
            <small>${escapeHtml(task.skill)} · ${escapeHtml(task.capability)}</small>
            <b>${escapeHtml(task.status)}</b>
          </article>
        `).join("")}
      </section>
      <section class="event-feed">
        <div class="card-topline"><span>事件流 · 可回放</span><strong>${events.length} events</strong></div>
        ${events.filter((event) => eventLabel[event.event_type]).map((event) => `
          <article class="event-row">
            <span>r${escapeHtml(event.revision)}</span>
            <div><strong>${escapeHtml(eventLabel[event.event_type])}</strong><small>${escapeHtml(event.worker ?? event.task_id ?? "control-plane")}</small></div>
            <code>${escapeHtml(event.event_type)}</code>
          </article>
        `).join("")}
      </section>
    </div>
    <div class="scope-note">
      <strong>演示证据：</strong>timeline 首次超时后重派备用 Worker；配置 evidence 重复投递被去重；补丁完成后进入人工 checkpoint，新增 SLO 证据使旧 approval revision 失效，绑定最新 revision 后恢复。${view.demo.events.length ? "当前状态已叠加浏览器本地注入事件。" : ""}${escapeHtml(coordination.boundary_note ?? "")}
    </div>
  `;
}

function renderPatch(scenario) {
  if (!scenario.selected_patch) {
    return `
      <div class="blocked-stage">
        <span>evaluation-only</span>
        <h3>此样例不会生成补丁</h3>
        <p>Badcase 与证据不足夹具只验证系统是否识别边界；它们不会进入 Patch Tournament、RiskGate 或 GitHub PR，避免把已知错误包装成自动修复。</p>
      </div>
    `;
  }
  const selected = scenario.selected_patch;
  const healthy = selected.results.filter((item) => item.healthy).length;
  return `
    <div class="patch-layout">
      <article class="winner-card">
        <span>SELECTED PATCH · ${escapeHtml(selected.candidate_id)}</span>
        <h3>${escapeHtml(selected.title)}</h3>
        <div class="winner-score">${selected.total_score.toFixed(4)}</div>
        <p>变更：<code>${escapeHtml(JSON.stringify(selected.changes))}</code></p>
        <p>回滚：<code>${escapeHtml(JSON.stringify(selected.rollback_changes))}</code></p>
        <div class="health-bar"><i style="width:${(healthy / selected.results.length) * 100}%"></i></div>
        <small>${healthy}/${selected.results.length} 强制故障族变体健康 · 最差失败率 ${percent(
          selected.worst_failure_rate,
          2,
        )}</small>
      </article>
      <div class="ranking-list">
        ${scenario.patches
          .map(
            (patch, index) => `
              <article class="${patch.candidate_id === selected.candidate_id ? "selected" : ""}">
                <span>#${index + 1}</span>
                <div>
                  <strong>${escapeHtml(patch.candidate_id)}</strong>
                  <small>${escapeHtml(patch.title)}</small>
                </div>
                <b>${patch.total_score.toFixed(4)}</b>
              </article>
            `,
          )
          .join("")}
      </div>
    </div>
    <div class="gene-list" aria-label="故障族变体">
      ${selected.results
        .map(
          (item) => `
            <article class="${item.healthy ? "healthy" : "unhealthy"}">
              <span>${item.healthy ? "PASS" : "BLOCK"}</span>
              <strong>${escapeHtml(item.name)}</strong>
              <small>${percent(item.failure_rate, 2)} · P99 ${milliseconds(item.p99_ms)}</small>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderGate(scenario) {
  const mode = effectiveMode();
  if (!mode) {
    return `
      <div class="blocked-stage">
        <span>pending · evaluation-only</span>
        <h3>评测夹具在门禁前停止</h3>
        <p>这不是缺失的绿色状态，而是明确的安全边界：没有可靠因果结论，就不生成补丁、不请求审批、不创建发布决策。</p>
      </div>
    `;
  }
  const gateItems = [
    ["human_approval", mode.human_approval, "具名人类授权"],
    ["quality_gate", mode.quality_gate, "自动证据门禁"],
    ["release_decision", mode.release_decision, "最终发布决策"],
  ];
  return `
    <div class="gate-explainer">
      ${gateItems
        .map(
          ([label, value, note]) => `
            <article class="${statusClass(value)}">
              <span>${label}</span>
              <strong>${escapeHtml(value)}</strong>
              <small>${note}</small>
            </article>
          `,
        )
        .join("")}
    </div>
    <div class="check-grid">
      ${mode.checks
        .map(
          (check) => `
            <article>
              <span class="status-pill ${statusClass(check.conclusion)}">${escapeHtml(
                check.conclusion,
              )}</span>
              <strong>${escapeHtml(check.name)}</strong>
              <p>${escapeHtml(check.summary)}</p>
              <small>${escapeHtml(check.source ?? "offline run evidence")}</small>
            </article>
          `,
        )
        .join("")}
    </div>
    <div class="blocker-row ${mode.blockers.length ? "has-blockers" : ""}">
      <strong>${mode.release_ready ? "满足离线放行条件" : "Fail closed：当前不可发布"}</strong>
      <span>${escapeHtml(mode.blockers.length ? mode.blockers.map(blockerLabel).join("；") : "无阻断项")}</span>
    </div>
  `;
}

function claimBlock(title, claims) {
  return `
    <article class="claim-block">
      <span>${escapeHtml(title)}</span>
      <ul>${(claims ?? []).map((claim) => `<li>${escapeHtml(claim)}</li>`).join("")}</ul>
    </article>
  `;
}

function renderEvidence(scenario) {
  if (!scenario.passport) {
    return `
      <div class="evidence-boundary">
        <span>NO PASSPORT GENERATED</span>
        <h3>Badcase 被保留为评测证据，而不是修复证据</h3>
        <p>${escapeHtml(scenario.evaluation.boundary_note)}</p>
        ${renderLinkCards()}
      </div>
    `;
  }
  const passport = scenario.passport;
  const integrity = passport.integrity ?? {};
  const mode = effectiveMode();
  const isBlockedBranch = mode && !mode.release_ready;
  const riskClaims = isBlockedBranch
    ? [
        `当前演示分支：quality_gate=${mode.quality_gate}，human_approval=${mode.human_approval}，release_decision=${mode.release_decision}。`,
        "因审批证据缺失或质量门禁失败，证据护照保持 draft，不构成发布许可。",
        ...(mode.blockers ?? []).map((blocker) => `阻断项：${blockerLabel(blocker)}`),
      ]
    : passport.risk_claims;
  return `
    ${
      isBlockedBranch
        ? `
          <div class="passport-branch-warning">
            <span>DRAFT PASSPORT · FAIL CLOSED</span>
            <strong>当前分支不会复用已批准运行的审批摘要</strong>
            <p>因果、验证和回滚证据仍可供评审，但 approval digest 必须与具名审批人、理由和策略版本重新绑定。</p>
          </div>
        `
        : ""
    }
    <div class="passport-grid">
      ${claimBlock("因果声明", passport.causal_claims)}
      ${claimBlock("验证声明", passport.verification_claims)}
      ${claimBlock("风险声明", riskClaims)}
      ${claimBlock("回滚声明", passport.rollback_claims)}
    </div>
    <div class="integrity-grid">
      <div><span>scenario_sha256</span><code>${escapeHtml(shortId(integrity.scenario_sha256, 24))}</code></div>
      <div><span>patch_sha256</span><code>${escapeHtml(shortId(integrity.patch_changes_sha256, 24))}</code></div>
      <div><span>approval_digest</span><code>${
        isBlockedBranch
          ? "not-issued · current branch blocked"
          : escapeHtml(shortId(integrity.approval_input_digest, 24))
      }</code></div>
      <div><span>policy</span><code>${escapeHtml(integrity.policy_version ?? "pending")}</code></div>
    </div>
    ${renderLinkCards()}
  `;
}

function renderLinkCards() {
  return `
    <div class="link-cards">
      ${view.data.links
        .map(
          (item) => `
            <a href="${escapeHtml(item.href)}" target="_blank" rel="noreferrer">
              <span>PUBLIC EVIDENCE</span>
              <strong>${escapeHtml(item.label)}</strong>
              <small>打开真实链接 ↗</small>
            </a>
          `,
        )
        .join("")}
    </div>
  `;
}

function caseTypeLabel(item) {
  if (item.case_type === "golden") return "Golden";
  if (item.case_type === "insufficient-evidence") return "证据不足";
  return "Badcase";
}

function renderLearning(scenario) {
  const evaluation = view.data.evaluation;
  const summary = evaluation.summary;
  const skillSource = scenario.skills?.length
    ? scenario
    : view.data.cases.find((item) => item.skills?.length);
  return `
    <div class="metric-row evaluation-metrics">
      ${metricCard("Golden", `${summary.golden_expectation_met}/${summary.golden_cases}`, "受支持的合成诊断")}
      ${metricCard(
        "Badcase / 证据不足",
        `${summary.case_type_counts.badcase + summary.case_type_counts["insufficient-evidence"]}`,
        "全部如实展示",
      )}
      ${metricCard("正确拒答", `${summary.correct_abstentions}/${summary.expected_abstention_cases}`, "当前仍有改进空间")}
      ${metricCard("错误强归因", `${summary.unexpected_assertion_cases}`, "保留为失败")}
    </div>
    <div class="evaluation-caption">
      <strong>限定口径：</strong>9/9 只表示确定性模拟器已建模变量上的 Golden Case；2 个未建模 Badcase 和 1 个证据冲突样例不计入成功数。
    </div>
    <div class="corpus-table-wrap">
      <table>
        <thead>
          <tr><th>场景</th><th>类型</th><th>期望</th><th>观测主因</th><th>状态</th><th>达成</th></tr>
        </thead>
        <tbody>
          ${evaluation.cases
            .map(
              (item) => `
                <tr class="${item.scenario_id === scenario.id ? "current" : ""}">
                  <td><button data-scenario="${escapeHtml(item.scenario_id)}" type="button">${escapeHtml(
                    item.scenario_id,
                  )}</button></td>
                  <td>${caseTypeLabel(item)}</td>
                  <td>${escapeHtml(
                    item.expected_outcome === "abstain" ? "拒答" : list(item.expected_primary_causes),
                  )}</td>
                  <td>${escapeHtml(list(item.observed_primary_causes))}</td>
                  <td><span class="status-pill ${statusClass(item.status)}">${escapeHtml(
                    item.status,
                  )}</span></td>
                  <td>${item.expectation_met ? "YES" : "NO"}</td>
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
    <div class="learning-bottom">
      <section>
        <span class="micro-label">SKILL CANDIDATES · OFFLINE</span>
        <div class="skill-chips">
          ${(skillSource?.skills ?? [])
            .map((item) => `<span>${escapeHtml(item.name)} · v${escapeHtml(item.version)}</span>`)
            .join("")}
        </div>
      </section>
      <section class="runtime-boundary">
        ${view.data.truthful_status
          .map(
            (item) => `
              <div>
                <strong>${escapeHtml(item.label)}</strong>
                <span class="status-pill ${statusClass(item.value)}">${escapeHtml(item.value)}</span>
              </div>
            `,
          )
          .join("")}
      </section>
    </div>
  `;
}

const stepCopy = {
  incident: "把 Issue、Git、依赖、配置、流量与告警合并到同一个可追踪事故窗口。",
  coordination: "根据新证据动态插入任务，按 capability 选择 Worker；失败重派、重复去重、人工暂停和恢复都留下可回放事件。",
  causal: "逐一撤销可疑变量并重放，区分主因、放大因素与已证伪假设。",
  patch: "候选补丁必须通过同源故障族；健康失败就停，不靠人工强行放行。",
  gate: "把人类授权、自动质量门禁和最终发布决策明确拆成三个状态。",
  evidence: "将因果、验证、风险、回滚与完整性摘要绑定为可审计证据护照。",
  learning: "9 个 Golden 与 3 个边界样例一起展示，成功和失败都沉淀为工程资产。",
};

function renderStage() {
  const scenario = currentScenario();
  const step = view.data.judge_steps[view.stepIndex];
  $("#step-kicker").textContent = `STEP ${step.number}`;
  $("#step-title").textContent = step.label;
  $("#step-summary").textContent = stepCopy[step.id];
  $("#step-progress-label").textContent = `${view.stepIndex + 1} / ${view.data.judge_steps.length}`;
  $("#step-progress-bar").style.width = `${((view.stepIndex + 1) / view.data.judge_steps.length) * 100}%`;
  $("#next-step").textContent =
    view.stepIndex === view.data.judge_steps.length - 1 ? "回到第一步" : "下一步";

  const renderers = {
    incident: renderIncident,
    coordination: renderCoordination,
    causal: renderCausal,
    patch: renderPatch,
    gate: renderGate,
    evidence: renderEvidence,
    learning: renderLearning,
  };
  $("#stage-content").innerHTML = renderers[step.id](scenario);

  $("#stage-content").querySelectorAll("button[data-scenario]").forEach((button) => {
    button.addEventListener("click", () => {
      view.scenarioId = button.dataset.scenario;
      $("#scenario-select").value = view.scenarioId;
      renderGateAndIdentity();
      renderStage();
    });
  });
}

function renderScenario() {
  renderGateAndIdentity();
  renderStage();
}

function bindControls() {
  $("#scenario-select").addEventListener("change", (event) => {
    view.scenarioId = event.target.value;
    resetDemoState();
    renderInjectionLog();
    renderScenario();
  });

  $("#injector-actions").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-inject]");
    if (!button) return;
    applyInjection(button.dataset.inject);
  });

  $("#decision-switch").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.disabled) return;
      view.mode = button.dataset.mode;
      renderScenario();
    });
  });

  $("#next-step").addEventListener("click", () => {
    view.stepIndex = (view.stepIndex + 1) % view.data.judge_steps.length;
    renderJudgeSteps();
    renderStage();
    $(".stage").scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function showError(error) {
  $("#loading-screen").hidden = true;
  const template = $("#error-template");
  const fragment = template.content.cloneNode(true);
  fragment.querySelector("p").textContent =
    `${error.message}。请先生成数据并通过本地 HTTP 服务打开页面；直接双击 file:// 页面通常无法读取 JSON。`;
  document.body.append(fragment);
}

async function init() {
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    view.data = await response.json();
    const preferred = view.data.cases.find((item) => item.id === "checkout-timeout");
    view.scenarioId = preferred?.id ?? view.data.cases[0]?.id;
    if (!view.scenarioId) throw new Error("JSON 中没有评测场景");

    $("#product-title").textContent = view.data.product.title;
    $("#product-subtitle").textContent = view.data.product.subtitle;
    renderExternalLinks();
    renderTruthStrip();
    renderScenarioOptions();
    renderInjectionLog();
    renderJudgeSteps();
    renderScenario();
    bindControls();

    const stamp = new Date(view.data.generated_at);
    $("#data-stamp").textContent = `JSON 生成时间：${stamp.toLocaleString("zh-CN", {
      hour12: false,
    })}`;
    $("#loading-screen").hidden = true;
    $("#app").hidden = false;
  } catch (error) {
    showError(error);
  }
}

init();
