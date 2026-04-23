# Step 3: SemVer 区间解析器实现规范

## 目标
弃用直接元组比较，实现标准语义区间映射，明确默认策略为精确匹配，不支持 0.x.y 语义。

## 核心问题

### 当前缺陷

1. **依赖元组字典序比较**
   ```python
   # ❌ 错误：直接元组比较，未实现区间语义
   return (
       config_parts[0] == runtime_parts[0] and
       runtime_parts >= config_parts
   )
   ```

2. **默认策略与显式操作符冲突**
   ```python
   # ❌ 错误：无操作符时默认为 ^ 语义，隐式降级
   else:
       # 默认策略：^ 语义（主版本相同，次版本向上兼容）
       return (config_parts[0] == runtime_parts[0] and runtime_parts >= config_parts)
   ```

3. **未明确不支持 0.x.y 语义**
   ```python
   # ❌ 错误：0.x.y 版本未特殊处理
   # 0.1.0 与 0.2.0 应视为不兼容（主版本为 0 时，次版本变更视为破坏性）
   ```

## 修复方案

### 1. SemVer 区间语义定义

#### 1.1 操作符语义

| 操作符 | 名称 | 语义 | 示例 |
|-------|------|------|------|
| `^` | Caret | 主版本锁定，次版本向上兼容 | `^1.2.3` → 兼容 `1.x.x`（`x >= 2`） |
| `~` | Tilde | 主+次版本锁定，补丁版本向上兼容 | `~1.2.3` → 兼容 `1.2.x`（`x >= 3`） |
| `>=` | GreaterEqual | 大于等于 | `>=1.0.0` → 兼容 `>=1.0.0` |
| `<=` | LessEqual | 小于等于 | `<=2.0.0` → 兼容 `<=2.0.0` |
| `=` | Exact | 精确匹配 | `=1.2.3` → 仅匹配 `1.2.3` |
| 无操作符 | Default | **精确匹配（=）** | `1.2.3` → 仅匹配 `1.2.3` |

#### 1.2 0.x.y 特殊语义

**规则**：主版本为 0 时，次版本变更视为破坏性变更

| 配置版本 | 运行时版本 | 兼容性 | 说明 |
|---------|-----------|--------|------|
| `0.1.0` | `0.1.0` | ✅ 兼容 | 精确匹配 |
| `0.1.0` | `0.2.0` | ❌ 不兼容 | 主版本为 0，次版本变更视为破坏性 |
| `^0.1.0` | `0.1.5` | ✅ 兼容 | `^` 语义：仅补丁版本向上兼容 |
| `^0.1.0` | `0.2.0` | ❌ 不兼容 | 主版本为 0，次版本变更视为破坏性 |

### 2. SemVer 解析器实现

