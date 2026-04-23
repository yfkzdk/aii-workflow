# Step 5: PreFlightReport 聚合 & DRY_RUN 模式规范

## 目标
建立 PreFlightReport 对象，聚合 errors/warnings/compatibility_status，启动失败时输出分级摘要，支持 JSON 导出，增加 --dry-run 标志。

## 核心问题

### 当前缺陷

1. **错误分散抛出，无统一收敛**
   ```python
   # ❌ 错误：错误分散抛出，无统一收敛
   if errors:
       print("❌ 启动前校验失败:")
       for error in errors:
           print(f"  - {error}")
       sys.exit(1)
   ```

2. **无状态机反馈**
   ```python
   # ❌ 错误：无状态机反馈
   # 缺乏预检状态追踪（PENDING/RUNNING/COMPLETED/FAILED）
   ```

3. **不支持 DRY_RUN 模式**
   ```python
   # ❌ 错误：不支持 DRY_RUN 模式
   # 无法仅输出预检结果而不初始化运行时
   ```

## 修复方案

### 1. PreFlightReport 对象

```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
from pathlib import Path

class PreFlightStatus(Enum):
    """预检状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class ErrorSeverity(Enum):
    """错误严重性"""
    BLOCK = "block"      # 阻断启动
    WARN = "warn"        # 警告
    INFO = "info"        # 信息

@dataclass
class PreFlightError:
    """预检错误"""
    code: str                    # 错误码（CFG-001）
    message: str                 # 错误消息
    severity: ErrorSeverity      # 严重性
    path: Optional[str] = None   # 文件路径（可选）
    suggestion: Optional[str] = None  # 修复建议（可选）

@dataclass
class PreFlightWarning:
    """预检警告"""
    code: str                    # 警告码
    message: str                 # 警告消息
    path: Optional[str] = None   # 文件路径（可选）

@dataclass
class CompatibilityStatus:
    """兼容性状态"""
    config_version: str          # 配置版本
    runtime_version: str         # 运行时版本
    compatible: bool             # 是否兼容
    operator: str                # 操作符（^, ~, >=, =）
    message: str                 # 兼容性消息

@dataclass
class PreFlightReport:
    """预检报告"""
    trace_id: str                          # 链路追踪 ID
    config_version: str                    # 配置版本
    status: PreFlightStatus = PreFlightStatus.PENDING  # 预检状态
    start_time: datetime = field(default_factory=datetime.now)  # 开始时间
    end_time: Optional[datetime] = None    # 结束时间

    errors: List[PreFlightError] = field(default_factory=list)  # 错误列表
    warnings: List[PreFlightWarning] = field(default_factory=list)  # 警告列表
    compatibility_status: Optional[CompatibilityStatus] = None  # 兼容性状态

    config_sources: List[str] = field(default_factory=list)  # 配置源列表
    placeholders_scanned: int = 0          # 扫描到的占位符数量
    variables_bound: int = 0               # 绑定的变量数量

    def add_error(self, error: PreFlightError):
        """添加错误"""
        self.errors.append(error)

    def add_warning(self, warning: PreFlightWarning):
        """添加警告"""
        self.warnings.append(warning)

    def set_compatibility_status(self, status: CompatibilityStatus):
        """设置兼容性状态"""
        self.compatibility_status = status

    def mark_completed(self):
        """标记完成"""
        self.status = PreFlightStatus.COMPLETED
        self.end_time = datetime.now()

    def mark_failed(self):
        """标记失败"""
        self.status = PreFlightStatus.FAILED
        self.end_time = datetime.now()

    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0

    def has_block_errors(self) -> bool:
        """是否有阻断性错误"""
        return any(e.severity == ErrorSeverity.BLOCK for e in self.errors)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "config_version": self.config_version,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else None,
            "errors": [
                {
                    "code": e.code,
                    "message": e.message,
                    "severity": e.severity.value,
                    "path": e.path,
                    "suggestion": e.suggestion
                }
                for e in self.errors
            ],
            "warnings": [
                {
                    "code": w.code,
                    "message": w.message,
                    "path": w.path
                }
                for w in self.warnings
            ],
            "compatibility_status": {
                "config_version": self.compatibility_status.config_version,
                "runtime_version": self.compatibility_status.runtime_version,
                "compatible": self.compatibility_status.compatible,
                "operator": self.compatibility_status.operator,
                "message": self.compatibility_status.message
            } if self.compatibility_status else None,
            "config_sources": self.config_sources,
            "placeholders_scanned": self.placeholders_scanned,
            "variables_bound": self.variables_bound
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save_to_file(self, path: str):
        """保存到文件"""
        Path(path).write_text(self.to_json(), encoding="utf-8")

    def print_summary(self):
        """打印分级摘要"""
        print("\n" + "=" * 80)
        print("PreFlight Report Summary")
        print("=" * 80)
        print(f"Trace ID: {self.trace_id}")
        print(f"Config Version: {self.config_version}")
        print(f"Status: {self.status.value.upper()}")
        print(f"Duration: {(self.end_time - self.start_time).total_seconds():.2f}s" if self.end_time else "N/A")
        print("")

        # 错误摘要
        if self.errors:
            print(f"Errors ({len(self.errors)}):")
            for error in self.errors:
                severity_icon = "❌" if error.severity == ErrorSeverity.BLOCK else "⚠️"
                print(f"  {severity_icon} [{error.code}] {error.message}")
                if error.path:
                    print(f"     Path: {error.path}")
                if error.suggestion:
                    print(f"     Suggestion: {error.suggestion}")
            print("")

        # 警告摘要
        if self.warnings:
            print(f"Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠️  [{warning.code}] {warning.message}")
                if warning.path:
                    print(f"     Path: {warning.path}")
            print("")

        # 兼容性状态
        if self.compatibility_status:
            status_icon = "✅" if self.compatibility_status.compatible else "❌"
            print(f"Compatibility Status:")
            print(f"  {status_icon} {self.compatibility_status.message}")
            print(f"     Config: {self.compatibility_status.config_version}")
            print(f"     Runtime: {self.compatibility_status.runtime_version}")
            print(f"     Operator: {self.compatibility_status.operator}")
            print("")

        # 统计信息
        print(f"Statistics:")
        print(f"  Config Sources: {len(self.config_sources)}")
        print(f"  Placeholders Scanned: {self.placeholders_scanned}")
        print(f"  Variables Bound: {self.variables_bound}")
        print("=" * 80 + "\n")
```

