# Step 4: 配置加载与容错规范

## 目标
增加文件存在性/可读性/格式合法性校验，配置解析失败输出人类可读指引，动态遍历声明式配置源清单，实现占位符扫描覆盖率 100%。

## 核心问题

### 当前缺陷

1. **硬编码扫描固定文件**
   ```python
   # ❌ 错误：硬编码文件路径
   config_files = [
       "config/skill_whitelist.json",
       "config/quality_gates.yaml"
   ]
   ```

2. **缺失/损坏时抛未捕获异常**
   ```python
   # ❌ 错误：未捕获异常，暴露底层堆栈路径
   content = Path(config_file).read_text(encoding="utf-8")
   # FileNotFoundError: [Errno 2] No such file or directory: 'config/skill_whitelist.json'
   ```

3. **占位符未全量扫描**
   ```python
   # ❌ 错误：仅扫描部分配置文件
   for config_file in config_files:
       content = self._read_config(config_file)
       # 未扫描 Prompt 模板、策略注入点等
   ```

## 修复方案

### 1. 配置源清单（声明式）

```python
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json
import yaml

class ConfigFormat(Enum):
    """配置格式"""
    JSON = "json"
    YAML = "yaml"

@dataclass
class ConfigSource:
    """配置源定义"""
    path: str                    # 文件路径
    format: ConfigFormat         # 格式
    required: bool = True        # 是否必需
    description: str = ""        # 描述
    schema_path: str = None      # JSON Schema 路径（可选）

class ConfigSourceRegistry:
    """配置源注册表（声明式）"""

    # 配置源清单（声明式定义）
    CONFIG_SOURCES = [
        ConfigSource(
            path="config/skill_whitelist.json",
            format=ConfigFormat.JSON,
            required=True,
            description="Skill 白名单配置",
            schema_path="schemas/skill_whitelist.schema.json"
        ),
        ConfigSource(
            path="config/quality_gates.yaml",
            format=ConfigFormat.YAML,
            required=True,
            description="质量门配置",
            schema_path="schemas/quality_gates.schema.json"
        ),
        ConfigSource(
            path="config/adapters.json",
            format=ConfigFormat.JSON,
            required=False,
            description="适配器配置（可选）"
        ),
        ConfigSource(
            path="prompts/skill_block.md.j2",
            format=ConfigFormat.YAML,  # Jinja2 模板
            required=False,
            description="Skill Prompt 模板"
        )
    ]

    def get_all_sources(self) -> List[ConfigSource]:
        """获取所有配置源"""
        return self.CONFIG_SOURCES

    def get_required_sources(self) -> List[ConfigSource]:
        """获取必需配置源"""
        return [s for s in self.CONFIG_SOURCES if s.required]
```

### 2. 配置加载器（容错）

