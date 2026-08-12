let reports = [],
  selectedRun = null,
  detailData = null,
  chatHistory = [],
  registryJobs = [],
  auditEvents = [],
  currentIdentity = null,
  jobSearchResults = null;
let locale = localStorage.getItem("aijc-locale") || "ko";
const T = {
  ko: {
    skipContent: "본문으로 건너뛰기",
    live: "운영 중",
    productType: "Job 품질 관제",
    navReports: "실행 리포트",
    navJobs: "감시 대상",
    navPolicies: "분석 정책",
    navEvidence: "근거 탐색",
    workspaceConnected: "워크스페이스 연결됨",
    title: "AI Job Checker",
    subtitle: "실행 이상부터 데이터 의미론까지, 근거 중심으로 진단합니다.",
    demoTitle: "진단 시나리오 실행",
    demoHelp: "샘플 Job으로 분석 흐름을 확인하세요.",
    scenarioNormal: "정상",
    scenarioStale: "데이터 지연",
    scenarioIncomplete: "불완전 데이터",
    scenarioSemantic: "의미론 오류",
    scenarioRuntime: "런타임 실패",
    kpiRuns: "분석 실행",
    kpiRunsHelp: "최근 리포트",
    kpiPass: "정상",
    kpiPassHelp: "정책 기준 통과",
    kpiAttention: "주의 필요",
    kpiAttentionHelp: "경고 또는 실패",
    kpiPolicy: "정책 버전",
    kpiPolicyHelp: "재현 가능한 스냅샷",
    recent: "최근 분석",
    runReports: "실행 리포트",
    refresh: "새로고침",
    loading: "리포트를 불러오는 중입니다…",
    loadingDetail: "실행 근거를 불러오는 중입니다…",
    empty: "아직 분석 리포트가 없습니다.",
    emptyHelp: "위 시나리오 중 하나를 실행해 첫 리포트를 만드세요.",
    error:
      "데이터를 불러오지 못했습니다. 연결과 권한을 확인한 뒤 새로고침하세요.",
    queued: "데모 실행이 요청되었습니다.",
    select: "실행을 선택하세요",
    selectHelp:
      "왼쪽에서 실행을 선택하면 판정, 근거, 수정 제안과 Code Agent가 표시됩니다.",
    verdict: "판정",
    riskScore: "위험 점수",
    confirmed: "확인된 사실",
    confirmedHelp: "Job API와 품질 측정에서 직접 확인된 값",
    metric: "품질 지표",
    observed: "측정값",
    threshold: "기준",
    result: "결과",
    pass: "통과",
    fail: "실패",
    recommendation: "권장 조치",
    recommendNone: "현재 기준에서 즉시 필요한 조치는 없습니다.",
    recommendFix:
      "실패 지표와 제안된 코드 변경을 검토한 뒤 Job을 다시 실행하세요.",
    diff: "제안 코드 변경",
    diffHelp: "실제 파일 경로와 주변 문맥을 포함한 unified diff",
    policy: "판정 기준",
    agent: "Code Agent에게 질문하기",
    agentHelp: "선택한 실행의 근거만 사용해 답합니다.",
    chatEmpty: "예: 실패 원인은 무엇이고 어느 코드를 바꿔야 하나요?",
    chatPlaceholder: "이 Job 실행에 대해 질문하세요…",
    send: "질문 보내기",
    thinking: "근거 검토 중…",
    chatError: "응답을 가져오지 못했습니다. 잠시 후 다시 시도하세요.",
    you: "나",
    assistant: "Code Agent",
    scope: "App service principal로 실행하며 선택한 run의 근거로 한정됩니다.",
    aiGenerated: "AI가 생성한 답변입니다. 적용 전에 검증하세요.",
    summary: "요약",
    severityNone: "정상",
    severityLow: "낮음",
    severityMedium: "중간",
    severityHigh: "높음",
    severityCritical: "매우 높음",
    controlPlane: "REGISTRY / CONTROL PLANE",
    jobsTitle: "감시 대상 Job",
    jobsSubtitle: "분석 대상을 등록하고, 권한·정책·watcher 상태를 하나의 운영 화면에서 제어합니다.",
    activeJobs: "활성",
    pausedJobs: "일시 중지",
    accessIssues: "권한 확인 필요",
    fleet: "LAKEFLOW FLEET",
    registry: "Job Registry",
    registryHelp: "App service principal이 접근할 수 있는 Job만 활성화할 수 있습니다.",
    refreshJobs: "Job registry 새로고침",
    findJob: "워크스페이스 Job 검색",
    jobSearchPlaceholder: "Job 이름 또는 ID 검색…",
    search: "검색",
    searchScope: "CAN_VIEW 이상이 부여되어 App에서 조회 가능한 Job만 표시됩니다.",
    job: "Job",
    policyVersion: "정책 버전",
    permission: "권한",
    watcher: "Watcher",
    actions: "작업",
    governance: "GOVERNANCE STREAM",
    auditTrail: "변경 감사 기록",
    auditHelp: "등록, 활성화, 일시 중지와 정책 변경 이력",
    executionIdentity: "App service principal로 실행",
    signedInFallback: "로그인 사용자 확인 불가",
    loadingJobs: "Job registry를 불러오는 중…",
    loadingSearch: "접근 가능한 Job을 검색하는 중…",
    noWatchedJobs: "등록된 감시 대상이 없습니다.",
    noSearchResults: "조건에 맞는 접근 가능한 Job이 없습니다.",
    searchPrompt: "이름 또는 ID로 Job을 검색해 등록하세요.",
    ready: "준비됨",
    accessRequired: "권한 필요",
    active: "활성",
    paused: "중지됨",
    neverChecked: "확인 대기",
    register: "등록",
    registered: "등록됨",
    activate: "활성화",
    pause: "일시 중지",
    savePolicy: "정책 저장",
    saving: "저장 중…",
    registrySaved: "Job registry가 업데이트되었습니다.",
    registryError: "Registry 작업을 완료하지 못했습니다. 권한과 연결을 확인하세요.",
    lastRun: "최근 run",
    lastCheck: "최근 확인",
    addedBy: "등록자",
    auditEmpty: "아직 기록된 변경이 없습니다.",
    auditRegistered: "Job 등록",
    auditActivated: "감시 활성화",
    auditPaused: "감시 일시 중지",
    auditPolicyUpdated: "정책 변경",
  },
  en: {
    skipContent: "Skip to content",
    live: "Live",
    productType: "Job quality operations",
    navReports: "Run reports",
    navJobs: "Watched Jobs",
    navPolicies: "Analysis policies",
    navEvidence: "Evidence explorer",
    workspaceConnected: "Workspace connected",
    title: "AI Job Checker",
    subtitle:
      "Diagnose run anomalies and data semantics with evidence you can trace.",
    demoTitle: "Run a diagnostic scenario",
    demoHelp: "Use a sample Job to inspect the analysis flow.",
    scenarioNormal: "Normal",
    scenarioStale: "Stale data",
    scenarioIncomplete: "Incomplete data",
    scenarioSemantic: "Semantic bug",
    scenarioRuntime: "Runtime failure",
    kpiRuns: "Analyzed runs",
    kpiRunsHelp: "Recent reports",
    kpiPass: "Healthy",
    kpiPassHelp: "Passed policy",
    kpiAttention: "Needs attention",
    kpiAttentionHelp: "Warning or failure",
    kpiPolicy: "Policy version",
    kpiPolicyHelp: "Reproducible snapshot",
    recent: "Recent analysis",
    runReports: "Run reports",
    refresh: "Refresh",
    loading: "Loading reports…",
    loadingDetail: "Loading run evidence…",
    empty: "No analysis reports yet.",
    emptyHelp: "Run a scenario above to create the first report.",
    error: "Unable to load data. Check access and connection, then refresh.",
    queued: "Demo run requested.",
    select: "Select a run",
    selectHelp:
      "Choose a run to inspect its verdict, evidence, code suggestion, and Code Agent.",
    verdict: "Verdict",
    riskScore: "Risk score",
    confirmed: "Confirmed facts",
    confirmedHelp:
      "Directly observed from the Jobs API and quality measurements",
    metric: "Quality metric",
    observed: "Observed",
    threshold: "Policy",
    result: "Result",
    pass: "Pass",
    fail: "Fail",
    recommendation: "Recommended action",
    recommendNone: "No immediate action is required under the current policy.",
    recommendFix:
      "Review failed metrics and the proposed code change, then rerun the Job.",
    diff: "Suggested code change",
    diffHelp: "Unified diff with the actual file path and surrounding context",
    policy: "Decision policy",
    agent: "Ask the Code Agent",
    agentHelp: "Answers use evidence from the selected run only.",
    chatEmpty: "Example: What failed, and which code should I change?",
    chatPlaceholder: "Ask about this Job run…",
    send: "Send question",
    thinking: "Reviewing evidence…",
    chatError: "Unable to get a response. Try again shortly.",
    you: "You",
    assistant: "Code Agent",
    scope:
      "Runs as the App service principal and is limited to this run evidence.",
    aiGenerated: "AI-generated answer. Verify before applying.",
    summary: "Summary",
    severityNone: "None",
    severityLow: "Low",
    severityMedium: "Medium",
    severityHigh: "High",
    severityCritical: "Critical",
    controlPlane: "REGISTRY / CONTROL PLANE",
    jobsTitle: "Watched Jobs",
    jobsSubtitle: "Register analysis targets and control access, policy, and watcher state from one operations surface.",
    activeJobs: "Active",
    pausedJobs: "Paused",
    accessIssues: "Access issues",
    fleet: "LAKEFLOW FLEET",
    registry: "Job Registry",
    registryHelp: "Only Jobs accessible to the App service principal can be activated.",
    refreshJobs: "Refresh Job registry",
    findJob: "Search workspace Jobs",
    jobSearchPlaceholder: "Search by Job name or ID…",
    search: "Search",
    searchScope: "Only Jobs visible to the App with CAN_VIEW or higher are returned.",
    job: "Job",
    policyVersion: "Policy version",
    permission: "Permission",
    watcher: "Watcher",
    actions: "Actions",
    governance: "GOVERNANCE STREAM",
    auditTrail: "Change Audit",
    auditHelp: "Registration, activation, pause, and policy history",
    executionIdentity: "Runs as App service principal",
    signedInFallback: "Signed-in user unavailable",
    loadingJobs: "Loading Job registry…",
    loadingSearch: "Searching accessible Jobs…",
    noWatchedJobs: "No watched Jobs are registered.",
    noSearchResults: "No accessible Jobs match this search.",
    searchPrompt: "Search by Job name or ID to register a target.",
    ready: "Ready",
    accessRequired: "Access required",
    active: "Active",
    paused: "Paused",
    neverChecked: "Awaiting check",
    register: "Register",
    registered: "Registered",
    activate: "Activate",
    pause: "Pause",
    savePolicy: "Save policy",
    saving: "Saving…",
    registrySaved: "Job registry updated.",
    registryError: "Unable to complete the registry operation. Check access and connection.",
    lastRun: "Last run",
    lastCheck: "Last check",
    addedBy: "Added by",
    auditEmpty: "No registry changes have been recorded yet.",
    auditRegistered: "Job registered",
    auditActivated: "Watcher activated",
    auditPaused: "Watcher paused",
    auditPolicyUpdated: "Policy changed",
  },
};
const t = (k) => T[locale][k] || k;
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const fmt = (v) =>
  v == null
    ? "—"
    : new Intl.DateTimeFormat(locale === "ko" ? "ko-KR" : "en-US", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(v));
