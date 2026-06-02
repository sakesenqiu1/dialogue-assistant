const API = "";
let currentConvId = null;
let currentProfile = null;

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (res.status === 204) return {};
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const msg = Array.isArray(detail)
      ? detail.map((d) => d.msg || d).join("; ")
      : detail || res.statusText || "请求失败";
    throw new Error(msg);
  }
  return data;
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s ?? "";
  return d.innerHTML;
}

function riskClass(score) {
  if (score < 35) return "low";
  if (score < 65) return "mid";
  return "high";
}

function formatTime(iso) {
  return new Date(iso).toLocaleString("zh-CN", { hour12: false });
}

function setTab(name) {
  document.querySelectorAll(".tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === name);
  });
  document.querySelectorAll(".tab-panel").forEach((p) => {
    p.classList.toggle("active", p.id === `tab-${name}`);
  });
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.onclick = () => setTab(btn.dataset.tab);
});

function enableConvActions(on) {
  $("btnImport").disabled = !on;
  $("btnImportSelf").disabled = !on;
  $("btnBuildProfile").disabled = !on;
  $("btnDeleteProfile").disabled = !on;
  $("btnAnalyze").disabled = !on;
  $("btnDeleteConv").disabled = !on;
  $("btnClearDialogue").disabled = !on;
  $("btnClearSelf").disabled = !on;
  $("btnClearAllMsgs").disabled = !on;
  $("btnSaveNarrative").disabled = !on;
  $("btnDeleteNarrative").disabled = !on;
  $("userNarrative").disabled = !on;
  $("logForm").classList.toggle("hidden", !on);
}

async function checkHealth() {
  const el = $("apiStatus");
  try {
    const h = await api("/api/health");
    el.textContent = h.api_configured ? "DeepSeek 已配置" : "请配置 .env API Key";
    el.className = "badge " + (h.api_configured ? "ok" : "warn");
  } catch {
    el.textContent = "服务未连接";
    el.className = "badge warn";
  }
}

async function loadConversations() {
  const list = await api("/api/conversations");
  const ul = $("convList");
  ul.innerHTML = "";
  if (!list.length) {
    ul.innerHTML = '<li class="empty-hint" style="padding:8px">点击「新建」</li>';
    return;
  }
  list.forEach((c) => {
    const li = document.createElement("li");
    li.className = "conv-item" + (c.id === currentConvId ? " active" : "");
    const badge = c.has_profile
      ? c.profile_stale
        ? '<span class="tag tag-warn">画像待更新</span>'
        : '<span class="tag tag-ok">已有画像</span>'
      : '<span class="tag">未建画像</span>';
    const narrTag = c.user_narrative
      ? '<span class="tag tag-ok">有旁白</span>'
      : "";
    const selfTag =
      c.self_narrative_count > 0
        ? `<span class="tag">${c.self_narrative_count} 自述</span>`
        : "";
    li.innerHTML = `
      <div class="conv-item-body">
        <div class="title">${escapeHtml(c.title)}</div>
        <div class="meta">${c.message_count} 条 ${selfTag} ${badge} ${narrTag}</div>
      </div>
      <button type="button" class="conv-del" title="删除此对话本" aria-label="删除">×</button>
    `;
    li.querySelector(".conv-item-body").onclick = () => selectConversation(c.id);
    li.querySelector(".conv-del").onclick = (e) => {
      e.stopPropagation();
      deleteConversation(c.id, c.title);
    };
    ul.appendChild(li);
  });
}

async function deleteConversation(id, title) {
  const name = title || "该对话本";
  if (
    !confirm(
      `确定删除「${name}」？\n将同时删除其中的聊天记录、画像与旁白，且无法恢复。`
    )
  ) {
    return;
  }
  try {
    await api(`/api/conversations/${id}`, { method: "DELETE" });
    if (currentConvId === id) {
      currentConvId = null;
      currentProfile = null;
      enableConvActions(false);
      $("userNarrative").value = "";
      $("narrativeStatus").textContent = "";
      renderUserNarrative("");
      $("profileBox").className = "profile-box empty-hint";
      $("profileBox").textContent = "请选择或新建对话本";
      $("profileBanner").classList.add("hidden");
      $("messageList").className = "message-list empty-hint";
      $("messageList").textContent = "暂无记录";
      $("pastAnalyses").className = "past-list empty-hint";
      $("pastAnalyses").textContent = "暂无";
      $("analysisResult").className = "analysis-result hidden";
      $("analysisResult").innerHTML = "";
    }
    await loadConversations();
  } catch (e) {
    alert(e.message);
  }
}

