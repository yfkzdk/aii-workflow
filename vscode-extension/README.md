# AII Workflow VS Code 扩展

用于管理AII工作流系统的VS Code扩展，提供可视化界面和便捷的操作方式。

## 功能特性

### 🚀 核心功能
- **一键启动**: 快速启动AII工作流系统
- **状态监控**: 实时监控系统状态和工作流进度
- **任务管理**: 创建、查看和管理AI任务
- **系统重置**: 一键重置系统到初始状态
- **备份管理**: 系统备份和恢复功能

### 🛠️ 便捷操作
- **命令面板集成**: 通过命令面板快速访问所有功能
- **侧边栏视图**: 在活动栏显示状态、任务和备份视图
- **快捷键支持**: 常用操作支持快捷键
- **上下文菜单**: 右键菜单快速创建任务
- **实时通知**: 任务状态变化实时通知

### 🔧 系统管理
- **系统验证**: 验证系统完整性
- **自动修复**: 自动检测和修复常见问题
- **配置管理**: 可视化配置系统参数
- **日志查看**: 查看系统运行日志

## 项目结构

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
│   ├── panel.html                # 面板HTML模板
│   ├── style.css                 # 样式文件
│   ├── script.js                 # 前端脚本
│   └── resources/                # 静态资源
├── resources/                    # 资源文件
│   ├── aii-icon.svg              # 扩展图标
│   └── aii-icon.png              # 扩展图标（PNG）
├── test/                         # 测试文件
├── package.json                  # 扩展配置文件
├── tsconfig.json                 # TypeScript配置
├── webpack.config.js             # Webpack配置
└── README.md                     # 本文件
```

## 安装说明

### 从源码安装
1. 克隆项目到本地
2. 安装依赖:
   ```bash
   cd vscode-extension
   npm install
   ```
3. 编译扩展:
   ```bash
   npm run compile
   ```
4. 打包扩展:
   ```bash
   npm run package
   ```
5. 在VS Code中安装生成的`.vsix`文件

### 开发模式
1. 安装VS Code扩展开发依赖
2. 运行开发模式:
   ```bash
   npm run watch
   ```
3. 按F5启动调试

## 配置说明

### 扩展配置
扩展提供以下配置选项:

```json
{
  "aiiWorkflow.enabled": true,
  "aiiWorkflow.workflowRoot": "",
  "aiiWorkflow.autoStart": false,
  "aiiWorkflow.refreshInterval": 30,
  "aiiWorkflow.showNotifications": true,
  "aiiWorkflow.powershellPath": "",
  "aiiWorkflow.backupAutoCleanup": true
}
```

### PowerShell模块依赖
扩展需要AII PowerShell模块支持，确保以下模块已正确安装:

1. `AIIWorkflow.psd1` - PowerShell模块清单
2. `Core.psm1` - 核心功能模块
3. `StateManager.psm1` - 状态管理模块
4. `TaskManager.psm1` - 任务管理模块
5. `VSCodeIntegration.psm1` - VS Code集成模块
6. `ResetManager.psm1` - 重置管理模块

## 使用指南

### 快速开始
1. 安装扩展后，VS Code左侧活动栏会出现AII Workflow图标
2. 点击图标打开侧边栏
3. 在状态视图中点击"启动工作流"按钮
4. 等待系统初始化完成

### 创建新任务
1. 在侧边栏点击"任务列表"视图
2. 点击"创建新任务"按钮
3. 输入任务描述
4. 点击"开始执行"按钮

### 系统重置
1. 在命令面板输入"AII Workflow: 重置系统"
2. 确认重置操作
3. 等待系统重置完成

### 备份管理
1. 在侧边栏点击"系统备份"视图
2. 查看现有备份列表
3. 点击"创建备份"按钮创建新备份
4. 选择备份并点击"恢复"按钮进行系统恢复

## 命令参考

### 核心命令
- `aii-workflow.start` - 启动工作流系统
- `aii-workflow.showPanel` - 显示控制面板
- `aii-workflow.createTask` - 创建新任务
- `aii-workflow.listTasks` - 查看任务列表
- `aii-workflow.resetSystem` - 重置系统
- `aii-workflow.showStatus` - 显示系统状态

### 系统管理命令
- `aii-workflow.validateSystem` - 验证系统完整性
- `aii-workflow.repairSystem` - 修复系统问题
- `aii-workflow.listBackups` - 列出系统备份
- `aii-workflow.backupSystem` - 创建系统备份

### 快捷键
- `Ctrl+Shift+A I` - 启动工作流
- `Ctrl+Shift+A P` - 显示控制面板
- `Ctrl+Shift+A T` - 创建新任务

## 故障排除

### 常见问题
1. **扩展无法启动**: 检查PowerShell模块是否正确安装
2. **状态监控不工作**: 检查工作流根目录配置
3. **任务执行失败**: 检查Python环境和依赖

### 日志查看
1. 打开VS Code输出面板 (`Ctrl+Shift+U`)
2. 选择"AII Workflow"输出通道
3. 查看详细的日志信息

## 开发指南

### 扩展架构
扩展采用MVVM架构:
- **Model**: PowerShell模块提供数据层
- **View**: Webview面板提供界面层
- **ViewModel**: TypeScript服务层连接Model和View

### 添加新功能
1. 在`package.json`中添加命令定义
2. 在`src/extension.ts`中注册命令处理器
3. 实现相应的TypeScript服务
4. 添加Webview界面（如果需要）
5. 更新侧边栏视图

### 测试扩展
```bash
# 运行单元测试
npm test

# 运行集成测试
npm run test-integration
```

## 许可证

MIT License

## 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开Pull Request