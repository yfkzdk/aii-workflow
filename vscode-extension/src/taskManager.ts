import * as vscode from 'vscode';
import { PowerShellExecutor } from './utils/psExecutor';
import { AIIWorkflowConfig } from '../extension';

export interface TaskInfo {
    id: string;
    name: string;
    description: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
    progress: number;
    startTime: Date;
    endTime?: Date;
    duration?: string;
    result?: any;
    logs?: string[];
}

export interface CreateTaskOptions {
    description: string;
    priority?: 'low' | 'normal' | 'high';
    timeout?: number;
    tags?: string[];
    notifyOnComplete?: boolean;
}

export class TaskManager {
    private tasks: Map<string, TaskInfo> = new Map();
    private taskTreeProvider: TaskTreeProvider | undefined;
    private psExecutor: PowerShellExecutor;

    constructor(
        private readonly context: vscode.ExtensionContext,
        private readonly config: AIIWorkflowConfig
    ) {
        this.psExecutor = new PowerShellExecutor(this.config.workflowRoot, this.config.powershellPath);

        // 初始化任务树提供器
        this.taskTreeProvider = new TaskTreeProvider(this.tasks);
        vscode.window.registerTreeDataProvider('aii-workflowTasksView', this.taskTreeProvider);

        // 加载现有任务
        this.loadTasks();
    }

    /**
     * 创建新任务
     */
    public async createTask(description: string, options?: Partial<CreateTaskOptions>): Promise<TaskInfo | undefined> {
        try {
            const taskOptions: CreateTaskOptions = {
                description,
                priority: options?.priority || 'normal',
                timeout: options?.timeout || 3600, // 默认1小时超时
                tags: options?.tags || [],
                notifyOnComplete: options?.notifyOnComplete ?? true
            };

            vscode.window.showInformationMessage(`正在创建任务: ${description}`);

            // 调用PowerShell创建任务
            const result = await this.psExecutor.createTask(description);

            if (result && result.id) {
                const taskInfo: TaskInfo = {
                    id: result.id,
                    name: result.name || `任务-${Date.now()}`,
                    description: result.description || description,
                    status: 'running',
                    progress: 0,
                    startTime: new Date(),
                    result: result
                };

                // 保存任务
                this.tasks.set(taskInfo.id, taskInfo);
                this.taskTreeProvider?.refresh();

                // 开始监控任务进度
                this.monitorTask(taskInfo.id);

                // 显示通知
                if (this.config.showNotifications) {
                    vscode.window.showInformationMessage(`任务已创建: ${taskInfo.name}`, '查看任务').then(selection => {
                        if (selection === '查看任务') {
                            this.showTaskDetails(taskInfo.id);
                        }
                    });
                }

                return taskInfo;
            } else {
                throw new Error('创建任务失败: 返回结果无效');
            }

        } catch (error) {
            vscode.window.showErrorMessage(`创建任务失败: ${error}`);
            return undefined;
        }
    }

    /**
     * 监控任务进度
     */
    private async monitorTask(taskId: string): Promise<void> {
        const task = this.tasks.get(taskId);
        if (!task) {
            return;
        }

        // 定期检查任务状态
        const checkInterval = setInterval(async () => {
            try {
                const status = await this.getTaskStatus(taskId);

                if (status) {
                    // 更新任务状态
                    task.status = status.status;
                    task.progress = status.progress;
                    task.endTime = status.endTime ? new Date(status.endTime) : undefined;
                    task.duration = status.duration;
                    task.result = status.result;
                    task.logs = status.logs;

                    // 刷新UI
                    this.taskTreeProvider?.refresh();

                    // 任务完成通知
                    if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
                        clearInterval(checkInterval);

                        if (this.config.showNotifications) {
                            const message = status.status === 'completed'
                                ? `任务完成: ${task.name}`
                                : `任务${status.status === 'failed' ? '失败' : '取消'}: ${task.name}`;

                            vscode.window.showInformationMessage(message, '查看详情').then(selection => {
                                if (selection === '查看详情') {
                                    this.showTaskDetails(taskId);
                                }
                            });
                        }
                    }
                } else {
                    // 任务可能已删除
                    clearInterval(checkInterval);
                    task.status = 'failed';
                    this.taskTreeProvider?.refresh();
                }
            } catch (error) {
                console.error(`监控任务 ${taskId} 失败:`, error);
            }
        }, 5000); // 每5秒检查一次

