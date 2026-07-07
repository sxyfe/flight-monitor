/* 结果区共用筛选 — Element Plus + ResultsFilterBridge */
(function () {
  const EMPTY_FILTER = () => ({
    countries: [],
    cities: [],
    outDates: [],
    retDates: [],
    tripType: "",
    maxPrice: null,
  });

  let filterState = EMPTY_FILTER();
  let offersRef = [];
  let metaRef = { code_to_country: {} };
  let onChangeCb = null;

  function cityCodesForOffer(o) {
    return [o.origin, o.out_dest || o.dest, o.ret_dest].filter(Boolean);
  }

  function cityLabelsForOffer(o) {
    return [
      o.origin_name,
      o.out_dest_name || o.dest_name,
      o.ret_dest_name,
    ].filter(Boolean);
  }

  function countriesForOffer(o, map) {
    const codes = [o.out_dest || o.dest, o.ret_dest].filter(Boolean);
    const set = new Set();
    codes.forEach((c) => {
      if (map[c]) set.add(map[c]);
    });
    return set;
  }

  function deriveOptions(offers, meta) {
    const map = meta?.code_to_country || {};
    const countrySet = new Set();
    const cityMap = new Map();
    const outDateSet = new Set();
    const retDateSet = new Set();

    offers.forEach((o) => {
      countriesForOffer(o, map).forEach((c) => countrySet.add(c));
      cityCodesForOffer(o).forEach((code) => {
        const name =
          code === o.origin
            ? o.origin_name
            : code === (o.out_dest || o.dest)
              ? o.out_dest_name || o.dest_name
              : o.ret_dest_name;
        if (!cityMap.has(code)) cityMap.set(code, name || code);
      });
      if (o.out_date) outDateSet.add(o.out_date);
      if (o.ret_date) retDateSet.add(o.ret_date);
    });

    return {
      countries: [...countrySet].sort(),
      cities: [...cityMap.entries()]
        .map(([code, name]) => ({ code, label: `${name}(${code})` }))
        .sort((a, b) => a.label.localeCompare(b.label, "zh")),
      outDates: [...outDateSet].sort(),
      retDates: [...retDateSet].sort(),
    };
  }

  function getFilteredOffers(offers, meta, state) {
    const list = offers || offersRef;
    const m = meta || metaRef;
    const f = state || filterState;
    const map = m.code_to_country || {};

    return list.filter((o) => {
      if (f.tripType && o.trip_type !== f.tripType) return false;
      if (f.maxPrice != null && f.maxPrice !== "" && o.price > Number(f.maxPrice)) return false;

      if (f.countries?.length) {
        const cs = countriesForOffer(o, map);
        if (!f.countries.some((c) => cs.has(c))) return false;
      }

      if (f.cities?.length) {
        const codes = cityCodesForOffer(o);
        const labels = cityLabelsForOffer(o);
        const hit = f.cities.some(
          (c) => codes.includes(c) || labels.includes(c)
        );
        if (!hit) return false;
      }

      if (f.outDates?.length && !f.outDates.includes(o.out_date)) return false;
      if (f.retDates?.length && !f.retDates.includes(o.ret_date)) return false;

      return true;
    });
  }

  function notifyChange() {
    if (onChangeCb) onChangeCb(getFilteredOffers());
  }

  function mountFilter() {
    const el = document.getElementById("results-filter-app");
    if (!el || typeof Vue === "undefined" || typeof ElementPlus === "undefined") return;
    if (el.__vue_app__) return;

    window.__epLocale =
      window.__epLocale ||
      window.ElementPlusLocaleZhCn ||
      (window.ElementPlus && window.ElementPlus.lang && window.ElementPlus.lang.zhCn) ||
      undefined;

    const { createApp, ref, watch, computed } = Vue;
    const locale = window.__epLocale;

    const app = createApp({
      setup() {
        const countries = ref([]);
        const cities = ref([]);
        const outDates = ref([]);
        const retDates = ref([]);
        const tripType = ref("");
        const maxPrice = ref(null);

        const countryOpts = ref([]);
        const cityOpts = ref([]);
        const outDateOpts = ref([]);
        const retDateOpts = ref([]);

        function syncState() {
          filterState = {
            countries: [...countries.value],
            cities: [...cities.value],
            outDates: [...outDates.value],
            retDates: [...retDates.value],
            tripType: tripType.value,
            maxPrice: maxPrice.value,
          };
          notifyChange();
        }

        watch([countries, cities, outDates, retDates, tripType, maxPrice], syncState, {
          deep: true,
        });

        function reset() {
          countries.value = [];
          cities.value = [];
          outDates.value = [];
          retDates.value = [];
          tripType.value = "";
          maxPrice.value = null;
        }

        const hint = computed(() => {
          const n = getFilteredOffers().length;
          const total = offersRef.length;
          return total ? `筛选后 ${n} / ${total} 条` : "";
        });

        window.ResultsFilterBridge._refreshOptions = () => {
          const opts = deriveOptions(offersRef, metaRef);
          countryOpts.value = opts.countries;
          cityOpts.value = opts.cities;
          outDateOpts.value = opts.outDates;
          retDateOpts.value = opts.retDates;
        };

        window.ResultsFilterBridge._refs = {
          countries,
          cities,
          outDates,
          retDates,
          tripType,
          maxPrice,
          reset,
          hint,
        };

        return {
          countries,
          cities,
          outDates,
          retDates,
          tripType,
          maxPrice,
          countryOpts,
          cityOpts,
          outDateOpts,
          retDateOpts,
          reset,
          hint,
        };
      },
      template: `
        <div class="results-filter" v-if="countryOpts.length || cityOpts.length">
          <div class="results-filter__row">
            <label>国家</label>
            <el-select v-model="countries" multiple filterable collapse-tags placeholder="全部" style="width:100%">
              <el-option v-for="c in countryOpts" :key="c" :label="c" :value="c" />
            </el-select>
          </div>
          <div class="results-filter__row">
            <label>城市</label>
            <el-select v-model="cities" multiple filterable collapse-tags placeholder="全部" style="width:100%">
              <el-option v-for="c in cityOpts" :key="c.code" :label="c.label" :value="c.code" />
            </el-select>
          </div>
          <div class="results-filter__row results-filter__row--dates">
            <div>
              <label>去程日</label>
              <el-select v-model="outDates" multiple filterable collapse-tags placeholder="全部" style="width:100%">
                <el-option v-for="d in outDateOpts" :key="d" :label="d" :value="d" />
              </el-select>
            </div>
            <div>
              <label>回程日</label>
              <el-select v-model="retDates" multiple filterable collapse-tags placeholder="全部" style="width:100%">
                <el-option v-for="d in retDateOpts" :key="d" :label="d" :value="d" />
              </el-select>
            </div>
          </div>
          <div class="results-filter__row results-filter__row--misc">
            <div>
              <label>行程类型</label>
              <el-select v-model="tripType" clearable placeholder="全部" style="width:100%">
                <el-option label="往返" value="round_trip" />
                <el-option label="开口程" value="open_jaw" />
              </el-select>
            </div>
            <div>
              <label>最高价 ¥</label>
              <el-input-number v-model="maxPrice" :min="0" :step="50" controls-position="right" style="width:100%" placeholder="不限" />
            </div>
            <el-button @click="reset">重置</el-button>
          </div>
          <p class="results-filter__hint">{{ hint }}</p>
        </div>
      `,
    });

    if (locale) app.use(ElementPlus, { locale });
    else app.use(ElementPlus);
    app.mount(el);
  }

  window.ResultsFilterBridge = {
    _refs: null,
    _refreshOptions: null,

    setOffers(offers, meta) {
      offersRef = offers || [];
      metaRef = meta || { code_to_country: {} };
      this._refreshOptions?.();
    },

    getFilterState() {
      return { ...filterState };
    },

    getFilteredOffers(offers, meta) {
      return getFilteredOffers(offers, meta);
    },

    onChange(cb) {
      onChangeCb = cb;
    },

    reset() {
      filterState = EMPTY_FILTER();
      this._refs?.reset?.();
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountFilter);
  } else {
    mountFilter();
  }
})();