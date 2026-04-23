# Step 2: 变量绑定引擎重构规范

## 目标
废弃逻辑或回退，改用显式存在性检查，严格区分 None（未绑定）与合法假值，返回三元组供下游直接消费。

## 核心问题

### 当前缺陷

1. **使用 `or` 逻辑回退**
   ```python
   # ❌ 错误：将 0/false/"" 误判为缺失
   value = context.get(var) or DEFAULT_VALUES.get(var)
   ```

2. **返回布尔值而非解析值**
   ```python
   # ❌ 错误：下游无法获取实际值
   def _check_variable_bound(self, var: str) -> bool:
       value = context.get(var)
       return value is not None
   ```

3. **关键/非关键变量路由混杂**
   ```python
   # ❌ 错误：缺乏分级处置
   if value is None:
       default_value = DEFAULT_VALUES.get(var)
       return default_value is not None
   ```

## 修复方案

### 1. 显式存在性检查

**原则**：`None` = 未绑定，`0`/`False`/`""` = 已绑定但为假值

**实现**：
```python
from typing import Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum

class BindingStatus(Enum):
    """变量绑定状态"""
    BOUND = "bound"                    # 已绑定（包括假值）
    UNBOUND_CRITICAL = "unbound_critical"  # 未绑定（关键变量）
    UNBOUND_NON_CRITICAL = "unbound_non_critical"  # 未绑定（非关键变量）
    DEFAULT_USED = "default_used"      # 使用默认值

@dataclass
class BindingResult:
    """变量绑定结果（三元组）"""
    resolved_value: Any              # 解析后的值（供下游直接消费）
    binding_status: BindingStatus    # 绑定状态
    warning_msg: Optional[str] = None  # 警告消息（非关键变量使用默认值时）

class VariableBindingEngine:
    """变量绑定引擎（显式存在性检查）"""

    # 关键变量白名单（缺失直接阻断）
    CRITICAL_VARIABLES = {
        "plan.id",
        "user.role",
        "stage.name"
    }

    # 非关键变量默认值
    DEFAULT_VALUES = {
        "project.security_level": "standard",
        "user.role": "developer",
        "stage.name": "unknown",
        "task.id": None  # 将自动生成
    }

    def resolve_variable(
        self,
        var: str,
        context: dict,
        trace_id: str,
        config_version: str
    ) -> BindingResult:
        """
        解析变量绑定（显式存在性检查）

        Args:
            var: 变量名
            context: 运行时上下文
            trace_id: 链路追踪 ID
            config_version: 配置版本

        Returns:
            BindingResult: (resolved_value, binding_status, warning_msg)
        """
        # 1. 显式存在性检查（区分 None 与假值）
        if var not in context:
            # 变量未绑定（不在上下文中）
            return self._handle_unbound_variable(
                var, trace_id, config_version
            )

        value = context[var]

        # 2. 区分 None（未绑定）与假值
        if value is None:
            # 显式 None：视为未绑定
            return self._handle_unbound_variable(
                var, trace_id, config_version
            )

        # 3. 已绑定（包括假值 0/False/""）
        return BindingResult(
            resolved_value=value,  # 原样透传（包括假值）
            binding_status=BindingStatus.BOUND,
            warning_msg=None
        )

    def _handle_unbound_variable(
        self,
        var: str,
        trace_id: str,
        config_version: str
    ) -> BindingResult:
        """处理未绑定变量"""
        # 1. 关键变量缺失：阻断启动
        if var in self.CRITICAL_VARIABLES:
            raise ConfigError(
                f"CFG-005: 关键变量 {var} 未绑定，无法启动",
                trace_id=trace_id,
                config_version=config_version,
                variable=var,
                severity="block"
            )

        # 2. 非关键变量：使用默认值
        default_value = self.DEFAULT_VALUES.get(var)

        if default_value is not None:
            # 有默认值：注入 + warn 日志
            warning_msg = (
                f"变量 {var} 未绑定，使用默认值: {default_value}"
            )

            # 写入审计日志
            self._log_warning(
                warning_msg,
                trace_id=trace_id,
                config_version=config_version,
                code="CFG-005",
                severity="warn"
            )

            return BindingResult(
                resolved_value=default_value,
                binding_status=BindingStatus.DEFAULT_USED,
                warning_msg=warning_msg
            )

        # 3. 无默认值：自动生成（如 task.id）
        if var == "task.id":
            import uuid
            generated_value = str(uuid.uuid4())

            warning_msg = f"变量 {var} 未绑定，自动生成: {generated_value}"

            self._log_warning(
                warning_msg,
                trace_id=trace_id,
                config_version=config_version,
                code="CFG-005",
                severity="warn"
            )

            return BindingResult(
                resolved_value=generated_value,
                binding_status=BindingStatus.DEFAULT_USED,
                warning_msg=warning_msg
            )

        # 4. 其他非关键变量：返回 None
        return BindingResult(
            resolved_value=None,
            binding_status=BindingStatus.UNBOUND_NON_CRITICAL,
            warning_msg=f"变量 {var} 未绑定且无默认值"
        )

    def _log_warning(
        self,
        message: str,
        trace_id: str,
        config_version: str,
        code: str,
        severity: str
    ):
        """写入审计日志"""
        import json
        from datetime import datetime
        from pathlib import Path

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "trace_id": trace_id,
            "config_version": config_version,
            "code": code,
            "severity": severity,
            "message": message
        }

        # 写入审计日志文件
        log_file = Path("artifacts/audit_log.jsonl")
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
```