### 2. PreFlightValidator（集成 Step 1-4）

```python
from typing import Dict, Any
import sys

class PreFlightValidator:
    """预检验证器（集成 Step 1-4）"""

    def __init__(self, trace_id: str, config_version: str, dry_run: bool = False):
        self.trace_id = trace_id
        self.config_version = config_version
        self.dry_run = dry_run
        self.report = PreFlightReport(
            trace_id=trace_id,
            config_version=config_version
        )

        # 初始化 Step 1-4 组件
        self.config_loader = ConfigLoader(trace_id, config_version)
        self.variable_engine = VariableBindingEngine()
        self.semver_parser = SemVerParser()
        self.placeholder_scanner = PlaceholderScanner(self.config_loader)

    def validate_all(self) -> PreFlightReport:
        """
        执行全量预检

        Returns:
            PreFlightReport: 预检报告
        """
        self.report.status = PreFlightStatus.RUNNING

        try:
            # Step 1: 标识符清洗（已在各模块中集成）
            self._step1_identifier_cleaning()

            # Step 2: 变量绑定
            self._step2_variable_binding()

            # Step 3: 版本兼容性
            self._step3_version_compatibility()

            # Step 4: 配置加载
            self._step4_config_loading()

            # Step 5: 占位符扫描
            self._step5_placeholder_scanning()

            # 标记完成
            if not self.report.has_block_errors():
                self.report.mark_completed()
            else:
                self.report.mark_failed()

        except Exception as e:
            # 捕获未预期异常
            self.report.add_error(PreFlightError(
                code="UNKNOWN",
                message=f"未预期错误: {str(e)}",
                severity=ErrorSeverity.BLOCK
            ))
            self.report.mark_failed()

        return self.report

    def _step1_identifier_cleaning(self):
        """Step 1: 标识符清洗"""
        # 已在各模块中集成（clean_config_dict, validate_error_code 等）
        pass

    def _step2_variable_binding(self):
        """Step 2: 变量绑定"""
        context = self._get_runtime_context()

        # 关键变量绑定
        critical_vars = ["plan.id", "user.role", "stage.name"]
        for var in critical_vars:
            try:
                result = self.variable_engine.resolve_variable(
                    var, context, self.trace_id, self.config_version
                )
                self.report.variables_bound += 1
            except ConfigError as e:
                self.report.add_error(PreFlightError(
                    code="CFG-005",
                    message=str(e),
                    severity=ErrorSeverity.BLOCK,
                    suggestion=f"设置环境变量或上下文: {var}"
                ))

        # 非关键变量绑定
        non_critical_vars = ["project.security_level", "task.id"]
        for var in non_critical_vars:
            result = self.variable_engine.resolve_variable(
                var, context, self.trace_id, self.config_version
            )
            if result.binding_status == BindingStatus.DEFAULT_USED:
                self.report.add_warning(PreFlightWarning(
                    code="CFG-005",
                    message=result.warning_msg
                ))
            self.report.variables_bound += 1

    def _step3_version_compatibility(self):
        """Step 3: 版本兼容性"""
        runtime_version = self._get_runtime_version()

        constraint = self.semver_parser.parse_constraint(self.config_version)
        compatible = self.semver_parser.satisfies(constraint, runtime_version)

        self.report.set_compatibility_status(CompatibilityStatus(
            config_version=self.config_version,
            runtime_version=runtime_version,
            compatible=compatible,
            operator=constraint.operator.value,
            message=f"配置版本 {self.config_version} 与运行时版本 {runtime_version} {'兼容' if compatible else '不兼容'}"
        ))

        if not compatible:
            self.report.add_error(PreFlightError(
                code="CFG-006",
                message=f"版本不兼容: 配置 {self.config_version} 与运行时 {runtime_version}",
                severity=ErrorSeverity.BLOCK,
                suggestion="检查配置版本或升级运行时"
            ))

    def _step4_config_loading(self):
        """Step 4: 配置加载"""
        try:
            configs = self.config_loader.load_all_configs()
            self.report.config_sources = list(configs.keys())
        except ConfigError as e:
            self.report.add_error(PreFlightError(
                code="CFG-001",
                message=str(e),
                severity=ErrorSeverity.BLOCK,
                suggestion="检查配置文件是否存在、格式是否正确、权限是否可读"
            ))

    def _step5_placeholder_scanning(self):
        """Step 5: 占位符扫描"""
        all_placeholders = self.placeholder_scanner.scan_all_placeholders()
        self.report.placeholders_scanned = sum(len(v) for v in all_placeholders.values())

    def _get_runtime_context(self) -> Dict[str, Any]:
        """获取运行时上下文"""
        # 从环境变量或配置文件获取
        import os
        return {
            "plan.id": os.getenv("PLAN_ID"),
            "user.role": os.getenv("USER_ROLE"),
            "stage.name": os.getenv("STAGE_NAME"),
            "project.security_level": os.getenv("PROJECT_SECURITY_LEVEL"),
            "task.id": os.getenv("TASK_ID")
        }

    def _get_runtime_version(self) -> str:
        """获取运行时版本"""
        import os
        return os.getenv("RUNTIME_VERSION", "1.0.0")
```

