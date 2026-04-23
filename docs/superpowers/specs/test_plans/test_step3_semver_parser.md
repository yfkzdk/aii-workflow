# Step 3 测试计划：SemVer 区间解析器实现

## 测试目标
验证 SemVer 解析器正确实现 `^`/`~`/`>=`/`<=`/`=` 语义，明确默认策略为精确匹配，正确处理 0.x.y 特殊语义。

## 测试环境
- Python 3.9+
- 依赖：pytest, dataclasses

## 测试用例

### 1. Caret 操作符测试（^）

#### 1.1 正向测试：兼容版本

| 测试ID | 配置版本 | 运行时版本 | 预期结果 | 说明 |
|-------|---------|-----------|---------|------|
| TC-S3-001 | `^1.2.3` | `1.2.3` | ✅ 兼容 | 精确匹配 |
| TC-S3-002 | `^1.2.3` | `1.5.0` | ✅ 兼容 | 主版本相同，次版本更高 |
| TC-S3-003 | `^1.2.3` | `1.2.5` | ✅ 兼容 | 主版本相同，补丁版本更高 |
| TC-S3-004 | `^1.0.0` | `1.5.0` | ✅ 兼容 | 主版本相同，次版本更高 |

#### 1.2 负向测试：不兼容版本

| 测试ID | 配置版本 | 运行时版本 | 预期结果 | 说明 |
|-------|---------|-----------|---------|------|
| TC-S3-101 | `^1.2.3` | `2.0.0` | ❌ 不兼容 | 主版本不同 |
| TC-S3-102 | `^1.2.3` | `1.1.0` | ❌ 不兼容 | 次版本过低 |
| TC-S3-103 | `^1.2.3` | `1.2.2` | ❌ 不兼容 | 补丁版本过低 |

### 2. Tilde 操作符测试（~）

#### 2.1 正向测试：兼容版本

| 测试ID | 配置版本 | 运行时版本 | 预期结果 | 说明 |
|-------|---------|-----------|---------|------|
| TC-S3-201 | `~1.2.3` | `1.2.3` | ✅ 兼容 | 精确匹配 |
| TC-S3-202 | `~1.2.3` | `1.2.5` | ✅ 兼容 | 主+次版本相同，补丁版本更高 |

#### 2.2 负向测试：不兼容版本

| 测试ID | 配置版本 | 运行时版本 | 预期结果 | 说明 |
|-------|---------|-----------|---------|------|
| TC-S3-301 | `~1.2.3` | `1.3.0` | ❌ 不兼容 | 次版本不同 |
| TC-S3-302 | `~1.2.3` | `2.0.0` | ❌ 不兼容 | 主版本不同 |

### 3. 精确匹配测试（= 或无操作符）

#### 3.1 正向测试：精确匹配

| 测试ID | 配置版本 | 运行时版本 | 预期结果 | 说明 |
|-------|---------|-----------|---------|------|
| TC-S3-401 | `1.2.3` | `1.2.3` | ✅ 兼容 | 无操作符，精确匹配 |
| TC-S3-402 | `=1.2.3` | `1.2.3` | ✅ 兼容 | 显式 =，精确匹配 |

#### 3.2 负向测试：不精确匹配

| 测试ID | 配置版本 | 运行时版本 | 预期结果 | 说明 |
|-------|---------|-----------|---------|------|
| TC-S3-501 | `1.2.3` | `1.2.5` | ❌ 不兼容 | 补丁版本不同 |
| TC-S3-502 | `1.2.3` | `1.5.0` | ❌ 不兼容 | 次版本不同 |
| TC-S3-503 | `=1.2.3` | `1.5.0` | ❌ 不兼容 | 次版本不同 |

### 4. 范围操作符测试（>=, <=）

#### 4.1 GreaterEqual 测试

| 测试ID | 配置版本 | 运行时版本 | 预期结果 | 说明 |
|-------|---------|-----------|---------|------|
| TC-S3-601 | `>=1.0.0` | `1.0.0` | ✅ 兼容 | 等于 |
| TC-S3-602 | `>=1.0.0` | `2.0.0` | ✅ 兼容 | 大于 |
| TC-S3-603 | `>=1.0.0` | `0.9.0` | ❌ 不兼容 | 小于 |

#### 4.2 LessEqual 测试

| 测试ID | 配置版本 | 运行时版本 | 预期结果 | 说明 |
|-------|---------|-----------|---------|------|
| TC-S3-701 | `<=2.0.0` | `2.0.0` | ✅ 兼容 | 等于 |
| TC-S3-702 | `<=2.0.0` | `1.0.0` | ✅ 兼容 | 小于 |
| TC-S3-703 | `<=2.0.0` | `3.0.0` | ❌ 不兼容 | 大于 |

### 5. 0.x.y 特殊语义测试

#### 5.1 Caret 操作符（0.x.y）