const fmtNum = (v) =>
  v == null
    ? "—"
    : new Intl.NumberFormat(locale === "ko" ? "ko-KR" : "en-US", {
        maximumFractionDigits: 4,
      }).format(v);
const scenarioName = (s) =>
  t(
    {
      normal: "scenarioNormal",
      stale: "scenarioStale",
      incomplete: "scenarioIncomplete",
      semantic_bug: "scenarioSemantic",
      runtime_failure: "scenarioRuntime",
    }[s] || s,
  );
const severityName = (s) =>
  t(
    {
      NONE: "severityNone",
      LOW: "severityLow",
      MEDIUM: "severityMedium",
      HIGH: "severityHigh",
      CRITICAL: "severityCritical",
    }[s] || s,
  );
const localizedSummary = (r) =>
  ({
    ko: {
      normal: "실행과 LTV 품질 기준이 정상 범위입니다.",
      stale: "LTV 산출 데이터가 freshness 기준을 초과했습니다.",
      incomplete: "산출 고객 완전성이 정책 기준보다 낮습니다.",
      semantic_bug: "LTV가 순매출이 아닌 절대 금액 합계로 계산되었습니다.",
      runtime_failure: "원본 Job이 런타임 오류로 실패했습니다.",
    },
    en: {
      normal: "The run and LTV quality checks are within policy.",
      stale: "The LTV output exceeds the freshness threshold.",
      incomplete: "Output customer completeness is below policy.",
      semantic_bug: "LTV uses absolute amounts instead of net revenue.",
      runtime_failure: "The source Job failed with a runtime error.",
    },
  })[locale][r.scenario] || r.summary;
