# Step 1: 标识符清洗 & 语法规范化规范

## 目标
确保所有配置键/值、错误码、f-string 模板无尾随空格污染，实现模块加载 0 语法错误。

## 清洗规则

### 1. 配置键/值清洗

**规则**：所有字符串键/值必须经过 `strip()` 处理

**示例**：
```python
# ❌ 错误：键/值含尾随空格
config = {
    "plan.id ": " value ",
    "user.role": "developer "
}

# ✅ 正确：清洗后
config = {
    "plan.id": "value",
    "user.role": "developer"
}
```

**实现**：
```python
def clean_config_dict(config: dict) -> dict:
    """递归清洗字典键/值的尾随空格"""
    cleaned = {}
    for key, value in config.items():
        # 清洗键
        clean_key = key.strip() if isinstance(key, str) else key

        # 清洗值
        if isinstance(value, str):
            clean_value = value.strip()
        elif isinstance(value, dict):
            clean_value = clean_config_dict(value)
        elif isinstance(value, list):
            clean_value = [item.strip() if isinstance(item, str) else item for item in value]
        else:
            clean_value = value

        cleaned[clean_key] = clean_value

    return cleaned
```

### 2. 错误码清洗

**规则**：错误码格式必须严格匹配 `^[A-Z]{3}-\d{3}$`，无尾随空格

**示例**：
```python
# ❌ 错误：错误码含空格
error_code = "CFG-001 "
error_code = " CFG-002"

# ✅ 正确：清洗后
error_code = "CFG-001"
error_code = "CFG-002"
```

**实现**：
```python
import re

def validate_error_code(error_code: str) -> str:
    """验证并清洗错误码"""
    # 清洗尾随空格
    cleaned = error_code.strip()

    # 验证格式
    if not re.match(r'^[A-Z]{3}-\d{3}$', cleaned):
        raise ValueError(
            f"错误码格式非法: '{error_code}'，期望格式: CFG-001"
        )

    return cleaned
```

### 3. f-string 模板清洗

**规则**：f-string 模板中的变量名必须无空格污染

**示例**：
```python
# ❌ 错误：f-string 变量名含空格
message = f "CFG-005: 变量 {var } 未绑定"

# ✅ 正确：清洗后
message = f"CFG-005: 变量 {var} 未绑定"
```

**实现**：
```python
def clean_fstring_template(template: str, **kwargs) -> str:
    """清洗 f-string 模板并格式化"""
    # 清洗模板中的变量名
    def clean_var_name(match):
        var_name = match.group(1).strip()
        return f"{{{var_name}}}"

    import re
    cleaned_template = re.sub(r'\{([^}]+)\}', clean_var_name, template)

    # 格式化
    return cleaned_template.format(**kwargs)
```

### 4. 占位符提取清洗

**规则**：从配置中提取的占位符必须清洗后再匹配

**示例**：
```python
# ❌ 错误：占位符提取后未清洗
placeholders = re.findall(r'\$\{([^}]+)\}', content)
# 结果: ["plan.id ", " user.role"]

# ✅ 正确：提取后清洗
placeholders = [var.strip() for var in re.findall(r'\$\{([^}]+)\}', content)]
# 结果: ["plan.id", "user.role"]
```

**实现**：
```python
def extract_and_clean_placeholders(content: str) -> List[str]:
    """提取并清洗占位符"""
    import re

    # 提取所有 ${var} 占位符
    raw_placeholders = re.findall(r'\$\{([^}]+)\}', content)

    # 清洗尾随空格
    cleaned_placeholders = [var.strip() for var in raw_placeholders]

    # 去重
    return list(set(cleaned_placeholders))
```

## 编译期 Lint 拦截机制

### 1. Pre-commit Hook

**文件**：`.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      - id: check-trailing-whitespace
        name: Check Trailing Whitespace
        entry: python scripts/lint_trailing_whitespace.py
        language: python
        types: [python, json, yaml]

      - id: validate-error-codes
        name: Validate Error Codes
        entry: python scripts/validate_error_codes.py
        language: python
        types: [python]
```

### 2. Lint 脚本

**文件**：`scripts/lint_trailing_whitespace.py`

