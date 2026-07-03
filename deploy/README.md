# Web 部署（方案 A）

## 1. exhaustive-viz → GitHub Pages

**一次性设置（GitHub 仓库）：**

1. 打开 https://github.com/sxyfe/flight-monitor/settings/pages
2. **Build and deployment → Source** 选 **GitHub Actions**
3. 推送 `main` 后工作流自动发布；也可在 Actions 里手动 **Run workflow**

**访问地址：** https://sxyfe.github.io/flight-monitor/

## 2. nl-search → Hugging Face Space

**一次性设置：**

1. 在 https://huggingface.co/settings/tokens 创建 **Write** Token
2. 在 https://github.com/sxyfe/flight-monitor/settings/secrets/actions 添加 **`HF_TOKEN`**
3. （可选）在 Space https://huggingface.co/spaces/sxyfe/nl-flight-search/settings 添加 Secrets：
   - `ROLLINGGO_API_KEY`
   - `LLM_API_KEY`（可选）

**自动部署：** 推送 `main` 且变更 `web/nl-search` / `scripts` 时触发。

**本地手动推送：**

```bash
export HF_TOKEN=hf_xxx
./deploy/nl-search/push-hf.sh
```

**访问地址：** https://huggingface.co/spaces/sxyfe/nl-flight-search
