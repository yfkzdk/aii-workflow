# AII Workflow VS Code 扩展安装指南

## 快速开始

### 1. 前置要求
- Visual Studio Code 1.60.0 或更高版本
- Node.js 16.0.0 或更高版本
- PowerShell 5.1 或更高版本
- AII 工作流系统已安装并配置

### 2. 安装步骤

#### 方法一：从源码安装（开发模式）
1. 克隆仓库：
```bash
git clone <repository-url>
cd aii-workflow-vscode
```

2. 安装依赖：
```bash
npm install
```

3. 编译扩展：
```bash
npm run compile
```

4. 在VS Code中启动扩展：
   - 按 `F5` 启动调试会话
   - 选择 "Extension Development Host" 窗口

#### 方法二：从VSIX文件安装（生产模式）
1. 打包扩展：
```bash
npm run package
```
2. 安装生成的 `.vsix` 文件：
   - 在VS Code中按 `Ctrl+Shift+P` (Windows/Linux) 或 `Cmd+Shift+P` (Mac)
   - 输入 "Extensions: Install from VSIX"
   - 选择生成的 `.vsix` 文件

#### 方法三：从市场安装（发布后）
1. 在VS Code扩展市场中搜索 "AII Workflow"
2. 点击安装按钮

## 配置说明

### 1. 扩展设置
扩展安装后，需要进行以下配置：

#### 必需配置
1. **工作流根目录**：
   - 打开VS Code设置 (`Ctrl+,`)
   - 搜索 "aiiWorkflow.workflowRoot"
   - 设置为AII工作流系统的根目录路径
   - 例如：`O:\AII\上下文助手`

#### 可选配置
1. **自动启动**：
   - `aiiWorkflow.autoStart`: 设置为 `true` 时，VS Code启动时自动启动AII工作流
   
2. **刷新间隔**：
   - `aiiWorkflow.refreshInterval`: 状态刷新间隔（秒），默认30秒
   
3. **通知设置**：
   - `aiiWorkflow.showNotifications`: 是否显示任务状态通知，默认 `true`
   
4. **PowerShell路径**：
   - `aiiWorkflow.powershellPath`: 自定义PowerShell路径，留空则自动检测
   
5. **备份自动清理**：
   - `aiiWorkflow.backupAutoCleanup`: 是否自动清理7天前的备份，默认 `true`

### 2. PowerShell模块配置
确保AII PowerShell模块已正确安装：

1. 打开PowerShell终端
2. 导航到工作流根目录
3. 运行安装脚本：
```powershell
.\powershell\install.ps1
```

4. 验证模块安装：
```powershell
Get-Module -ListAvailable -Name AIIWorkflow
Import-Module AIIWorkflow
Get-Command -Module AIIWorkflow
```

### 3. 环境验证
安装完成后，执行以下步骤验证环境：

1. 打开VS Code命令面板 (`Ctrl+Shift+P`)
2. 输入 "AII Workflow: 验证系统完整性"
3. 检查验证结果，确保所有模块状态正常

## 功能使用

### 1. 基本功能

#### 启动工作流
- 命令面板输入: "AII Workflow: 启动工作流"
- 快捷键: `Ctrl+Shift+A I`
- 侧边栏: 点击AII Workflow图标，点击"启动"按钮

#### 状态监控
- 侧边栏: 查看系统状态、资源使用情况、任务列表
- 实时刷新: 每30秒自动刷新一次
- 手动刷新: 点击刷新按钮或按 `F5`

#### 任务管理
- 创建任务: 命令面板输入 "AII Workflow: 创建新任务"
- 查看任务: 侧边栏任务列表视图
- 任务详情: 点击任务查看详细信息

#### 系统重置
- 命令面板输入: "AII Workflow: 重置系统"
- 注意: 此操作会清除所有任务和状态，建议先备份

### 2. 高级功能

#### 备份管理
1. 创建备份：
   - 命令面板输入: "AII Workflow: 备份系统"
   - 侧边栏: 系统备份视图 → 创建备份

2. 恢复备份：
   - 侧边栏: 系统备份视图 → 选择备份 → 恢复

3. 删除备份：
   - 侧边栏: 系统备份视图 → 选择备份 → 删除

#### 系统验证和修复
1. 验证系统：
   - 命令面板输入: "AII Workflow: 验证系统完整性"
   - 查看验证报告，了解系统状态

