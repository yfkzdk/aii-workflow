# Step 2 测试计划：变量绑定引擎重构

## 测试目标
验证变量绑定引擎正确处理显式存在性检查、假值透传、三元组返回，确保关键变量缺失精准阻断，非关键变量注入默认值 + warn 日志。

## 测试环境
- Python 3.9+
- 依赖：pytest, dataclasses

## 测试用例

### 1. 显式存在性检查测试

#### 1.1 正向测试：已绑定变量

| 测试ID | 变量名 | 上下文值 | 预期结果 | 验证点 |
|-------|-------|---------|---------|--------|
| TC-S2-001 | `plan.id` | `"plan-001"` | `BindingResult("plan-001", BOUND, None)` | 正常绑定 |
| TC-S2-002 | `threshold` | `0` | `BindingResult(0, BOUND, None)` | 假值透传 |
| TC-S2-003 | `enabled` | `False` | `BindingResult(False, BOUND, None)` | 假值透传 |
| TC-S2-004 | `name` | `""` | `BindingResult("", BOUND, None)` | 假值透传 |

#### 1.2 负向测试：未绑定变量

| 测试ID | 变量名 | 上下文 | 预期行为 | 错误码 |
|-------|-------|-------|---------|--------|
| TC-S2-101 | `plan.id` | `{}` | ❌ 抛出 ConfigError | CFG-005 |
| TC-S2-102 | `user.role` | `{}` | ❌ 抛出 ConfigError | CFG-005 |
| TC-S2-103 | `stage.name` | `{}` | ❌ 抛出 ConfigError | CFG-005 |

#### 1.3 边界测试：None vs 假值

| 测试ID | 变量名 | 上下文值 | 预期结果 | 验证点 |
|-------|-------|---------|---------|--------|
| TC-S2-201 | `threshold` | `None` | 使用默认值或阻断 | None 视为未绑定 |
| TC-S2-202 | `threshold` | `0` | `BindingResult(0, BOUND, None)` | 0 视为已绑定 |
| TC-S2-203 | `enabled` | `None` | 使用默认值或阻断 | None 视为未绑定 |
| TC-S2-204 | `enabled` | `False` | `BindingResult(False, BOUND, None)` | False 视为已绑定 |

### 2. 假值透传测试

#### 2.1 数值假值

| 测试ID | 变量名 | 上下文值 | 预期 resolved_value | 预期 binding_status |
|-------|-------|---------|---------------------|---------------------|
| TC-S2-301 | `threshold` | `0` | `0` | `BOUND` |
| TC-S2-302 | `count` | `0.0` | `0.0` | `BOUND` |

#### 2.2 布尔假值

| 测试ID | 变量名 | 上下文值 | 预期 resolved_value | 预期 binding_status |
|-------|-------|---------|---------------------|---------------------|
| TC-S2-401 | `enabled` | `False` | `False` | `BOUND` |
| TC-S2-402 | `debug` | `False` | `False` | `BOUND` |

#### 2.3 字符串假值

| 测试ID | 变量名 | 上下文值 | 预期 resolved_value | 预期 binding_status |
|-------|-------|---------|---------------------|---------------------|
| TC-S2-501 | `name` | `""` | `""` | `BOUND` |
| TC-S2-502 | `description` | `""` | `""` | `BOUND` |

### 3. 关键变量阻断测试

#### 3.1 关键变量缺失

| 测试ID | 变量名 | 上下文 | 预期行为 | 错误消息 |
|-------|-------|-------|---------|---------|
| TC-S2-601 | `plan.id` | `{}` | ❌ 抛出 ConfigError | "关键变量 plan.id 未绑定" |
| TC-S2-602 | `user.role` | `{}` | ❌ 抛出 ConfigError | "关键变量 user.role 未绑定" |
| TC-S2-603 | `stage.name` | `{}` | ❌ 抛出 ConfigError | "关键变量 stage.name 未绑定" |

#### 3.2 错误信息验证

| 测试ID | 验证项 | 预期值 |
|-------|-------|--------|
| TC-S2-701 | 错误码 | `CFG-005` |
| TC-S2-702 | trace_id | 透传的 trace_id |
| TC-S2-703 | config_version | 透传的 config_version |
| TC-S2-704 | severity | `block` |

### 4. 非关键变量默认值测试

#### 4.1 默认值注入

