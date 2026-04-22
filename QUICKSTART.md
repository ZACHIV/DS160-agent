# DS-160 表单助手 - 快速启动指南

自动化美国签证 DS-160 表单填写工具。

## 系统要求

- Python 3.10+
- Google Chrome 或 Chromium（已安装）
- uv 包管理器或 pip

## 安装

### 1. 创建虚拟环境并安装依赖

```bash
cd /home/zhangzheng/0_platform/personal/idea/amercican_visa

# 使用 uv（推荐，更快）
uv venv
source .venv/bin/activate
uv pip install fastapi uvicorn

# 或使用 pip
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn
```

## 启动流程

### 第 1 步：启动 Chrome（开启远程调试）

```bash
DISPLAY=:1 /opt/google/chrome/chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/home/zhangzheng/0_platform/personal/idea/amercican_visa/.visible-browser-profile \
  --no-first-run \
  --disable-extensions \
  https://ceac.state.gov/genniv/
```

**或简单地用这个命令**（如果已安装 google-chrome）：
```bash
google-chrome --remote-debugging-port=9222 https://ceac.state.gov/genniv/ &
```

> ⚠️ **重要**：确保 Chrome 完全加载后再进行下一步

### 第 2 步：启动本地服务器

在**新终端标签**中：

```bash
cd /home/zhangzheng/0_platform/personal/idea/amercican_visa

# 激活虚拟环境
source .venv/bin/activate

# 启动服务
PYTHONPATH=src python -m visa_agent.server
```

你应该看到：
```
INFO:     Uvicorn running on http://127.0.0.1:8765
```

### 第 3 步：打开前端网页

在浏览器中打开：
```
file:///home/zhangzheng/0_platform/personal/idea/amercican_visa/app/ds160-assistant.html
```

或直接点击 Chrome 浏览器的地址栏，输入上述路径。

## 使用说明

### 前端界面

1. **连接状态**：
   - 🟢 **已连接 ✓** - 服务和 Chrome 连接正常
   - 🟡 **已连接 (无DS-160标签)** - 服务运行，但 Chrome 未打开 DS-160 表单
   - 🔴 **服务未启动** - 本地服务未运行

2. **一键填入当前页** - 点击自动填写当前 DS-160 页面的所有字段
3. **保存当前页** - 点击保存按钮保存当前页进度
4. **重置标记** - 清除页面完成标记

### 工作流程

1. 在 Chrome 中导航到 DS-160 表单页面
2. 前端自动检测当前页面（左侧导航显示当前页面名称）
3. 点击"一键填入当前页"按钮
4. 等待 1-2 秒，字段会自动填写
5. 如果有错误提示（如缺少字段），手动修正后点击"保存当前页"
6. 继续到下一页

### 支持的页面

✅ 已实现：
- Personal Information (个人信息)
- Passport (护照)
- Travel Plans (旅行计划)
- Travel Companions (旅行同伴)
- Previous U.S. Travel (之前的美国旅行)
- Address & Phone (地址和电话)
- Employment (工作)
- Family (家庭)
- Security Background (安全背景)

## 配置

### 修改申请人信息

编辑 `sample_data/china_b1b2_sample.json`：

```json
{
  "case_id": "CN-B1B2-001",
  "identity": {
    "surname": "ZHANG",
    "given_names": "WEI",
    "date_of_birth": "1990-08-15",
    ...
  }
}
```

### 修改服务端口

编辑 `src/visa_agent/server.py` 最后几行：

```python
uvicorn.run(
    "visa_agent.server:app",
    host="127.0.0.1",
    port=8765,  # <-- 修改这里
    ...
)
```

然后重启服务。

## 故障排除

### 问题：连接失败 "Chrome not reachable on CDP port"

**解决**：
1. 确保 Chrome 已启动并指定了 `--remote-debugging-port=9222`
2. 检查端口是否被占用：
   ```bash
   ss -tlnp | grep 9222
   ```
3. 杀死旧 Chrome 进程：
   ```bash
   pkill -f "chrome.*9222"
   ```
4. 重新启动 Chrome

### 问题：页面无法检测

**解决**：
1. 确认 Chrome 显示的是 DS-160 表单页面
2. 检查浏览器开发者工具（F12）是否有 JS 错误
3. 尝试刷新页面

### 问题：字段填写失败

**解决**：
1. 检查前端提示的"缺失字段"，可能需要手动填写某些内容
2. 等待 2 秒让表单刷新
3. 查看浏览器控制台（F12）的网络请求错误

## 开发者注意

### 项目结构

```
.
├── app/                          # 前端 (HTML/CSS/JS)
│   ├── ds160-assistant.html
│   ├── ds160-assistant.js
│   ├── ds160-assistant.css
│   └── data/draft_bundle.js      # 自动生成
├── src/visa_agent/
│   ├── server.py                 # FastAPI 本地服务
│   ├── schema.py                 # 数据模型
│   ├── mapping.py                # 字段映射
│   ├── planner.py                # 执行计划
│   └── browser/
│       ├── cdp_client.py         # Chrome DevTools Protocol
│       ├── live_form_fill.py     # 表单填写逻辑
│       ├── locators.py           # 页面选择器
│       └── ...
└── sample_data/
    └── china_b1b2_sample.json    # 示例申请人数据
```

### 添加新页面支持

1. 在 `src/visa_agent/browser/live_form_fill.py` 中添加 `fill_xxx_page()` 函数
2. 在 `src/visa_agent/browser/locators.py` 中添加页面的选择器和字段
3. 在 `_PAGE_FILL_HANDLERS` 字典中注册处理函数

## 许可

仅用于教学和个人使用。

## 联系

有问题或建议，请查看项目文档。
