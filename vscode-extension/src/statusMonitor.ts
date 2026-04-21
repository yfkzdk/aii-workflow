import * as vscode from 'vscode';
import { PowerShellExecutor } from './utils/psExecutor';
import { AIIWorkflowConfig } from '../extension';

export interface WorkflowStatus {
    isRunning: boolean;
    lastHeartbeat?: Date;
    activeTasks: number;
    totalTasks: number;
    systemStatus: 'healthy' | 'warning' | 'error' | 'unknown';
    cpuUsage?: number;
    memoryUsage?: number;
    diskUsage?: number;
    uptime?: string;
}

export interface TaskStatus {
    id: string;
    name: string;
    description: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
    progress: number;
    startTime: Date;
    endTime?: Date;
    duration?: string;
}

export interface SystemInfo {
    workflowRoot: string;
    pythonVersion?: string;
    powershellVersion?: string;
    vsCodeExtensionVersion?: string;
    moduleStatus: {
        core: boolean;
        stateManager: boolean;
        taskManager: boolean;
        vscodeIntegration: boolean;
        resetManager: boolean;
    };
    lastBackup?: Date;
    backupCount: number;
}

export class StatusMonitor {
    private status: WorkflowStatus = {
        isRunning: false,
        activeTasks: 0,
        totalTasks: 0,
        systemStatus: 'unknown'
    };

    private tasks: TaskStatus[] = [];
    private systemInfo: SystemInfo = {
        workflowRoot: '',
        moduleStatus: {
            core: false,
            stateManager: false,
            taskManager: false,
            vscodeIntegration: false,
            resetManager: false
        },
        backupCount: 0
    };

    private refreshTimer: NodeJS.Timeout | undefined;
    private statusBarItem: vscode.StatusBarItem;
    private eventEmitter = new vscode.EventEmitter<WorkflowStatus>();

    public readonly onStatusChange = this.eventEmitter.event;

    constructor(
        private readonly context: vscode.ExtensionContext,
        private readonly config: AIIWorkflowConfig
    ) {
        // 创建状态栏项
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.tooltip = 'AII Workflow状态监控';
        this.updateStatusBar();

        // 注册配置变更监听
        vscode.workspace.onDidChangeConfiguration(this.handleConfigChange, this, context.subscriptions);
    }

    private handleConfigChange(event: vscode.ConfigurationChangeEvent): void {
        if (event.affectsConfiguration('aiiWorkflow')) {
            this.stop();
            this.start();
        }
    }

    public async start(): Promise<void> {
        // 停止现有的定时器
        this.stop();

        // 初始获取状态
        await this.refresh();

        // 设置定时刷新
        const interval = this.config.refreshInterval * 1000; // 转换为毫秒
        this.refreshTimer = setInterval(() => {
            this.refresh().catch(error => {
                console.error('状态刷新失败:', error);
            });
        }, interval);

        // 显示状态栏
        this.statusBarItem.show();

        vscode.window.showInformationMessage('AII Workflow状态监控已启动');
    }

    public stop(): void {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = undefined;
        }