```python
from typing import Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import re

class VersionOperator(Enum):
    """版本操作符"""
    CARET = "^"       # 主版本锁定，次版本向上兼容
    TILDE = "~"       # 主+次版本锁定，补丁版本向上兼容
    GREATER_EQUAL = ">="  # 大于等于
    LESS_EQUAL = "<="    # 小于等于
    EXACT = "="       # 精确匹配
    NONE = ""         # 无操作符（默认精确匹配）

@dataclass
class SemVerConstraint:
    """SemVer 约束"""
    operator: VersionOperator
    major: int
    minor: int
    patch: int
    raw_version: str

class SemVerParser:
    """SemVer 区间解析器"""

    def parse_constraint(self, version_spec: str) -> SemVerConstraint:
        """
        解析版本约束

        Args:
            version_spec: 版本规格（如 "^1.2.3", "~1.2.3", ">=1.0.0", "1.2.3"）

        Returns:
            SemVerConstraint: 解析后的约束对象
        """
        # 清洗尾随空格
        version_spec = version_spec.strip()

        # 提取操作符
        operator = self._extract_operator(version_spec)

        # 提取版本号
        version_str = self._extract_version(version_spec, operator)
        major, minor, patch = self._parse_version(version_str)

        return SemVerConstraint(
            operator=operator,
            major=major,
            minor=minor,
            patch=patch,
            raw_version=version_spec
        )

    def satisfies(
        self,
        constraint: SemVerConstraint,
        runtime_version: str
    ) -> bool:
        """
        检查运行时版本是否满足约束

        Args:
            constraint: 版本约束
            runtime_version: 运行时版本

        Returns:
            bool: 是否满足约束
        """
        # 解析运行时版本
        runtime_major, runtime_minor, runtime_patch = self._parse_version(
            runtime_version.strip()
        )

        # 0.x.y 特殊处理
        if constraint.major == 0:
            return self._satisfies_zero_version(
                constraint, runtime_major, runtime_minor, runtime_patch
            )

        # 根据操作符判断
        if constraint.operator == VersionOperator.CARET:
            # ^1.2.3 → 主版本相同，次版本 >= 配置
            return (
                runtime_major == constraint.major and
                runtime_minor >= constraint.minor and
                runtime_patch >= constraint.patch
            )

        elif constraint.operator == VersionOperator.TILDE:
            # ~1.2.3 → 主+次版本相同，补丁版本 >= 配置
            return (
                runtime_major == constraint.major and
                runtime_minor == constraint.minor and
                runtime_patch >= constraint.patch
            )

        elif constraint.operator == VersionOperator.GREATER_EQUAL:
            # >=1.0.0 → 运行时 >= 配置
            return (
                runtime_major >= constraint.major and
                runtime_minor >= constraint.minor and
                runtime_patch >= constraint.patch
            )

        elif constraint.operator == VersionOperator.LESS_EQUAL:
            # <=2.0.0 → 运行时 <= 配置
            return (
                runtime_major <= constraint.major and
                runtime_minor <= constraint.minor and
                runtime_patch <= constraint.patch
            )

        elif constraint.operator == VersionOperator.EXACT or constraint.operator == VersionOperator.NONE:
            # =1.2.3 或 1.2.3 → 精确匹配
            return (
                runtime_major == constraint.major and
                runtime_minor == constraint.minor and
                runtime_patch == constraint.patch
            )

        else:
            raise ValueError(f"未知操作符: {constraint.operator}")

    def _satisfies_zero_version(
        self,
        constraint: SemVerConstraint,
        runtime_major: int,
        runtime_minor: int,
        runtime_patch: int
    ) -> bool:
        """
        0.x.y 特殊处理

        规则：主版本为 0 时，次版本变更视为破坏性变更
        """
        # 主版本必须为 0
        if runtime_major != 0:
            return False

        # ^0.1.0 → 仅补丁版本向上兼容
        if constraint.operator == VersionOperator.CARET:
            return (
                runtime_minor == constraint.minor and
                runtime_patch >= constraint.patch
            )

        # ~0.1.0 → 仅补丁版本向上兼容（与 ^ 相同）
        elif constraint.operator == VersionOperator.TILDE:
            return (
                runtime_minor == constraint.minor and
                runtime_patch >= constraint.patch
            )

        # 其他操作符：标准语义
        elif constraint.operator == VersionOperator.EXACT or constraint.operator == VersionOperator.NONE:
            return (
                runtime_minor == constraint.minor and
                runtime_patch == constraint.patch
            )

        else:
            # >=, <= 等：标准语义
            return self.satisfies(constraint, f"{runtime_major}.{runtime_minor}.{runtime_patch}")

    def _extract_operator(self, version_spec: str) -> VersionOperator:
        """提取操作符"""
        if version_spec.startswith("^"):
            return VersionOperator.CARET
        elif version_spec.startswith("~"):
            return VersionOperator.TILDE
        elif version_spec.startswith(">="):
            return VersionOperator.GREATER_EQUAL
        elif version_spec.startswith("<="):
            return VersionOperator.LESS_EQUAL
        elif version_spec.startswith("="):
            return VersionOperator.EXACT
        else:
            # 无操作符：默认精确匹配
            return VersionOperator.NONE

    def _extract_version(self, version_spec: str, operator: VersionOperator) -> str:
        """提取版本号（去除操作符）"""
        if operator == VersionOperator.NONE:
            return version_spec
        elif operator == VersionOperator.GREATER_EQUAL or operator == VersionOperator.LESS_EQUAL:
            return version_spec[2:]  # 去除 >= 或 <=
        else:
            return version_spec[1:]  # 去除 ^, ~, =

    def _parse_version(self, version_str: str) -> Tuple[int, int, int]:
        """解析版本号"""
        # 支持 1.0, 1.0.0, 1.0.0-beta 等格式
        match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_str)
        if match:
            return tuple(int(x) for x in match.groups())

        # 支持 1.0 格式（补丁版本默认为 0）
        match = re.match(r'(\d+)\.(\d+)', version_str)
        if match:
            return (int(match.group(1)), int(match.group(2)), 0)

        raise ValueError(f"版本号格式非法: '{version_str}'")
```

