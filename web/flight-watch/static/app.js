const { createApp, ref, reactive, computed, onMounted, watch } = Vue;

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
    const status = reactive({ rollinggo_configured: false });

    const carriersStr = computed({
      get: () => (form.filters.carriers || []).join(","),
      set: (v) => {
        form.filters.carriers = v.split(/[,，\s]+/).filter(Boolean).map((x) => x.toUpperCase());
      },
    });

    async function api(path, opts = {}) {
      const res = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...opts,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
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

    async function importPreset(id) {
      loading.value = true;
      try {
        await api(`/api/presets/${id}/import`, { method: "POST" });
        message.value = "预设已导入（默认未启用）";
        tab.value = "list";
        await loadWatches();
      } catch (e) {
        error.value = String(e.message || e);
      } finally {
        loading.value = false;
      }
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
            (data.items || []).slice(0, 8).forEach((item) => {
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
    <span class="muted">独立 Web 工具 · 与桌面/nl-search 无集成</span>
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
      <h2>我的监控</h2>
      <button class="btn btn-primary btn-sm" @click="tab='edit'; resetForm()">+ 新建监控</button>
      <div v-if="!watches.length" class="muted" style="margin-top:12px">暂无监控，可从预设库导入或新建。</div>
      <div v-for="w in watches" :key="w.id" class="watch-row">
        <div>
          <strong>{{ w.name }}</strong>
          <div class="watch-meta">
            <span class="tag">{{ w.trip_mode }}</span>
            <span v-for="l in w.legs" :key="l.from_city+l.date">{{ l.from_city }}→{{ l.to_city }} {{ l.date }}</span>
          </div>
          <div class="watch-meta" v-if="w.latest_snapshot">
            最近：{{ w.latest_snapshot.currency }} {{ w.latest_snapshot.price ?? '—' }}
            · {{ w.latest_snapshot.provider }}
            <span v-if="w.latest_snapshot.bookable">· 同票参考</span>
          </div>
          <div class="watch-meta">限价 {{ w.currency }} {{ w.alerts.max_price }} · 每 {{ w.schedule.interval_hours }}h</div>
        </div>
        <div style="display:flex;flex-direction:column;gap:6px;align-items:flex-end">
          <label class="toggle"><input type="checkbox" :checked="w.enabled" @change="toggleWatch(w)" /> 启用</label>
          <button class="btn btn-secondary btn-sm" @click="pollWatch(w.id)">立即查价</button>
          <button class="btn btn-ghost btn-sm" @click="editWatch(w)">编辑</button>
          <button class="btn btn-ghost btn-sm" @click="loadSnapshots(w.id)">历史</button>
          <button class="btn btn-ghost btn-sm" @click="deleteWatch(w.id)">删除</button>
        </div>
      </div>
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
        <label>回程日期</label><input type="date" v-model="form.return_date" />
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
        <div class="field"><label>日期</label><input type="date" v-model="leg.date" /></div>
        <button v-if="form.legs.length>1 && form.trip_mode!=='one_way' && form.trip_mode!=='round_trip'" class="btn btn-ghost btn-sm" @click="removeLeg(i)">删除航段</button>
      </div>
      <button v-if="form.trip_mode==='multi_leg' || form.trip_mode==='open_jaw'" class="btn btn-ghost btn-sm" @click="addLeg">+ 添加航段</button>
      <div class="grid2" style="margin-top:12px">
        <div class="field"><label>限价 ({{ form.currency }})</label><input type="number" v-model.number="form.alerts.max_price" /></div>
        <div class="field"><label>轮询间隔（小时）</label><input type="number" v-model.number="form.schedule.interval_hours" min="1" /></div>
        <div class="field"><label>销售区 ISO（如 CN/US/NL）</label><input v-model="form.sales_region" placeholder="CN" /></div>
        <div class="field"><label>航司过滤（逗号分隔）</label><input v-model="carriersStr" placeholder="DL,UA" /></div>
      </div>
      <div class="field"><label>备注</label><textarea v-model="form.notes" rows="2"></textarea></div>
      <button class="btn btn-primary" :disabled="loading" @click="saveWatch">保存</button>
    </div>

    <div v-if="tab==='presets'" class="card">
      <h2>预设库 · 达美开口（15 条）</h2>
      <p class="muted">导入后可编辑日期/限价；默认未启用。</p>
      <div v-for="p in presets" :key="p.id" class="watch-row">
        <div>
          <strong>{{ p.name }}</strong>
          <div class="watch-meta">参考价 ¥{{ p.reference_price }} · {{ p.legs.map(l=>l.from_city+'→'+l.to_city).join(' / ') }}</div>
          <div v-if="p.notes" class="watch-meta">{{ p.notes }}</div>
        </div>
        <button class="btn btn-secondary btn-sm" @click="importPreset(p.id)">导入</button>
      </div>
    </div>

    <div v-if="tab==='history'" class="card">
      <h2>查价历史 {{ selectedId || '' }}</h2>
      <div v-if="!snapshots.length" class="muted">选择监控后查看历史快照。</div>
      <table v-else style="width:100%;font-size:0.85rem;border-collapse:collapse">
        <tr style="text-align:left;color:var(--muted)"><th>时间</th><th>价格</th><th>Provider</th><th>可订</th></tr>
        <tr v-for="s in snapshots" :key="s.id" style="border-top:1px solid var(--line)">
          <td>{{ s.checked_at }}</td>
          <td>{{ s.currency }} {{ s.price ?? '—' }}</td>
          <td>{{ s.provider }}</td>
          <td>{{ s.bookable ? '是' : '否' }}</td>
        </tr>
      </table>
    </div>

    <div v-if="tab==='settings'" class="card">
      <h2>设置</h2>
      <p class="muted">凭据仅保存在本机，不会上传。</p>
      <div class="field"><label>RollingGo Base URL</label><input v-model="config.rollinggo.base_url" /></div>
      <div class="field">
        <label>RollingGo API Key</label>
        <input :type="showRgKey ? 'text' : 'password'" v-model="config.rollinggo.api_key" />
        <button class="btn btn-ghost btn-sm" style="margin-top:6px" @click="showRgKey=!showRgKey">{{ showRgKey ? '隐藏' : '显示' }}</button>
      </div>
      <div class="field"><label>飞书 Webhook</label><input v-model="config.notify.feishu_webhook" placeholder="https://..." /></div>
      <div class="field">
        <label>PushPlus Token</label>
        <input :type="showPushplus ? 'text' : 'password'" v-model="config.notify.pushplus_token" />
        <button class="btn btn-ghost btn-sm" style="margin-top:6px" @click="showPushplus=!showPushplus">{{ showPushplus ? '隐藏' : '显示' }}</button>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">
        <button class="btn btn-secondary btn-sm" @click="saveConfig">保存</button>
        <button class="btn btn-ghost btn-sm" @click="testRollingGo">测试 RollingGo</button>
        <button class="btn btn-ghost btn-sm" @click="testNotify('/api/config/test-feishu')">测试飞书</button>
        <button class="btn btn-ghost btn-sm" @click="testNotify('/api/config/test-pushplus')">测试 PushPlus</button>
      </div>
      <p class="muted" style="margin-top:12px">
        定时监控需保持本服务运行；或使用 cron：<code>curl -X POST http://127.0.0.1:8767/api/watch/run-once</code>
      </p>
    </div>
  </div>
  `,
}).mount("#app");