        this.statusBarItem.hide();
    }

    public async refresh(): Promise<void> {
        try {
            const psExecutor = new PowerShellExecutor(this.config.workflowRoot, this.config.powershellPath);

            // 并行获取各种状态信息
            const [workflowStatus, taskList, systemInfo, backupList] = await Promise.all([
                this.getWorkflowStatus(psExecutor),
                this.getTaskList(psExecutor),
                this.getSystemInfo(psExecutor),
                this.getBackupList(psExecutor)
            ]);

            // 更新状态
            this.status = workflowStatus;
            this.tasks = taskList;
            this.systemInfo = systemInfo;
            this.systemInfo.backupCount = backupList.length;

            // 更新状态栏
            this.updateStatusBar();

            // 触发状态变更事件
            this.eventEmitter.fire(this.status);

            // 发送通知（如果启用）
            if (this.config.showNotifications && this.hasImportantChanges()) {
                this.showNotifications();
            }

        } catch (error) {
            console.error('刷新状态失败:', error);

            // 更新为错误状态
            this.status = {
                isRunning: false,
                activeTasks: 0,
                totalTasks: 0,
                systemStatus: 'error'
            };

            this.updateStatusBar();
        }
    }

    private async getWorkflowStatus(psExecutor: PowerShellExecutor): Promise<WorkflowStatus> {
        try {
            const status = await psExecutor.getWorkflowStatus();

            return {
                isRunning: status?.isRunning || false,
                lastHeartbeat: status?.lastHeartbeat ? new Date(status.lastHeartbeat) : undefined,
                activeTasks: status?.activeTasks || 0,
                totalTasks: status?.totalTasks || 0,
                systemStatus: status?.systemStatus || 'unknown',
                cpuUsage: status?.cpuUsage,
                memoryUsage: status?.memoryUsage,
                diskUsage: status?.diskUsage,
                uptime: status?.uptime
            };
        } catch (error) {
            console.error('获取工作流状态失败:', error);
            return {
                isRunning: false,
                activeTasks: 0,
                totalTasks: 0,
                systemStatus: 'error'
            };
        }
    }

    private async getTaskList(psExecutor: PowerShellExecutor): Promise<TaskStatus[]> {
        try {
            const tasks = await psExecutor.listTasks();

            return tasks.map((task: any) => ({
                id: task.id || `task-${Date.now()}`,
                name: task.name || '未命名任务',
                description: task.description || '无描述',
                status: this.mapTaskStatus(task.status),
                progress: task.progress || 0,
                startTime: task.startTime ? new Date(task.startTime) : new Date(),
                endTime: task.endTime ? new Date(task.endTime) : undefined,
                duration: task.duration || ''
            }));
        } catch (error) {
            console.error('获取任务列表失败:', error);
            return [];
        }
    }

    private mapTaskStatus(status: string): TaskStatus['status'] {
        const statusMap: { [key: string]: TaskStatus['status'] } = {
            'pending': 'pending',
            'running': 'running',
            'completed': 'completed',
            'failed': 'failed',
            'cancelled': 'cancelled',
            '等待中': 'pending',
            '运行中': 'running',
            '已完成': 'completed',
            '已失败': 'failed',
            '已取消': 'cancelled'
        };

        return statusMap[status] || 'pending';
    }

    private async getSystemInfo(psExecutor: PowerShellExecutor): Promise<SystemInfo> {
        try {
            // 这里需要从PowerShell模块获取系统信息
            // 暂时返回模拟数据
            return {
                workflowRoot: this.config.workflowRoot,
                moduleStatus: {
                    core: true,
                    stateManager: true,
                    taskManager: true,
                    vscodeIntegration: true,
                    resetManager: true
                },
                backupCount: 0
            };
        } catch (error) {
            console.error('获取系统信息失败:', error);
            return {
                workflowRoot: this.config.workflowRoot,
                moduleStatus: {
                    core: false,
                    stateManager: false,
                    taskManager: false,
                    vscodeIntegration: false,
                    resetManager: false
                },
                backupCount: 0
            };
        }
    }

    private async getBackupList(psExecutor: PowerShellExecutor): Promise<any[]> {
        try {
            return await psExecutor.listBackups();
        } catch (error) {
            console.error('获取备份列表失败:', error);
            return [];
        }
    }

    private updateStatusBar(): void {
        let text = '';
        let tooltip = 'AII Workflow状态: ';

        switch (this.status.systemStatus) {
            case 'healthy':
                text = '$(check) AII';
                tooltip += '健康';
                this.statusBarItem.color = new vscode.ThemeColor('statusBar.foreground');
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.background');
                break;
            case 'warning':
                text = '$(warning) AII';
                tooltip += '警告';
                this.statusBarItem.color = new vscode.ThemeColor('statusBarItem.warningForeground');
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
                break;
            case 'error':
                text = '$(error) AII';
                tooltip += '错误';
                this.statusBarItem.color = new vscode.ThemeColor('statusBarItem.errorForeground');
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
                break;
            default:
                text = '$(question) AII';
                tooltip += '未知';
                break;
        }

        // 添加任务计数
        if (this.status.activeTasks > 0) {
            text += ` (${this.status.activeTasks})`;
            tooltip += ` | 活动任务: ${this.status.activeTasks}`;
        }

        // 添加运行状态
        if (this.status.isRunning) {
            tooltip += ' | 运行中';
        } else {
            tooltip += ' | 已停止';
        }

        this.statusBarItem.text = text;
        this.statusBarItem.tooltip = tooltip;

        // 设置点击命令
        this.statusBarItem.command = 'aii-workflow.showStatus';
    }

    private hasImportantChanges(): boolean {
        // 这里可以添加逻辑来检测重要的状态变化
        // 例如：任务失败、系统错误等
        return false;
    }

    private showNotifications(): void {
        // 根据状态显示通知
        if (this.status.systemStatus === 'error') {
            vscode.window.showErrorMessage('AII工作流系统出现错误');
        } else if (this.status.systemStatus === 'warning') {
            vscode.window.showWarningMessage('AII工作流系统有警告');
        }
    }

    public getStatus(): WorkflowStatus {
        return { ...this.status };
    }

    public getTasks(): TaskStatus[] {
        return [...this.tasks];
    }

    public getSystemInfo(): SystemInfo {
        return { ...this.systemInfo };
    }

    public async showStatus(): Promise<void> {
        const panel = vscode.window.createWebviewPanel(
            'aiiWorkflowStatus',
            'AII Workflow状态',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true
            }
        );

        // 更新Webview内容
        this.updateStatusWebview(panel);

        // 监听面板关闭
        panel.onDidDispose(() => {
            // 清理资源
        }, null, this.context.subscriptions);
    }

    private updateStatusWebview(panel: vscode.WebviewPanel): void {
        const status = this.getStatus();
        const tasks = this.getTasks();
        const systemInfo = this.getSystemInfo();

        const html = `
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>AII Workflow状态</title>
                <style>
                    body {
                        font-family: var(--vscode-font-family);
                        padding: 20px;
                        background-color: var(--vscode-editor-background);
                        color: var(--vscode-editor-foreground);
                    }

                    .status-container {
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 20px;
                        margin-bottom: 20px;
                    }

                    .status-card {
                        background-color: var(--vscode-editor-background);
                        border: 1px solid var(--vscode-panel-border);
                        border-radius: 6px;
                        padding: 15px;
                    }

                    .status-header {
                        display: flex;
                        align-items: center;
                        margin-bottom: 10px;
                    }

                    .status-icon {
                        font-size: 24px;
                        margin-right: 10px;
                    }

                    .status-title {
                        font-size: 16px;
                        font-weight: bold;
                    }

                    .status-value {
                        font-size: 28px;
                        font-weight: bold;
                        margin: 10px 0;
                    }

                    .status-details {
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
                    }

                    .task-list {
                        margin-top: 20px;
                    }

                    .task-item {
                        background-color: var(--vscode-input-background);
                        border: 1px solid var(--vscode-panel-border);
                        border-radius: 4px;
                        padding: 10px;
                        margin-bottom: 10px;
                    }

                    .task-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 5px;
                    }

                    .task-name {
                        font-weight: bold;
                    }

                    .task-status {
                        padding: 2px 8px;
                        border-radius: 12px;
                        font-size: 12px;
                    }

                    .task-status.pending {
                        background-color: var(--vscode-statusBarItem-prominentBackground);
                        color: white;
                    }

                    .task-status.running {
                        background-color: var(--vscode-statusBarItem-warningBackground);
                        color: white;
                    }

                    .task-status.completed {
                        background-color: var(--vscode-statusBarItem-remoteBackground);
                        color: white;
                    }

                    .task-status.failed {
                        background-color: var(--vscode-statusBarItem-errorBackground);
                        color: white;
                    }

                    .progress-bar {
                        height: 4px;
                        background-color: var(--vscode-progressBar-background);
                        border-radius: 2px;
                        margin: 5px 0;
                        overflow: hidden;
                    }

                    .progress-fill {
                        height: 100%;
                        background-color: var(--vscode-progressBar-foreground);
                        transition: width 0.3s ease;
                    }

                    .system-info {
                        margin-top: 20px;
                    }

                    .info-grid {
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                        gap: 10px;
                        margin-top: 10px;
                    }

                    .info-item {
                        background-color: var(--vscode-input-background);
                        padding: 8px;
                        border-radius: 4px;
                        font-size: 12px;
                    }

                    .info-label {
                        font-weight: bold;
                        margin-bottom: 2px;
                    }

                    .info-value {
                        color: var(--vscode-descriptionForeground);
                    }

                    .refresh-button {
                        background-color: var(--vscode-button-background);
                        color: var(--vscode-button-foreground);
                        border: none;
                        padding: 8px 16px;
                        border-radius: 2px;
                        cursor: pointer;
                        margin-top: 10px;
                    }

                    .refresh-button:hover {
                        background-color: var(--vscode-button-hoverBackground);
                    }
                </style>
            </head>
            <body>
                <div class="status-container">
                    <div class="status-card">
                        <div class="status-header">
                            <div class="status-icon">📊</div>
                            <div class="status-title">系统状态</div>
                        </div>
                        <div class="status-value">${status.systemStatus === 'healthy' ? '健康' :
                            status.systemStatus === 'warning' ? '警告' :
                            status.systemStatus === 'error' ? '错误' : '未知'}</div>
                        <div class="status-details">
                            <div>运行状态: ${status.isRunning ? '运行中' : '已停止'}</div>
                            <div>活动任务: ${status.activeTasks}</div>
                            <div>总任务数: ${status.totalTasks}</div>
                            ${status.uptime ? `<div>运行时间: ${status.uptime}</div>` : ''}
                        </div>
                    </div>

                    <div class="status-card">
                        <div class="status-header">
                            <div class="status-icon">💻</div>
                            <div class="status-title">资源使用</div>
                        </div>
                        ${status.cpuUsage !== undefined ? `
                            <div style="margin-bottom: 8px;">
                                <div style="display: flex; justify-content: space-between;">
                                    <span>CPU: </span>
                                    <span>${status.cpuUsage.toFixed(1)}%</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${status.cpuUsage}%"></div>
                                </div>
                            </div>
                        ` : ''}
                        ${status.memoryUsage !== undefined ? `
                            <div style="margin-bottom: 8px;">
                                <div style="display: flex; justify-content: space-between;">
                                    <span>内存: </span>
                                    <span>${status.memoryUsage.toFixed(1)}%</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${status.memoryUsage}%"></div>
                                </div>
                            </div>
                        ` : ''}
                        ${status.diskUsage !== undefined ? `
                            <div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span>磁盘: </span>
                                    <span>${status.diskUsage.toFixed(1)}%</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${status.diskUsage}%"></div>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>

                <div class="task-list">
                    <h3>任务列表 (${tasks.length})</h3>
                    ${tasks.length > 0 ? tasks.map(task => `
                        <div class="task-item">
                            <div class="task-header">
                                <div class="task-name">${this.escapeHtml(task.name)}</div>
                                <div class="task-status ${task.status}">${this.getStatusText(task.status)}</div>
                            </div>
                            <div>${this.escapeHtml(task.description)}</div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${task.progress}%"></div>
                            </div>
                            <div style="font-size: 11px; color: var(--vscode-descriptionForeground); margin-top: 5px;">
                                开始时间: ${task.startTime.toLocaleString()} | 进度: ${task.progress}%
                                ${task.duration ? ` | 耗时: ${task.duration}` : ''}
                            </div>
                        </div>
                    `).join('') : '<div style="text-align: center; padding: 20px; color: var(--vscode-descriptionForeground);">暂无任务</div>'}
                </div>

                <div class="system-info">
                    <h3>系统信息</h3>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">工作流根目录</div>
                            <div class="info-value">${this.escapeHtml(systemInfo.workflowRoot)}</div>
                        </div>
                        ${systemInfo.pythonVersion ? `
                            <div class="info-item">
                                <div class="info-label">Python版本</div>
                                <div class="info-value">${this.escapeHtml(systemInfo.pythonVersion)}</div>
                            </div>
                        ` : ''}
                        ${systemInfo.powershellVersion ? `
                            <div class="info-item">
                                <div class="info-label">PowerShell版本</div>
                                <div class="info-value">${this.escapeHtml(systemInfo.powershellVersion)}</div>
                            </div>
                        ` : ''}
                        <div class="info-item">
                            <div class="info-label">备份数量</div>
                            <div class="info-value">${systemInfo.backupCount}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">模块状态</div>
                            <div class="info-value">${Object.values(systemInfo.moduleStatus).filter(v => v).length}/5 正常</div>
                        </div>
                    </div>
                </div>

                <button class="refresh-button" onclick="refreshStatus()">刷新状态</button>

                <script>
                    const vscode = acquireVsCodeApi();

                    function refreshStatus() {
                        vscode.postMessage({
                            command: 'refresh'
                        });
                    }

                    // 自动刷新
                    setInterval(refreshStatus, 30000);
                </script>
            </body>
            </html>
        `;

        panel.webview.html = html;
    }

    private escapeHtml(text: string): string {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    private getStatusText(status: TaskStatus['status']): string {
        const statusMap = {
            pending: '等待中',
            running: '运行中',
            completed: '已完成',
            failed: '已失败',
            cancelled: '已取消'
        };
        return statusMap[status] || '未知';
    }

    public dispose(): void {
        this.stop();
        this.statusBarItem.dispose();
        this.eventEmitter.dispose();
    }
}