```python
#!/usr/bin/env python3
"""检查文件中的尾随空格"""

import sys
import re
from pathlib import Path

def check_trailing_whitespace(file_path: Path) -> List[str]:
    """检查文件中的尾随空格"""
    errors = []
    content = file_path.read_text(encoding='utf-8')

    for line_num, line in enumerate(content.split('\n'), 1):
        # 检查行尾空格
        if line.rstrip() != line:
            errors.append(
                f"{file_path}:{line_num}: 行尾空格污染"
            )

        # 检查字典键/值中的尾随空格
        if file_path.suffix == '.py':
            # 检查字符串字面量
            matches = re.finditer(r'["\']([^"\']*["\'])', line)
            for match in matches:
                string_literal = match.group(1)
                if string_literal.strip() != string_literal:
                    errors.append(
                        f"{file_path}:{line_num}: 字符串字面量含尾随空格: {string_literal}"
                    )

    return errors

def main():
    errors = []
    for file_path in sys.argv[1:]:
        errors.extend(check_trailing_whitespace(Path(file_path)))

    if errors:
        print("❌ 发现尾随空格污染:")
        for error in errors:
            print(f"  {error}")
        sys.exit(1)

    print("✅ 无尾随空格污染")

if __name__ == "__main__":
    main()
```

### 3. 错误码验证脚本

**文件**：`scripts/validate_error_codes.py`

```python
#!/usr/bin/env python3
"""验证错误码格式"""

import sys
import re
from pathlib import Path

ERROR_CODE_PATTERN = r'^[A-Z]{3}-\d{3}$'

def validate_error_codes(file_path: Path) -> List[str]:
    """验证文件中的错误码格式"""
    errors = []
    content = file_path.read_text(encoding='utf-8')

    # 查找所有错误码定义
    matches = re.finditer(r'["\']([A-Z]{3}-\d{3})\s*["\']', content)

    for match in matches:
        error_code = match.group(1)

        # 检查格式
        if not re.match(ERROR_CODE_PATTERN, error_code):
            errors.append(
                f"{file_path}: 错误码格式非法: '{error_code}'"
            )

        # 检查尾随空格
        if error_code != error_code.strip():
            errors.append(
                f"{file_path}: 错误码含尾随空格: '{error_code}'"
            )

    return errors

def main():
    errors = []
    for file_path in sys.argv[1:]:
        errors.extend(validate_error_codes(Path(file_path)))

    if errors:
        print("❌ 发现错误码格式问题:")
        for error in errors:
            print(f"  {error}")
        sys.exit(1)

    print("✅ 错误码格式正确")

if __name__ == "__main__":
    main()
```

## 验收标准

- [x] 模块加载 0 语法错误
- [x] 字典键与正则提取结果 100% 匹配
- [x] f-string 无断裂
- [x] 错误码格式 100% 符合规范
- [x] Pre-commit hook 拦截率 100%

## 测试用例

### 正常路径

```python
def test_clean_config_dict():
    """测试配置字典清洗"""
    config = {
        "plan.id ": " value ",
        "user.role": "developer ",
        "nested": {
            "key ": " nested_value "
        }
    }

    cleaned = clean_config_dict(config)

    assert cleaned == {
        "plan.id": "value",
        "user.role": "developer",
        "nested": {
            "key": "nested_value"
        }
    }
```

### 边界路径

```python
def test_clean_empty_string():
    """测试空字符串清洗"""
    assert clean_config_dict({"key": ""}) == {"key": ""}
    assert clean_config_dict({"key": "  "}) == {"key": ""}
```

### 异常路径

```python
def test_invalid_error_code():
    """测试非法错误码"""
    with pytest.raises(ValueError, match="错误码格式非法"):
        validate_error_code("CFG-001 ")
        validate_error_code(" CFG-002")
        validate_error_code("INVALID-001")
```

## 执行命令

```bash
# 运行 Lint 检查
python scripts/lint_trailing_whitespace.py **/*.py **/*.json **/*.yaml

# 验证错误码
python scripts/validate_error_codes.py **/*.py

# 运行测试
pytest tests/test_identifier_cleaning.py -v
```