function renderUserNarrative(text) {
  const t = (text || "").trim();
  const has = !!t;

  if ($("btnDeleteNarrative")) {
    $("btnDeleteNarrative").disabled = !currentConvId || !has;
  }

  const preview = $("narrativePreview");
  const histBox = $("narrativeHistoryBox");
  const histCard = $("narrativeHistoryCard");

  const cardInner = `
    <div class="msg-head">
      <span class="who">你的补充说明 · 手动旁白</span>
      <button type="button" class="msg-del" data-action="del-narrative">删除</button>
    </div>
    <div class="msg-body">${escapeHtml(t)}</div>
  `;

  if (!has) {
    preview?.classList.add("hidden");
    histBox?.classList.add("hidden");
    return;
  }

  if (preview) {
    preview.className = "narrative-preview";
    preview.innerHTML = `
      <p class="preview-label">已保存的旁白（下方可继续编辑）</p>
      <div class="msg user_narrative-side">${cardInner}</div>
    `;
    preview.querySelector("[data-action=del-narrative]")?.addEventListener(
      "click",
      deleteUserNarrative
    );
  }

  if (histBox && histCard) {
    histBox.classList.remove("hidden");
    histCard.className = "msg user_narrative-side";
    histCard.innerHTML = cardInner;
    histCard
      .querySelector("[data-action=del-narrative]")
      ?.addEventListener("click", deleteUserNarrative);
  }
}

async function deleteUserNarrative() {
  if (!currentConvId) return;
  if (!confirm("确定删除手动旁白？删除后可重新填写并保存。")) return;
  try {
    await api(`/api/conversations/${currentConvId}/narrative`, {
      method: "DELETE",
    });
    $("userNarrative").value = "";
    $("narrativeStatus").textContent = "旁白已删除";
    renderUserNarrative("");
    await loadConversations();
  } catch (e) {
    alert(e.message);
  }
}

async function loadConversationDetail() {
  if (!currentConvId) return;
  const c = await api(`/api/conversations/${currentConvId}`);
  $("userNarrative").value = c.user_narrative || "";
  $("narrativeStatus").textContent = c.user_narrative
    ? "已保存旁白，生成画像/发送辅助时会使用"
    : "";
  renderUserNarrative(c.user_narrative);
}

async function selectConversation(id) {
  currentConvId = id;
  enableConvActions(true);
  await loadConversations();
  await Promise.all([
    loadConversationDetail(),
    loadMessages(),
    loadProfile(),
    loadPastAnalyses(),
  ]);
}

async function loadMessages() {
  const box = $("messageList");
  if (!currentConvId) return;
  const msgs = await api(`/api/conversations/${currentConvId}/messages`);
  if (!msgs.length) {
    box.className = "message-list empty-hint";
    box.textContent = "暂无记录，请在「导入与画像」中粘贴或上传";
    return;
  }
  box.className = "message-list";
  const roleLabel = (r) => {
    if (r === "me") return "我";
    if (r === "self_narrative") return "Ta 自述";
    return "Ta";
  };
  box.innerHTML = msgs
    .map(
      (m) => `
    <div class="msg ${m.role}" data-id="${m.id}">
      <div class="msg-head">
        <span class="who">${roleLabel(m.role)} · ${formatTime(m.created_at)}</span>
        <button type="button" class="msg-del" data-id="${m.id}" title="删除此条">删除</button>
      </div>
      <div class="msg-body">${escapeHtml(m.content)}</div>
    </div>`
    )
    .join("");
  box.querySelectorAll(".msg-del").forEach((btn) => {
    btn.onclick = async (e) => {
      e.stopPropagation();
      const id = parseInt(btn.dataset.id, 10);
      if (!confirm("确定删除这一条记录？")) return;
      await deleteOneMessage(id);
    };
  });
  box.scrollTop = box.scrollHeight;
}