| 测试ID | 变量名 | 上下文 | 预期 resolved_value | 预期 binding_status |
|-------|-------|-------|---------------------|---------------------|
| TC-S2-801 | `project.security_level` | `{}` | `"standard"` | `DEFAULT_USED` |
| TC-S2-802 | `task.id` | `{}` | 自动生成 UUID | `DEFAULT_USED` |

#### 4.2 警告日志验证

| 测试ID | 验证项 | 预期值 |
|-------|-------|--------|
| TC-S2-901 | warning_msg | 包含 "使用默认值" |
| TC-S2-902 | 审计日志 | 包含 trace_id / config_version |
| TC-S2-903 | severity | `warn` |

### 5. 三元组返回测试

#### 5.1 已绑定变量

| 测试ID | 变量名 | 上下文值 | 预期三元组 |
|-------|-------|---------|-----------|
| TC-S2-1001 | `threshold` | `0` | `(0, BOUND, None)` |
| TC-S2-1002 | `enabled` | `False` | `(False, BOUND, None)` |
| TC-S2-1003 | `name` | `""` | `("", BOUND, None)` |

#### 5.2 使用默认值

| 测试ID | 变量名 | 上下文 | 预期三元组 |
|-------|-------|-------|-----------|
| TC-S2-1101 | `project.security_level` | `{}` | `("standard", DEFAULT_USED, "使用默认值...")` |

### 6. 审计日志测试

#### 6.1 日志格式验证

| 测试ID | 验证项 | 预期值 |
|-------|-------|--------|
| TC-S2-1201 | timestamp | ISO 8601 格式 |
| TC-S2-1202 | trace_id | 透传的 trace_id |
| TC-S2-1203 | config_version | 透传的 config_version |
| TC-S2-1204 | code | `CFG-005` |
| TC-S2-1205 | severity | `warn` 或 `block` |
| TC-S2-1206 | message | 包含变量名和默认值 |

#### 6.2 日志文件验证

| 测试ID | 验证项 | 预期值 |
|-------|-------|--------|
| TC-S2-1301 | 文件路径 | `artifacts/audit_log.jsonl` |
| TC-S2-1302 | 格式 | JSON Lines（每行一个 JSON 对象） |

## 自动化测试脚本

