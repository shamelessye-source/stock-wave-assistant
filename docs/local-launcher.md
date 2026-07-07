# 本地启动说明

本项目是本地 Web 应用。脚本只在当前机器启动后端和前端，不创建云端服务，不注册后台常驻进程，也不替代现有开发命令。

## 首次准备

在项目根目录运行：

```powershell
py -m pip install -e ".[test]"
npm.cmd install
Copy-Item .env.example .env
```

如果需要手动验证真实 AkShare 数据源，再安装可选依赖并显式开启 provider。默认本地启动仍使用 mock/fake 模式。

## 一键启动

```powershell
scripts\start-local.ps1
```

脚本会执行以下检查和动作：

- 检查 `py`、`node`、`npm.cmd` 是否可用。
- 检查 Python 和 Node 依赖是否已安装。
- 检查 `8000` 和 `5173` 端口是否空闲。
- 启动 FastAPI 后端。
- 启动 Vite 前端。
- 打开 `http://127.0.0.1:5173`。
- 把本次启动的进程信息写入 `.local/local-launcher.json`。

## 停止应用

```powershell
scripts\stop-local.ps1
```

停止脚本只读取 `.local/local-launcher.json` 中记录的 PID，并校验命令行特征后停止对应进程。它不会按进程名批量结束所有 Python 或 Node 进程。

## 端口冲突

如果端口已被占用，启动脚本会停止并提示。可以先运行：

```powershell
scripts\stop-local.ps1
```

也可以指定空闲端口：

```powershell
scripts\start-local.ps1 -ApiPort 8001 -WebPort 5174
```

## 开发启动

开发者仍可使用原有命令分别启动后端和前端：

```powershell
py -m uvicorn app.main:app --host 127.0.0.1 --port 8000
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

一键脚本只是本地使用入口，不删除也不替代这些开发命令。

## 桌面快捷方式

本阶段不提供 `create-shortcut.ps1`。如果后续需要双击启动，可以在独立任务中增加桌面快捷方式脚本；当前本地启动入口仍是 `scripts\start-local.ps1`。