async function deleteOneMessage(messageId) {
  if (!currentConvId) return;
  try {
    await api(
      `/api/conversations/${currentConvId}/messages/${messageId}`,
      { method: "DELETE" }
    );
    await loadMessages();
    await loadConversations();
    await loadProfile();
  } catch (e) {
    alert(e.message);
  }
}

async function clearMessages(scope, label) {
  if (!currentConvId) return;
  if (!confirm(`确定${label}？删除后无法恢复。`)) return;
  try {
    await api(`/api/conversations/${currentConvId}/messages/clear`, {
      method: "POST",
      body: JSON.stringify({ scope }),
    });
    await loadMessages();
    await loadConversations();
    await loadProfile();
  } catch (e) {
    alert(e.message);
  }
}

function renderProfile(p) {
  currentProfile = p;
  const box = $("profileBox");
  const banner = $("profileBanner");
  if (!p) {
    box.className = "profile-box empty-hint";
    box.textContent =
      "尚无画像。导入聊天记录后点击「AI 分析并生成画像」（至少 5 条，建议越多越好）";
    banner.classList.add("hidden");
    return;
  }

  const i = p.insights;
  const stale = p.is_stale
    ? '<p class="stale-warn">聊天记录已增加，建议重新生成画像以保持准确</p>'
    : "";

  box.className = "profile-box";
  box.innerHTML = `
    ${stale}
    <div class="profile-card highlight">${escapeHtml(i.reference_card || p.summary_compact)}</div>
    <div class="profile-grid">
      <div class="profile-card"><h4>Ta 是怎样的人</h4><p>${escapeHtml(i.friend_summary)}</p></div>
      <div class="profile-card"><h4>沟通风格</h4><p>${escapeHtml(i.communication_style)}</p></div>
      <div class="profile-card"><h4>冲突模式</h4><p>${escapeHtml(i.conflict_patterns)}</p></div>
    </div>
    ${listBlock("敏感触发点", i.triggers, "danger")}
    ${listBlock("对你有效的话术/做法", i.what_works, "ok")}
    ${listBlock("你容易踩雷的习惯", i.my_blind_spots, "warn")}
    ${listBlock("建议做", i.do_list, "ok")}
    ${listBlock("建议避免", i.dont_list, "danger")}
    ${phaseBlock(i.phase_signals)}
    <p class="meta">基于 ${p.message_count_at_build} 条记录 · 更新于 ${formatTime(p.updated_at)}</p>
  `;

  banner.classList.remove("hidden");
  banner.innerHTML = `<strong>画像已启用</strong> · ${escapeHtml((i.reference_card || "").slice(0, 120))}${(i.reference_card || "").length > 120 ? "…" : ""}`;
}

function listBlock(title, arr, cls) {
  if (!arr?.length) return "";
  return `<div class="profile-card ${cls}"><h4>${title}</h4><ul>${arr.map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul></div>`;
}

function phaseBlock(phase) {
  if (!phase || typeof phase !== "object") return "";
  const rows = Object.entries(phase)
    .map(([k, v]) => `<li><strong>${escapeHtml(k)}</strong> ${escapeHtml(v)}</li>`)
    .join("");
  return rows
    ? `<div class="profile-card"><h4>情绪阶段信号</h4><ul>${rows}</ul></div>`
    : "";
}

async function loadProfile() {
  if (!currentConvId) return;
  try {
    const p = await api(`/api/conversations/${currentConvId}/profile`);
    renderProfile(p);
  } catch {
    renderProfile(null);
  }
}