### 3. DRY_RUN 模式

```python
import argparse

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Skill 调用集成系统")
    parser.add_argument("--dry-run", action="store_true", help="仅执行预检，不初始化运行时")
    parser.add_argument("--trace-id", default="trace-001", help="链路追踪 ID")
    parser.add_argument("--config-version", default="1.0.0", help="配置版本")
    parser.add_argument("--output", default="artifacts/preflight_report.json", help="报告输出路径")

    args = parser.parse_args()

    # 初始化预检验证器
    validator = PreFlightValidator(
        trace_id=args.trace_id,
        config_version=args.config_version,
        dry_run=args.dry_run
    )

    # 执行预检
    report = validator.validate_all()

    # 打印分级摘要
    report.print_summary()

    # 保存报告
    report.save_to_file(args.output)
    print(f"✅ 预检报告已保存: {args.output}")

    # DRY_RUN 模式：仅输出预检结果，不初始化运行时
    if args.dry_run:
        print("🔍 DRY_RUN 模式: 仅执行预检，不初始化运行时")
        if report.has_block_errors():
            print("❌ 预检失败，存在阻断性错误")
            sys.exit(1)
        else:
            print("✅ 预检通过，可以启动")
            sys.exit(0)

    # 正常模式：预检通过后初始化运行时
    if report.has_block_errors():
        print("❌ 预检失败，无法启动")
        sys.exit(1)

    print("✅ 预检通过，初始化运行时...")
    # 初始化运行时（略）

if __name__ == "__main__":
    main()
```

