import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(
    import.meta.url)), "..");
const nlSearchDir = path.join(projectRoot, "web", "nl-search");
const venvBin = path.join(nlSearchDir, ".venv", process.platform === "win32" ? "Scripts" : "bin");
const venvPython = path.join(venvBin, process.platform === "win32" ? "python.exe" : "python");
const pipIndex = "https://pypi.tuna.tsinghua.edu.cn/simple";
const DEFAULT_PORT = 8765;
const MAX_PORT_ATTEMPTS = 20;
const HOST = "127.0.0.1";

const REQUIREMENTS = [
    path.join(projectRoot, "web", "nl-search", "requirements.txt"),
    path.join(projectRoot, "web", "flight-watch", "requirements.txt"),
    path.join(projectRoot, "web", "billing", "requirements.txt"),
];

const RELOAD_DIRS = [
    path.join(projectRoot, "web", "gateway"),
    path.join(projectRoot, "web", "nl-search"),
    path.join(projectRoot, "web", "flight-watch"),
    path.join(projectRoot, "web", "billing"),
    path.join(projectRoot, "web", "shared"),
    path.join(projectRoot, "scripts"),
];

function ensureVenv() {
    if (!existsSync(venvPython)) {
        console.log("正在创建 Python 虚拟环境…");
        const venvResult = spawnSync("python3", ["-m", "venv", ".venv"], {
            cwd: nlSearchDir,
            stdio: "inherit",
        });
        if (venvResult.status !== 0) process.exit(venvResult.status ? ? 1);
    }

    for (const req of REQUIREMENTS) {
        const pipResult = spawnSync(
            venvPython, ["-m", "pip", "install", "-r", req, "-i", pipIndex], { cwd: nlSearchDir, stdio: "inherit" },
        );
        if (pipResult.status !== 0) process.exit(pipResult.status ? ? 1);
    }
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

function printRoutes(base) {
    console.log("");
    console.log("Flight Monitor Web（统一网关，与线上一致）");
    console.log(`  首页       ${base}/`);
    console.log(`  查价       ${base}/nl-search/`);
    console.log(`  监控       ${base}/flight-watch/`);
    console.log(`  使用说明   ${base}/billing/`);
    console.log(`  Skill ${base}/skill/`);
    console.log("");
}

async function main() {
    ensureVenv();

    const preferredPort = Number(process.env.NL_SEARCH_PORT) || DEFAULT_PORT;
    const port = await findAvailablePort(preferredPort);

    if (port !== preferredPort) {
        console.log(`端口 ${preferredPort} 已被占用，改用 ${port}`);
    }

    const base = `http://${HOST}:${port}`;
    printRoutes(base);

    const uvicornArgs = [
        "-m",
        "uvicorn",
        "web.gateway.server:app",
        "--host",
        HOST,
        "--port",
        String(port),
        "--reload",
        ...RELOAD_DIRS.flatMap((dir) => ["--reload-dir", dir]),
    ];

    const child = spawn(venvPython, uvicornArgs, {
        cwd: projectRoot,
        env: {
            ...process.env,
            PYTHONPATH: projectRoot,
            WEB_ROOT: "/nl-search",
            NL_SEARCH_PORT: String(port),
        },
        stdio: "inherit",
    });

    child.on("exit", (code) => process.exit(code ? ? 1));
}

main().catch((err) => {
    console.error(err.message);
    process.exit(1);
});