| 测试ID | 配置版本 | 运行时版本 | 预期结果 | 说明 |
|-------|---------|-----------|---------|------|
| TC-S3-801 | `^0.1.0` | `0.1.0` | ✅ 兼容 | 精确匹配 |
| TC-S3-802 | `^0.1.0` | `0.1.5` | ✅ 兼容 | 仅补丁版本向上兼容 |
| TC-S3-803 | `^0.1.0` | `0.2.0` | ❌ 不兼容 | 主版本为 0，次版本变更视为破坏性 |
| TC-S3-804 | `^0.1.0` | `1.0.0` | ❌ 不兼容 | 主版本不同 |

#### 5.2 Tilde 操作符（0.x.y）

| 测试ID | 配置版本 | 运行时版本 | 预期结果 | 说明 |
|-------|---------|-----------|---------|------|
| TC-S3-901 | `~0.1.0` | `0.1.0` | ✅ 兼容 | 精确匹配 |
| TC-S3-902 | `~0.1.0` | `0.1.5` | ✅ 兼容 | 仅补丁版本向上兼容 |
| TC-S3-903 | `~0.1.0` | `0.2.0` | ❌ 不兼容 | 主版本为 0，次版本变更视为破坏性 |

#### 5.3 精确匹配（0.x.y）

| 测试ID | 配置版本 | 运行时版本 | 预期结果 | 说明 |
|-------|---------|-----------|---------|------|
| TC-S3-1001 | `0.1.0` | `0.1.0` | ✅ 兼容 | 精确匹配 |
| TC-S3-1002 | `0.1.0` | `0.2.0` | ❌ 不兼容 | 精确匹配 |

### 6. 版本号格式测试

#### 6.1 合法格式

| 测试ID | 版本号 | 预期解析结果 | 说明 |
|-------|-------|-------------|------|
| TC-S3-1101 | `1.2.3` | `(1, 2, 3)` | 标准格式 |
| TC-S3-1102 | `1.0` | `(1, 0, 0)` | 补丁版本默认为 0 |
| TC-S3-1103 | ` 1.2.3 ` | `(1, 2, 3)` | 尾随空格自动清理 |

#### 6.2 非法格式

| 测试ID | 版本号 | 预期行为 | 错误消息 |
|-------|-------|---------|---------|
| TC-S3-1201 | `invalid` | ❌ 抛出 ValueError | "版本号格式非法" |
| TC-S3-1202 | `1` | ❌ 抛出 ValueError | "版本号格式非法" |

### 7. 默认策略测试

#### 7.1 无操作符默认为精确匹配

| 测试ID | 配置版本 | 运行时版本 | 预期结果 | 说明 |
|-------|---------|-----------|---------|------|
| TC-S3-1301 | `1.2.3` | `1.2.3` | ✅ 兼容 | 默认精确匹配 |
| TC-S3-1302 | `1.2.3` | `1.5.0` | ❌ 不兼容 | 默认精确匹配 |
| TC-S3-1303 | `1.2.3` | `1.2.5` | ❌ 不兼容 | 默认精确匹配 |

## 自动化测试脚本