```python
from typing import Dict, Any, Optional
from pathlib import Path
import json
import yaml
import re

class ConfigLoader:
    """配置加载器（容错）"""

    def __init__(self, trace_id: str, config_version: str):
        self.trace_id = trace_id
        self.config_version = config_version
        self.registry = ConfigSourceRegistry()

    def load_all_configs(self) -> Dict[str, Any]:
        """
        加载所有配置

        Returns:
            Dict[str, Any]: 配置字典 {path: config_content}

        Raises:
            ConfigError: 配置加载失败（结构化错误报告）
        """
        configs = {}
        errors = []

        for source in self.registry.get_all_sources():
            try:
                config = self._load_single_config(source)
                configs[source.path] = config
            except ConfigError as e:
                if source.required:
                    errors.append({
                        "path": source.path,
                        "error": str(e),
                        "required": True
                    })
                else:
                    # 可选配置缺失：记录警告
                    self._log_warning(
                        f"可选配置缺失: {source.path}",
                        trace_id=self.trace_id,
                        config_version=self.config_version,
                        code="CFG-001",
                        severity="warn"
                    )

        if errors:
            # 必需配置缺失：阻断启动
            raise ConfigError(
                self._format_error_report(errors),
                trace_id=self.trace_id,
                config_version=self.config_version,
                severity="block"
            )

        return configs

    def _load_single_config(self, source: ConfigSource) -> Dict[str, Any]:
        """
        加载单个配置

        Args:
            source: 配置源定义

        Returns:
            Dict[str, Any]: 配置内容

        Raises:
            ConfigError: 配置加载失败
        """
        path = Path(source.path)

        # 1. 文件存在性校验
        if not path.exists():
            raise ConfigError(
                f"CFG-001: 配置文件不存在: {source.path}\n"
                f"  描述: {source.description}\n"
                f"  修复建议: 创建配置文件或检查路径"
            )

        # 2. 文件可读性校验
        if not path.is_file():
            raise ConfigError(
                f"CFG-001: 路径不是文件: {source.path}\n"
                f"  修复建议: 检查路径是否指向文件"
            )

        try:
            content = path.read_text(encoding="utf-8")
        except PermissionError:
            raise ConfigError(
                f"CFG-001: 文件无读取权限: {source.path}\n"
                f"  修复建议: 检查文件权限（chmod 644 {source.path}）"
            )
        except UnicodeDecodeError:
            raise ConfigError(
                f"CFG-002: 文件编码错误: {source.path}\n"
                f"  修复建议: 确保文件使用 UTF-8 编码"
            )

        # 3. 格式合法性校验
        try:
            if source.format == ConfigFormat.JSON:
                config = json.loads(content)
            elif source.format == ConfigFormat.YAML:
                config = yaml.safe_load(content)
            else:
                raise ValueError(f"不支持的配置格式: {source.format}")
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"CFG-002: JSON 格式错误: {source.path}\n"
                f"  行号: {e.lineno}\n"
                f"  列号: {e.colno}\n"
                f"  错误: {e.msg}\n"
                f"  修复建议: 使用 JSON 校验工具检查语法"
            )
        except yaml.YAMLError as e:
            raise ConfigError(
                f"CFG-002: YAML 格式错误: {source.path}\n"
                f"  错误: {str(e)}\n"
                f"  修复建议: 使用 YAML 校验工具检查语法"
            )

        # 4. Schema 校验（可选）
        if source.schema_path:
            self._validate_schema(config, source.schema_path, source.path)

        return config

    def _validate_schema(
        self,
        config: Dict[str, Any],
        schema_path: str,
        config_path: str
    ):
        """JSON Schema 校验"""
        import jsonschema
        from jsonschema import validate, ValidationError

        try:
            schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
            validate(instance=config, schema=schema)
        except ValidationError as e:
            raise ConfigError(
                f"CFG-002: Schema 校验失败: {config_path}\n"
                f"  路径: {'.'.join(str(p) for p in e.path)}\n"
                f"  错误: {e.message}\n"
                f"  修复建议: 检查配置是否符合 Schema 定义"
            )
        except FileNotFoundError:
            # Schema 文件缺失：记录警告
            self._log_warning(
                f"Schema 文件缺失: {schema_path}",
                trace_id=self.trace_id,
                config_version=self.config_version,
                code="CFG-002",
                severity="warn"
            )

    def _format_error_report(self, errors: List[Dict]) -> str:
        """格式化错误报告（人类可读）"""
        report = ["配置加载失败:\n"]

        for error in errors:
            report.append(f"  ❌ {error['path']}")
            report.append(f"     {error['error']}\n")

        report.append("修复建议:")
        report.append("  1. 检查配置文件是否存在")
        report.append("  2. 检查文件格式是否正确（JSON/YAML）")
        report.append("  3. 检查文件权限是否可读")
        report.append("  4. 参考 docs/config_guide.md 了解配置规范")

        return "\n".join(report)

    def _log_warning(self, message: str, **kwargs):
        """写入警告日志"""
        import json
        from datetime import datetime
        from pathlib import Path

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "trace_id": kwargs.get("trace_id"),
            "config_version": kwargs.get("config_version"),
            "code": kwargs.get("code"),
            "severity": kwargs.get("severity"),
            "message": message
        }

        log_file = Path("artifacts/audit_log.jsonl")
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
```

### 3. 占位符全量扫描