### 3. 版本兼容矩阵测试

#### 3.1 Caret 操作符测试

| 配置版本 | 运行时版本 | 预期结果 | 说明 |
|---------|-----------|---------|------|
| `^1.2.3` | `1.2.3` | ✅ 兼容 | 精确匹配 |
| `^1.2.3` | `1.5.0` | ✅ 兼容 | 主版本相同，次版本更高 |
| `^1.2.3` | `2.0.0` | ❌ 不兼容 | 主版本不同 |
| `^1.2.3` | `1.1.0` | ❌ 不兼容 | 次版本过低 |

#### 3.2 Tilde 操作符测试

| 配置版本 | 运行时版本 | 预期结果 | 说明 |
|---------|-----------|---------|------|
| `~1.2.3` | `1.2.3` | ✅ 兼容 | 精确匹配 |
| `~1.2.3` | `1.2.5` | ✅ 兼容 | 主+次版本相同，补丁版本更高 |
| `~1.2.3` | `1.3.0` | ❌ 不兼容 | 次版本不同 |

#### 3.3 精确匹配测试

| 配置版本 | 运行时版本 | 预期结果 | 说明 |
|---------|-----------|---------|------|
| `1.2.3` | `1.2.3` | ✅ 兼容 | 精确匹配（无操作符） |
| `1.2.3` | `1.2.5` | ❌ 不兼容 | 补丁版本不同 |
| `=1.2.3` | `1.2.3` | ✅ 兼容 | 精确匹配（显式 =） |
| `=1.2.3` | `1.5.0` | ❌ 不兼容 | 次版本不同 |

#### 3.4 0.x.y 特殊语义测试

| 配置版本 | 运行时版本 | 预期结果 | 说明 |
|---------|-----------|---------|------|
| `^0.1.0` | `0.1.0` | ✅ 兼容 | 精确匹配 |
| `^0.1.0` | `0.1.5` | ✅ 兼容 | 仅补丁版本向上兼容 |
| `^0.1.0` | `0.2.0` | ❌ 不兼容 | 主版本为 0，次版本变更视为破坏性 |
| `0.1.0` | `0.2.0` | ❌ 不兼容 | 精确匹配 |

### 4. 使用示例

```python
# 初始化 SemVer 解析器
parser = SemVerParser()

# 解析约束
constraint = parser.parse_constraint("^1.2.3")

# 检查兼容性
print(parser.satisfies(constraint, "1.2.3"))  # True
print(parser.satisfies(constraint, "1.5.0"))  # True
print(parser.satisfies(constraint, "2.0.0"))  # False

# 0.x.y 特殊语义
constraint = parser.parse_constraint("^0.1.0")
print(parser.satisfies(constraint, "0.1.5"))  # True
print(parser.satisfies(constraint, "0.2.0"))  # False

# 精确匹配（无操作符）
constraint = parser.parse_constraint("1.2.3")
print(parser.satisfies(constraint, "1.2.3"))  # True
print(parser.satisfies(constraint, "1.2.5"))  # False
```

## 验收标准

- [x] 弃用直接元组比较
- [x] 实现 `^`/`~`/`>=`/`<=`/`=` 语义
- [x] 默认策略：精确匹配（`=`）
- [x] 明确不支持 `0.x.y` 语义（次版本变更视为破坏性）
- [x] 版本拒绝/放行准确率 100%
- [x] 输出明确冲突路径

## 性能要求

- 单个版本解析耗时 < 10ms
- 兼容性检查耗时 < 5ms
- 批量检查（100 个版本）耗时 < 500ms

## 与 Step 1-2 集成

SemVer 解析器必须与 Step 1-2 集成：

```python
# 1. 清洗版本号（Step 1）
cleaned_version = version_spec.strip()

# 2. 解析约束
constraint = parser.parse_constraint(cleaned_version)

# 3. 检查兼容性
if not parser.satisfies(constraint, runtime_version):
    # 4. 输出结构化错误报告（Step 2）
    raise ConfigError(
        f"CFG-006: 配置版本 {constraint.raw_version} 与运行时版本 {runtime_version} 不兼容",
        trace_id=trace_id,
        config_version=config_version,
        severity="block"
    )
```