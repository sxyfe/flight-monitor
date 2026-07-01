## 视觉

主视觉采用 demo-bilibili 暖色 token（`#f3efe6` / `#e85d3b` / `#0d6e6e`），布局采用 exhaustive-viz 的 Hero + 280px 侧栏 + 主内容 Grid。字体使用系统栈，不依赖 Google Fonts。

## 数据

单文件 HTML，`<script id="report-data">` 内嵌：

```json
{
  "meta": { "date_range", "max_price", "min_stay_days", "search_mode", "generated_at" },
  "origins": {},
  "destinations_by_country": {},
  "offers": []
}
```

## 交互流

筛选 → 排序 → 对筛选全集分页 → 渲染当前页 DOM。筛选/排序变更时 `page = 1`。Chart.js 基于筛选后全集更新。

## 表单去重

demo 往返/开口程分 Tab + 双 pager 与 viz 侧栏行程 Tab 重叠，保留侧栏 Tab，单一 pager。

## 表格列

`#` · 类型 · 路线 · 出发 · 返程 · 停留 · 价格 · 可订 · 航班详情