function renderAnalysis(data) {
  const rc = riskClass(data.anger_risk);
  const reasons = (data.anger_reasons || [])
    .map((r) => `<li>${escapeHtml(r)}</li>`)
    .join("");
  const pers = (data.personalized_reasons || [])
    .map((r) => `<li>${escapeHtml(r)}</li>`)
    .join("");
  const opts = (data.optimized_versions || [])
    .map(
      (o, i) => `
    <div class="opt-item">
      <div class="label">${escapeHtml(o.label || "方案" + (i + 1))}</div>
      <div class="text">${escapeHtml(o.text)}</div>
      <button type="button" class="btn btn-secondary btn-sm" data-copy="${i}">复制</button>
    </div>`
    )
    .join("");

  const el = $("analysisResult");
  el.className = "analysis-result";
  el.innerHTML = `
    ${!data.used_profile ? '<p class="stale-warn">尚未建立画像或旁白，分析仅基于近期对话。建议先填写旁白或生成画像。</p>' : ""}
    <div class="risk-card">
      <div class="risk-ring ${rc}">${data.anger_risk}</div>
      <div class="risk-detail">
        <h3>激怒风险：${escapeHtml(data.anger_level)}</h3>
        <p class="muted">以 Ta 的画像为主${data.used_profile ? "" : "（建议先生成画像）"}，参考材料为均匀节选</p>
      </div>
    </div>
    ${pers ? `<div class="profile-card warn"><h4>结合 Ta 的画像</h4><ul class="reasons">${pers}</ul></div>` : ""}
    ${reasons ? `<ul class="reasons">${reasons}</ul>` : ""}
    ${data.profile_tip ? `<div class="advice"><strong>画像提醒：</strong>${escapeHtml(data.profile_tip)}</div>` : ""}
    <div class="optimized-block"><strong>优化文案</strong>${opts}</div>
    ${data.advice ? `<div class="advice"><strong>建议：</strong>${escapeHtml(data.advice)}</div>` : ""}
  `;

  el.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.onclick = () => {
      const i = parseInt(btn.dataset.copy, 10);
      const text = data.optimized_versions[i]?.text;
      if (text) navigator.clipboard.writeText(text);
      btn.textContent = "已复制";
    };
  });
}

async function loadPastAnalyses() {
  const box = $("pastAnalyses");
  if (!currentConvId) return;
  const rows = await api(`/api/conversations/${currentConvId}/analyses`);
  if (!rows.length) {
    box.className = "past-list empty-hint";
    box.textContent = "暂无";
    return;
  }
  box.className = "past-list";
  box.innerHTML = rows
    .map(
      (a) => `
    <div class="past-item">
      <div class="meta">${formatTime(a.created_at)} · 风险 ${a.anger_risk}（${escapeHtml(a.anger_level)}）</div>
      <div class="draft">${escapeHtml(a.draft_text)}</div>
      ${a.personalized_reasons?.length ? `<div class="meta">画像：${escapeHtml(a.personalized_reasons.join("；"))}</div>` : ""}
    </div>`
    )
    .join("");
}

$("btnNewConv").onclick = async () => {
  const title = prompt("对话本名称", "与 Ta 的对话");
  if (title === null) return;
  const c = await api("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ title: title || "与 Ta 的对话" }),
  });
  await selectConversation(c.id);
};

$("btnDeleteConv").onclick = () => {
  if (!currentConvId) return;
  const item = document.querySelector(".conv-item.active .title");
  deleteConversation(currentConvId, item?.textContent || "");
};

$("btnSaveNarrative").onclick = async () => {
  if (!currentConvId) return;
  const text = $("userNarrative").value;
  try {
    const c = await api(`/api/conversations/${currentConvId}/narrative`, {
      method: "PATCH",
      body: JSON.stringify({ user_narrative: text }),
    });
    $("narrativeStatus").textContent = text.trim()
      ? "旁白已保存"
      : "旁白已清空";
    renderUserNarrative(c.user_narrative);
    await loadConversations();
  } catch (e) {
    alert(e.message);
  }
};

$("btnDeleteNarrative").onclick = deleteUserNarrative;

$("btnImportSelf").onclick = async () => {
  const text = $("importSelfText").value.trim();
  if (!text || !currentConvId) return;
  $("importSelfStatus").textContent = "导入中…";
  try {
    const r = await api(
      `/api/conversations/${currentConvId}/import-self-narrative`,
      {
        method: "POST",
        body: JSON.stringify({
          text,
          clear_existing_self: $("importSelfClear").checked,
        }),
      }
    );
    $("importSelfStatus").textContent = `已导入 ${r.imported} 段自述，当前共 ${r.self_narrative_total} 段`;
    $("importSelfText").value = "";
    await loadMessages();
    await loadConversations();
    await loadProfile();
  } catch (e) {
    $("importSelfStatus").textContent = e.message;
    alert(e.message);
  }
};

