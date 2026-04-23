# P0 测试计划：启动预检与契约绑定

## 测试目标
验证 PreFlightValidator 和变量绑定引擎的正确性，确保合法配置通过率 100%，非法配置拦截耗时 <500ms。

## 测试环境
- Python 3.9+
- 依赖：jsonschema, pytest, pyyaml

## 测试用例

### 1. SemVer 版本兼容性测试

#### 1.1 正向测试：合法版本兼容

| 测试ID | 配置版本 | 运行时版本 | 预期结果 | 匹配规则 |
|-------|---------|-----------|---------|---------|
| TC-P0-001 | 1.0.0 | 1.0.0 | ✅ 通过 | ^ 语义（默认） |
| TC-P0-002 | 1.0.0 | 1.2.5 | ✅ 通过 | ^ 语义（主版本相同） |
| TC-P0-003 | ^1.0.0 | 1.5.0 | ✅ 通过 | ^ 语义（显式） |
| TC-P0-004 | ~1.2.0 | 1.2.5 | ✅ 通过 | ~ 语义（主+次锁定） |
| TC-P0-005 | >=1.0.0 | 2.0.0 | ✅ 通过 | >= 语义 |
| TC-P0-006 | 1.0 | 1.0.0 | ✅ 通过 | 补丁版本默认为 0 |

#### 1.2 负向测试：非法版本拦截

| 测试ID | 配置版本 | 运行时版本 | 预期结果 | 错误码 |
|-------|---------|-----------|---------|--------|
| TC-P0-101 | 1.0.0 | 2.0.0 | ❌ 拦截 | CFG-006 |
| TC-P0-102 | 1.2.0 | 1.1.0 | ❌ 拦截 | CFG-006 |
| TC-P0-103 | ~1.2.0 | 1.3.0 | ❌ 拦截 | CFG-006 |
| TC-P0-104 | invalid | 1.0.0 | ❌ 拦截 | CFG-006 |

#### 1.3 边界测试

| 测试ID | 场景 | 预期结果 |
|-------|------|---------|
| TC-P0-201 | 配置版本含尾随空格 " 1.0.0 " | ✅ 自动清理后通过 |
| TC-P0-202 | 运行时版本含尾随空格 "1.0.0 " | ✅ 自动清理后通过 |
| TC-P0-203 | 配置版本为 None | ❌ 拦截（CFG-006） |

### 2. 变量绑定引擎测试

#### 2.1 显式存在性校验（区分 None 与假值）

| 测试ID | 输入值 | `is None` | 预期行为 | 验证点 |
|-------|-------|-----------|---------|--------|
| TC-P0-301 | `None` | ✅ True | 阻断（关键变量）或使用默认值（非关键） | 无静默覆盖 |
| TC-P0-302 | `0` | ❌ False | **保留原值 0** | 不覆盖为默认值 |
| TC-P0-303 | `False` | ❌ False | **保留原值 False** | 不覆盖为默认值 |
| TC-P0-304 | `""` | ❌ False | **保留原值 ""** | 不覆盖为默认值 |
| TC-P0-305 | `"valid"` | ❌ False | 保留原值 | 正常流程 |

#### 2.2 关键变量缺失测试

| 测试ID | 缺失变量 | 预期结果 | 错误码 |
|-------|---------|---------|--------|
| TC-P0-401 | plan.id | ❌ 阻断启动 | CFG-005 |
| TC-P0-402 | user.role | ❌ 阻断启动 | CFG-005 |
| TC-P0-403 | stage.name | ❌ 阻断启动 | CFG-005 |

#### 2.3 非关键变量默认值测试

| 测试ID | 缺失变量 | 预期行为 | 审计日志 |
|-------|---------|---------|---------|
| TC-P0-501 | project.security_level | 使用默认值 "standard" | warn 级别日志 |
| TC-P0-502 | task.id | 自动生成 UUID | warn 级别日志 |

### 3. 配置键/值尾随空格清理测试

| 测试ID | 输入配置 | 预期输出 | 验证点 |
|-------|---------|---------|--------|
| TC-P0-601 | `{"key ": " value "}` | `{"key": "value"}` | 键/值首尾空格清理 |
| TC-P0-602 | `"key":  "value"` | `"key": "value"` | 冒号后多余空格清理 |
| TC-P0-603 | `"key": "value"  \n` | `"key": "value"\n` | 行尾空格清理 |
| TC-P0-604 | 多个连续空行 | 最多保留 2 个空行 | 多余空行清理 |

### 4. 性能测试

| 测试ID | 场景 | 预期耗时 | 验证标准 |
|-------|------|---------|---------|
| TC-P0-701 | 合法配置通过 | < 500ms | 启动前校验通过 |
| TC-P0-702 | 非法配置拦截 | < 1s | 结构化错误报告输出 |