function notice(msg, show = true) {
  const e = document.querySelector("#notice");
  e.textContent = msg;
  e.hidden = !show;
}
function applyLocale() {
  document.documentElement.lang = locale;
  document
    .querySelectorAll("[data-i18n]")
    .forEach((e) => (e.textContent = t(e.dataset.i18n)));
  document
    .querySelectorAll("[data-i18n-placeholder]")
    .forEach((e) => (e.placeholder = t(e.dataset.i18nPlaceholder)));
  document
    .querySelectorAll("[data-i18n-aria]")
    .forEach((e) => e.setAttribute("aria-label", t(e.dataset.i18nAria)));
  document.querySelector("#locale").textContent =
    locale === "ko" ? "EN · English" : "KO · 한국어";
  document.querySelector("#refresh").title = t("refresh");
  document.querySelector("#refresh").setAttribute("aria-label", t("refresh"));
  localStorage.setItem("aijc-locale", locale);
  renderReports();
  renderDetail();
  renderRegistry();
  renderAudit();
}
function emptyDetail(kind = "select") {
  document.querySelector("#detail").innerHTML =
    `<div class="empty"><span>⌁</span><h2>${t(kind)}</h2><p>${t(kind + "Help")}</p></div>`;
}
function renderSkeleton() {
  document.querySelector("#detail").innerHTML =
    '<div class="skeleton" aria-hidden="true"><i></i><i></i><i></i></div>';
}
async function load() {
  notice(t("loading"));
  try {
    const res = await fetch("/api/reports");
    if (!res.ok) throw Error(res.status);
    reports = await res.json();
    document.querySelector("#total").textContent = fmtNum(reports.length);
    document.querySelector("#passed").textContent = fmtNum(
      reports.filter((r) => r.verdict === "PASS").length,
    );
    document.querySelector("#failed").textContent = fmtNum(
      reports.filter((r) => r.verdict !== "PASS").length,
    );
    document.querySelector("#policy").textContent =
      reports[0]?.policy_version || "—";
    renderReports();
    notice("", false);
    const requested = Number(new URLSearchParams(location.search).get("run"));
    if (!reports.length) emptyDetail("empty");
    else if (!selectedRun)
      await detail(
        reports.some((r) => r.source_run_id === requested)
          ? requested
          : reports[0].source_run_id,
      );
  } catch (e) {
    notice(`${t("error")} (${e.message})`);
    emptyDetail("empty");
  }
}
function renderReports() {
  const root = document.querySelector("#reports");
  root.innerHTML = reports
    .map(
      (r) =>
        `<button type="button" class="report ${Number(selectedRun) === r.source_run_id ? "selected" : ""}" data-run="${r.source_run_id}"><span aria-hidden="true" class="status-dot ${r.verdict}"></span><span><strong>${esc(scenarioName(r.scenario))}</strong><small>Run #${r.source_run_id} · ${fmt(r.created_at)}</small></span><span class="pill ${r.severity}">${esc(severityName(r.severity))}</span></button>`,
    )
    .join("");
  root
    .querySelectorAll("button")
    .forEach((b) => (b.onclick = () => detail(Number(b.dataset.run))));
}
async function detail(run) {
  selectedRun = Number(run);
  chatHistory = [];
  renderReports();
  renderSkeleton();
  notice(t("loadingDetail"));
  const url = new URL(location.href);
  url.searchParams.set("view", "reports");
  url.searchParams.set("run", selectedRun);
  history.replaceState(null, "", url);
  try {
    const res = await fetch(`/api/reports/${run}`);
    if (!res.ok) throw Error(res.status);
    detailData = await res.json();
    renderDetail();
    notice("", false);
  } catch (e) {
    notice(`${t("error")} (${e.message})`);
  }
}
function renderDetail() {
  if (!detailData) {
    emptyDetail();
    return;
  }
  const r = detailData;
  const metrics = r.metrics || [],
    pending = chatHistory.some((m) => m.pending);
  document.querySelector("#detail").innerHTML =
    `<div class="detail-head"><div><p class="eyebrow">RUN #${r.source_run_id} / ${esc(scenarioName(r.scenario))}</p><h2>${esc(localizedSummary(r))}</h2><small>${fmt(r.created_at)} · <span translate="no">${esc(r.model_endpoint)}</span></small></div><div class="verdict-card"><span>${t("verdict")}</span><strong class="verdict ${r.verdict}">${r.verdict}</strong><small>${t("riskScore")} ${fmtNum(r.score)}/100</small></div></div><section><div class="section-heading"><div><h3>${t("confirmed")}</h3><p>${t("confirmedHelp")}</p></div></div><div class="metric-table-wrap"><table><thead><tr><th scope="col">${t("metric")}</th><th scope="col">${t("observed")}</th><th scope="col">${t("threshold")}</th><th scope="col">${t("result")}</th></tr></thead><tbody>${metrics.map((m) => `<tr><th scope="row" translate="no">${esc(m.metric_key)}</th><td>${fmtNum(m.metric_value)}</td><td>${fmtNum(m.threshold_value)}</td><td><span class="check ${m.passed ? "ok" : "bad"}">${m.passed ? "✓ " + t("pass") : "! " + t("fail")}</span></td></tr>`).join("")}</tbody></table></div></section><section class="action ${r.verdict === "PASS" ? "good" : "warn"}"><span aria-hidden="true">${r.verdict === "PASS" ? "✓" : "!"}</span><div><h3>${t("recommendation")}</h3><p>${r.verdict === "PASS" ? t("recommendNone") : t("recommendFix")}</p></div></section>${r.suggested_diff ? `<section><div class="section-heading"><div><h3>${t("diff")}</h3><p>${t("diffHelp")}</p></div></div><pre class="diff" translate="no">${esc(r.suggested_diff)}</pre></section>` : ""}<details><summary>${t("policy")} · ${esc(r.policy_version)} · <span translate="no">${esc((r.policy_hash || "").slice(0, 12))}</span></summary><pre translate="no">${esc(r.policy_snapshot)}</pre></details><section class="chat"><div class="section-heading"><div><h3>${t("agent")}</h3><p>${t("agentHelp")}</p></div></div><div id="messages" class="messages" aria-live="polite" aria-busy="${pending}">${renderMessages()}</div><form id="chatForm"><label class="sr-only" for="chatInput">${t("chatPlaceholder")}</label><textarea id="chatInput" name="job-question" autocomplete="off" rows="2" maxlength="2000" placeholder="${t("chatPlaceholder")}"></textarea><button type="submit" ${pending ? "disabled" : ""}>${pending ? t("thinking") : t("send") + " →"}</button></form><small class="scope">ⓘ ${t("scope")}</small></section>`;
  document.querySelector("#chatForm").onsubmit = askAgent;
}
function renderMessages() {
  return chatHistory.length
    ? chatHistory
        .map(
          (m) =>
            `<div class="message ${m.role}"><strong>${m.role === "user" ? t("you") : t("assistant")}</strong><p>${esc(m.content)}</p>${m.role === "assistant" && !m.pending ? `<small class="ai-note">${t("aiGenerated")}</small>` : ""}</div>`,
        )
        .join("")
    : `<div class="chat-empty">${t("chatEmpty")}</div>`;
}
async function askAgent(e) {
  e.preventDefault();
  const input = document.querySelector("#chatInput"),
    message = input.value.trim();
  if (!message) return;
  const history = [...chatHistory];
  chatHistory.push(
    { role: "user", content: message },
    { role: "assistant", content: t("thinking"), pending: true },
  );
  renderDetail();
  try {
    const res = await fetch(`/api/reports/${selectedRun}/chat`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message, locale, history }),
    });
    const body = await res.json();
    if (!res.ok) throw Error(body.detail || res.status);
    chatHistory[chatHistory.length - 1] = {
      role: "assistant",
      content: body.answer,
    };
  } catch (err) {
    chatHistory[chatHistory.length - 1] = {
      role: "assistant",
      content: `${t("chatError")} (${err.message})`,
    };
  }
  renderDetail();
  document.querySelector("#messages")?.scrollTo(0, 99999);
}