### 4. 使用示例

#### 4.1 正常模式

```bash
# 执行预检并初始化运行时
python main.py --trace-id trace-001 --config-version 1.0.0

# 输出示例：
# ================================================================================
# PreFlight Report Summary
# ================================================================================
# Trace ID: trace-001
# Config Version: 1.0.0
# Status: COMPLETED
# Duration: 0.45s
#
# Compatibility Status:
#   ✅ 配置版本 1.0.0 与运行时版本 1.0.0 兼容
#      Config: 1.0.0
#      Runtime: 1.0.0
#      Operator: =
#
# Statistics:
#   Config Sources: 2
#   Placeholders Scanned: 5
#   Variables Bound: 5
# ================================================================================
#
# ✅ 预检报告已保存: artifacts/preflight_report.json
# ✅ 预检通过，初始化运行时...
```

#### 4.2 DRY_RUN 模式

```bash
# 仅执行预检，不初始化运行时
python main.py --dry-run --trace-id trace-001 --config-version 1.0.0

# 输出示例：
# ================================================================================
# PreFlight Report Summary
# ================================================================================
# ...
# ================================================================================
#
# ✅ 预检报告已保存: artifacts/preflight_report.json
# 🔍 DRY_RUN 模式: 仅执行预检，不初始化运行时
# ✅ 预检通过，可以启动
```

#### 4.3 预检失败示例

```bash
python main.py --dry-run --config-version 2.0.0

# 输出示例：
# ================================================================================
# PreFlight Report Summary
# ================================================================================
# Trace ID: trace-001
# Config Version: 2.0.0
# Status: FAILED
# Duration: 0.12s
#
# Errors (1):
#   ❌ [CFG-006] 版本不兼容: 配置 2.0.0 与运行时 1.0.0
#      Suggestion: 检查配置版本或升级运行时
#
# Compatibility Status:
#   ❌ 配置版本 2.0.0 与运行时版本 1.0.0 不兼容
#      Config: 2.0.0
#      Runtime: 1.0.0
#      Operator: =
# ================================================================================
#
# ✅ 预检报告已保存: artifacts/preflight_report.json
# 🔍 DRY_RUN 模式: 仅执行预检，不初始化运行时
# ❌ 预检失败，存在阻断性错误
```

## 验收标准

- [x] PreFlightReport 对象聚合 errors/warnings/compatibility_status
- [x] 启动失败时输出分级摘要
- [x] 支持 JSON 导出
- [x] 支持 --dry-run 标志
- [x] 无静默失败
- [x] 预检状态机（PENDING/RUNNING/COMPLETED/FAILED）

## 性能要求

- 预检总耗时 < 1s
- 报告生成耗时 < 50ms
- JSON 导出耗时 < 10ms

## 与 Step 1-4 集成

PreFlightValidator 已集成 Step 1-4：

```python
# Step 1: 标识符清洗（已集成到各模块）
# Step 2: 变量绑定（VariableBindingEngine）
# Step 3: 版本兼容性（SemVerParser）
# Step 4: 配置加载（ConfigLoader）
# Step 5: 占位符扫描（PlaceholderScanner）
```