```python
import pytest
from dataclasses import dataclass
from enum import Enum
from typing import Tuple

class VersionOperator(Enum):
    CARET = "^"
    TILDE = "~"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EXACT = "="
    NONE = ""

@dataclass
class SemVerConstraint:
    operator: VersionOperator
    major: int
    minor: int
    patch: int
    raw_version: str

class TestStep3SemVerParser:
    """Step 3 测试：SemVer 区间解析器实现"""

    def test_caret_compatible(self):
        """测试 Caret 操作符兼容版本"""
        parser = SemVerParser()

        # TC-S3-001: ^1.2.3 与 1.2.3 兼容
        constraint = parser.parse_constraint("^1.2.3")
        assert parser.satisfies(constraint, "1.2.3") == True

        # TC-S3-002: ^1.2.3 与 1.5.0 兼容
        assert parser.satisfies(constraint, "1.5.0") == True

    def test_caret_incompatible(self):
        """测试 Caret 操作符不兼容版本"""
        parser = SemVerParser()

        # TC-S3-101: ^1.2.3 与 2.0.0 不兼容
        constraint = parser.parse_constraint("^1.2.3")
        assert parser.satisfies(constraint, "2.0.0") == False

        # TC-S3-102: ^1.2.3 与 1.1.0 不兼容
        assert parser.satisfies(constraint, "1.1.0") == False

    def test_tilde_compatible(self):
        """测试 Tilde 操作符兼容版本"""
        parser = SemVerParser()

        # TC-S3-201: ~1.2.3 与 1.2.3 兼容
        constraint = parser.parse_constraint("~1.2.3")
        assert parser.satisfies(constraint, "1.2.3") == True

        # TC-S3-202: ~1.2.3 与 1.2.5 兼容
        assert parser.satisfies(constraint, "1.2.5") == True

    def test_tilde_incompatible(self):
        """测试 Tilde 操作符不兼容版本"""
        parser = SemVerParser()

        # TC-S3-301: ~1.2.3 与 1.3.0 不兼容
        constraint = parser.parse_constraint("~1.2.3")
        assert parser.satisfies(constraint, "1.3.0") == False

    def test_exact_match(self):
        """测试精确匹配"""
        parser = SemVerParser()

        # TC-S3-401: 1.2.3 与 1.2.3 兼容（无操作符）
        constraint = parser.parse_constraint("1.2.3")
        assert parser.satisfies(constraint, "1.2.3") == True

        # TC-S3-501: 1.2.3 与 1.2.5 不兼容（无操作符）
        assert parser.satisfies(constraint, "1.2.5") == False

        # TC-S3-402: =1.2.3 与 1.2.3 兼容（显式 =）
        constraint = parser.parse_constraint("=1.2.3")
        assert parser.satisfies(constraint, "1.2.3") == True

    def test_zero_version_caret(self):
        """测试 0.x.y Caret 操作符"""
        parser = SemVerParser()

        # TC-S3-801: ^0.1.0 与 0.1.0 兼容
        constraint = parser.parse_constraint("^0.1.0")
        assert parser.satisfies(constraint, "0.1.0") == True

        # TC-S3-802: ^0.1.0 与 0.1.5 兼容
        assert parser.satisfies(constraint, "0.1.5") == True

        # TC-S3-803: ^0.1.0 与 0.2.0 不兼容
        assert parser.satisfies(constraint, "0.2.0") == False

    def test_zero_version_exact(self):
        """测试 0.x.y 精确匹配"""
        parser = SemVerParser()

        # TC-S3-1001: 0.1.0 与 0.1.0 兼容
        constraint = parser.parse_constraint("0.1.0")
        assert parser.satisfies(constraint, "0.1.0") == True

        # TC-S3-1002: 0.1.0 与 0.2.0 不兼容
        assert parser.satisfies(constraint, "0.2.0") == False

    def test_version_format_standard(self):
        """测试版本号格式（标准）"""
        parser = SemVerParser()

        # TC-S3-1101: 1.2.3
        constraint = parser.parse_constraint("1.2.3")
        assert constraint.major == 1
        assert constraint.minor == 2
        assert constraint.patch == 3

        # TC-S3-1102: 1.0
        constraint = parser.parse_constraint("1.0")
        assert constraint.major == 1
        assert constraint.minor == 0
        assert constraint.patch == 0

    def test_version_format_invalid(self):
        """测试版本号格式（非法）"""
        parser = SemVerParser()

        # TC-S3-1201: invalid
        with pytest.raises(ValueError, match="版本号格式非法"):
            parser.parse_constraint("invalid")

    def test_default_strategy(self):
        """测试默认策略（精确匹配）"""
        parser = SemVerParser()

        # TC-S3-1301: 1.2.3 与 1.2.3 兼容
        constraint = parser.parse_constraint("1.2.3")
        assert constraint.operator == VersionOperator.NONE
        assert parser.satisfies(constraint, "1.2.3") == True

        # TC-S3-1302: 1.2.3 与 1.5.0 不兼容
        assert parser.satisfies(constraint, "1.5.0") == False

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
```

## 验收标准

- [x] 弃用直接元组比较
- [x] 实现 `^`/`~`/`>=`/`<=`/`=` 语义
- [x] 默认策略：精确匹配（`=`）
- [x] 明确不支持 `0.x.y` 语义（次版本变更视为破坏性）
- [x] 版本拒绝/放行准确率 100%
- [x] 输出明确冲突路径

## 测试执行命令

```bash
# 运行所有 Step 3 测试
pytest tests/test_step3_semver_parser.py -v

# 运行 Caret 操作符测试
pytest tests/test_step3_semver_parser.py::TestStep3SemVerParser::test_caret_compatible -v
pytest tests/test_step3_semver_parser.py::TestStep3SemVerParser::test_caret_incompatible -v

# 运行 Tilde 操作符测试
pytest tests/test_step3_semver_parser.py::TestStep3SemVerParser::test_tilde_compatible -v

# 运行 0.x.y 特殊语义测试
pytest tests/test_step3_semver_parser.py::TestStep3SemVerParser::test_zero_version_caret -v

# 生成测试覆盖率报告
pytest tests/test_step3_semver_parser.py --cov=semver_parser --cov-report=html
```

## 性能要求

- 单个版本解析耗时 < 10ms
- 兼容性检查耗时 < 5ms
- 批量检查（100 个版本）耗时 < 500ms

## 通过标准

- 所有测试用例通过率 100%
- 测试覆盖率 ≥ 90%
- 性能要求满足率 100%
- 版本拒绝/放行准确率 100%
