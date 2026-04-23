# Step 1 测试计划：标识符清洗 & 语法规范化

## 测试目标
验证所有配置键/值、错误码、f-string 模板无尾随空格污染，实现模块加载 0 语法错误。

## 测试环境
- Python 3.9+
- 依赖：pytest, pyyaml, jsonschema

## 测试用例

### 1. 配置字典清洗测试

#### 1.1 正向测试：合法配置清洗

| 测试ID | 输入配置 | 预期输出 | 验证点 |
|-------|---------|---------|--------|
| TC-S1-001 | `{"plan.id ": " value "}` | `{"plan.id": "value"}` | 键/值首尾空格清理 |
| TC-S1-002 | `{"user.role": "developer "}` | `{"user.role": "developer"}` | 值尾随空格清理 |
| TC-S1-003 | `{"nested": {"key ": " value "}}` | `{"nested": {"key": "value"}}` | 嵌套字典清洗 |
| TC-S1-004 | `{"list": [" item1 ", " item2 "]}` | `{"list": ["item1", "item2"]}` | 列表元素清洗 |

#### 1.2 边界测试

| 测试ID | 输入配置 | 预期输出 | 验证点 |
|-------|---------|---------|--------|
| TC-S1-101 | `{"key": ""}` | `{"key": ""}` | 空字符串保留 |
| TC-S1-102 | `{"key": "  "}` | `{"key": ""}` | 纯空格清理为空字符串 |
| TC-S1-103 | `{"key": 0}` | `{"key": 0}` | 非字符串值保留 |
| TC-S1-104 | `{"key": False}` | `{"key": False}` | 布尔值保留 |

#### 1.3 异常测试

| 测试ID | 输入配置 | 预期行为 | 验证点 |
|-------|---------|---------|--------|
| TC-S1-201 | `None` | 返回 `{}` | None 输入处理 |
| TC-S1-202 | `{}` | 返回 `{}` | 空字典处理 |

### 2. 错误码验证测试

#### 2.1 正向测试：合法错误码

| 测试ID | 输入错误码 | 预期结果 | 验证点 |
|-------|-----------|---------|--------|
| TC-S1-301 | `"CFG-001"` | ✅ 通过 | 标准格式 |
| TC-S1-302 | `"EXE-101"` | ✅ 通过 | 标准格式 |
| TC-S1-303 | `"QTY-201"` | ✅ 通过 | 标准格式 |
| TC-S1-304 | `"APP-301"` | ✅ 通过 | 标准格式 |

#### 2.2 负向测试：非法错误码

| 测试ID | 输入错误码 | 预期行为 | 错误消息 |
|-------|-----------|---------|---------|
| TC-S1-401 | `"CFG-001 "` | ❌ 抛出 ValueError | "错误码格式非法" |
| TC-S1-402 | `" CFG-002"` | ❌ 抛出 ValueError | "错误码格式非法" |
| TC-S1-403 | `"INVALID-001"` | ❌ 抛出 ValueError | "错误码格式非法" |
| TC-S1-404 | `"CFG-1"` | ❌ 抛出 ValueError | "错误码格式非法" |

### 3. f-string 模板清洗测试

#### 3.1 正向测试

| 测试ID | 输入模板 | 变量 | 预期输出 | 验证点 |
|-------|---------|------|---------|--------|
| TC-S1-501 | `"变量 {var} 未绑定"` | `var="plan.id"` | `"变量 plan.id 未绑定"` | 标准格式化 |
| TC-S1-502 | `"变量 {var } 未绑定"` | `var="plan.id"` | `"变量 plan.id 未绑定"` | 变量名清洗 |

#### 3.2 边界测试

| 测试ID | 输入模板 | 变量 | 预期输出 | 验证点 |
|-------|---------|------|---------|--------|
| TC-S1-601 | `"值: {value}"` | `value=0` | `"值: 0"` | 假值格式化 |
| TC-S1-602 | `"值: {value}"` | `value=False` | `"值: False"` | 布尔值格式化 |
| TC-S1-603 | `"值: {value}"` | `value=""` | `"值: "` | 空字符串格式化 |

### 4. 占位符提取清洗测试

#### 4.1 正向测试

| 测试ID | 输入内容 | 预期输出 | 验证点 |
|-------|---------|---------|--------|
| TC-S1-701 | `"${plan.id}"` | `["plan.id"]` | 标准占位符 |
| TC-S1-702 | `"${plan.id }"` | `["plan.id"]` | 占位符清洗 |
| TC-S1-703 | `"${ plan.id }"` | `["plan.id"]` | 占位符清洗 |
| TC-S1-704 | `"${plan.id} ${user.role}"` | `["plan.id", "user.role"]` | 多占位符去重 |

#### 4.2 边界测试

| 测试ID | 输入内容 | 预期输出 | 验证点 |
|-------|---------|---------|--------|
| TC-S1-801 | `"无占位符"` | `[]` | 无占位符 |
| TC-S1-802 | `"${}"` | `[]` | 空占位符过滤 |

### 5. Lint 检查测试

#### 5.1 文件检查测试

| 测试ID | 测试文件 | 预期结果 | 验证点 |
|-------|---------|---------|--------|
| TC-S1-901 | 合法 Python 文件 | ✅ 通过 | 无尾随空格 |
| TC-S1-902 | 合法 JSON 文件 | ✅ 通过 | 无尾随空格 |
| TC-S1-903 | 合法 YAML 文件 | ✅ 通过 | 无尾随空格 |

