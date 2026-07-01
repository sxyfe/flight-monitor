import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const nlSearchDir = path.join(projectRoot, "web", "nl-search");
const venvBin = path.join(nlSearchDir, ".venv", process.platform === "win32" ? "Scripts" : "bin");
const venvPython = path.join(venvBin, process.platform === "win32" ? "python.exe" : "python");
const pipIndex = "https://pypi.tuna.tsinghua.edu.cn/simple";
const DEFAULT_PORT = 8765;
const MAX_PORT_ATTEMPTS = 20;
const HOST = "127.0.0.1";

function ensureVenv() {
  if (existsSync(venvPython)) return;

  console.log("正在创建 Python 虚拟环境…");
  const venvResult = spawnSync("python3", ["-m", "venv", ".venv"], {
    cwd: nlSearchDir,
    stdio: "inherit",
  });
  if (venvResult.status !== 0) process.exit(venvResult.status ?? 1);

  const pipResult = spawnSync(
    venvPython,
    ["-m", "pip", "install", "-r", "requirements.txt", "-i", pipIndex],
    { cwd: nlSearchDir, stdio: "inherit" },
  );
  if (pipResult.status !== 0) process.exit(pipResult.status ?? 1);
}

function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => {
      server.close(() => resolve(true));
    });
    server.listen(port, HOST);
  });
}

async function findAvailablePort(startPort) {
  for (let offset = 0; offset < MAX_PORT_ATTEMPTS; offset += 1) {
    const port = startPort + offset;
    if (await isPortAvailable(port)) return port;
  }
  throw new Error(
    `在 ${startPort}–${startPort + MAX_PORT_ATTEMPTS - 1} 范围内未找到可用端口`,
  );
}

async function main() {
  ensureVenv();

  const preferredPort = Number(process.env.NL_SEARCH_PORT) || DEFAULT_PORT;
  const port = await findAvailablePort(preferredPort);

  if (port !== preferredPort) {
    console.log(`端口 ${preferredPort} 已被占用，改用 ${port} 启动 nl-search`);
  }
  console.log(`nl-search 本地地址: http://${HOST}:${port}`);

  const child = spawn(
    venvPython,
    ["-m", "uvicorn", "server:app", "--host", HOST, "--port", String(port), "--reload"],
    {
      cwd: nlSearchDir,
      env: { ...process.env, NL_SEARCH_PORT: String(port) },
      stdio: "inherit",
    },
  );

  child.on("exit", (code) => process.exit(code ?? 1));
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