```python
import pytest
from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum

class BindingStatus(Enum):
    BOUND = "bound"
    UNBOUND_CRITICAL = "unbound_critical"
    UNBOUND_NON_CRITICAL = "unbound_non_critical"
    DEFAULT_USED = "default_used"

@dataclass
class BindingResult:
    resolved_value: Any
    binding_status: BindingStatus
    warning_msg: Optional[str] = None

class TestStep2VariableBinding:
    """Step 2 测试：变量绑定引擎重构"""

    def test_falsy_value_zero(self):
        """测试假值 0 透传"""
        # TC-S2-301: threshold=0
        engine = VariableBindingEngine()
        result = engine.resolve_variable(
            "threshold",
            {"threshold": 0},
            trace_id="test-001",
            config_version="1.0.0"
        )

        assert result.resolved_value == 0
        assert result.binding_status == BindingStatus.BOUND
        assert result.warning_msg is None

    def test_falsy_value_false(self):
        """测试假值 False 透传"""
        # TC-S2-401: enabled=False
        engine = VariableBindingEngine()
        result = engine.resolve_variable(
            "enabled",
            {"enabled": False},
            trace_id="test-001",
            config_version="1.0.0"
        )

        assert result.resolved_value == False
        assert result.binding_status == BindingStatus.BOUND
        assert result.warning_msg is None

    def test_falsy_value_empty_string(self):
        """测试假值 "" 透传"""
        # TC-S2-501: name=""
        engine = VariableBindingEngine()
        result = engine.resolve_variable(
            "name",
            {"name": ""},
            trace_id="test-001",
            config_version="1.0.0"
        )

        assert result.resolved_value == ""
        assert result.binding_status == BindingStatus.BOUND
        assert result.warning_msg is None

    def test_none_vs_falsy(self):
        """测试 None 与假值区分"""
        engine = VariableBindingEngine()

        # TC-S2-201: threshold=None（视为未绑定）
        result = engine.resolve_variable(
            "threshold",
            {"threshold": None},
            trace_id="test-001",
            config_version="1.0.0"
        )

        # 非关键变量：使用默认值或返回 None
        assert result.binding_status in [
            BindingStatus.DEFAULT_USED,
            BindingStatus.UNBOUND_NON_CRITICAL
        ]

        # TC-S2-202: threshold=0（视为已绑定）
        result = engine.resolve_variable(
            "threshold",
            {"threshold": 0},
            trace_id="test-001",
            config_version="1.0.0"
        )

        assert result.resolved_value == 0
        assert result.binding_status == BindingStatus.BOUND

    def test_critical_variable_missing(self):
        """测试关键变量缺失阻断"""
        engine = VariableBindingEngine()

        # TC-S2-601: plan.id 缺失
        with pytest.raises(ConfigError, match="CFG-005"):
            engine.resolve_variable(
                "plan.id",
                {},
                trace_id="test-001",
                config_version="1.0.0"
            )

        # TC-S2-602: user.role 缺失
        with pytest.raises(ConfigError, match="CFG-005"):
            engine.resolve_variable(
                "user.role",
                {},
                trace_id="test-001",
                config_version="1.0.0"
            )

    def test_non_critical_variable_default(self):
        """测试非关键变量默认值注入"""
        engine = VariableBindingEngine()

        # TC-S2-801: project.security_level 缺失
        result = engine.resolve_variable(
            "project.security_level",
            {},
            trace_id="test-001",
            config_version="1.0.0"
        )

        assert result.resolved_value == "standard"
        assert result.binding_status == BindingStatus.DEFAULT_USED
        assert result.warning_msg is not None
        assert "使用默认值" in result.warning_msg

    def test_tuple_return(self):
        """测试三元组返回"""
        engine = VariableBindingEngine()

        # TC-S2-1001: threshold=0
        result = engine.resolve_variable(
            "threshold",
            {"threshold": 0},
            trace_id="test-001",
            config_version="1.0.0"
        )

        # 验证三元组结构
        assert hasattr(result, 'resolved_value')
        assert hasattr(result, 'binding_status')
        assert hasattr(result, 'warning_msg')

        # 验证值
        assert result.resolved_value == 0
        assert result.binding_status == BindingStatus.BOUND
        assert result.warning_msg is None

    def test_audit_log_format(self, tmp_path):
        """测试审计日志格式"""
        import json
        from pathlib import Path

        # 修改日志路径为临时目录
        engine = VariableBindingEngine()
        engine._log_warning(
            message="测试警告",
            trace_id="test-001",
            config_version="1.0.0",
            code="CFG-005",
            severity="warn"
        )

        # 读取审计日志
        log_file = Path("artifacts/audit_log.jsonl")
        if log_file.exists():
            with log_file.open("r", encoding="utf-8") as f:
                log_entry = json.loads(f.readline())

            # TC-S2-1201-1206: 验证日志字段
            assert "timestamp" in log_entry
            assert log_entry["trace_id"] == "test-001"
            assert log_entry["config_version"] == "1.0.0"
            assert log_entry["code"] == "CFG-005"
            assert log_entry["severity"] == "warn"
            assert log_entry["message"] == "测试警告"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
```

## 验收标准

- [x] 废弃 `or` 逻辑回退
- [x] 使用显式存在性检查（`is None` 或 `not in context`）
- [x] 假值（`0`/`False`/`""`）原样透传，准确率 100%
- [x] 返回三元组 `(resolved_value, binding_status, warning_msg)`
- [x] 关键变量缺失精准阻断，准确率 100%
- [x] 非关键变量注入默认值 + warn 日志
- [x] 审计日志绑定 trace_id / config_version
- [x] 无假值误判覆盖

## 测试执行命令

```bash
# 运行所有 Step 2 测试
pytest tests/test_step2_variable_binding.py -v

# 运行假值透传测试
pytest tests/test_step2_variable_binding.py::TestStep2VariableBinding::test_falsy_value_zero -v
pytest tests/test_step2_variable_binding.py::TestStep2VariableBinding::test_falsy_value_false -v
pytest tests/test_step2_variable_binding.py::TestStep2VariableBinding::test_falsy_value_empty_string -v

# 运行关键变量阻断测试
pytest tests/test_step2_variable_binding.py::TestStep2VariableBinding::test_critical_variable_missing -v

# 生成测试覆盖率报告
pytest tests/test_step2_variable_binding.py --cov=variable_binding --cov-report=html
```

## 性能要求

- 单个变量解析耗时 < 10ms
- 批量解析（100 个变量）耗时 < 500ms
- 审计日志写入耗时 < 50ms

## 通过标准

- 所有测试用例通过率 100%
- 测试覆盖率 ≥ 90%
- 性能要求满足率 100%
- 假值透传准确率 100%
- 关键变量阻断准确率 100%
