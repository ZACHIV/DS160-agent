# DS-160 签证助手 Quickstart

China B1/B2 签证 DS-160 表格一键填写工具。

## 一键使用（推荐）

### 下载二进制包

从 Release 页面下载对应平台的 `ds160-assistant` 包，解压后：

```bash
# Linux / macOS
./ds160-assistant
```

首次运行会自动：
- 启动 Chrome 并打开 CEAC 签证申请页面
- 启动本地服务 (http://127.0.0.1:8765)
- 打开浏览器进入操作界面

只需安装 Chrome/Chromium 浏览器即可。Python 无需安装。

### 从源码构建

```bash
git clone <repo>
cd amercican_visa

# 安装依赖 + 构建
bash scripts/install-deps.sh
bash scripts/build.sh

# 运行
./dist/ds160-assistant/ds160-assistant
```

构建 onefile 单文件版本：
```bash
bash scripts/build.sh onefile
# 输出: dist/ds160-assistant (单个可执行文件)
```

## 开发环境

```bash
bash scripts/install-deps.sh

# 启动开发服务（require Chrome）
bash scripts/start.sh
# 打开 http://127.0.0.1:8765

# 或者手动启动
PYTHONPATH=src python -m visa_agent.server
```

## 使用流程

```
1. 打开 http://127.0.0.1:8765
2. 选择"填写资料" → 录入申请信息 → 导出 dossier JSON
3. 选择"开始填写" → 导入 dossier JSON
4. 在 Chrome 窗口中完成 CEAC 验证码
5. 点击"一键填入"开始自动填表
```

## 数据安全

- 导出资料可选择**加密导出**（AES-256-GCM），需要设置密码
- 导入加密文件时输入密码即可解密
- 加密/解密支持离线模式（浏览器端 Web Crypto API）

## Key Files

- `src/visa_agent/__main__.py` — 应用启动入口
- `src/visa_agent/server.py` — FastAPI 服务
- `src/visa_agent/encryption.py` — 加密模块
- `src/visa_agent/checkpoint.py` — 断点续填
- `src/visa_agent/audit_log.py` — 操作审计日志
- `src/visa_agent/browser/live_form_fill.py` — 表单填写引擎
- `app/intake.html` + `app/intake.js` — 资料采集页
- `app/ds160-assistant.html` + `app/ds160-assistant.js` — 自动填表页
- `docs/dossier.schema.json` — 申请资料规范
- `scripts/build.sh` — PyInstaller 构建脚本
- `scripts/start.sh` — 开发环境一键启动

## Verify

```bash
# 运行测试
PYTHONPATH=src python -m pytest tests/

# 检查服务
curl http://127.0.0.1:8765/status

# 检查 DOM 漂移
curl http://127.0.0.1:8765/dom-drift

# 查看审计日志
curl http://127.0.0.1:8765/audit-log
```