        // 设置超时
        setTimeout(() => {
            clearInterval(checkInterval);
            const task = this.tasks.get(taskId);
            if (task && task.status === 'running') {
                task.status = 'failed';
                this.taskTreeProvider?.refresh();

                if (this.config.showNotifications) {
                    vscode.window.showWarningMessage(`任务超时: ${task.name}`, '查看详情').then(selection => {
                        if (selection === '查看详情') {
                            this.showTaskDetails(taskId);
                        }
                    });
                }
            }
        }, (task.result?.timeout || 3600) * 1000);
    }

    /**
     * 获取任务状态
     */
    private async getTaskStatus(taskId: string): Promise<any> {
        try {
            // 这里需要调用PowerShell获取任务状态
            // 暂时返回模拟数据
            const task = this.tasks.get(taskId);
            if (!task) {
                return null;
            }

            // 模拟进度更新
            const elapsed = Date.now() - task.startTime.getTime();
            const progress = Math.min(100, Math.floor((elapsed / 60000) * 100)); // 假设1分钟完成

            return {
                id: taskId,
                status: progress >= 100 ? 'completed' : 'running',
                progress: progress,
                endTime: progress >= 100 ? new Date().toISOString() : undefined,
                duration: `${Math.floor(elapsed / 1000)}秒`,
                result: task.result,
                logs: [`任务 ${taskId} 执行中...`, `进度: ${progress}%`]
            };
        } catch (error) {
            console.error(`获取任务状态失败: ${error}`);
            return null;
        }
    }

    /**
     * 加载现有任务
     */
    private async loadTasks(): Promise<void> {
        try {
            const tasks = await this.psExecutor.listTasks();

            tasks.forEach((task: any) => {
                const taskInfo: TaskInfo = {
                    id: task.id || `task-${Date.now()}`,
                    name: task.name || '未命名任务',
                    description: task.description || '无描述',
                    status: this.mapTaskStatus(task.status),
                    progress: task.progress || 0,
                    startTime: task.startTime ? new Date(task.startTime) : new Date(),
                    endTime: task.endTime ? new Date(task.endTime) : undefined,
                    duration: task.duration || '',
                    result: task.result,
                    logs: task.logs || []
                };

                this.tasks.set(taskInfo.id, taskInfo);
            });

            this.taskTreeProvider?.refresh();
        } catch (error) {
            console.error('加载任务失败:', error);
        }
    }

    /**
     * 映射任务状态
     */
    private mapTaskStatus(status: string): TaskInfo['status'] {
        const statusMap: { [key: string]: TaskInfo['status'] } = {
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

    /**
     * 显示任务列表
     */
    public async showTaskList(): Promise<void> {
        // 如果已经有任务视图，则聚焦到该视图
        const view = vscode.window.createTreeView('aii-workflowTasksView', {
            treeDataProvider: this.taskTreeProvider
        });

        view.reveal({} as any, { focus: true });
    }

    /**
     * 显示任务详情
     */
    public async showTaskDetails(taskId: string): Promise<void> {
        const task = this.tasks.get(taskId);
        if (!task) {
            vscode.window.showWarningMessage('任务不存在');
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'aiiTaskDetails',
            `任务详情: ${task.name}`,
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true
            }
        );

        this.updateTaskDetailsWebview(panel, task);
    }

    /**
     * 更新任务详情Webview
     */
    private updateTaskDetailsWebview(panel: vscode.WebviewPanel, task: TaskInfo): void {
        const html = `
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>任务详情: ${this.escapeHtml(task.name)}</title>
                <style>
                    body {
                        font-family: var(--vscode-font-family);
                        padding: 20px;
                        background-color: var(--vscode-editor-background);
                        color: var(--vscode-editor-foreground);
                    }

                    .task-header {
                        margin-bottom: 20px;
                        padding-bottom: 15px;
                        border-bottom: 1px solid var(--vscode-panel-border);
                    }

                    .task-title {
                        font-size: 18px;
                        font-weight: bold;
                        margin-bottom: 10px;
                    }

                    .task-meta {
                        display: flex;
                        gap: 20px;
                        margin-bottom: 10px;
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
                    }

                    .task-status {
                        display: inline-block;
                        padding: 2px 8px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: bold;
                    }

                    .status-pending { background-color: #007acc; color: white; }
                    .status-running { background-color: #d67e00; color: white; }
                    .status-completed { background-color: #388a34; color: white; }
                    .status-failed { background-color: #f14c4c; color: white; }
                    .status-cancelled { background-color: #6e6e6e; color: white; }

                    .progress-container {
                        margin: 20px 0;
                    }

                    .progress-bar {
                        height: 10px;
                        background-color: var(--vscode-progressBar-background);
                        border-radius: 5px;
                        overflow: hidden;
                        margin-bottom: 5px;
                    }

                    .progress-fill {
                        height: 100%;
                        background-color: var(--vscode-progressBar-foreground);
                        transition: width 0.3s ease;
                    }

                    .progress-text {
                        text-align: center;
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
                    }

                    .section {
                        margin-bottom: 25px;
                    }

                    .section-title {
                        font-size: 14px;
                        font-weight: bold;
                        margin-bottom: 10px;
                        color: var(--vscode-foreground);
                        border-left: 3px solid var(--vscode-focusBorder);
                        padding-left: 8px;
                    }

                    .section-content {
                        background-color: var(--vscode-input-background);
                        border: 1px solid var(--vscode-panel-border);
                        border-radius: 4px;
                        padding: 15px;
                        font-size: 13px;
                        line-height: 1.5;
                    }

                    .log-entry {
                        margin-bottom: 5px;
                        padding: 3px 5px;
                        border-radius: 2px;
                        font-family: var(--vscode-editor-font-family);
                        font-size: 12px;
                    }

                    .log-entry:nth-child(odd) {
                        background-color: var(--vscode-editor-inactiveSelectionBackground);
                    }

                    .log-timestamp {
                        color: var(--vscode-descriptionForeground);
                        margin-right: 10px;
                    }

                    .log-message {
                        color: var(--vscode-editor-foreground);
                    }

                    .result-json {
                        white-space: pre-wrap;
                        word-break: break-all;
                        font-family: var(--vscode-editor-font-family);
                        font-size: 12px;
                        background-color: var(--vscode-editor-background);
                        padding: 10px;
                        border-radius: 4px;
                        max-height: 300px;
                        overflow-y: auto;
                    }

                    .action-buttons {
                        display: flex;
                        gap: 10px;
                        margin-top: 20px;
                    }

                    .action-button {
                        background-color: var(--vscode-button-background);
                        color: var(--vscode-button-foreground);
                        border: none;
                        padding: 8px 16px;
                        border-radius: 2px;
                        cursor: pointer;
                        font-size: 12px;
                    }

                    .action-button:hover {
                        background-color: var(--vscode-button-hoverBackground);
                    }

                    .action-button.danger {
                        background-color: var(--vscode-errorForeground);
                    }

                    .action-button.danger:hover {
                        background-color: var(--vscode-inputValidation-errorBackground);
                    }

                    .action-button:disabled {
                        opacity: 0.5;
                        cursor: not-allowed;
                    }
                </style>
            </head>
            <body>
                <div class="task-header">
                    <div class="task-title">${this.escapeHtml(task.name)}</div>
                    <div class="task-meta">
                        <div>ID: ${task.id}</div>
                        <div>状态: <span class="task-status status-${task.status}">${this.getStatusText(task.status)}</span></div>
                        <div>开始时间: ${task.startTime.toLocaleString()}</div>
                        ${task.endTime ? `<div>结束时间: ${task.endTime.toLocaleString()}</div>` : ''}
                        ${task.duration ? `<div>耗时: ${task.duration}</div>` : ''}
                    </div>
                </div>

                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${task.progress}%"></div>
                    </div>
                    <div class="progress-text">进度: ${task.progress}%</div>
                </div>

                <div class="section">
                    <div class="section-title">任务描述</div>
                    <div class="section-content">${this.escapeHtml(task.description)}</div>
                </div>

                ${task.logs && task.logs.length > 0 ? `
                    <div class="section">
                        <div class="section-title">执行日志 (${task.logs.length}条)</div>
                        <div class="section-content">
                            ${task.logs.map((log, index) => `
                                <div class="log-entry">
                                    <span class="log-timestamp">[${new Date().toLocaleTimeString()}]</span>
                                    <span class="log-message">${this.escapeHtml(log)}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                ${task.result ? `
                    <div class="section">
                        <div class="section-title">执行结果</div>
                        <div class="section-content">
                            <div class="result-json">${this.escapeHtml(JSON.stringify(task.result, null, 2))}</div>
                        </div>
                    </div>
                ` : ''}

                <div class="action-buttons">
                    <button class="action-button" onclick="refreshTask()" id="refreshBtn">刷新</button>
                    ${task.status === 'running' ? `
                        <button class="action-button danger" onclick="cancelTask()" id="cancelBtn">取消任务</button>
                    ` : ''}
                    <button class="action-button" onclick="closePanel()">关闭</button>
                </div>

                <script>
                    const vscode = acquireVsCodeApi();
                    const taskId = "${task.id}";

                    function refreshTask() {
                        vscode.postMessage({
                            command: 'refreshTask',
                            taskId: taskId
                        });
                    }

                    function cancelTask() {
                        const confirmed = confirm('确定要取消此任务吗？');
                        if (confirmed) {
                            vscode.postMessage({
                                command: 'cancelTask',
                                taskId: taskId
                            });
                        }
                    }

                    function closePanel() {
                        vscode.postMessage({
                            command: 'closePanel'
                        });
                    }

                    // 自动刷新（如果任务还在运行）
                    ${task.status === 'running' ? `
                        setInterval(refreshTask, 5000);
                    ` : ''}

                    // 处理来自扩展的消息
                    window.addEventListener('message', event => {
                        const message = event.data;
                        switch (message.command) {
                            case 'taskUpdated':
                                // 重新加载页面
                                location.reload();
                                break;
                        }
                    });
                </script>
            </body>
            </html>
        `;

        panel.webview.html = html;

        // 处理Webview消息
        panel.webview.onDidReceiveMessage(
            async message => {
                switch (message.command) {
                    case 'refreshTask':
                        // 刷新任务状态
                        const updatedTask = this.tasks.get(message.taskId);
                        if (updatedTask) {
                            this.updateTaskDetailsWebview(panel, updatedTask);
                        }
                        break;

                    case 'cancelTask':
                        // 取消任务
                        await this.cancelTask(message.taskId);
                        break;

                    case 'closePanel':
                        panel.dispose();
                        break;
                }
            },
            undefined,
            this.context.subscriptions
        );
    }

    /**
     * 取消任务
     */
    private async cancelTask(taskId: string): Promise<void> {
        try {
            const task = this.tasks.get(taskId);
            if (!task) {
                vscode.window.showWarningMessage('任务不存在');
                return;
            }

            if (task.status !== 'running') {
                vscode.window.showWarningMessage('只能取消运行中的任务');
                return;
            }

            // 这里需要调用PowerShell取消任务
            // 暂时模拟取消
            task.status = 'cancelled';
            task.progress = 0;
            task.endTime = new Date();
            task.duration = `${Math.floor((Date.now() - task.startTime.getTime()) / 1000)}秒`;

            this.taskTreeProvider?.refresh();

            vscode.window.showInformationMessage(`任务已取消: ${task.name}`);

        } catch (error) {
            vscode.window.showErrorMessage(`取消任务失败: ${error}`);
        }
    }

    /**
     * 获取任务状态文本
     */
    private getStatusText(status: TaskInfo['status']): string {
        const statusMap = {
            pending: '等待中',
            running: '运行中',
            completed: '已完成',
            failed: '已失败',
            cancelled: '已取消'
        };
        return statusMap[status] || '未知';
    }

    /**
     * HTML转义
     */
    private escapeHtml(text: string): string {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 获取所有任务
     */
    public getTasks(): TaskInfo[] {
        return Array.from(this.tasks.values());
    }

    /**
     * 根据ID获取任务
     */
    public getTaskById(id: string): TaskInfo | undefined {
        return this.tasks.get(id);
    }

    /**
     * 清理资源
     */
    public dispose(): void {
        if (this.taskTreeProvider) {
            this.taskTreeProvider.dispose();
        }
        this.tasks.clear();
    }
}

class TaskTreeProvider implements vscode.TreeDataProvider<TaskTreeItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<TaskTreeItem | undefined | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    constructor(private tasks: Map<string, TaskInfo>) {}

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: TaskTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: TaskTreeItem): Thenable<TaskTreeItem[]> {
        if (element) {
            // 如果有子元素，返回子元素
            return Promise.resolve([]);
        } else {
            // 返回任务列表
            const taskItems = Array.from(this.tasks.values()).map(task =>
                new TaskTreeItem(task)
            );

            // 按状态和开始时间排序
            taskItems.sort((a, b) => {
                const statusOrder = { running: 0, pending: 1, completed: 2, failed: 3, cancelled: 4 };
                const orderA = statusOrder[a.task.status] || 5;
                const orderB = statusOrder[b.task.status] || 5;

                if (orderA !== orderB) {
                    return orderA - orderB;
                }

                return b.task.startTime.getTime() - a.task.startTime.getTime();
            });

            return Promise.resolve(taskItems);
        }
    }

    dispose(): void {
        this._onDidChangeTreeData.dispose();
    }
}

class TaskTreeItem extends vscode.TreeItem {
    constructor(public readonly task: TaskInfo) {
        super(task.name, vscode.TreeItemCollapsibleState.None);

        this.id = task.id;
        this.description = this.getDescription();
        this.tooltip = this.getTooltip();
        this.iconPath = this.getIcon();
        this.contextValue = this.getContextValue();
        this.command = {
            command: 'aii-workflow.showTaskDetails',
            title: '查看任务详情',
            arguments: [task.id]
        };
    }

    private getDescription(): string {
        return `${this.getStatusText()} | ${this.task.progress}%`;
    }

    private getStatusText(): string {
        const statusMap = {
            pending: '等待中',
            running: '运行中',
            completed: '已完成',
            failed: '已失败',
            cancelled: '已取消'
        };
        return statusMap[this.task.status] || '未知';
    }

    private getTooltip(): string {
        return `任务: ${this.task.name}
描述: ${this.task.description}
状态: ${this.getStatusText()}
进度: ${this.task.progress}%
开始时间: ${this.task.startTime.toLocaleString()}
${this.task.endTime ? `结束时间: ${this.task.endTime.toLocaleString()}` : ''}
${this.task.duration ? `耗时: ${this.task.duration}` : ''}`;
    }

    private getIcon(): vscode.ThemeIcon {
        switch (this.task.status) {
            case 'running':
                return new vscode.ThemeIcon('sync~spin');
            case 'completed':
                return new vscode.ThemeIcon('check');
            case 'failed':
                return new vscode.ThemeIcon('error');
            case 'cancelled':
                return new vscode.ThemeIcon('circle-slash');
            default:
                return new vscode.ThemeIcon('clock');
        }
    }

    private getContextValue(): string {
        switch (this.task.status) {
            case 'running':
                return 'runningTask';
            case 'pending':
                return 'pendingTask';
            default:
                return 'completedTask';
        }
    }
}