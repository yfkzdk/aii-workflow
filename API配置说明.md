# API 配置说明

## 当前配置

你的 API key 已保存在 `.env` 文件中：
```
OPENAI_API_KEY=sk-bd05f1dfdc4544cb8073ee96d0792d68
```

## 可能的问题

API 连接超时，可能原因：

1. **网络访问限制**: 如果在中国大陆，可能无法直接访问 OpenAI API
2. **API 服务商**: 这个 key 可能属于其他 OpenAI 兼容服务（如国内的代理服务）
3. **需要代理**: 可能需要配置代理才能访问

## 解决方案

### 方案 1: 使用 Mock 模式（推荐新手）

系统已支持完整的 Mock 测试，无需真实 API：

```bash
# 运行 demo（Mock 模式）
python demo/demo_phase3.py

# 运行测试
python -m pytest tests/ -v
```

### 方案 2: 配置自定义 API 端点

如果你使用的是 OpenAI 兼容服务（如国内的代理），请告诉我：
- 服务商名称
- API base URL（如 `https://api.example.com/v1`）

我可以帮你配置。

### 方案 3: 使用 Anthropic Claude API

如果你想使用原设计的 Claude API，需要：
1. 访问 https://console.anthropic.com/
2. 获取 `sk-ant-` 格式的 API key
3. 我会帮你配置

### 方案 4: 配置代理

如果你有代理，可以这样设置：

```bash
# Windows CMD
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890

# Windows PowerShell
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"

# Linux/macOS
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
```

## 当前系统状态

✅ 系统已完全优化完成
✅ 74/74 测试通过
✅ Mock 模式可用
⚠️ 真实 API 需要配置

## 下一步

请告诉我：
1. 这个 API key 是哪个服务商的？
2. 是否需要配置代理？
3. 或者先使用 Mock 模式体验系统？
