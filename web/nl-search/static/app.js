/* 页面壳：设置、NL/表单/矩阵、搜索、暖色报告 / 矩阵结果 */
(function() {
    let confirmedIntent = null;
    let confirmedMatrixIntent = null;
    let offers = [];
    let matrixOffers = [];
    let searchMode = "smart";
    let currentSearchId = null;
    let currentEventSource = null;
    let activeQueryTab = "nl";
    let currentSearchKind = "standard";
    let searchSettings = { soft_limit_enabled: true, soft_query_limit: 500 };
    let lastCompletedSearchId = null;

    const $ = (id) => document.getElementById(id);

    function getSearchMode() {
        return window.SearchModeBridge ?.getMode ?.() || "smart";
    }

    function setConfirmMsg(text, type) {
        const el = $("confirmMsg");
        if (!el) return;
        el.textContent = text || "";
        el.className = type ? `msg-${type}` : "";
    }

    function setSearchStatus(text, type) {
        const el = $("searchStatus");
        if (!el) return;
        el.textContent = text || "";
        el.className = type ? `msg-${type}` : "";
    }

    function setMatrixSearchStatus(text, type) {
        const el = $("matrixSearchStatus");
        if (!el) return;
        el.textContent = text || "";
        el.className = type ? `msg-${type}` : "";
    }

    function focusSearchIssue() {
        $("searchStatus") ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
        document.querySelector("#intent-editor-app .ui-msg") ?.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
        });
    }

    async function api(path, opts = {}) {
        const url = typeof window.apiUrl === "function" ? window.apiUrl(path) : path;
        const method = (opts.method || "GET").toUpperCase();
        const { headers: optHeaders = {}, body, ...restOpts } = opts;
        const headers = {
            "Content-Type": "application/json",
            ...optHeaders,
        };
        const fetchOpts = {
            credentials: "include",
            method,
            headers,
            ...restOpts,
        };
        if (body !== undefined) {
            fetchOpts.body = typeof body === "string" ? body : JSON.stringify(body);
        }
        if (method === "POST" && !fetchOpts.cache) {
            fetchOpts.cache = "no-store";
        }
        const res = await fetch(url, fetchOpts);
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw { status: res.status, ...data };
        return data;
    }

    function newClientRequestId() {
        if (typeof crypto !== "undefined" && crypto.randomUUID) {
            return crypto.randomUUID();
        }
        return `req_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
    }

    function validateSearchStartResponse(r, options = {}) {
        if (!r?.search_id) {
            throw { message: "搜索启动失败：未返回 search_id" };
        }
        if (r.stream_url && !r.stream_nonce) {
            throw { message: "搜索启动失败：缺少 stream_nonce，请硬刷新页面（Cmd+Shift+R）" };
        }
        if (options.fromHistory && options.lastSearchId && r.search_id === options.lastSearchId) {
            throw {
                message: "再次搜索未创建新任务（search_id 未变化），请硬刷新后重试",
            };
        }
    }

    async function postSearch(body, options = {}) {
        const clientRequestId = newClientRequestId();
        return api("/api/search", {
            method: "POST",
            cache: "no-store",
            headers: { "X-Client-Request-Id": clientRequestId },
            body: { ...body, client_request_id: clientRequestId },
        });
    }

    window.addEventListener("nl-intent-status", (e) => {
        const { msg, msgType } = e.detail || {};
        setConfirmMsg(msg || "", msgType || "");
        if (msg) setSearchStatus(msg, msgType || "warn");
    });

    function openSettingsView() {
        $("viewMain").classList.add("hidden");
        $("viewSettings").classList.remove("hidden");
        loadConfig();
        refreshLlmHint();
    }

    $("btnSettings").onclick = () => openSettingsView();

    function parseSettingsDeepLink() {
        const settings = new URLSearchParams(window.location.search).get("settings");
        if (settings === "key" || settings === "1" || settings === "true") {
            openSettingsView();
        }
    }
    $("btnBackFromSettings").onclick = () => {
        $("viewSettings").classList.add("hidden");
        $("viewMain").classList.remove("hidden");
        refreshLlmHint();
    };

    document.querySelectorAll(".btn-eye").forEach((btn) => {
        btn.onclick = () => {
            const input = $(btn.dataset.target);
            if (!input) return;
            input.type = input.type === "password" ? "text" : "password";
        };
    });

    async function loadConfig() {
        try {
            const c = await api("/api/config");
            $("rgUrl").value = c.rollinggo ?.base_url || "https://mcp.rollinggo.cn";
            $("rgKey").value = c.rollinggo ?.api_key || "";
            $("llmUrl").value = c.llm ?.base_url || "https://api.openai.com/v1";
            $("llmKey").value = c.llm ?.api_key || "";
            $("llmModel").value = c.llm ?.model || "gpt-4o-mini";
            searchSettings = {
                soft_limit_enabled: c.search ?.soft_limit_enabled !== false,
                soft_query_limit: Number(c.search ?.soft_query_limit ?? 500),
            };
            if ($("softLimitEnabled")) $("softLimitEnabled").checked = searchSettings.soft_limit_enabled;
            if ($("softQueryLimit")) $("softQueryLimit").value = searchSettings.soft_query_limit;
            await renderConfigStatus();
        } catch (_) {}
    }

    async function renderConfigStatus() {
        const row = $("configStatusRow");
        if (!row) return;
        try {
            const st = await api("/api/config/status");
            const pills = [
                { label: "RollingGo", ok: st.rollinggo_configured },
                { label: "LLM（可选）", ok: st.llm_configured },
            ];
            row.innerHTML = pills
                .map(
                    (p) =>
                        `<span class="config-pill ${p.ok ? "ok" : "off"}">${p.label}：${p.ok ? "已配置" : "未配置"}</span>`
                )
                .join("");
        } catch (_) {
            row.innerHTML = "";
        }
    }

    async function refreshLlmHint() {
        const el = $("llmHint");
        if (!el) return;
        try {
            const st = await api("/api/config/status");
            if (st.llm_configured) {
                el.textContent = "已配置 LLM，大模型解析更准确。";
                el.className = "parse-hint parse-hint-ok";
            } else {
                el.textContent =
                    "在设置中配置 LLM 后，大语言模型解析更准确；未配置时使用规则回退，复杂句子可能不完整。";
                el.className = "parse-hint";
            }
        } catch (_) {
            el.textContent =
                "在设置中配置 LLM 后，大语言模型解析更准确；未配置时使用规则回退，复杂句子可能不完整。";
        }
    }

    $("btnSaveConfig").onclick = async() => {
        try {
            await api("/api/config", {
                method: "POST",
                body: JSON.stringify({
                    rollinggo: { base_url: $("rgUrl").value, api_key: $("rgKey").value },
                    llm: {
                        base_url: $("llmUrl").value,
                        api_key: $("llmKey").value,
                        model: $("llmModel").value,
                    },
                    search: {
                        soft_limit_enabled: $("softLimitEnabled") ?.checked !== false,
                        soft_query_limit: Number($("softQueryLimit") ?.value || 0),
                    },
                }),
            });
            searchSettings = {
                soft_limit_enabled: $("softLimitEnabled") ?.checked !== false,
                soft_query_limit: Number($("softQueryLimit") ?.value || 0),
            };
            $("configStatus").textContent = "配置已保存";
            refreshLlmHint();
            renderConfigStatus();
        } catch (e) {
            $("configStatus").textContent = e.detail || "保存失败";
        }
    };

    $("btnTestRg").onclick = async() => {
        await $("btnSaveConfig").onclick();
        try {
            const r = await api("/api/config/test-rollinggo", { method: "POST" });
            $("configStatus").textContent = r.message;
        } catch (e) {
            $("configStatus").textContent = e.detail || "RollingGo 连接失败";
        }
    };

    $("btnTestLlm").onclick = async() => {
        await $("btnSaveConfig").onclick();
        try {
            const r = await api("/api/config/test-llm", { method: "POST" });
            $("configStatus").textContent = r.message;
            refreshLlmHint();
        } catch (e) {
            $("configStatus").textContent = e.detail || "LLM 连接失败";
        }
    };

    loadConfig();
    refreshLlmHint();
    parseSettingsDeepLink();

    function initSiteNav() {
        const href = typeof window.siteHref === "function" ? window.siteHref : (p) => p;
        const links = {
            navHome: href("/"),
            navWatch: href("/flight-watch/"),
            navSkill: href("/skill/"),
            navNlSearch: href("/nl-search/"),
        };
        Object.entries(links).forEach(([id, url]) => {
            const el = $(id);
            if (el) el.href = url;
        });
    }

    initSiteNav();

    $("btnMatrixBack")?.addEventListener("click", () => {
        $("matrixResultsSection")?.classList.add("hidden");
        switchQueryTab("matrix");
        window.scrollTo({ top: 0, behavior: "smooth" });
    });

    async function refreshSearchSettings() {
        try {
            const st = await api("/api/config/status");
            searchSettings = {
                soft_limit_enabled: st.search_soft_limit_enabled !== false,
                soft_query_limit: Number(st.search_soft_query_limit ?? 500),
            };
        } catch (_) {}
    }

    function saveSearchHistory(kind, intent, extras = {}) {
        if (!window.SearchHistory?.add || !intent) return;
        window.SearchHistory.add({
            kind,
            searchMode: extras.searchMode || getSearchMode(),
            intent,
            originLabels: extras.originLabels || {},
            destLabels: extras.destLabels || {},
            dateMode: extras.dateMode || "range",
            nlQuery: extras.nlQuery || "",
        });
    }

    function yieldToUi() {
        return new Promise((resolve) => requestAnimationFrame(() => resolve()));
    }

    function shutdownSearchStream() {
        const es = currentEventSource;
        currentEventSource = null;
        currentSearchId = null;
        if (es) {
            es.onerror = null;
            es.close();
        }
    }

    async function cancelActiveSearchIfAny() {
        const sid = currentSearchId;
        shutdownSearchStream();
        if (!sid) return;
        try {
            await api(`/api/search/${sid}/cancel`, { method: "POST" });
        } catch (_) {}
    }

    function clearSearchResultsUi(progressText = "启动搜索…") {
        offers = [];
        matrixOffers = [];
        $("resultsSection")?.classList.add("hidden");
        $("matrixResultsSection")?.classList.add("hidden");
        $("progressSection")?.classList.remove("hidden");
        $("progressBar").style.width = "0%";
        $("progressText").textContent = progressText;
        $("progressHits").textContent = "";
        $("viewMain")?.classList.remove("hidden");
        const matrixRoot = $("matrixReportRoot");
        if (matrixRoot) matrixRoot.innerHTML = "";
        $("progressSection")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function beginSearchUi(kind, progressText) {
        clearSearchResultsUi(progressText);
        currentSearchKind = kind;
        $("btnSearch").disabled = kind === "standard";
        if ($("btnMatrixSearch")) $("btnMatrixSearch").disabled = kind === "matrix";
        if ($("btnStopSearch")) $("btnStopSearch").disabled = false;
    }

    async function launchStandardSearch(intent, mode, est = 0, options = {}) {
        confirmedIntent = intent;
        searchMode = mode === "exhaustive" ? "exhaustive" : "smart";
        await refreshSearchSettings();
        if (
            searchSettings.soft_limit_enabled &&
            searchSettings.soft_query_limit > 0 &&
            est > searchSettings.soft_query_limit
        ) {
            setSearchStatus(
                `预估 ${est} 次查询，超过软提示阈值 ${searchSettings.soft_query_limit} 次，仍将启动搜索`,
                "warn"
            );
        }

        offers = [];
        if (!options.skipBeginUi) {
            beginSearchUi("standard", "启动搜索…");
        }
        if (!searchSettings.soft_limit_enabled || !searchSettings.soft_query_limit || est <= searchSettings.soft_query_limit) {
            setSearchStatus("正在启动搜索…", "ok");
        }

        try {
            const r = await postSearch({ intent: confirmedIntent, mode: searchMode }, options);
            validateSearchStartResponse(r, {
                fromHistory: options.fromHistory,
                lastSearchId: lastCompletedSearchId,
            });
            if (!r.stream_url) {
                const meta = window.IntentEditorBridge?.getFormMeta?.() || {};
                saveSearchHistory("standard", confirmedIntent, {
                    searchMode,
                    originLabels: meta.originLabels,
                    destLabels: meta.destLabels,
                    nlQuery: activeQueryTab === "nl" ? ($("nlQuery")?.value || "").trim() : "",
                });
                showResults(r);
                setSearchStatus("");
                resetSearchUi();
                return;
            }
            currentSearchId = r.search_id;
            $("progressText").textContent = `新搜索 ${r.search_id} · 正在启动…`;
            if (!searchSettings.soft_limit_enabled || !searchSettings.soft_query_limit || est <= searchSettings.soft_query_limit) {
                setSearchStatus("");
            }
            const meta = window.IntentEditorBridge?.getFormMeta?.() || {};
            saveSearchHistory("standard", confirmedIntent, {
                searchMode,
                originLabels: meta.originLabels,
                destLabels: meta.destLabels,
                nlQuery: activeQueryTab === "nl" ? ($("nlQuery")?.value || "").trim() : "",
            });
            startSearchStream(r, est, "standard");
        } catch (e) {
            const errText = formatError(normalizeApiError(e));
            $("progressText").textContent = errText;
            setSearchStatus(errText, "err");
            resetSearchUi();
        }
    }

    async function launchMatrixSearch(intent, est = 0, options = {}) {
        confirmedMatrixIntent = intent;
        await refreshSearchSettings();
        if (
            searchSettings.soft_limit_enabled &&
            searchSettings.soft_query_limit > 0 &&
            est > searchSettings.soft_query_limit
        ) {
            setMatrixSearchStatus(
                `预估 ${est} 次查询，超过软提示阈值 ${searchSettings.soft_query_limit} 次，仍将启动搜索`,
                "warn"
            );
        }

        matrixOffers = [];
        if (!options.skipBeginUi) {
            beginSearchUi("matrix", "启动矩阵搜索…");
        }
        if (!searchSettings.soft_limit_enabled || !searchSettings.soft_query_limit || est <= searchSettings.soft_query_limit) {
            setMatrixSearchStatus(est ? `预计查询 ${est} 次，正在启动…` : "正在启动矩阵搜索…", "ok");
        }

        try {
            const r = await postSearch(
                {
                    intent: confirmedMatrixIntent,
                    search_type: "matrix",
                },
                options
            );
            validateSearchStartResponse(r, {
                fromHistory: options.fromHistory,
                lastSearchId: lastCompletedSearchId,
            });
            if (!r.stream_url) {
                const meta = window.MatrixEditorBridge?.getFormMeta?.() || {};
                saveSearchHistory("matrix", confirmedMatrixIntent, {
                    originLabels: meta.originLabels,
                    destLabels: meta.destLabels,
                    dateMode: meta.dateMode,
                });
                showMatrixResults(r);
                setMatrixSearchStatus("");
                resetSearchUi();
                return;
            }
            if (!searchSettings.soft_limit_enabled || !searchSettings.soft_query_limit || est <= searchSettings.soft_query_limit) {
                setMatrixSearchStatus("");
            }
            currentSearchId = r.search_id;
            $("progressText").textContent = `新搜索 ${r.search_id} · 正在启动…`;
            const meta = window.MatrixEditorBridge?.getFormMeta?.() || {};
            saveSearchHistory("matrix", confirmedMatrixIntent, {
                originLabels: meta.originLabels,
                destLabels: meta.destLabels,
                dateMode: meta.dateMode,
            });
            startSearchStream(r, est, "matrix");
        } catch (e) {
            const err = normalizeApiError(e);
            let errText = formatError(err);
            const v = err.validation || err.detail?.validation;
            if (v?.errors?.length) errText = v.errors.join("；");
            $("progressText").textContent = errText;
            setMatrixSearchStatus(errText, "err");
            resetSearchUi();
        }
    }

    async function restoreSearchRecord(record, { autoSearch = false } = {}) {
        if (!record?.intent) return;
        const intent = JSON.parse(JSON.stringify(record.intent));

        if (record.kind === "matrix") {
            if (!window.MatrixEditorBridge?.loadIntent) return;
            window.MatrixEditorBridge.loadIntent(intent, {
                originLabels: record.originLabels,
                destLabels: record.destLabels,
                dateMode: record.dateMode,
            });
            switchQueryTab("matrix");
            if (!autoSearch) {
                setMatrixSearchStatus("已加载矩阵条件", "");
                return;
            }
            setMatrixSearchStatus("正在重新搜索…", "ok");
            await cancelActiveSearchIfAny();
            beginSearchUi("matrix", "正在重新查价…");
            await yieldToUi();
            await launchMatrixSearch(intent, 0, { skipBeginUi: true, fromHistory: true });
            return;
        }

        if (record.nlQuery && $("nlQuery")) $("nlQuery").value = record.nlQuery;
        window.IntentEditorBridge?.loadIntent(intent, null, {
            originLabels: record.originLabels,
            destLabels: record.destLabels,
        });
        const mode = record.searchMode || "smart";
        if (record.searchMode && window.SearchModeBridge?.setMode) {
            window.SearchModeBridge.setMode(mode);
        }
        switchQueryTab(autoSearch ? "form" : record.nlQuery ? "nl" : "form");
        if (!autoSearch) {
            setSearchStatus("已加载搜索条件", "");
            return;
        }
        setSearchStatus("正在重新搜索…", "ok");
        await cancelActiveSearchIfAny();
        beginSearchUi("standard", "正在重新查价…");
        await yieldToUi();
        await launchStandardSearch(intent, mode, 0, { skipBeginUi: true, fromHistory: true });
    }

    window.SearchHistoryBridge = {
        rerun: restoreSearchRecord,
        refresh: () => window.SearchHistory?.renderPanel?.(),
    };

    function resetSearchUi() {
        currentSearchId = null;
        currentEventSource = null;
        $("btnSearch").disabled = false;
        if ($("btnMatrixSearch")) $("btnMatrixSearch").disabled = false;
        if ($("btnStopSearch")) $("btnStopSearch").disabled = true;
    }

    function switchQueryTab(tab) {
        activeQueryTab = tab;
        const tabs = { nl: $("tabNl"), form: $("tabForm"), matrix: $("tabMatrix") };
        const panels = { nl: $("panelNl"), form: $("panelForm"), matrix: $("panelMatrix") };
        Object.keys(tabs).forEach((k) => {
            tabs[k] ?.classList.toggle("active", k === tab);
            if (panels[k]) panels[k].style.display = k === tab ? "block" : "none";
        });
        $("searchToolbarStandard") ?.classList.toggle("hidden", tab === "matrix");
        $("searchToolbarMatrix") ?.classList.toggle("hidden", tab !== "matrix");
    }

    $("tabNl").onclick = () => switchQueryTab("nl");
    $("tabForm").onclick = () => switchQueryTab("form");
    $("tabMatrix").onclick = () => switchQueryTab("matrix");

    function finishSearch(data, cancelled = false) {
        if (currentSearchId) lastCompletedSearchId = currentSearchId;
        const kind =
            data?.meta?.search_type === "matrix" || currentSearchKind === "matrix"
                ? "matrix"
                : "standard";
        if (kind === "matrix") {
            finishMatrixSearch(data, cancelled);
            return;
        }
        showResults(data, true);
        const pricingMsg = pricingServiceMessage(data);
        if (pricingMsg) {
            setSearchStatus(pricingMsg, "err");
        } else if (cancelled) {
            setSearchStatus(
                `搜索已停止，保留 ${(data.offers || []).length} 条命中结果`,
                "warn"
            );
        } else {
            setSearchStatus("", "");
        }
        resetSearchUi();
    }

    function showMatrixResults(data, hideProgress = true) {
        matrixOffers = data.offers || [];
        window.MatrixView ?.render({
            offers: matrixOffers,
            intent: confirmedMatrixIntent,
            meta: data.meta || {},
            stats: data.stats || {},
            pricingWarning: data.pricing_warning,
        });
        $("matrixResultsSection")?.classList.remove("hidden");
        $("resultsSection")?.classList.add("hidden");
        $("viewMain")?.classList.remove("hidden");
        if (hideProgress) $("progressSection")?.classList.add("hidden");
    }

    function finishMatrixSearch(data, cancelled = false) {
        showMatrixResults(data, true);
        const pricingMsg = pricingServiceMessage(data);
        if (pricingMsg) {
            setMatrixSearchStatus(pricingMsg, "err");
        } else if (cancelled) {
            setMatrixSearchStatus(
                `搜索已停止，保留 ${(data.offers || []).length} 个价格`,
                "warn"
            );
        } else {
            const count = (data.offers || []).length;
            const stats = data.stats || {};
            const total = Number(stats.total_queries || 0);
            const errors = Number(stats.errors || 0);
            if (!count && total > 0 && errors >= total) {
                const sample =
                    data.meta?.sample_error || data.stats?.sample_error || "";
                setMatrixSearchStatus(
                    sample
                        ? `查价完成：${total} 次查询均未得到有效价格（${sample}）`
                        : `查价完成：${total} 次查询均未得到有效价格，请检查 API Key 或稍后重试`,
                    "err"
                );
            } else if (!count && total > 0) {
                setMatrixSearchStatus(`查价完成，暂无命中（已查询 ${total} 次）`, "warn");
            } else if (!count) {
                setMatrixSearchStatus("查价完成，暂无命中", "warn");
            } else {
                setMatrixSearchStatus("", "");
            }
        }
        resetSearchUi();
    }

    $("btnStopSearch") ?.addEventListener("click", async() => {
        if (!currentSearchId) return;
        $("btnStopSearch").disabled = true;
        $("progressText").textContent = "正在停止…";
        try {
            await api(`/api/search/${currentSearchId}/cancel`, { method: "POST" });
        } catch (_) {}
    });

    $("btnParse").onclick = async() => {
        const q = $("nlQuery").value.trim();
        if (!q) return;
        $("parseMsg").textContent = "解析中…";
        try {
            const r = await api("/api/intent/parse", { method: "POST", body: JSON.stringify({ query: q }) });
            const base = r.validation.valid ?
                "解析成功，原文已保留，可在表单 Tab 核对后直接搜索" :
                "解析完成，请在表单 Tab 核对后开始搜索";
            $("parseMsg").textContent = base + "，已切至表单 Tab";
            window.IntentEditorBridge ?.loadIntent(r.intent, r.validation);
            if (r.validation) {
                window.dispatchEvent(
                    new CustomEvent("nl-intent-status", {
                        detail: {
                            msg: r.validation.valid ? "" : "解析结果需核对，请查看表单 Tab",
                            msgType: r.validation.valid ? "" : "warn",
                        },
                    })
                );
            }
            $("tabForm").click();
        } catch (e) {
            $("parseMsg").textContent = e.detail || "解析失败";
        }
    };

    function normalizeApiError(e) {
        if (!e) return {};
        const detail = e.detail;
        if (detail && typeof detail === "object" && !Array.isArray(detail)) {
            return {
                ...e,
                code: detail.code ?? e.code,
                message: detail.message ?? e.message,
                validation: detail.validation ?? e.validation,
                estimated_queries: detail.estimated_queries ?? e.estimated_queries,
            };
        }
        return e;
    }

    function formatError(e) {
        const err = normalizeApiError(e);
        if (!err || (!err.message && !err.detail && !err.code)) return "搜索失败";
        if (typeof err.message === "string") return err.message;
        if (err.code === "LOGIN_REQUIRED" || err.code === "SUBSCRIPTION_REQUIRED" || err.code === "QUOTA_EXCEEDED") {
            return err.message || "当前无法完成搜索";
        }
        if (typeof err.detail === "string") return err.detail;
        if (err.detail && typeof err.detail.message === "string") return err.detail.message;
        try {
            return JSON.stringify(err.detail || err.message || err);
        } catch (_) {
            return "搜索失败";
        }
    }

    function formatProgressText(p, searchId) {
        const done = Number(p ?.done ?? 0);
        const total = Number(p ?.total ?? 0);
        const idPart = searchId ? `新搜索 ${searchId} · ` : "";
        return `${idPart}已查询 ${done}/${total} 次`;
    }

    function formatProgressHits(p, kind) {
        const hits = Number(p ?.hits ?? (kind === "matrix" ? matrixOffers.length : offers.length));
        if (p ?.pricing_service_abnormal) {
            return "查价服务异常，暂无有效命中";
        }
        return kind === "matrix" ? `已命中 ${hits} 个价格` : `已命中 ${hits} 条航线`;
    }

    function pricingServiceMessage(data) {
        const stats = data ?.stats || {};
        const meta = data ?.meta || {};
        const abnormal =
            stats.pricing_service_abnormal ||
            meta.pricing_service_abnormal ||
            Boolean(data ?.pricing_warning);
        if (!abnormal) return "";
        const detail =
            data ?.pricing_warning ||
            stats.api_failure_message ||
            meta.pricing_service_message ||
            meta.api_failure_message ||
            "";
        const n = Number(stats.api_failures || meta.api_failures || 0);
        if (detail && detail !== "查价服务异常") {
            return n > 0 ?
                `查价服务异常：${detail}（${n} 次查价失败）` :
                `查价服务异常：${detail}`;
        }
        return n > 0 ?
            `查价服务异常（${n} 次查价失败，请稍后重试或在设置页测试 RollingGo 查价）` :
            "查价服务异常，请稍后重试或在设置页测试 RollingGo 查价";
    }

    function showResults(data, hideProgress = true) {
        offers = data.offers || [];
        searchMode = getSearchMode();
        const querySummary =
            window.IntentEditorBridge ?.getQueryString ?.() ||
            window.IntentQuery ?.intentToQueryString(confirmedIntent, {}) ||
            "";

        window.ReportBridge ?.init({
            offers,
            intent: confirmedIntent,
            meta: {
                ...(data.meta || {}),
                pricing_service_abnormal: Boolean(
                    data.stats ?.pricing_service_abnormal || data.meta ?.pricing_service_abnormal
                ),
                pricing_service_message: data.pricing_warning ||
                    data.stats ?.api_failure_message ||
                    data.meta ?.pricing_service_message ||
                    "",
                api_failures: data.stats ?.api_failures ?? data.meta ?.api_failures,
            },
            mode: searchMode,
            querySummary,
        });

        $("resultsSection").classList.remove("hidden");
        $("matrixResultsSection") ?.classList.add("hidden");
        $("viewMain")?.classList.remove("hidden");
        if (hideProgress) $("progressSection").classList.add("hidden");
    }

    function startSearchStream(r, est, kind) {
        shutdownSearchStream();

        const boundSearchId = r.search_id;
        currentSearchId = boundSearchId;
        currentSearchKind = kind;
        const isActive = () => currentSearchId === boundSearchId;

        const streamPath = r.stream_nonce
            ? `${r.stream_url}?nonce=${encodeURIComponent(r.stream_nonce)}`
            : r.stream_url;
        const es = new EventSource(
            typeof window.apiUrl === "function" ? window.apiUrl(streamPath) : streamPath
        );
        currentEventSource = es;
        es.addEventListener("progress", (e) => {
            if (!isActive()) return;
            const p = JSON.parse(e.data);
            $("progressBar").style.width = (p.total ? (p.done / p.total) * 100 : 0) + "%";
            $("progressText").textContent = formatProgressText(p, boundSearchId);
            $("progressHits").textContent = formatProgressHits(p, kind);
        });
        es.addEventListener("offer", (e) => {
            if (!isActive()) return;
            const offer = JSON.parse(e.data);
            if (kind === "matrix") {
                matrixOffers.push(offer);
                $("progressHits").textContent = formatProgressHits({ hits: matrixOffers.length }, kind);
            } else {
                offers.push(offer);
                $("progressHits").textContent = formatProgressHits({ hits: offers.length }, kind);
            }
        });
        es.addEventListener("completed", (e) => {
            if (!isActive()) {
                es.close();
                return;
            }
            es.close();
            if (currentEventSource === es) currentEventSource = null;
            finishSearch(JSON.parse(e.data), false);
        });
        es.addEventListener("cancelled", (e) => {
            if (!isActive()) {
                es.close();
                return;
            }
            es.close();
            if (currentEventSource === es) currentEventSource = null;
            finishSearch(JSON.parse(e.data), true);
        });
        es.addEventListener("error", (e) => {
            if (!isActive()) {
                es.close();
                return;
            }
            let errText = "搜索失败";
            if (e.data) {
                try {
                    const err = JSON.parse(e.data);
                    errText = formatError(err);
                    $("progressText").textContent = errText;
                } catch (_) {
                    $("progressText").textContent = errText;
                }
            }
            es.close();
            if (currentEventSource === es) currentEventSource = null;
            const hitList = kind === "matrix" ? matrixOffers : offers;
            if (hitList.length) {
                finishSearch({ offers: [...hitList], stats: {}, meta: { search_type: kind } }, false);
                const partialMsg = `${errText}，已保留 ${hitList.length} 条命中结果`;
                if (kind === "matrix") {
                    setMatrixSearchStatus(partialMsg, "warn");
                } else {
                    setSearchStatus(partialMsg, "warn");
                }
            } else if (kind === "matrix") {
                setMatrixSearchStatus(errText, "err");
            } else {
                setSearchStatus(errText, "err");
            }
            resetSearchUi();
        });
        es.onerror = () => {
            if (!isActive() || es !== currentEventSource) {
                es.close();
                return;
            }
            const hitList = kind === "matrix" ? matrixOffers : offers;
            es.close();
            currentEventSource = null;
            if (hitList.length) {
                finishSearch({ offers: [...hitList], stats: {}, meta: { search_type: kind } }, false);
                const partialMsg = `搜索连接中断，已保留 ${hitList.length} 条命中结果`;
                if (kind === "matrix") {
                    setMatrixSearchStatus(partialMsg, "warn");
                } else {
                    setSearchStatus(partialMsg, "warn");
                }
                resetSearchUi();
                return;
            }
            if (kind === "matrix") {
                setMatrixSearchStatus("搜索连接中断", "err");
            } else {
                setSearchStatus("搜索连接中断", "err");
            }
            resetSearchUi();
        };
    }

    async function doSearch() {
        setSearchStatus("");

        if (!window.IntentEditorBridge ?.validateIntent) {
            setSearchStatus("表单未就绪，请硬刷新页面（Cmd+Shift+R）", "err");
            $("tabForm").click();
            focusSearchIssue();
            return;
        }

        let validated;
        try {
            validated = await window.IntentEditorBridge.validateIntent();
        } catch (e) {
            setSearchStatus(e.message || "意图校验失败", "err");
            $("tabForm").click();
            focusSearchIssue();
            return;
        }

        if (!validated ?.ok) {
            setSearchStatus(validated.message || "请完善表单条件后再搜索", validated.msgType || "warn");
            $("tabForm").click();
            focusSearchIssue();
            return;
        }

        searchMode = getSearchMode();
        const est =
            searchMode === "exhaustive" ?
            validated.validation ?.estimated_queries_exhaustive :
            validated.validation ?.estimated_queries_smart;
        await launchStandardSearch(validated.intent, searchMode, est || 0);
    }

    async function doMatrixSearch() {
        setMatrixSearchStatus("");

        if (!window.MatrixEditorBridge ?.validateIntent) {
            setMatrixSearchStatus("矩阵表单未就绪，请硬刷新页面（Cmd+Shift+R）", "err");
            switchQueryTab("matrix");
            return;
        }

        let validated;
        try {
            validated = await window.MatrixEditorBridge.validateIntent();
        } catch (e) {
            setMatrixSearchStatus(e.message || "校验失败", "err");
            switchQueryTab("matrix");
            return;
        }

        if (!validated ?.ok) {
            setMatrixSearchStatus(validated.message || "请完善矩阵条件后再搜索", "err");
            switchQueryTab("matrix");
            return;
        }

        const est = validated.validation ?.estimated_queries_smart || 0;
        await launchMatrixSearch(validated.intent, est);
    }

    $("btnSearch").onclick = () => doSearch();
    $("btnMatrixSearch") ?.addEventListener("click", () => doMatrixSearch());
})();