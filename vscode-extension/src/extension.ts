import * as vscode from 'vscode';
import { StatusMonitor } from './statusMonitor';
import { TaskManager } from './taskManager';
import { ResetManager } from './resetManager';
import { BackupManager } from './backupManager';
import { AIIWebviewPanel } from './webview/panel';
import { PowerShellExecutor } from './utils/psExecutor';

// 扩展配置接口
interface AIIWorkflowConfig {
    enabled: boolean;
    workflowRoot: string;
    autoStart: boolean;
    refreshInterval: number;
    showNotifications: boolean;
    powershellPath: string;
    backupAutoCleanup: boolean;
}

export class AIIWorkflowExtension {
    private static instance: AIIWorkflowExtension;

    private statusMonitor: StatusMonitor | undefined;
    private taskManager: TaskManager | undefined;
    private resetManager: ResetManager | undefined;
    private backupManager: BackupManager | undefined;
    private psExecutor: PowerShellExecutor | undefined;

    private config: AIIWorkflowConfig;
    private webviewPanel: AIIWebviewPanel | undefined;

    private constructor(private readonly context: vscode.ExtensionContext) {
        this.config = this.loadConfig();
    }

    public static getInstance(context?: vscode.ExtensionContext): AIIWorkflowExtension {
        if (!AIIWorkflowExtension.instance && context) {
            AIIWorkflowExtension.instance = new AIIWorkflowExtension(context);
        }
        return AIIWorkflowExtension.instance;
    }

    private loadConfig(): AIIWorkflowConfig {
        const config = vscode.workspace.getConfiguration('aiiWorkflow');

        return {
            enabled: config.get<boolean>('enabled', true),
            workflowRoot: config.get<string>('workflowRoot', ''),
            autoStart: config.get<boolean>('autoStart', false),
            refreshInterval: config.get<number>('refreshInterval', 30),
            showNotifications: config.get<boolean>('showNotifications', true),
            powershellPath: config.get<string>('powershellPath', ''),
            backupAutoCleanup: config.get<boolean>('backupAutoCleanup', true)
        };
    }

    private async initializeServices(): Promise<boolean> {
        try {
            // 初始化PowerShell执行器
            this.psExecutor = new PowerShellExecutor(this.config.workflowRoot);

            // 检查工作流根目录
            if (!this.config.workflowRoot) {
                await this.promptForWorkflowRoot();
                this.config = this.loadConfig();

                if (!this.config.workflowRoot) {
                    vscode.window.showErrorMessage('AII工作流根目录未配置。请在设置中配置aiiWorkflow.workflowRoot');
                    return false;
                }
            }

            // 验证系统完整性
            const isValid = await this.validateSystem();
            if (!isValid) {
                const choice = await vscode.window.showWarningMessage(
                    'AII工作流系统验证失败。是否尝试修复？',
                    '修复', '取消'
                );

                if (choice === '修复') {
                    await this.repairSystem();
                } else {
                    return false;
                }
            }

            // 初始化各个管理器
            this.statusMonitor = new StatusMonitor(this.context, this.config);
            this.taskManager = new TaskManager(this.context, this.config);
            this.resetManager = new ResetManager(this.context, this.config);
            this.backupManager = new BackupManager(this.context, this.config);

            // 启动状态监控
            this.statusMonitor.start();

            // 自动启动工作流（如果配置）
            if (this.config.autoStart) {
                await this.startWorkflow();
            }

            return true;

        } catch (error) {
            vscode.window.showErrorMessage(`初始化AII工作流扩展失败: ${error}`);
            return false;
        }
    }

    private async promptForWorkflowRoot(): Promise<void> {
        const result = await vscode.window.showOpenDialog({
            canSelectFiles: false,
            canSelectFolders: true,
            canSelectMany: false,
            openLabel: '选择AII工作流根目录',
            title: '选择AII工作流根目录'
        });

        if (result && result.length > 0) {
            const workflowRoot = result[0].fsPath;

            // 验证目录结构
            const isValid = await this.validateWorkflowRoot(workflowRoot);
            if (isValid) {
                await vscode.workspace.getConfiguration().update(
                    'aiiWorkflow.workflowRoot',
                    workflowRoot,
                    vscode.ConfigurationTarget.Global
                );

                vscode.window.showInformationMessage(`AII工作流根目录已设置为: ${workflowRoot}`);
            } else {
                vscode.window.showErrorMessage('所选目录不是有效的AII工作流根目录');
            }
        }
    }

    private async validateWorkflowRoot(rootPath: string): Promise<boolean> {
        if (!this.psExecutor) {
            return false;
        }

        try {
            const result = await this.psExecutor.executeCommand(
                `Test-Path -Path "${rootPath}\\ww_enhanced.py" -PathType Leaf`
            );

            return result.trim() === 'True';
        } catch (error) {
            return false;
        }
    }

    private async validateSystem(): Promise<boolean> {
        if (!this.psExecutor) {
            return false;
        }

        try {
            const result = await this.psExecutor.executeCommand('Test-AIISystem');
            return result && result.includes('"Status": "健康"');
        } catch (error) {
            return false;
        }
    }

    private async repairSystem(): Promise<void> {
        if (!this.psExecutor) {
            return;
        }

        try {
            await this.psExecutor.executeCommand('Repair-AIISystem');
            vscode.window.showInformationMessage('系统修复完成');
        } catch (error) {
            vscode.window.showErrorMessage(`系统修复失败: ${error}`);
        }
    }