2. 修复系统：
   - 命令面板输入: "AII Workflow: 修复系统"
   - 自动修复常见问题

### 3. 快捷键参考

| 功能 | 快捷键 | 说明 |
|------|--------|------|
| 启动工作流 | `Ctrl+Shift+A I` | 启动AII工作流系统 |
| 显示控制面板 | `Ctrl+Shift+A P` | 打开状态监控面板 |
| 创建新任务 | `Ctrl+Shift+A T` | 创建新的AI任务 |

## 故障排除

### 常见问题

#### 1. 扩展无法启动
**症状**: VS Code侧边栏没有AII Workflow图标
**解决方法**:
1. 检查VS Code版本是否 >= 1.60.0
2. 重新加载VS Code窗口 (`Ctrl+Shift+P` → "Developer: Reload Window")
3. 检查扩展是否被禁用

#### 2. 无法连接到PowerShell模块
**症状**: 状态显示"错误"或"未知"
**解决方法**:
1. 验证工作流根目录配置
2. 检查PowerShell模块是否正确安装
3. 打开PowerShell终端，手动运行 `Import-Module AIIWorkflow`
4. 查看VS Code输出面板的"AII Workflow"通道

#### 3. 任务创建失败
**症状**: 创建任务时显示错误
**解决方法**:
1. 验证Python环境是否正确配置
2. 检查工作流脚本是否可执行
3. 查看任务日志获取详细信息

### 日志查看

1. 打开VS Code输出面板 (`Ctrl+Shift+U`)
2. 选择"AII Workflow"输出通道
3. 查看详细的日志信息，包括：
   - 扩展启动日志
   - PowerShell命令执行日志
   - 任务执行日志
   - 错误和警告信息

### 调试模式

如需更详细的日志，可以启用调试模式：

1. 修改VS Code设置：
```json
{
  "aiiWorkflow.debug": true
}
```

2. 重启VS Code
3. 查看调试日志

## 开发指南

### 项目结构
```
vscode-extension/
├── src/                          # TypeScript源代码
│   ├── extension.ts              # 扩展入口文件
│   ├── statusMonitor.ts          # 状态监控服务
│   ├── taskManager.ts            # 任务管理器
│   ├── resetManager.ts           # 重置管理器
│   ├── backupManager.ts          # 备份管理器
│   ├── webview/                  # Webview相关
│   │   ├── panel.ts              # Webview面板管理
│   │   ├── statusPanel.ts        # 状态面板
│   │   └── taskPanel.ts          # 任务面板
│   └── utils/                    # 工具函数
│       ├── psExecutor.ts         # PowerShell执行器
│       ├── fileUtils.ts          # 文件操作工具
│       └── configManager.ts      # 配置管理器
├── webview/                      # Webview前端文件
├── resources/                    # 资源文件
├── test/                         # 测试文件
├── package.json                  # 扩展配置文件
├── tsconfig.json                 # TypeScript配置
├── webpack.config.js             # Webpack配置
└── README.md                     # 说明文档
```

### 开发命令

```bash
# 安装依赖
npm install

# 开发模式（自动编译）
npm run watch

# 生产编译
npm run compile

# 打包扩展
npm run package

# 代码检查
npm run lint

# 运行测试
npm test
```

### 调试扩展

1. 按 `F5` 启动调试
2. 选择 "Extension Development Host"
3. 在新窗口中测试扩展功能
4. 在调试控制台查看日志

### 添加新功能

1. 在 `package.json` 中添加命令定义
2. 在 `src/extension.ts` 中注册命令处理器
3. 实现相应的TypeScript服务类
4. 如果需要UI，创建Webview面板
5. 更新侧边栏视图（如果需要）

## 更新日志

### v1.0.0 (2026-04-15)
- 初始版本发布
- 支持AII工作流状态监控
- 支持任务创建和管理
- 支持系统重置和备份恢复
- 集成PowerShell模块
- 提供Webview控制面板

## 联系方式

- 问题反馈: [GitHub Issues](https://github.com/yourusername/aii-workflow-vscode/issues)
- 文档: [README.md](README.md)
- 源代码: [GitHub Repository](https://github.com/yourusername/aii-workflow-vscode)

## 许可证

MIT License - 详见 LICENSE 文件