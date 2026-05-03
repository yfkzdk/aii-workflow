# API 配置完整指南

## 当前状态

✅ 系统已完全优化完成
✅ 74/74 测试通过
✅ Mock 模式可用
⚠️ API 连接超时（需要配置）

## 问题分析

两个 API key 都连接超时，可能原因：

1. **网络限制**: 如果在中国大陆，无法直接访问 OpenAI API
2. **需要代理**: 可能需要配置 HTTP 代理
3. **API 服务商**: 这些 key 可能属于其他 OpenAI 兼容服务

## 解决方案

### 方案 1: 使用 Mock 模式（立即可用）

系统已支持完整的 Mock 测试，无需真实 API：

```bash
# 运行 demo（Mock 模式）
python demo/demo_phase3.py

# 运行所有测试
python -m pytest tests/ -v

# 运行覆盖率测试
pytest --cov=core --cov-report=html tests/
```

**优点**: 无需配置，立即可用
**缺点**: 不会调用真实 LLM

---

### 方案 2: 配置代理（如果你有代理）

如果你有 HTTP 代理，可以这样配置：

**Windows CMD:**
```cmd
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
python demo/demo_phase3.py
```

**Windows PowerShell:**
```powershell
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
python demo/demo_phase3.py
```

**Linux/macOS:**
```bash
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
python demo/demo_phase3.py
```

---

### 方案 3: 使用国内 OpenAI 兼容服务

如果你使用的是国内的 OpenAI 兼容服务（如 API2D、CloseAI 等），需要配置 base_url：

**步骤 1: 编辑 `.env` 文件**

```bash
# 打开 .env 文件
notepad .env
```

**步骤 2: 添加 base_url 配置**

```env
OPENAI_API_KEY=sk-9909ab0c8d534f45be16968071a875ba
OPENAI_BASE_URL=https://your-service-url/v1
OPENAI_MODEL=gpt-3.5-turbo
```

**常见服务商的 base_url:**
- API2D: `https://api2d.com/v1`
- CloseAI: `https://api.closeai-proxy.xyz/v1`
- OpenAI-SB: `https://api.openai-sb.com/v1`

---

### 方案 4: 使用 Anthropic Claude API（原设计）

如果你想使用原设计的 Claude API：

**步骤 1: 获取 Claude API key**
- 访问 https://console.anthropic.com/
- 注册并获取 `sk-ant-` 格式的 API key

**步骤 2: 安装 Anthropic SDK**
```bash
pip install anthropic
```

**步骤 3: 配置环境变量**
```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

---

## 快速测试

### 测试 Mock 模式
```bash
cd "O:/AII/上下文助手/"
python demo/demo_phase3.py
```

### 测试 API 连接
```bash
python core/openai_caller.py
```

---

## 我的建议

**推荐顺序:**

1. **先体验 Mock 模式** → 了解系统功能
2. **配置代理或 base_url** → 如果你有相关资源
3. **获取 Claude API key** → 使用原设计的 API

---

## 需要帮助？

请告诉我：
1. 你是否有 HTTP 代理？
2. 这些 API key 是哪个服务商的？
3. 是否需要我帮你配置特定的 base_url？
4. 或者先使用 Mock 模式体验系统？

---

**当前配置文件位置:**
- API key: `.env`
- 代理设置: 环境变量
- 系统配置: `config/`

**测试状态:**
- ✅ Mock 模式: 可用
- ⏳ 真实 API: 需要配置