### 2. 假值透传验证

**测试用例**：
```python
def test_falsy_value_passthrough():
    """测试假值透传"""
    engine = VariableBindingEngine()

    # 测试 0
    result = engine.resolve_variable(
        "threshold",
        {"threshold": 0},
        trace_id="test-001",
        config_version="1.0.0"
    )
    assert result.resolved_value == 0  # 保留原值
    assert result.binding_status == BindingStatus.BOUND

    # 测试 False
    result = engine.resolve_variable(
        "enabled",
        {"enabled": False},
        trace_id="test-001",
        config_version="1.0.0"
    )
    assert result.resolved_value == False  # 保留原值
    assert result.binding_status == BindingStatus.BOUND

    # 测试 ""
    result = engine.resolve_variable(
        "name",
        {"name": ""},
        trace_id="test-001",
        config_version="1.0.0"
    )
    assert result.resolved_value == ""  # 保留原值
    assert result.binding_status == BindingStatus.BOUND
```

### 3. 关键变量阻断

**测试用例**：
```python
def test_critical_variable_blocking():
    """测试关键变量缺失阻断"""
    engine = VariableBindingEngine()

    # plan.id 缺失
    with pytest.raises(ConfigError, match="CFG-005"):
        engine.resolve_variable(
            "plan.id",
            {},  # 空上下文
            trace_id="test-001",
            config_version="1.0.0"
        )

    # user.role 缺失
    with pytest.raises(ConfigError, match="CFG-005"):
        engine.resolve_variable(
            "user.role",
            {},
            trace_id="test-001",
            config_version="1.0.0"
        )
```

### 4. 非关键变量默认值

**测试用例**：
```python
def test_non_critical_variable_default():
    """测试非关键变量默认值注入"""
    engine = VariableBindingEngine()

    # project.security_level 缺失
    result = engine.resolve_variable(
        "project.security_level",
        {},  # 空上下文
        trace_id="test-001",
        config_version="1.0.0"
    )

    assert result.resolved_value == "standard"  # 默认值
    assert result.binding_status == BindingStatus.DEFAULT_USED
    assert result.warning_msg is not None  # 有警告消息
    assert "使用默认值" in result.warning_msg
```

## 使用示例

### 正常路径

```python
# 初始化变量绑定引擎
engine = VariableBindingEngine()

# 解析变量
context = {
    "plan.id": "plan-001",
    "user.role": "developer",
    "stage.name": "executing",
    "threshold": 0,  # 假值
    "enabled": False  # 假值
}

# 解析 threshold（假值透传）
result = engine.resolve_variable(
    "threshold",
    context,
    trace_id="trace-001",
    config_version="1.0.0"
)

print(result.resolved_value)  # 0（保留原值）
print(result.binding_status)  # BindingStatus.BOUND
print(result.warning_msg)  # None

# 解析 project.security_level（使用默认值）
result = engine.resolve_variable(
    "project.security_level",
    context,
    trace_id="trace-001",
    config_version="1.0.0"
)

print(result.resolved_value)  # "standard"（默认值）
print(result.binding_status)  # BindingStatus.DEFAULT_USED
print(result.warning_msg)  # "变量 project.security_level 未绑定，使用默认值: standard"
```

### 异常路径

```python
# 关键变量缺失
try:
    result = engine.resolve_variable(
        "plan.id",
        {},  # 空上下文
        trace_id="trace-001",
        config_version="1.0.0"
    )
except ConfigError as e:
    print(e.message)  # "CFG-005: 关键变量 plan.id 未绑定，无法启动"
    print(e.trace_id)  # "trace-001"
    print(e.config_version)  # "1.0.0"
    print(e.severity)  # "block"
```

## 验收标准

- [x] 废弃 `or` 逻辑回退
- [x] 使用显式存在性检查（`is None` 或 `not in context`）
- [x] 假值（`0`/`False`/`""`）原样透传
- [x] 返回三元组 `(resolved_value, binding_status, warning_msg)`
- [x] 关键变量缺失精准阻断
- [x] 非关键变量注入默认值 + warn 日志
- [x] 审计日志绑定 trace_id / config_version

## 性能要求

- 单个变量解析耗时 < 10ms
- 批量解析（100 个变量）耗时 < 500ms
- 审计日志写入耗时 < 50ms

## 与 Step 1 集成

变量绑定引擎必须与 Step 1 的标识符清洗集成：

```python
# 1. 清洗变量名
cleaned_var = var.strip()

# 2. 清洗上下文键/值
cleaned_context = clean_config_dict(context)

# 3. 解析变量
result = engine.resolve_variable(
    cleaned_var,
    cleaned_context,
    trace_id=trace_id,
    config_version=config_version
)
```