#### 5.2 拦截测试

| 测试ID | 测试文件 | 预期行为 | 验证点 |
|-------|---------|---------|--------|
| TC-S1-1001 | Python 文件含尾随空格 | ❌ 拦截 | Lint 拦截 |
| TC-S1-1002 | JSON 文件含尾随空格 | ❌ 拦截 | Lint 拦截 |
| TC-S1-1003 | YAML 文件含尾随空格 | ❌ 拦截 | Lint 拦截 |

## 自动化测试脚本

```python
import pytest
import re
from pathlib import Path
from typing import List, Dict

class TestStep1IdentifierCleaning:
    """Step 1 测试：标识符清洗 & 语法规范化"""

    def test_clean_config_dict_basic(self):
        """测试配置字典清洗（基础）"""
        # TC-S1-001: 键/值首尾空格清理
        config = {"plan.id ": " value "}
        cleaned = clean_config_dict(config)
        assert cleaned == {"plan.id": "value"}

    def test_clean_config_dict_nested(self):
        """测试嵌套字典清洗"""
        # TC-S1-003: 嵌套字典清洗
        config = {"nested": {"key ": " value "}}
        cleaned = clean_config_dict(config)
        assert cleaned == {"nested": {"key": "value"}}

    def test_clean_config_dict_list(self):
        """测试列表元素清洗"""
        # TC-S1-004: 列表元素清洗
        config = {"list": [" item1 ", " item2 "]}
        cleaned = clean_config_dict(config)
        assert cleaned == {"list": ["item1", "item2"]}

    def test_clean_config_dict_falsy_values(self):
        """测试假值保留"""
        # TC-S1-103: 非字符串值保留
        config = {"key": 0, "flag": False}
        cleaned = clean_config_dict(config)
        assert cleaned == {"key": 0, "flag": False}

    def test_validate_error_code_valid(self):
        """测试合法错误码"""
        # TC-S1-301: 标准格式
        assert validate_error_code("CFG-001") == "CFG-001"
        assert validate_error_code("EXE-101") == "EXE-101"

    def test_validate_error_code_invalid(self):
        """测试非法错误码"""
        # TC-S1-401: 尾随空格
        with pytest.raises(ValueError, match="错误码格式非法"):
            validate_error_code("CFG-001 ")

        # TC-S1-403: 非法格式
        with pytest.raises(ValueError, match="错误码格式非法"):
            validate_error_code("INVALID-001")

    def test_clean_fstring_template(self):
        """测试 f-string 模板清洗"""
        # TC-S1-502: 变量名清洗
        template = "变量 {var } 未绑定"
        result = clean_fstring_template(template, var="plan.id")
        assert result == "变量 plan.id 未绑定"

    def test_clean_fstring_template_falsy_value(self):
        """测试假值格式化"""
        # TC-S1-601: 假值格式化
        template = "值: {value}"
        result = clean_fstring_template(template, value=0)
        assert result == "值: 0"

    def test_extract_and_clean_placeholders(self):
        """测试占位符提取清洗"""
        # TC-S1-702: 占位符清洗
        content = "${plan.id } ${ user.role}"
        placeholders = extract_and_clean_placeholders(content)
        assert set(placeholders) == {"plan.id", "user.role"}

    def test_lint_trailing_whitespace_valid(self, tmp_path):
        """测试 Lint 检查（合法文件）"""
        # TC-S1-901: 合法 Python 文件
        file_path = tmp_path / "valid.py"
        file_path.write_text('key = "value"\n')

        errors = check_trailing_whitespace(file_path)
        assert len(errors) == 0

    def test_lint_trailing_whitespace_invalid(self, tmp_path):
        """测试 Lint 拦截（非法文件）"""
        # TC-S1-1001: Python 文件含尾随空格
        file_path = tmp_path / "invalid.py"
        file_path.write_text('key = "value" \n')

        errors = check_trailing_whitespace(file_path)
        assert len(errors) > 0
        assert "行尾空格污染" in errors[0]

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
```

## 验收标准

- [x] 配置字典清洗正确率 100%
- [x] 错误码验证通过率 100%
- [x] f-string 模板清洗正确率 100%
- [x] 占位符提取清洗正确率 100%
- [x] Lint 检查拦截率 100%
- [x] 模块加载 0 语法错误
- [x] 字典键与正则提取结果 100% 匹配
- [x] f-string 无断裂

## 测试执行命令

```bash
# 运行所有 Step 1 测试
pytest tests/test_step1_identifier_cleaning.py -v

# 运行 Lint 检查
python scripts/lint_trailing_whitespace.py **/*.py **/*.json **/*.yaml

# 验证错误码
python scripts/validate_error_codes.py **/*.py

# 生成测试覆盖率报告
pytest tests/test_step1_identifier_cleaning.py --cov=identifier_cleaning --cov-report=html
```

## 性能要求

- 配置字典清洗耗时 < 100ms（1000 个键值对）
- 错误码验证耗时 < 10ms（单个）
- 占位符提取耗时 < 50ms（100 个占位符）
- Lint 检查耗时 < 1s（单个文件）

## 通过标准

- 所有测试用例通过率 100%
- 测试覆盖率 ≥ 90%
- 性能要求满足率 100%
- Lint 检查通过率 100%
