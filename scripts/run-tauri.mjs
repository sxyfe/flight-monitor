import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const args = process.argv.slice(2);
const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const tauriCli = path.join(
  projectRoot,
  "node_modules",
  ".bin",
  process.platform === "win32" ? "tauri.cmd" : "tauri",
);

function cargoBinDir() {
  const home = os.homedir();
  return process.platform === "win32"
    ? path.join(home, ".cargo", "bin")
    : path.join(home, ".cargo", "bin");
}

function ensureCargoOnPath(env) {
  const cargoDir = cargoBinDir();
  const cargoName = process.platform === "win32" ? "cargo.exe" : "cargo";
  const cargoPath = path.join(cargoDir, cargoName);

  if (!existsSync(cargoPath)) {
    console.error(
      [
        "未找到 Rust 工具链 (cargo)。请先安装 Rust：",
        "  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
        "安装完成后重启终端，或执行：",
        "  source \"$HOME/.cargo/env\"",
      ].join("\n"),
    );
    process.exit(1);
  }

  const pathKey = process.platform === "win32" ? "Path" : "PATH";
  const currentPath = env[pathKey] ?? "";
  if (!currentPath.split(path.delimiter).includes(cargoDir)) {
    env[pathKey] = `${cargoDir}${path.delimiter}${currentPath}`;
  }

  return env;
}

const env = ensureCargoOnPath({ ...process.env });
const result = spawnSync(tauriCli, args, {
  cwd: projectRoot,
  env,
  stdio: "inherit",
  shell: process.platform === "win32",
});

process.exit(result.status ?? 1);
