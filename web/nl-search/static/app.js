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
        const res = await fetch(url, {
            headers: { "Content-Type": "application/json" },
            ...opts,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw { status: res.status, ...data };
        return data;
    }

    window.addEventListener("nl-intent-status", (e) => {
        const { msg, msgType } = e.detail || {};
        setConfirmMsg(msg || "", msgType || "");
        if (msg) setSearchStatus(msg, msgType || "warn");
    });

    $("btnSettings").onclick = () => {
        $("viewMain").classList.add("hidden");
        $("viewSettings").classList.remove("hidden");
        loadConfig();
        refreshLlmHint();
    };
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
        } catch (_) {}
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

    async function refreshSearchSettings() {
        try {
            const st = await api("/api/config/status");
            searchSettings = {
                soft_limit_enabled: st.search_soft_limit_enabled !== false,
                soft_query_limit: Number(st.search_soft_query_limit ?? 500),
            };
        } catch (_) {}
    }

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

    function updateVizLink(searchId) {
        const btn = $("btnOpenViz");
        if (!btn) return;
        if (!searchId || currentSearchKind === "matrix") {
            btn.classList.add("hidden");
            return;
        }
        const prefix = location.pathname.includes("/nl-search")
            ? location.pathname.replace(/\/nl-search\/?.*$/, "")
            : "";
        btn.href = `${prefix}/viz/?search_id=${encodeURIComponent(searchId)}`;
        btn.classList.remove("hidden");
    }

    function finishSearch(data, cancelled = false) {
        if (currentSearchKind === "matrix") {
            finishMatrixSearch(data, cancelled);
            return;
        }
        showResults(data, true);
        updateVizLink(currentSearchId);
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
        confirmedMatrixIntent = confirmedMatrixIntent || data.intent || null;
        window.MatrixView ?.render({
            offers: matrixOffers,
            intent: confirmedMatrixIntent,
            meta: data.meta || {},
            stats: data.stats || {},
            pricingWarning: data.pricing_warning,
        });
        $("matrixResultsSection") ?.classList.remove("hidden");
        $("resultsSection") ?.classList.add("hidden");
        if (hideProgress) $("progressSection") ?.classList.add("hidden");
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
            setMatrixSearchStatus("", "");
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
        if (typeof err.detail === "string") return err.detail;
        if (err.detail && typeof err.detail.message === "string") return err.detail.message;
        try {
            return JSON.stringify(err.detail || err.message || err);
        } catch (_) {
            return "搜索失败";
        }
    }

    function formatProgressText(p) {
        const done = Number(p ?.done ?? 0);
        const total = Number(p ?.total ?? 0);
        return `已查询 ${done}/${total} 次`;
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
        if (hideProgress) $("progressSection").classList.add("hidden");
    }

    function startSearchStream(r, est, kind) {
        currentSearchId = r.search_id;
        currentSearchKind = kind;
        const es = new EventSource(
            typeof window.apiUrl === "function" ? window.apiUrl(r.stream_url) : r.stream_url
        );
        currentEventSource = es;
        es.addEventListener("progress", (e) => {
            const p = JSON.parse(e.data);
            $("progressBar").style.width = (p.total ? (p.done / p.total) * 100 : 0) + "%";
            $("progressText").textContent = formatProgressText(p);
            $("progressHits").textContent = formatProgressHits(p, kind);
        });
        es.addEventListener("offer", (e) => {
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
            es.close();
            finishSearch(JSON.parse(e.data), false);
        });
        es.addEventListener("cancelled", (e) => {
            es.close();
            finishSearch(JSON.parse(e.data), true);
        });
        es.addEventListener("error", (e) => {
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
            const hitList = kind === "matrix" ? matrixOffers : offers;
            if (hitList.length) {
                finishSearch({ offers: [...hitList], stats: {}, meta: {} }, false);
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
            const hitList = kind === "matrix" ? matrixOffers : offers;
            es.close();
            if (hitList.length) {
                finishSearch({ offers: [...hitList], stats: {}, meta: {} }, false);
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

        confirmedIntent = validated.intent;
        searchMode = getSearchMode();
        await refreshSearchSettings();
        const est =
            searchMode === "exhaustive" ?
            validated.validation ?.estimated_queries_exhaustive :
            validated.validation ?.estimated_queries_smart;
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
        currentSearchKind = "standard";
        currentSearchId = null;
        currentEventSource ?.close();
        currentEventSource = null;
        $("progressSection").classList.remove("hidden");
        $("resultsSection").classList.add("hidden");
        $("matrixResultsSection") ?.classList.add("hidden");
        $("progressBar").style.width = "0%";
        $("progressText").textContent = "启动搜索…";
        $("progressHits").textContent = "";
        $("btnSearch").disabled = true;
        if ($("btnStopSearch")) $("btnStopSearch").disabled = false;
        if (!searchSettings.soft_limit_enabled || !searchSettings.soft_query_limit || est <= searchSettings.soft_query_limit) {
            setSearchStatus("正在启动搜索…", "ok");
        }
        try {
            const r = await api("/api/search", {
                method: "POST",
                body: JSON.stringify({ intent: confirmedIntent, mode: searchMode }),
            });
            if (!r.stream_url) {
                showResults(r);
                setSearchStatus("");
                resetSearchUi();
                return;
            }
            currentSearchId = r.search_id;
            if (!searchSettings.soft_limit_enabled || !searchSettings.soft_query_limit || est <= searchSettings.soft_query_limit) {
                setSearchStatus("");
            }
            startSearchStream(r, est, "standard");
        } catch (e) {
            const errText = formatError(normalizeApiError(e));
            $("progressText").textContent = errText;
            setSearchStatus(errText, "err");
            resetSearchUi();
        }
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

        confirmedMatrixIntent = validated.intent;
        await refreshSearchSettings();
        const est = validated.validation ?.estimated_queries_smart || 0;
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
        currentSearchKind = "matrix";
        currentSearchId = null;
        currentEventSource ?.close();
        currentEventSource = null;
        $("progressSection").classList.remove("hidden");
        $("resultsSection").classList.add("hidden");
        $("matrixResultsSection") ?.classList.add("hidden");
        $("progressBar").style.width = "0%";
        $("progressText").textContent = "启动矩阵搜索…";
        $("progressHits").textContent = "";
        $("btnMatrixSearch").disabled = true;
        if ($("btnStopSearch")) $("btnStopSearch").disabled = false;
        if (!searchSettings.soft_limit_enabled || !searchSettings.soft_query_limit || est <= searchSettings.soft_query_limit) {
            setMatrixSearchStatus(est ? `预计查询 ${est} 次，正在启动…` : "正在启动矩阵搜索…", "ok");
        }

        try {
            const r = await api("/api/search", {
                method: "POST",
                body: JSON.stringify({
                    intent: confirmedMatrixIntent,
                    search_type: "matrix",
                }),
            });
            if (!r.stream_url) {
                showMatrixResults(r);
                setMatrixSearchStatus("");
                resetSearchUi();
                return;
            }
            if (!searchSettings.soft_limit_enabled || !searchSettings.soft_query_limit || est <= searchSettings.soft_query_limit) {
                setMatrixSearchStatus("");
            }
            startSearchStream(r, est, "matrix");
        } catch (e) {
            const err = normalizeApiError(e);
            let errText = formatError(err);
            const v = err.validation || err.detail ?.validation;
            if (v ?.errors ?.length) errText = v.errors.join("；");
            $("progressText").textContent = errText;
            setMatrixSearchStatus(errText, "err");
            resetSearchUi();
        }
    }

    $("btnSearch").onclick = () => doSearch();
    $("btnMatrixSearch") ?.addEventListener("click", () => doMatrixSearch());
})();