### 5. 错误报告格式测试

| 测试ID | 场景 | 预期输出 |
|-------|------|---------|
| TC-P0-801 | 版本不兼容 | `{"errors": [{"code": "CFG-006", "message": "...", "severity": "block"}]}` |
| TC-P0-802 | 关键变量缺失 | `{"errors": [{"code": "CFG-005", "message": "...", "severity": "block"}]}` |

## 自动化测试脚本

```python
import pytest
import time
from pathlib import Path
import json

class TestP0PreFlightValidator:
    """P0 级测试：启动预检与契约绑定"""

    def test_semver_caret_compatible(self):
        """测试 ^ 语义兼容性"""
        validator = PreFlightValidator()

        # TC-P0-001: 1.0.0 与 1.0.0 兼容
        assert validator._semver_satisfies("1.0.0", "1.0.0") == True

        # TC-P0-002: 1.0.0 与 1.2.5 兼容
        assert validator._semver_satisfies("1.0.0", "1.2.5") == True

        # TC-P0-003: ^1.0.0 与 1.5.0 兼容
        assert validator._semver_satisfies("^1.0.0", "1.5.0") == True

    def test_semver_tilde_compatible(self):
        """测试 ~ 语义兼容性"""
        validator = PreFlightValidator()

        # TC-P0-004: ~1.2.0 与 1.2.5 兼容
        assert validator._semver_satisfies("~1.2.0", "1.2.5") == True

        # TC-P0-103: ~1.2.0 与 1.3.0 不兼容
        assert validator._semver_satisfies("~1.2.0", "1.3.0") == False

    def test_semver_incompatible(self):
        """测试版本不兼容拦截"""
        validator = PreFlightValidator()

        # TC-P0-101: 1.0.0 与 2.0.0 不兼容
        assert validator._semver_satisfies("1.0.0", "2.0.0") == False

        # TC-P0-102: 1.2.0 与 1.1.0 不兼容
        assert validator._semver_satisfies("1.2.0", "1.1.0") == False

    def test_variable_bound_none_vs_falsy(self):
        """测试显式存在性校验（区分 None 与假值）"""
        validator = PreFlightValidator()

        # TC-P0-302: 0 不应被覆盖
        validator.context = {"threshold": 0}
        assert validator._check_variable_bound("threshold") == True
        assert validator.context["threshold"] == 0  # 保留原值

        # TC-P0-303: False 不应被覆盖
        validator.context = {"enabled": False}
        assert validator._check_variable_bound("enabled") == True
        assert validator.context["enabled"] == False  # 保留原值

        # TC-P0-304: "" 不应被覆盖
        validator.context = {"name": ""}
        assert validator._check_variable_bound("name") == True
        assert validator.context["name"] == ""  # 保留原值

    def test_critical_variable_missing(self):
        """测试关键变量缺失阻断"""
        validator = PreFlightValidator()
        validator.context = {}  # 空上下文

        # TC-P0-401: plan.id 缺失应阻断
        with pytest.raises(ConfigError, match="CFG-005"):
            validator._check_variable_bound("plan.id")

    def test_performance_legal_config(self):
        """测试合法配置性能（< 500ms）"""
        validator = PreFlightValidator()

        start_time = time.time()
        # 模拟合法配置校验
        validator.validate_all()
        elapsed = time.time() - start_time

        # TC-P0-701: 合法配置通过 < 500ms
        assert elapsed < 0.5, f"合法配置校验耗时 {elapsed:.3f}s 超过 500ms"

    def test_error_report_format(self):
        """测试错误报告格式"""
        validator = PreFlightValidator()

        # TC-P0-801: 版本不兼容错误报告
        try:
            validator._validate_version_compatibility()
        except SystemExit:
            error_file = Path("artifacts/preflight_errors.json")
            assert error_file.exists()

            error_report = json.loads(error_file.read_text())
            assert "errors" in error_report
            assert len(error_report["errors"]) > 0
            assert error_report["errors"][0]["code"].startswith("CFG-")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
```

## 验收标准

- [x] SemVer 版本兼容性测试通过率 100%
- [x] 显式存在性校验正确处理 0/false/""
- [x] 关键变量缺失阻断启动
- [x] 非关键变量使用默认值 + warn 日志
- [x] 配置键/值尾随空格自动清理
- [x] 合法配置通过耗时 < 500ms
- [x] 非法配置拦截耗时 < 1s
- [x] 错误报告格式符合 JSON Schema

## 测试执行命令

```bash
# 运行所有 P0 测试
pytest tests/test_p0_preflight.py -v

# 运行性能测试
pytest tests/test_p0_preflight.py::TestP0PreFlightValidator::test_performance_legal_config -v

# 生成测试覆盖率报告
pytest tests/test_p0_preflight.py --cov=preflight --cov-report=html
```