    // 公开方法 - 命令处理
    public async startWorkflow(): Promise<void> {
        if (!this.psExecutor) {
            vscode.window.showErrorMessage('PowerShell执行器未初始化');
            return;
        }

        try {
            vscode.window.showInformationMessage('正在启动AII工作流...');

            const result = await this.psExecutor.executeCommand('Start-AIIWorkflow');

            if (result && result.includes('Workflow started successfully')) {
                vscode.window.showInformationMessage('AII工作流启动成功');

                // 更新状态监控
                if (this.statusMonitor) {
                    this.statusMonitor.refresh();
                }
            } else {
                vscode.window.showErrorMessage('AII工作流启动失败');
            }

        } catch (error) {
            vscode.window.showErrorMessage(`启动AII工作流失败: ${error}`);
        }
    }

    public async showPanel(): Promise<void> {
        if (!this.webviewPanel) {
            this.webviewPanel = new AIIWebviewPanel(this.context, this.config);
        }

        this.webviewPanel.show();
    }

    public async createTask(): Promise<void> {
        const description = await vscode.window.showInputBox({
            prompt: '请输入任务描述',
            placeHolder: '例如: 分析项目架构并生成文档',
            validateInput: (text) => {
                return text && text.trim().length > 0 ? null : '任务描述不能为空';
            }
        });

        if (description && this.taskManager) {
            await this.taskManager.createTask(description);
        }
    }

    public async listTasks(): Promise<void> {
        if (this.taskManager) {
            await this.taskManager.showTaskList();
        }
    }

    public async resetSystem(): Promise<void> {
        const choice = await vscode.window.showWarningMessage(
            '此操作将重置AII工作流系统，所有任务和状态将被清除。确认重置？',
            { modal: true },
            '确认重置', '取消'
        );

        if (choice === '确认重置' && this.resetManager) {
            await this.resetManager.resetSystem();
        }
    }

    public async showStatus(): Promise<void> {
        if (this.statusMonitor) {
            await this.statusMonitor.showStatus();
        }
    }

    public async validateSystemCommand(): Promise<void> {
        const isValid = await this.validateSystem();

        if (isValid) {
            vscode.window.showInformationMessage('✅ AII工作流系统验证通过');
        } else {
            vscode.window.showWarningMessage('⚠️ AII工作流系统验证失败');
        }
    }

    public async repairSystemCommand(): Promise<void> {
        await this.repairSystem();
    }

    public async listBackups(): Promise<void> {
        if (this.backupManager) {
            await this.backupManager.showBackupList();
        }
    }

    public async backupSystem(): Promise<void> {
        if (this.backupManager) {
            await this.backupManager.createBackup();
        }
    }

    public async refreshAll(): Promise<void> {
        if (this.statusMonitor) {
            this.statusMonitor.refresh();
        }

        vscode.window.showInformationMessage('AII工作流状态已刷新');
    }

    public dispose(): void {
        // 清理资源
        if (this.statusMonitor) {
            this.statusMonitor.dispose();
        }

        if (this.taskManager) {
            this.taskManager.dispose();
        }

        if (this.resetManager) {
            this.resetManager.dispose();
        }

        if (this.backupManager) {
            this.backupManager.dispose();
        }

        if (this.webviewPanel) {
            this.webviewPanel.dispose();
        }

        if (this.psExecutor) {
            this.psExecutor.dispose();
        }
    }

    public getConfig(): AIIWorkflowConfig {
        return { ...this.config };
    }
}

// 扩展激活函数
export function activate(context: vscode.ExtensionContext): void {
    console.log('AII Workflow扩展已激活');

    // 创建扩展实例
    const extension = AIIWorkflowExtension.getInstance(context);

    // 注册命令
    const commands = [
        vscode.commands.registerCommand('aii-workflow.start', () => extension.startWorkflow()),
        vscode.commands.registerCommand('aii-workflow.showPanel', () => extension.showPanel()),
        vscode.commands.registerCommand('aii-workflow.createTask', () => extension.createTask()),
        vscode.commands.registerCommand('aii-workflow.listTasks', () => extension.listTasks()),
        vscode.commands.registerCommand('aii-workflow.resetSystem', () => extension.resetSystem()),
        vscode.commands.registerCommand('aii-workflow.showStatus', () => extension.showStatus()),
        vscode.commands.registerCommand('aii-workflow.validateSystem', () => extension.validateSystemCommand()),
        vscode.commands.registerCommand('aii-workflow.repairSystem', () => extension.repairSystemCommand()),
        vscode.commands.registerCommand('aii-workflow.listBackups', () => extension.listBackups()),
        vscode.commands.registerCommand('aii-workflow.backupSystem', () => extension.backupSystem()),
        vscode.commands.registerCommand('aii-workflow.refresh', () => extension.refreshAll())
    ];

    // 添加到订阅
    commands.forEach(command => context.subscriptions.push(command));

    // 初始化服务
    extension.initializeServices().then(success => {
        if (success) {
            console.log('AII Workflow扩展初始化成功');
        } else {
            console.warn('AII Workflow扩展初始化失败');
        }
    });
}

// 扩展停用函数
export function deactivate(): void {
    console.log('AII Workflow扩展已停用');

    const extension = AIIWorkflowExtension.getInstance();
    if (extension) {
        extension.dispose();
    }
}