实现一个完整的FastAPI限流中间件

需求：编写一个可复用的FastAPI限流中间件，用于保护API端点。

**功能要求**：
1. 基于IP地址的令牌桶算法限流
2. 支持全局限制和端点级限制
3. 可配置的限制参数（请求数/时间窗口）
4. 返回标准的HTTP 429状态码和消息
5. 使用Redis作为存储后端（可选内存存储回退）

**技术约束**：
1. 使用Python 3.8+和FastAPI框架
2. 支持异步操作
3. 包含完整的类型注解
4. 提供使用示例和测试用例
5. 代码必须符合PEP 8规范

**文件结构**：
- `artifacts/code/rate_limiter.py` - 主限流器实现
- `artifacts/code/example_usage.py` - 使用示例
- `artifacts/code/test_rate_limiter.py` - 单元测试
- `artifacts/code/requirements.txt` - 依赖说明

**验收标准**：
1. 代码能够通过Python语法检查
2. 限流逻辑正确实现
3. 包含完整的文档字符串
4. 提供至少3个测试用例