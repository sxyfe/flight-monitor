const { createApp, ref, reactive, computed, onMounted, watch } = Vue;

const TRIP_LABELS = {
  round_trip: "往返",
  one_way: "单程",
  multi_leg: "多段",
  open_jaw: "开口程",
};

function todayIsoDate() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const emptyWatch = () => ({
  name: "",
  enabled: true,
  trip_mode: "open_jaw",
  legs: [
    { from_city: "PVG", to_city: "LAX", date: "" },
    { from_city: "LAX", to_city: "NRT", date: "" },
  ],
  return_date: "",
  pricing_mode: "auto",
  sales_region: "CN",
  currency: "CNY",
  filters: { carriers: [], cabin: "ECONOMY" },
  alerts: { max_price: 4000, drop_abs: 200, drop_pct: 5, cooldown_hours: 24 },
  schedule: { interval_hours: 12, active_until: "" },
  notes: "",
});

createApp({
  setup() {
    const tab = ref("list");
    const watches = ref([]);
    const presets = ref([]);
    const snapshots = ref([]);
    const selectedId = ref(null);
    const form = reactive(emptyWatch());
    const editingId = ref(null);
    const loading = ref(false);
    const message = ref("");
    const error = ref("");

    const config = reactive({
      rollinggo: { base_url: "https://mcp.rollinggo.cn", api_key: "" },
      notify: { feishu_webhook: "", pushplus_token: "" },
    });
    const showRgKey = ref(false);
    const showPushplus = ref(false);
    const status = reactive({
      rollinggo_configured: false,
      feishu_configured: false,
      pushplus_configured: false,
    });
    const listFilter = ref("all");
    const listSort = ref("updated");
    const presetPreview = ref(null);
    const showAdvancedAlerts = ref(false);
    const minDate = todayIsoDate();

    const filteredWatches = computed(() => {
      let rows = [...watches.value];
      if (listFilter.value === "enabled") rows = rows.filter((w) => w.enabled);
      if (listFilter.value === "disabled") rows = rows.filter((w) => !w.enabled);
      rows.sort((a, b) => {
        if (listSort.value === "name") return (a.name || "").localeCompare(b.name || "", "zh");
        if (listSort.value === "price") {
          const pa = a.latest_snapshot?.price ?? Infinity;
          const pb = b.latest_snapshot?.price ?? Infinity;
          return pa - pb;
        }
        const ta = a.latest_snapshot?.checked_at || a.updated_at || "";
        const tb = b.latest_snapshot?.checked_at || b.updated_at || "";
        return tb.localeCompare(ta);
      });
      return rows;
    });

    const enabledCount = computed(() => watches.value.filter((w) => w.enabled).length);
    const importedPresetIds = computed(() => {
      const names = new Set(watches.value.map((w) => w.name));
      return new Set(presets.value.filter((p) => names.has(p.name)).map((p) => p.id));
    });

    function tripLabel(mode) {
      return TRIP_LABELS[mode] || mode;
    }

    function formatLegs(w) {
      return (w.legs || [])
        .map((l) => `${l.from_city}→${l.to_city}${l.date ? " " + l.date : ""}`)
        .join(" · ");
    }

    function priceStatus(w) {
      const p = w.latest_snapshot?.price;
      const max = w.alerts?.max_price;
      if (p == null || max == null) return "";
      return p <= max ? "hit" : "above";
    }

    function priceStatusText(w) {
      const s = priceStatus(w);
      if (s === "hit") return "已低于限价";
      if (s === "above") return "高于限价";
      return "待查价";
    }

    const carriersStr = computed({
      get: () => (form.filters.carriers || []).join(","),
      set: (v) => {
        form.filters.carriers = v.split(/[,，\s]+/).filter(Boolean).map((x) => x.toUpperCase());
      },
    });

    const API_BASE = (() => {
      const m = location.pathname.match(/^(.*\/flight-watch)\/?/);
      return m ? m[1] : "";
    })();

    async function api(path, opts = {}) {
      const res = await fetch(`${API_BASE}${path}`, {
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        ...opts,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail;
        const msg =
          typeof detail === "object" && detail?.message
            ? detail.message
            : typeof detail === "string"
              ? detail
              : data.message || res.statusText;
        const err = new Error(msg);
        err.code = typeof detail === "object" ? detail.code : undefined;
        throw err;
      }
      return data;
    }

    async function loadWatches() {
      const data = await api("/api/watches");
      watches.value = data.items || [];
    }

    async function loadPresets() {
      const data = await api("/api/presets");
      presets.value = data.items || [];
    }

    async function loadConfig() {
      const cfg = await api("/api/config");
      Object.assign(config, cfg);
      const st = await api("/api/config/status");
      Object.assign(status, st);
    }

    async function saveConfig() {
      await api("/api/config", { method: "POST", body: JSON.stringify(config) });
      message.value = "设置已保存";
      await loadConfig();
    }

    function resetForm() {
      Object.assign(form, emptyWatch());
      editingId.value = null;
    }

    function editWatch(w) {
      editingId.value = w.id;
      Object.assign(form, {
        name: w.name,
        enabled: w.enabled,
        trip_mode: w.trip_mode,
        legs: JSON.parse(JSON.stringify(w.legs)),
        return_date: w.return_date || "",
        pricing_mode: w.pricing_mode || "auto",
        sales_region: w.sales_region || "",
        currency: w.currency || "CNY",
        filters: w.filters || { carriers: [], cabin: "ECONOMY" },
        alerts: w.alerts,
        schedule: w.schedule,
        notes: w.notes || "",
      });
      tab.value = "edit";
    }

    async function saveWatch() {
      loading.value = true;
      error.value = "";
      try {
        const payload = JSON.parse(JSON.stringify(form));
        if (payload.trip_mode === "round_trip" && payload.legs.length > 1) {
          payload.legs = [payload.legs[0]];
        }
        if (payload.trip_mode === "one_way") {
          payload.legs = [payload.legs[0]];
        }
        if (editingId.value) {
          await api(`/api/watches/${editingId.value}`, {
            method: "PUT",
            body: JSON.stringify(payload),
          });
        } else {
          await api("/api/watches", { method: "POST", body: JSON.stringify(payload) });
        }
        message.value = "监控已保存";
        resetForm();
        tab.value = "list";
        await loadWatches();
      } catch (e) {
        error.value = String(e.message || e);
      } finally {
        loading.value = false;
      }
    }

    async function deleteWatch(id) {
      if (!confirm("确定删除该监控？")) return;
      await api(`/api/watches/${id}`, { method: "DELETE" });
      await loadWatches();
    }

    async function toggleWatch(w) {
      await api(`/api/watches/${w.id}/enable?enabled=${!w.enabled}`, { method: "POST" });
      await loadWatches();
    }

    async function pollWatch(id, dry = false) {
      loading.value = true;
      error.value = "";
      try {
        const data = await api(`/api/watches/${id}/poll?dry_run=${dry}`, { method: "POST" });
        message.value = data.poll?.ok
          ? `查价完成：${data.poll.currency || ""} ${data.poll.price}${data.poll.notified ? "（已通知）" : ""}`
          : `查价失败：${data.poll?.error || "未知"}`;
        await loadWatches();
        if (selectedId.value === id) await loadSnapshots(id);
      } catch (e) {
        error.value = String(e.message || e);
      } finally {
        loading.value = false;
      }
    }

    async function loadSnapshots(id) {
      selectedId.value = id;
      const data = await api(`/api/watches/${id}/snapshots`);
      snapshots.value = data.items || [];
      tab.value = "history";
    }

    async function importPreset(id, goEdit = false) {
      loading.value = true;
      error.value = "";
      try {
        const data = await api(`/api/presets/${id}/import`, { method: "POST" });
        message.value = goEdit
          ? "预设已导入，请补全日期后启用"
          : "预设已导入（默认未启用，可在列表编辑）";
        presetPreview.value = null;
        tab.value = goEdit ? "edit" : "list";
        await loadWatches();
        if (goEdit && data.id) editWatch(data);
      } catch (e) {
        error.value = String(e.message || e);
      } finally {
        loading.value = false;
      }
    }

    async function importAllPresets() {
      if (!confirm(`确定导入全部 ${presets.value.length} 条达美开口预设？（默认均未启用）`)) return;
      loading.value = true;
      error.value = "";
      try {
        const data = await api("/api/presets/import-all", { method: "POST" });
        message.value = `已导入 ${data.count || 0} 条预设，请逐条补日期并启用`;
        tab.value = "list";
        await loadWatches();
      } catch (e) {
        error.value = String(e.message || e);
      } finally {
        loading.value = false;
      }
    }

    function openPresetPreview(p) {
      presetPreview.value = p;
    }

    function closePresetPreview() {
      presetPreview.value = null;
    }

    function siteHref(path) {
      const p = path.startsWith("/") ? path : `/${path}`;
      const m = location.pathname.match(/^(.*\/flight-watch)\/?/);
      const prefix = m ? m[1].replace(/\/flight-watch\/?$/, "") : "";
      return `${prefix}${p}`;
    }

    function addLeg() {
      form.legs.push({ from_city: "", to_city: "", date: "" });
    }

    function removeLeg(i) {
      if (form.legs.length > 1) form.legs.splice(i, 1);
    }

    function setupAirportInput(inputEl, leg, field) {
      if (!inputEl) return;
      let dd = null;
      let timer = null;
      inputEl.addEventListener("input", () => {
        clearTimeout(timer);
        timer = setTimeout(async () => {
          const q = inputEl.value.trim();
          if (q.length < 2) return;
          try {
            const data = await api(`/api/airports/search?q=${encodeURIComponent(q)}`);
            if (dd) dd.remove();
            dd = document.createElement("div");
            dd.className = "airport-dd";
            const items = (data.items || []).slice(0, 8);
            if (!items.length) {
              const empty = document.createElement("div");
              empty.className = "airport-dd-empty";
              empty.textContent = "未搜索到机场";
              dd.appendChild(empty);
            } else {
              items.forEach((item) => {
                const row = document.createElement("div");
                const code = item.airportCode || item.cityCode;
                row.textContent = `${item.cityName || ""} ${item.airportName || ""} (${code})`;
                row.onclick = () => {
                  leg[field] = code;
                  inputEl.value = `${item.cityName || code} (${code})`;
                  dd.remove();
                  dd = null;
                };
                dd.appendChild(row);
              });
            }
            inputEl.parentElement.appendChild(dd);
          } catch (_) {}
        }, 300);
      });
    }

    onMounted(async () => {
      try {
        await loadConfig();
        await loadWatches();
        await loadPresets();
      } catch (e) {
        error.value = String(e.message || e);
      }
    });

    watch(
      () => form.trip_mode,
      (mode) => {
        if (mode === "one_way" || mode === "round_trip") {
          form.legs = [form.legs[0] || { from_city: "", to_city: "", date: "" }];
        } else if (form.legs.length < 2) {
          form.legs.push({ from_city: "", to_city: "", date: "" });
        }
      }
    );

    async function testRollingGo() {
      error.value = "";
      message.value = "";
      try {
        await saveConfig();
        const r = await api("/api/config/test-rollinggo", { method: "POST" });
        message.value = r.message || "RollingGo 连接成功";
      } catch (e) {
        error.value = String(e.message || e);
      }
    }

    async function testNotify(path) {
      error.value = "";
      message.value = "";
      try {
        await saveConfig();
        const r = await api(path, { method: "POST" });
        message.value = r.message || "成功";
      } catch (e) {
        error.value = String(e.message || e);
      }
    }

    return {
      tab,
      watches,
      presets,
      snapshots,
      selectedId,
      form,
      editingId,
      loading,
      message,
      error,
      config,
      showRgKey,
      showPushplus,
      status,
      listFilter,
      listSort,
      presetPreview,
      showAdvancedAlerts,
      minDate,
      filteredWatches,
      enabledCount,
      importedPresetIds,
      tripLabel,
      formatLegs,
      priceStatus,
      priceStatusText,
      carriersStr,
      loadWatches,
      saveConfig,
      resetForm,
      editWatch,
      saveWatch,
      deleteWatch,
      toggleWatch,
      pollWatch,
      loadSnapshots,
      importPreset,
      importAllPresets,
      openPresetPreview,
      closePresetPreview,
      siteHref,
      addLeg,
      removeLeg,
      setupAirportInput,
      testRollingGo,
      testNotify,
    };
  },
  template: `
  <header>
    <h1>Flight <span>Watch</span> · 机票监控</h1>
    <div class="header-right">
      <nav class="header-nav" aria-label="站点导航">
        <a :href="siteHref('/')">首页</a>
        <a :href="siteHref('/nl-search/')">查价</a>
        <span class="header-nav-active">监控</span>
      </nav>
      <span class="muted">Web · 飞书/微信通知</span>
    </div>
  </header>
  <div class="wrap">
    <div class="tabs">
      <button class="tab-btn" :class="{active: tab==='list'}" @click="tab='list'">监控列表</button>
      <button class="tab-btn" :class="{active: tab==='edit'}" @click="tab='edit'; if(!editingId) resetForm()">新建/编辑</button>
      <button class="tab-btn" :class="{active: tab==='presets'}" @click="tab='presets'">预设库</button>
      <button class="tab-btn" :class="{active: tab==='history'}" @click="tab='history'">历史</button>
      <button class="tab-btn" :class="{active: tab==='settings'}" @click="tab='settings'">设置</button>
    </div>

    <p v-if="message" class="card muted">{{ message }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="tab==='list'" class="card">
      <div class="list-toolbar">
        <h2>我的监控 <span class="count-badge">{{ watches.length }}</span></h2>
        <div class="list-toolbar-actions">
          <button class="btn btn-primary btn-sm" @click="tab='edit'; resetForm()">+ 新建</button>
          <button class="btn btn-ghost btn-sm" @click="tab='presets'">从预设导入</button>
        </div>
      </div>
      <div class="list-filters">
        <select v-model="listFilter" class="list-select" aria-label="筛选">
          <option value="all">全部 ({{ watches.length }})</option>
          <option value="enabled">已启用 ({{ enabledCount }})</option>
          <option value="disabled">未启用 ({{ watches.length - enabledCount }})</option>
        </select>
        <select v-model="listSort" class="list-select" aria-label="排序">
          <option value="updated">最近查价</option>
          <option value="price">当前价格</option>
          <option value="name">名称</option>
        </select>
      </div>
      <div v-if="!filteredWatches.length" class="empty-state">
        <p>暂无监控</p>
        <p class="muted">从<strong>预设库</strong>一键导入达美开口方案，或新建自定义规则。</p>
        <button class="btn btn-secondary btn-sm" @click="tab='presets'">浏览预设库</button>
      </div>
      <article v-for="w in filteredWatches" :key="w.id" class="watch-card" :class="{ 'is-disabled': !w.enabled }">
        <div class="watch-card-main">
          <div class="watch-card-head">
            <strong>{{ w.name }}</strong>
            <span class="status-pill" :class="w.enabled ? 'on' : 'off'">{{ w.enabled ? '监控中' : '已暂停' }}</span>
            <span class="status-pill trip">{{ tripLabel(w.trip_mode) }}</span>
            <span v-if="priceStatus(w)==='hit'" class="status-pill hit">{{ priceStatusText(w) }}</span>
          </div>
          <p class="watch-meta">{{ formatLegs(w) }}</p>
          <p class="watch-meta" v-if="w.latest_snapshot">
            最近 ¥{{ Math.round(w.latest_snapshot.price).toLocaleString() }}
            <span class="muted">/ 限价 ¥{{ w.alerts.max_price }}</span>
            · {{ w.latest_snapshot.checked_at?.slice(0, 16) || '—' }}
            <span v-if="w.latest_snapshot.bookable" class="tag">同票</span>
          </p>
          <p class="watch-meta muted" v-else>尚未查价 · 每 {{ w.schedule.interval_hours }}h 轮询</p>
        </div>
        <div class="watch-card-actions">
          <label class="toggle"><input type="checkbox" :checked="w.enabled" @change="toggleWatch(w)" /> 启用</label>
          <button class="btn btn-secondary btn-sm" @click="pollWatch(w.id)">查价</button>
          <button class="btn btn-ghost btn-sm" @click="editWatch(w)">编辑</button>
          <button class="btn btn-ghost btn-sm" @click="loadSnapshots(w.id)">历史</button>
          <button class="btn btn-ghost btn-sm danger" @click="deleteWatch(w.id)">删除</button>
        </div>
      </article>
    </div>

    <div v-if="tab==='edit'" class="card">
      <h2>{{ editingId ? '编辑监控' : '新建监控' }}</h2>
      <div class="field"><label>名称</label><input v-model="form.name" placeholder="例如：达美开口 上海-美国-东京" /></div>
      <div class="grid2">
        <div class="field">
          <label>行程类型</label>
          <select v-model="form.trip_mode">
            <option value="round_trip">往返</option>
            <option value="one_way">单程</option>
            <option value="multi_leg">多段</option>
            <option value="open_jaw">开口程</option>
          </select>
        </div>
        <div class="field">
          <label>查价模式</label>
          <select v-model="form.pricing_mode">
            <option value="auto">自动（同票优先）</option>
            <option value="same_ticket">强制同票 swoop</option>
            <option value="split_one_way">仅分段相加</option>
          </select>
        </div>
      </div>
      <div v-if="form.trip_mode==='round_trip'" class="field">
        <label>回程日期</label><input type="date" v-model="form.return_date" :min="form.legs[0]?.date || minDate" />
      </div>
      <div v-for="(leg, i) in form.legs" :key="i" class="leg-block">
        <strong>航段 {{ i+1 }}</strong>
        <div class="grid2" style="margin-top:8px">
          <div class="field rel">
            <label>出发</label>
            <input :value="leg.from_city" @input="leg.from_city = $event.target.value.toUpperCase()" placeholder="PVG 或搜索" :ref="el => setupAirportInput(el, leg, 'from_city')" />
          </div>
          <div class="field rel">
            <label>到达</label>
            <input :value="leg.to_city" @input="leg.to_city = $event.target.value.toUpperCase()" placeholder="LAX" :ref="el => setupAirportInput(el, leg, 'to_city')" />
          </div>
        </div>
        <div class="field"><label>日期</label><input type="date" v-model="leg.date" :min="minDate" /></div>
        <button v-if="form.legs.length>1 && form.trip_mode!=='one_way' && form.trip_mode!=='round_trip'" class="btn btn-ghost btn-sm" @click="removeLeg(i)">删除航段</button>
      </div>
      <button v-if="form.trip_mode==='multi_leg' || form.trip_mode==='open_jaw'" class="btn btn-ghost btn-sm" @click="addLeg">+ 添加航段</button>
      <div class="grid2" style="margin-top:12px">
        <div class="field"><label>限价 ({{ form.currency }})</label><input type="number" v-model.number="form.alerts.max_price" /></div>
        <div class="field"><label>轮询间隔（小时）</label><input type="number" v-model.number="form.schedule.interval_hours" min="1" /></div>
        <div class="field"><label>销售区 ISO（如 CN/US/NL）</label><input v-model="form.sales_region" placeholder="CN" /></div>
        <div class="field"><label>航司过滤（逗号分隔）</label><input v-model="carriersStr" placeholder="DL,UA" /></div>
      </div>
      <div class="advanced-block">
        <button type="button" class="btn btn-ghost btn-sm advanced-toggle" @click="showAdvancedAlerts = !showAdvancedAlerts">
          {{ showAdvancedAlerts ? '收起高级告警' : '高级告警设置' }}
        </button>
        <div v-show="showAdvancedAlerts" class="advanced-panel grid2">
          <div class="field"><label>降价金额阈值 ({{ form.currency }})</label><input type="number" v-model.number="form.alerts.drop_abs" min="0" /></div>
          <div class="field"><label>降价百分比阈值 (%)</label><input type="number" v-model.number="form.alerts.drop_pct" min="0" max="100" step="0.1" /></div>
          <div class="field"><label>通知冷却（小时）</label><input type="number" v-model.number="form.alerts.cooldown_hours" min="1" /></div>
          <div class="field"><label>监控截止日期</label><input type="date" v-model="form.schedule.active_until" :min="minDate" /></div>
        </div>
      </div>
      <div class="field"><label>备注</label><textarea v-model="form.notes" rows="2"></textarea></div>
      <button class="btn btn-primary" :disabled="loading" @click="saveWatch">保存</button>
    </div>

    <div v-if="tab==='presets'" class="card">
      <div class="list-toolbar">
        <h2>预设库 · 达美开口（{{ presets.length }} 条）</h2>
        <button class="btn btn-secondary btn-sm" :disabled="loading || !presets.length" @click="importAllPresets">全部导入</button>
      </div>
      <p class="muted">导入后默认<strong>未启用</strong>，需补全航段日期并设置限价后再开启监控。</p>
      <article v-for="p in presets" :key="p.id" class="preset-card">
        <div>
          <strong>{{ p.name }}</strong>
          <span v-if="importedPresetIds.has(p.id)" class="status-pill imported">已导入</span>
          <div class="watch-meta">参考 ¥{{ p.reference_price }} · {{ p.legs.map(l=>l.from_city+'→'+l.to_city).join(' / ') }}</div>
          <div v-if="p.notes" class="watch-meta">{{ p.notes }}</div>
        </div>
        <div class="preset-actions">
          <button class="btn btn-ghost btn-sm" @click="openPresetPreview(p)">预览</button>
          <button class="btn btn-secondary btn-sm" @click="importPreset(p.id, true)">导入并编辑</button>
        </div>
      </article>
    </div>

    <div v-if="presetPreview" class="modal-backdrop" @click.self="closePresetPreview">
      <div class="modal-card">
        <h3>{{ presetPreview.name }}</h3>
        <p class="watch-meta">参考价 ¥{{ presetPreview.reference_price }} · {{ tripLabel(presetPreview.trip_mode) }}</p>
        <ul class="preset-leg-list">
          <li v-for="(leg, i) in presetPreview.legs" :key="i">航段 {{ i+1 }}：{{ leg.from_city }} → {{ leg.to_city }}<span v-if="leg.date"> · {{ leg.date }}</span></li>
        </ul>
        <p v-if="presetPreview.notes" class="muted">{{ presetPreview.notes }}</p>
        <div class="modal-actions">
          <button class="btn btn-ghost btn-sm" @click="closePresetPreview">关闭</button>
          <button class="btn btn-primary btn-sm" @click="importPreset(presetPreview.id, true)">导入并编辑</button>
        </div>
      </div>
    </div>

    <div v-if="tab==='history'" class="card">
      <h2>查价历史 <span class="muted" style="font-weight:400">{{ selectedId || '' }}</span></h2>
      <div v-if="!snapshots.length" class="muted">选择监控后查看历史快照。</div>
      <div v-else class="history-scroll">
        <table class="history-table">
          <thead>
            <tr><th>时间</th><th>价格</th><th>Provider</th><th>可订</th></tr>
          </thead>
          <tbody>
            <tr v-for="s in snapshots" :key="s.id">
              <td>{{ s.checked_at }}</td>
              <td>{{ s.currency }} {{ s.price ?? '—' }}</td>
              <td>{{ s.provider }}</td>
              <td>{{ s.bookable ? '是' : '否' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="tab==='settings'" class="card">
      <h2>设置</h2>
      <p class="muted">凭据仅保存在本机，不会上传。</p>
      <div class="notify-status-row">
        <span class="status-pill" :class="status.rollinggo_configured ? 'on' : 'off'">RollingGo：{{ status.rollinggo_configured ? '已配置' : '未配置' }}</span>
        <span class="status-pill" :class="status.feishu_configured ? 'on' : 'off'">飞书：{{ status.feishu_configured ? '已配置' : '未配置' }}</span>
        <span class="status-pill" :class="status.pushplus_configured ? 'on' : 'off'">微信：{{ status.pushplus_configured ? '已配置' : '未配置' }}</span>
      </div>
      <div class="field"><label>RollingGo Base URL</label><input v-model="config.rollinggo.base_url" /></div>
      <div class="field">
        <label>RollingGo API Key</label>
        <input :type="showRgKey ? 'text' : 'password'" v-model="config.rollinggo.api_key" />
        <button class="btn btn-ghost btn-sm" style="margin-top:6px" @click="showRgKey=!showRgKey">{{ showRgKey ? '隐藏' : '显示' }}</button>
      </div>
      <div class="field"><label>飞书 Webhook</label><input v-model="config.notify.feishu_webhook" placeholder="https://..." /></div>
      <div class="field">
        <label>微信通知（PushPlus Token）<a href="https://www.pushplus.plus/" target="_blank" rel="noopener" style="font-weight:400;margin-left:6px">申请 Token →</a></label>
        <input :type="showPushplus ? 'text' : 'password'" v-model="config.notify.pushplus_token" placeholder="关注 PushPlus 公众号后获取" />
        <button class="btn btn-ghost btn-sm" style="margin-top:6px" @click="showPushplus=!showPushplus">{{ showPushplus ? '隐藏' : '显示' }}</button>
        <p class="muted" style="margin-top:6px;font-size:0.78rem">降价告警将推送到微信；可与飞书同时配置双通道通知。</p>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">
        <button class="btn btn-secondary btn-sm" @click="saveConfig">保存</button>
        <button class="btn btn-ghost btn-sm" @click="testRollingGo">测试 RollingGo</button>
        <button class="btn btn-ghost btn-sm" @click="testNotify('/api/config/test-feishu')">测试飞书</button>
        <button class="btn btn-ghost btn-sm" @click="testNotify('/api/config/test-pushplus')">测试微信</button>
      </div>
      <p class="muted" style="margin-top:12px">
        定时监控需保持本服务运行；或使用 cron：<code>curl -X POST http://127.0.0.1:8767/api/watch/run-once</code>
      </p>
    </div>
  </div>
  `,
}).mount("#app");