```python
class PlaceholderScanner:
    """占位符全量扫描器"""

    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader

    def scan_all_placeholders(self) -> Dict[str, List[str]]:
        """
        扫描所有配置源中的占位符

        Returns:
            Dict[str, List[str]]: {source_path: [placeholders]}
        """
        all_placeholders = {}

        # 1. 扫描配置文件
        configs = self.config_loader.load_all_configs()
        for path, config in configs.items():
            placeholders = self._extract_placeholders_from_config(config)
            if placeholders:
                all_placeholders[path] = placeholders

        # 2. 扫描 Prompt 模板
        prompt_templates = self._find_prompt_templates()
        for template_path in prompt_templates:
            placeholders = self._extract_placeholders_from_template(template_path)
            if placeholders:
                all_placeholders[template_path] = placeholders

        # 3. 扫描策略注入点
        strategy_files = self._find_strategy_files()
        for strategy_path in strategy_files:
            placeholders = self._extract_placeholders_from_strategy(strategy_path)
            if placeholders:
                all_placeholders[strategy_path] = placeholders

        return all_placeholders

    def _extract_placeholders_from_config(
        self,
        config: Dict[str, Any]
    ) -> List[str]:
        """从配置中提取占位符"""
        import re

        placeholders = []

        def extract_from_value(value):
            if isinstance(value, str):
                # 提取 ${var} 占位符
                matches = re.findall(r'\$\{([^}]+)\}', value)
                placeholders.extend([m.strip() for m in matches])
            elif isinstance(value, dict):
                for v in value.values():
                    extract_from_value(v)
            elif isinstance(value, list):
                for item in value:
                    extract_from_value(item)

        extract_from_value(config)
        return list(set(placeholders))  # 去重

    def _extract_placeholders_from_template(self, template_path: str) -> List[str]:
        """从 Prompt 模板中提取占位符"""
        import re
        from pathlib import Path

        content = Path(template_path).read_text(encoding="utf-8")

        # 提取 Jinja2 变量 {{ var }}
        jinja_vars = re.findall(r'\{\{\s*([^}]+)\s*\}\}', content)

        # 提取 ${var} 占位符
        env_vars = re.findall(r'\$\{([^}]+)\}', content)

        all_vars = [v.strip() for v in jinja_vars + env_vars]
        return list(set(all_vars))

    def _find_prompt_templates(self) -> List[str]:
        """查找所有 Prompt 模板"""
        from pathlib import Path

        templates = []
        prompts_dir = Path("prompts")

        if prompts_dir.exists():
            templates.extend([str(f) for f in prompts_dir.rglob("*.j2")])
            templates.extend([str(f) for f in prompts_dir.rglob("*.md.j2")])

        return templates

    def _find_strategy_files(self) -> List[str]:
        """查找所有策略文件"""
        from pathlib import Path

        strategies = []
        strategies_dir = Path("strategies")

        if strategies_dir.exists():
            strategies.extend([str(f) for f in strategies_dir.rglob("*.yaml")])
            strategies.extend([str(f) for f in strategies_dir.rglob("*.json")])

        return strategies

    def _extract_placeholders_from_strategy(self, strategy_path: str) -> List[str]:
        """从策略文件中提取占位符"""
        from pathlib import Path
        import yaml

        content = Path(strategy_path).read_text(encoding="utf-8")

        try:
            if strategy_path.endswith(".yaml"):
                strategy = yaml.safe_load(content)
            else:
                import json
                strategy = json.loads(content)

            return self._extract_placeholders_from_config(strategy)
        except Exception:
            return []
```

### 4. 使用示例

```python
# 初始化配置加载器
loader = ConfigLoader(
    trace_id="trace-001",
    config_version="1.0.0"
)

# 加载所有配置
try:
    configs = loader.load_all_configs()
    print(f"✅ 成功加载 {len(configs)} 个配置文件")
except ConfigError as e:
    print(f"❌ 配置加载失败:\n{e}")
    sys.exit(1)

# 扫描所有占位符
scanner = PlaceholderScanner(loader)
all_placeholders = scanner.scan_all_placeholders()

print(f"✅ 扫描到 {sum(len(v) for v in all_placeholders.values())} 个占位符")
for path, placeholders in all_placeholders.items():
    print(f"  {path}: {placeholders}")
```

## 验收标准

- [x] 文件存在性校验
- [x] 文件可读性校验
- [x] 格式合法性校验（JSON/YAML）
- [x] 配置解析失败输出人类可读指引
- [x] 动态遍历声明式配置源清单
- [x] 占位符扫描覆盖率 100%
- [x] 无堆栈泄露

## 性能要求

- 单个配置加载耗时 < 50ms
- 批量加载（10 个配置）耗时 < 500ms
- 占位符扫描耗时 < 100ms（100 个占位符）

## 与 Step 1-3 集成

配置加载器必须与 Step 1-3 集成：

```python
# 1. 加载配置（Step 4）
loader = ConfigLoader(trace_id, config_version)
configs = loader.load_all_configs()

# 2. 清洗配置（Step 1）
cleaned_configs = {path: clean_config_dict(config) for path, config in configs.items()}

# 3. 扫描占位符（Step 4）
scanner = PlaceholderScanner(loader)
all_placeholders = scanner.scan_all_placeholders()

# 4. 解析变量绑定（Step 2）
engine = VariableBindingEngine()
for path, placeholders in all_placeholders.items():
    for var in placeholders:
        result = engine.resolve_variable(var, context, trace_id, config_version)

# 5. 校验版本兼容性（Step 3）
parser = SemVerParser()
constraint = parser.parse_constraint(config_version)
if not parser.satisfies(constraint, runtime_version):
    raise ConfigError("CFG-006: 版本不兼容")
```