$("btnImport").onclick = async () => {
  const text = $("importText").value.trim();
  if (!text || !currentConvId) return;
  $("importStatus").textContent = "导入中…";
  try {
    const r = await api(`/api/conversations/${currentConvId}/import`, {
      method: "POST",
      body: JSON.stringify({
        text,
        friend_nickname: $("friendNick").value.trim() || null,
        clear_existing: $("importClear").checked,
      }),
    });
    $("importStatus").textContent = `已导入 ${r.imported} 条，当前共 ${r.total_messages} 条`;
    $("importText").value = "";
    await loadMessages();
    await loadConversations();
    await loadProfile();
  } catch (e) {
    $("importStatus").textContent = e.message;
    alert(e.message);
  }
};

$("importFile").onchange = async (ev) => {
  const file = ev.target.files?.[0];
  if (!file || !currentConvId) return;
  const fd = new FormData();
  fd.append("file", file);
  if ($("friendNick").value.trim()) {
    fd.append("friend_nickname", $("friendNick").value.trim());
  }
  fd.append("clear_existing", $("importClear").checked ? "true" : "false");
  $("importStatus").textContent = "上传解析中…";
  try {
    const res = await fetch(
      `/api/conversations/${currentConvId}/import-file`,
      { method: "POST", body: fd }
    );
    const r = await res.json();
    if (!res.ok) throw new Error(r.detail || "上传失败");
    $("importStatus").textContent = `已导入 ${r.imported} 条，共 ${r.total_messages} 条`;
    await loadMessages();
    await loadConversations();
    await loadProfile();
  } catch (e) {
    $("importStatus").textContent = e.message;
    alert(e.message);
  }
  ev.target.value = "";
};

$("btnClearDialogue").onclick = () =>
  clearMessages("dialogue", "清空所有对话记录（保留自述）");
$("btnClearSelf").onclick = () =>
  clearMessages("self_narrative", "清空所有 Ta 自述（保留对话）");
$("btnClearAllMsgs").onclick = () =>
  clearMessages("all", "清空本对话本中的全部导入记录");

$("btnDeleteProfile").onclick = async () => {
  if (!currentConvId) return;
  if (!confirm("确定删除当前画像？聊天记录与旁白会保留，可重新生成画像。")) return;
  try {
    await api(`/api/conversations/${currentConvId}/profile`, {
      method: "DELETE",
    });
    renderProfile(null);
    await loadConversations();
    alert("画像已删除");
  } catch (e) {
    alert(e.message);
  }
};

$("btnBuildProfile").onclick = async () => {
  if (!currentConvId) return;
  if (!confirm("将调用 DeepSeek 分析全部聊天记录，记录较多时可能需要 1–3 分钟，继续？")) {
    return;
  }
  const box = $("profileBox");
  box.className = "profile-box";
  box.textContent = "AI 正在分析提炼画像，请稍候…";
  $("btnBuildProfile").disabled = true;
  try {
    const p = await api(
      `/api/conversations/${currentConvId}/profile/build`,
      { method: "POST" }
    );
    renderProfile(p);
    await loadConversations();
    alert("画像已生成！之后「发送辅助」将自动引用。");
  } catch (e) {
    box.textContent = e.message;
    alert(e.message);
  } finally {
    $("btnBuildProfile").disabled = false;
  }
};

$("logForm").onsubmit = async (e) => {
  e.preventDefault();
  if (!currentConvId) return;
  const content = $("logContent").value.trim();
  if (!content) return;
  await api(`/api/conversations/${currentConvId}/messages`, {
    method: "POST",
    body: JSON.stringify({ role: $("logRole").value, content }),
  });
  $("logContent").value = "";
  await loadMessages();
  await loadConversations();
  await loadProfile();
};

$("btnAnalyze").onclick = async () => {
  if (!currentConvId) return;
  const draft = $("draftInput").value.trim();
  if (!draft) {
    alert("请填写草稿");
    return;
  }
  const panel = document.querySelector(".compose-panel");
  panel.classList.add("loading");
  $("btnAnalyze").disabled = true;
  try {
    const data = await api(`/api/conversations/${currentConvId}/analyze`, {
      method: "POST",
      body: JSON.stringify({
        draft,
        intent: $("intentInput").value.trim() || null,
      }),
    });
    renderAnalysis(data);
    setTab("assist");
    await loadPastAnalyses();
  } catch (e) {
    alert(e.message);
  } finally {
    panel.classList.remove("loading");
    $("btnAnalyze").disabled = false;
  }
};

checkHealth();
loadConversations();
enableConvActions(false);