function jobNotice(message, show = true) {
  const root = document.querySelector("#jobNotice");
  root.textContent = message;
  root.hidden = !show;
}

async function api(path, options) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw Error(body.detail || response.status);
  return body;
}

function setView(view, updateUrl = true) {
  const next = view === "jobs" ? "jobs" : "reports";
  document.querySelector("#reportsView").hidden = next !== "reports";
  document.querySelector("#jobsView").hidden = next !== "jobs";
  document.querySelector("#main").dataset.view = next;
  document.querySelectorAll("[data-view-link]").forEach((link) => {
    const active = link.dataset.viewLink === next;
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  if (updateUrl) {
    const url = new URL(location.href);
    url.searchParams.set("view", next);
    if (next === "jobs") url.searchParams.delete("run");
    history.pushState(null, "", url);
  }
  if (next === "jobs" && !registryJobs.length) loadRegistry();
}

function renderRegistry() {
  const root = document.querySelector("#watchedJobs");
  if (!root) return;
  document.querySelector("#activeJobs").textContent = fmtNum(
    registryJobs.filter((job) => job.enabled).length,
  );
  document.querySelector("#pausedJobs").textContent = fmtNum(
    registryJobs.filter((job) => !job.enabled).length,
  );
  document.querySelector("#accessIssues").textContent = fmtNum(
    registryJobs.filter((job) => !job.permission_ready).length,
  );
  if (!registryJobs.length) {
    root.innerHTML = `<tr><td colspan="5"><div class="table-empty">${t("noWatchedJobs")}</div></td></tr>`;
    return;
  }
  root.innerHTML = registryJobs
    .map(
      (job) => `<tr data-job-id="${job.job_id}">
        <td data-label="${t("job")}"><div class="job-cell"><span class="job-node ${job.enabled ? "online" : ""}" aria-hidden="true"></span><span><strong>${esc(job.job_name)}</strong><small translate="no">#${job.job_id} · ${t("addedBy")} ${esc(job.added_by || "—")}</small></span></div></td>
        <td data-label="${t("policyVersion")}"><div class="policy-control"><label class="sr-only" for="policy-${job.job_id}">${t("policyVersion")}</label><input id="policy-${job.job_id}" name="policy-version-${job.job_id}" autocomplete="off" spellcheck="false" maxlength="32" value="${esc(job.policy_version || "1.1.0")}" translate="no"><button type="button" data-action="policy" title="${t("savePolicy")}" aria-label="${t("savePolicy")}">↗</button></div></td>
        <td data-label="${t("permission")}"><span class="registry-badge ${job.permission_ready ? "ready" : "blocked"}"><i aria-hidden="true"></i>${t(job.permission_ready ? "ready" : "accessRequired")}</span></td>
        <td data-label="${t("watcher")}"><span class="watch-state ${job.enabled ? "active" : "paused"}">${t(job.enabled ? "active" : "paused")}</span><small>${job.last_checked_at ? `${t("lastCheck")} ${fmt(job.last_checked_at)}` : t("neverChecked")}${job.last_run_id ? ` · ${t("lastRun")} #${job.last_run_id}` : ""}</small></td>
        <td data-label="${t("actions")}"><button type="button" class="registry-action ${job.enabled ? "pause" : "activate"}" data-action="toggle">${t(job.enabled ? "pause" : "activate")}</button></td>
      </tr>`,
    )
    .join("");
  root.querySelectorAll("[data-action='toggle']").forEach((button) => {
    button.onclick = () => {
      const row = button.closest("tr");
      const job = registryJobs.find((item) => item.job_id === Number(row.dataset.jobId));
      updateRegistryJob(job.job_id, { enabled: !job.enabled }, button);
    };
  });
  root.querySelectorAll("[data-action='policy']").forEach((button) => {
    button.onclick = () => {
      const row = button.closest("tr");
      const input = row.querySelector("input");
      updateRegistryJob(Number(row.dataset.jobId), { policy_version: input.value }, button);
    };
  });
}

function renderAudit() {
  const root = document.querySelector("#auditLog");
  if (!root) return;
  document.querySelector("#signedInUser").textContent =
    currentIdentity?.email || currentIdentity?.user || t("signedInFallback");
  if (!auditEvents.length) {
    root.innerHTML = `<li class="audit-empty">${t("auditEmpty")}</li>`;
    return;
  }
  const labels = {
    REGISTERED: "auditRegistered",
    ACTIVATED: "auditActivated",
    PAUSED: "auditPaused",
    POLICY_UPDATED: "auditPolicyUpdated",
  };
  root.innerHTML = auditEvents
    .map(
      (event) => `<li><span class="audit-marker" aria-hidden="true"></span><div><strong>${t(labels[event.action] || event.action)}</strong><p><span translate="no">Job #${event.job_id}</span>${event.details?.job_name ? ` · ${esc(event.details.job_name)}` : ""}</p><small>${fmt(event.event_time)} · ${esc(event.actor || "—")}</small></div></li>`,
    )
    .join("");
}

function renderJobSearchResults() {
  const root = document.querySelector("#jobSearchResults");
  if (jobSearchResults === null) {
    root.innerHTML = `<div class="search-empty">⌘ <span>${t("searchPrompt")}</span></div>`;
    return;
  }
  if (!jobSearchResults.length) {
    root.innerHTML = `<div class="search-empty">${t("noSearchResults")}</div>`;
    return;
  }
  const defaultPolicy = reports[0]?.policy_version || "1.1.0";
  root.innerHTML = jobSearchResults
    .map((job) => {
      const exists = registryJobs.some((item) => item.job_id === job.job_id);
      return `<article><span class="result-glyph" aria-hidden="true">J</span><div><strong>${esc(job.job_name)}</strong><small translate="no">Job #${job.job_id}</small></div><span class="registry-badge ready"><i aria-hidden="true"></i>${t("ready")}</span><label class="sr-only" for="new-policy-${job.job_id}">${t("policyVersion")}</label><input id="new-policy-${job.job_id}" name="new-policy-${job.job_id}" autocomplete="off" spellcheck="false" maxlength="32" value="${esc(defaultPolicy)}" translate="no"><button type="button" data-register="${job.job_id}" ${exists ? "disabled" : ""}>${t(exists ? "registered" : "register")}</button></article>`;
    })
    .join("");
  root.querySelectorAll("[data-register]").forEach((button) => {
    button.onclick = () => {
      const id = Number(button.dataset.register);
      const policy = document.querySelector(`#new-policy-${id}`).value;
      registerJob(id, policy, button);
    };
  });
}

async function loadRegistry() {
  jobNotice(t("loadingJobs"));
  try {
    [registryJobs, auditEvents, currentIdentity] = await Promise.all([
      api("/api/watched-jobs"),
      api("/api/watched-jobs/audit"),
      api("/api/whoami"),
    ]);
    renderRegistry();
    renderAudit();
    renderJobSearchResults();
    jobNotice("", false);
  } catch (error) {
    jobNotice(`${t("registryError")} (${error.message})`);
  }
}

async function searchJobs(event) {
  event.preventDefault();
  const input = document.querySelector("#jobSearch");
  const button = event.submitter || event.currentTarget.querySelector("button");
  button.disabled = true;
  button.textContent = t("loadingSearch");
  try {
    jobSearchResults = await api(`/api/jobs?search=${encodeURIComponent(input.value.trim())}`);
    const url = new URL(location.href);
    if (input.value.trim()) url.searchParams.set("q", input.value.trim());
    else url.searchParams.delete("q");
    history.replaceState(null, "", url);
    renderJobSearchResults();
  } catch (error) {
    jobNotice(`${t("registryError")} (${error.message})`);
  } finally {
    button.disabled = false;
    button.textContent = t("search");
  }
}

async function registerJob(jobId, policyVersion, button) {
  button.disabled = true;
  button.textContent = t("saving");
  try {
    await api("/api/watched-jobs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ job_id: jobId, policy_version: policyVersion }),
    });
    jobNotice(t("registrySaved"));
    await loadRegistry();
  } catch (error) {
    jobNotice(`${t("registryError")} (${error.message})`);
    button.disabled = false;
    button.textContent = t("register");
  }
}

async function updateRegistryJob(jobId, payload, button) {
  button.disabled = true;
  const original = button.textContent;
  button.textContent = t("saving");
  try {
    await api(`/api/watched-jobs/${jobId}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    await loadRegistry();
    jobNotice(t("registrySaved"));
  } catch (error) {
    jobNotice(`${t("registryError")} (${error.message})`);
    button.disabled = false;
    button.textContent = original;
  }
}

document.querySelector("#locale").onclick = () => {
  locale = locale === "ko" ? "en" : "ko";
  applyLocale();
};
document.querySelector("#refresh").onclick = load;
document.querySelector("#refreshJobs").onclick = loadRegistry;
document.querySelector("#jobSearchForm").onsubmit = searchJobs;
document.querySelectorAll("[data-view-link]").forEach((link) => {
  link.onclick = (event) => {
    event.preventDefault();
    setView(link.dataset.viewLink);
  };
});
window.onpopstate = () => setView(new URLSearchParams(location.search).get("view"), false);
document.querySelectorAll("[data-scenario]").forEach(
  (b) =>
    (b.onclick = async () => {
      b.disabled = true;
      try {
        const res = await fetch("/api/demo", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ scenario: b.dataset.scenario }),
        });
        const body = await res.json();
        if (!res.ok) throw Error(body.detail || res.status);
        notice(`${t("queued")} Run #${body.run_id}`);
      } catch (e) {
        notice(`${t("error")} (${e.message})`);
      } finally {
        b.disabled = false;
      }
    }),
);
applyLocale();
load();
renderJobSearchResults();
const initialParams = new URLSearchParams(location.search);
const initialView = initialParams.get("view") === "jobs" ? "jobs" : "reports";
document.querySelector("#jobSearch").value = initialParams.get("q") || "";
setView(initialView, false);
