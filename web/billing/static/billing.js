(function () {
  const API = window.location.pathname.replace(/\/?$/, "") + "/api";
  let plans = [];
  let me = null;
  let authMode = "login";

  async function api(path, opts = {}) {
    const res = await fetch(API + path, {
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
      ...opts,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
    return data;
  }

  function toast(msg) {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.classList.remove("hidden");
    setTimeout(() => el.classList.add("hidden"), 3200);
  }

  function featureList(p) {
    const items = [
      `每日 ${p.search_queries_per_day} 次搜索`,
      `最多 ${p.max_watches} 条监控`,
      p.matrix_enabled ? "价格矩阵" : null,
      p.exhaustive_enabled ? "全量穷举" : "精简穷举",
      p.duration_days ? `${p.duration_days} 天有效` : "永久有效",
    ].filter(Boolean);
    return items.map((t) => `<li>${t}</li>`).join("");
  }

  function renderPlans() {
    const grid = document.getElementById("plansGrid");
    grid.innerHTML = plans
      .map((p) => {
        const isTrial = p.id === "free_trial";
        const price = isTrial ? "免费" : p.price_display;
        const btn = isTrial
          ? `<button type="button" class="btn btn-primary plan-btn" data-action="register">注册试用</button>`
          : `<button type="button" class="btn btn-primary plan-btn" data-plan="${p.id}">立即订阅</button>`;
        return `
          <article class="plan-card ${p.highlight ? "highlight" : ""}">
            <div class="plan-name">${p.name}</div>
            <div class="plan-price">${price}</div>
            <p class="plan-tagline">${p.tagline}</p>
            <ul class="plan-features">${featureList(p)}</ul>
            ${btn}
          </article>`;
      })
      .join("");
    grid.querySelectorAll(".plan-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (btn.dataset.action === "register") openAuth("register");
        else checkout(btn.dataset.plan);
      });
    });
  }

  function renderAccount() {
    const banner = document.getElementById("accountBanner");
    const authArea = document.getElementById("authArea");
    if (!me || !me.authenticated) {
      banner.classList.add("hidden");
      authArea.innerHTML = `
        <button type="button" class="btn btn-ghost" id="btnLogin">登录</button>
        <button type="button" class="btn btn-primary" id="btnRegister">注册试用</button>`;
      document.getElementById("btnLogin").onclick = () => openAuth("login");
      document.getElementById("btnRegister").onclick = () => openAuth("register");
      return;
    }
    const ent = me.entitlements || {};
    const planName = ent.plan_name || ent.plan || "无有效套餐";
    const usage = ent.search_usage_today ?? 0;
    const limit = ent.search_queries_per_day ?? "—";
    banner.classList.remove("hidden");
    banner.innerHTML = `
      当前账户：<strong>${me.user.email}</strong> · 套餐：<strong>${planName}</strong>
      · 今日搜索 <strong>${usage}/${limit}</strong>
      ${ent.expires_at ? ` · 到期 ${new Date(ent.expires_at).toLocaleDateString("zh-CN")}` : ""}
      <button type="button" class="btn btn-ghost btn-sm" id="btnLogout" style="margin-left:8px">退出</button>`;
    document.getElementById("btnLogout").onclick = logout;
    authArea.innerHTML = `<span class="user-chip">${me.user.email}</span>`;
  }

  function openAuth(mode) {
    authMode = mode;
    document.getElementById("authTitle").textContent = mode === "register" ? "注册 · 免费试用" : "登录";
    document.getElementById("authHint").textContent =
      mode === "register" ? "注册后自动开通 7 天免费试用" : "";
    document.getElementById("authDialog").showModal();
  }

  async function logout() {
    await api("/auth/logout", { method: "POST" });
    me = null;
    renderAccount();
    toast("已退出登录");
  }

  async function checkout(planId) {
    if (!me || !me.authenticated) {
      openAuth("login");
      toast("请先登录后再订阅");
      return;
    }
    try {
      const data = await api("/checkout", {
        method: "POST",
        body: JSON.stringify({ plan_id: planId }),
      });
      if (data.checkout_url) window.location.href = data.checkout_url;
    } catch (e) {
      toast(e.message || "创建订单失败");
    }
  }

  async function refresh() {
    const [planData, meData] = await Promise.all([
      api("/plans"),
      api("/me").catch(() => ({ authenticated: false })),
    ]);
    plans = planData.plans || [];
    me = meData;
    renderPlans();
    renderAccount();
  }

  document.getElementById("authForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("authEmail").value.trim();
    const password = document.getElementById("authPassword").value;
    const path = authMode === "register" ? "/auth/register" : "/auth/login";
    try {
      await api(path, { method: "POST", body: JSON.stringify({ email, password }) });
      document.getElementById("authDialog").close();
      toast(authMode === "register" ? "注册成功，已开通免费试用" : "登录成功");
      await refresh();
    } catch (err) {
      document.getElementById("authHint").textContent = err.message || "失败";
    }
  });

  document.getElementById("authCancel").onclick = () => document.getElementById("authDialog").close();
  document.getElementById("btnLogin")?.addEventListener("click", () => openAuth("login"));
  document.getElementById("btnRegister")?.addEventListener("click", () => openAuth("register"));

  const params = new URLSearchParams(location.search);
  if (params.get("checkout") === "success") toast("支付成功，会员已生效");
  if (params.get("checkout") === "cancel") toast("已取消支付");

  refresh().catch((e) => toast(e.message || "加载失败"));
})();
