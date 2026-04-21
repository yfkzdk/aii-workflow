import * as vscode from 'vscode';
import { AIIWebviewPanel, WebviewPanelOptions } from './panel';
import { AIIWorkflowConfig } from '../extension';
import { StatusMonitor } from '../statusMonitor';

export class StatusPanel extends AIIWebviewPanel {
    private statusMonitor: StatusMonitor;

    constructor(
        context: vscode.ExtensionContext,
        config: AIIWorkflowConfig
    ) {
        const options: WebviewPanelOptions = {
            title: 'AII Workflow 状态监控',
            viewColumn: vscode.ViewColumn.One,
            preserveFocus: true
        };

        super(context, 'aiiStatusPanel', options);
        this.statusMonitor = new StatusMonitor(context, config);
    }

    protected getHtml(): string {
        const nonce = this.getNonce();

        return `
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';">
                <title>AII Workflow 状态监控</title>
                <style>
                    :root {
                        --vscode-font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                        --vscode-editor-background: #1e1e1e;
                        --vscode-editor-foreground: #cccccc;
                        --vscode-input-background: #3c3c3c;
                        --vscode-panel-border: #808080;
                        --vscode-focusBorder: #007acc;
                        --vscode-foreground: #cccccc;
                        --vscode-descriptionForeground: #858585;
                        --vscode-statusBarItem-warningBackground: #d67e00;
                        --vscode-statusBarItem-errorBackground: #f14c4c;
                        --vscode-statusBarItem-remoteBackground: #388a34;
                        --vscode-progressBar-background: #3c3c3c;
                        --vscode-progressBar-foreground: #007acc;
                    }

                    body {
                        font-family: var(--vscode-font-family);
                        padding: 20px;
                        background-color: var(--vscode-editor-background);
                        color: var(--vscode-editor-foreground);
                        margin: 0;
                        line-height: 1.5;
                    }

                    .header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 30px;
                        padding-bottom: 15px;
                        border-bottom: 1px solid var(--vscode-panel-border);
                    }

                    .title {
                        font-size: 24px;
                        font-weight: bold;
                        color: var(--vscode-foreground);
                    }

                    .action-buttons {
                        display: flex;
                        gap: 10px;
                    }

                    .action-button {
                        background-color: var(--vscode-button-background);
                        color: var(--vscode-button-foreground);
                        border: none;
                        padding: 8px 16px;
                        border-radius: 2px;
                        cursor: pointer;
                        font-size: 14px;
                        display: flex;
                        align-items: center;
                        gap: 6px;
                        transition: background-color 0.2s;
                    }

                    .action-button:hover {
                        background-color: var(--vscode-button-hoverBackground);
                    }

                    .action-button.primary {
                        background-color: var(--vscode-button-secondaryBackground);
                    }

                    .action-button.primary:hover {
                        background-color: var(--vscode-button-secondaryHoverBackground);
                    }

                    .action-button:disabled {
                        opacity: 0.5;
                        cursor: not-allowed;
                    }

                    .status-container {
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                        gap: 20px;
                        margin-bottom: 30px;
                    }

                    .status-card {
                        background-color: var(--vscode-input-background);
                        border: 1px solid var(--vscode-panel-border);
                        border-radius: 8px;
                        padding: 20px;
                        transition: all 0.3s ease;
                    }

                    .status-card:hover {
                        border-color: var(--vscode-focusBorder);
                        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                    }

                    .status-header {
                        display: flex;
                        align-items: center;
                        margin-bottom: 15px;
                    }

                    .status-icon {
                        font-size: 24px;
                        margin-right: 12px;
                        width: 40px;
                        height: 40px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border-radius: 8px;
                        background-color: rgba(0, 122, 204, 0.1);
                    }

                    .status-title {
                        font-size: 16px;
                        font-weight: bold;
                        color: var(--vscode-foreground);
                    }

                    .status-value {
                        font-size: 28px;
                        font-weight: bold;
                        margin: 10px 0;
                        color: var(--vscode-foreground);
                    }

                    .status-details {
                        font-size: 14px;
                        color: var(--vscode-descriptionForeground);
                        line-height: 1.6;
                    }

                    .detail-item {
                        margin-bottom: 8px;
                        display: flex;
                        justify-content: space-between;
                    }

                    .detail-label {
                        color: var(--vscode-descriptionForeground);
                    }

                    .detail-value {
                        color: var(--vscode-foreground);
                        font-weight: 500;
                    }

                    .progress-container {
                        margin: 15px 0;
                    }

                    .progress-bar {
                        height: 8px;
                        background-color: var(--vscode-progressBar-background);
                        border-radius: 4px;
                        overflow: hidden;
                        margin-bottom: 6px;
                    }

                    .progress-fill {
                        height: 100%;
                        background-color: var(--vscode-progressBar-foreground);
                        transition: width 0.3s ease;
                    }

                    .progress-text {
                        display: flex;
                        justify-content: space-between;
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
                    }

                    .tasks-section {
                        margin-top: 30px;
                    }

                    .section-title {
                        font-size: 18px;
                        font-weight: bold;
                        margin-bottom: 15px;
                        color: var(--vscode-foreground);
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }

                    .tasks-list {
                        display: flex;
                        flex-direction: column;
                        gap: 12px;
                    }

                    .task-item {
                        background-color: var(--vscode-input-background);
                        border: 1px solid var(--vscode-panel-border);
                        border-radius: 6px;
                        padding: 15px;
                        transition: all 0.2s ease;
                    }

                    .task-item:hover {
                        border-color: var(--vscode-focusBorder);
                        transform: translateY(-2px);
                    }

                    .task-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 10px;
                    }

                    .task-name {
                        font-weight: bold;
                        font-size: 14px;
                        color: var(--vscode-foreground);
                    }

                    .task-status {
                        padding: 4px 12px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: bold;
                        text-transform: uppercase;
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

                    .task-status.cancelled {
                        background-color: #6e6e6e;
                        color: white;
                    }

                    .task-description {
                        font-size: 13px;
                        color: var(--vscode-descriptionForeground);
                        margin-bottom: 10px;
                        line-height: 1.4;
                    }

                    .task-meta {
                        display: flex;
                        justify-content: space-between;
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
                    }

                    .empty-state {
                        text-align: center;
                        padding: 40px 20px;
                        color: var(--vscode-descriptionForeground);
                    }

                    .empty-icon {
                        font-size: 48px;
                        margin-bottom: 20px;
                        opacity: 0.5;
                    }

                    .empty-text {
                        margin-bottom: 20px;
                        font-size: 14px;
                    }

                    .loading {
                        text-align: center;
                        padding: 40px;
                        color: var(--vscode-descriptionForeground);
                    }

                    .loading-spinner {
                        border: 3px solid var(--vscode-panel-border);
                        border-top: 3px solid var(--vscode-focusBorder);
                        border-radius: 50%;
                        width: 40px;
                        height: 40px;
                        animation: spin 1s linear infinite;
                        margin: 0 auto 20px;
                    }

                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }

                    .system-info {
                        margin-top: 30px;
                    }

                    .info-grid {
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                        gap: 15px;
                        margin-top: 15px;
                    }

                    .info-item {
                        background-color: var(--vscode-input-background);
                        border: 1px solid var(--vscode-panel-border);
                        border-radius: 6px;
                        padding: 12px;
                        transition: all 0.2s ease;
                    }

                    .info-item:hover {
                        border-color: var(--vscode-focusBorder);
                    }

                    .info-label {
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
                        margin-bottom: 4px;
                        font-weight: 500;
                    }

                    .info-value {
                        font-size: 14px;
                        color: var(--vscode-foreground);
                        font-weight: 600;
                        word-break: break-all;
                    }

                    .module-status {
                        display: inline-block;
                        width: 8px;
                        height: 8px;
                        border-radius: 50%;
                        margin-right: 6px;
                    }

                    .module-status.healthy {
                        background-color: #388a34;
                    }

                    .module-status.warning {
                        background-color: #d67e00;
                    }

                    .module-status.error {
                        background-color: #f14c4c;
                    }

                    .module-status.unknown {
                        background-color: #6e6e6e;
                    }

                    .last-updated {
                        text-align: center;
                        margin-top: 20px;
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
                        padding-top: 15px;
                        border-top: 1px solid var(--vscode-panel-border);
                    }

                    @media (max-width: 768px) {
                        .status-container {
                            grid-template-columns: 1fr;
                        }

                        .info-grid {
                            grid-template-columns: 1fr;
                        }
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <div class="title">AII Workflow 状态监控</div>
                    <div class="action-buttons">
                        <button class="action-button" onclick="refreshStatus()" id="refreshBtn">
                            <span>🔄</span> 刷新状态
                        </button>
                        <button class="action-button primary" onclick="startWorkflow()" id="startBtn">
                            <span>🚀</span> 启动工作流
                        </button>
                    </div>
                </div>

                <div id="loading" class="loading">
                    <div class="loading-spinner"></div>
                    <div>正在加载状态信息...</div>
                </div>

                <div id="content" style="display: none;">
                    <div class="status-container" id="statusContainer">
                        <!-- 状态卡片将通过JavaScript动态生成 -->
                    </div>

                    <div class="tasks-section">
                        <div class="section-title">
                            <span>📋 任务列表</span>
                            <span id="taskCount">(0)</span>
                        </div>
                        <div class="tasks-list" id="tasksList">
                            <!-- 任务列表将通过JavaScript动态生成 -->
                        </div>
                    </div>

                    <div class="system-info">
                        <div class="section-title">
                            <span>⚙️ 系统信息</span>
                        </div>
                        <div class="info-grid" id="systemInfoGrid">
                            <!-- 系统信息将通过JavaScript动态生成 -->
                        </div>
                    </div>

                    <div class="last-updated">
                        最后更新: <span id="lastUpdated">--:--:--</span>
                    </div>
                </div>

                <script nonce="${nonce}">
                    const vscode = acquireVsCodeApi();

                    // 状态颜色映射
                    const statusColors = {
                        'healthy': '#388a34',
                        'warning': '#d67e00',
                        'error': '#f14c4c',
                        'unknown': '#6e6e6e'
                    };

                    // 状态文本映射
                    const statusTexts = {
                        'healthy': '健康',
                        'warning': '警告',
                        'error': '错误',
                        'unknown': '未知'
                    };

                    // 任务状态映射
                    const taskStatusTexts = {
                        'pending': '等待中',
                        'running': '运行中',
                        'completed': '已完成',
                        'failed': '已失败',
                        'cancelled': '已取消'
                    };

                    let currentStatus = null;
                    let currentTasks = [];
                    let currentSystemInfo = null;

                    // 页面加载时请求状态
                    window.addEventListener('DOMContentLoaded', () => {
                        refreshStatus();
                        // 定时刷新状态
                        setInterval(refreshStatus, 30000); // 30秒刷新一次
                    });

                    function refreshStatus() {
                        document.getElementById('loading').style.display = 'block';
                        document.getElementById('content').style.display = 'none';

                        vscode.postMessage({
                            command: 'refreshStatus'
                        });
                    }

                    function startWorkflow() {
                        const button = document.getElementById('startBtn');
                        button.disabled = true;
                        button.innerHTML = '<span>⏳</span> 启动中...';

                        vscode.postMessage({
                            command: 'startWorkflow'
                        });

                        // 5秒后恢复按钮状态
                        setTimeout(() => {
                            button.disabled = false;
                            button.innerHTML = '<span>🚀</span> 启动工作流';
                        }, 5000);
                    }

                    function showTaskDetails(taskId) {
                        vscode.postMessage({
                            command: 'showTaskDetails',
                            taskId: taskId
                        });
                    }

                    function formatFileSize(bytes) {
                        if (bytes === 0) return '0 B';
                        const k = 1024;
                        const sizes = ['B', 'KB', 'MB', 'GB'];
                        const i = Math.floor(Math.log(bytes) / Math.log(k));
                        return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
                    }

                    function formatDateTime(dateString) {
                        if (!dateString) return '未知';
                        const date = new Date(dateString);
                        return date.toLocaleString('zh-CN');
                    }

                    function formatDuration(duration) {
                        if (!duration) return '--:--';
                        return duration;
                    }

                    function updateUI() {
                        if (!currentStatus) return;

                        // 更新状态卡片
                        const statusContainer = document.getElementById('statusContainer');
                        statusContainer.innerHTML = '';

                        // 系统状态卡片
                        const systemStatusCard = \`
                            <div class="status-card">
                                <div class="status-header">
                                    <div class="status-icon">📊</div>
                                    <div class="status-title">系统状态</div>
                                </div>
                                <div class="status-value" style="color: \${statusColors[currentStatus.systemStatus] || '#6e6e6e'}">
                                    \${statusTexts[currentStatus.systemStatus] || '未知'}
                                </div>
                                <div class="status-details">
                                    <div class="detail-item">
                                        <span class="detail-label">运行状态:</span>
                                        <span class="detail-value">\${currentStatus.isRunning ? '运行中' : '已停止'}</span>
                                    </div>
                                    <div class="detail-item">
                                        <span class="detail-label">活动任务:</span>
                                        <span class="detail-value">\${currentStatus.activeTasks}</span>
                                    </div>
                                    <div class="detail-item">
                                        <span class="detail-label">总任务数:</span>
                                        <span class="detail-value">\${currentStatus.totalTasks}</span>
                                    </div>
                                    \${currentStatus.uptime ? \`
                                        <div class="detail-item">
                                            <span class="detail-label">运行时间:</span>
                                            <span class="detail-value">\${currentStatus.uptime}</span>
                                        </div>
                                    \` : ''}
                                </div>
                            </div>
                        \`;

                        // 资源使用卡片
                        const resourceCard = \`
                            <div class="status-card">
                                <div class="status-header">
                                    <div class="status-icon">💻</div>
                                    <div class="status-title">资源使用</div>
                                </div>
                                \${currentStatus.cpuUsage !== undefined ? \`
                                    <div class="progress-container">
                                        <div class="progress-text">
                                            <span>CPU</span>
                                            <span>\${currentStatus.cpuUsage.toFixed(1)}%</span>
                                        </div>
                                        <div class="progress-bar">
                                            <div class="progress-fill" style="width: \${currentStatus.cpuUsage}%"></div>
                                        </div>
                                    </div>
                                \` : '<div style="text-align: center; color: var(--vscode-descriptionForeground); padding: 20px;">资源数据不可用</div>'}
                                \${currentStatus.memoryUsage !== undefined ? \`
                                    <div class="progress-container">
                                        <div class="progress-text">
                                            <span>内存</span>
                                            <span>\${currentStatus.memoryUsage.toFixed(1)}%</span>
                                        </div>
                                        <div class="progress-bar">
                                            <div class="progress-fill" style="width: \${currentStatus.memoryUsage}%"></div>
                                        </div>
                                    </div>
                                \` : ''}
                                \${currentStatus.diskUsage !== undefined ? \`
                                    <div class="progress-container">
                                        <div class="progress-text">
                                            <span>磁盘</span>
                                            <span>\${currentStatus.diskUsage.toFixed(1)}%</span>
                                        </div>
                                        <div class="progress-bar">
                                            <div class="progress-fill" style="width: \${currentStatus.diskUsage}%"></div>
                                        </div>
                                    </div>
                                \` : ''}
                            </div>
                        \`;

                        statusContainer.innerHTML = systemStatusCard + resourceCard;

                        // 更新任务列表
                        const taskCount = document.getElementById('taskCount');
                        const tasksList = document.getElementById('tasksList');

                        if (currentTasks.length === 0) {
                            taskCount.textContent = '(0)';
                            tasksList.innerHTML = \`
                                <div class="empty-state">
                                    <div class="empty-icon">📝</div>
                                    <div class="empty-text">暂无任务</div>
                                </div>
                            \`;
                        } else {
                            taskCount.textContent = \`(\${currentTasks.length})\`;
                            tasksList.innerHTML = currentTasks.map(task => \`
                                <div class="task-item" onclick="showTaskDetails('\${task.id}')" style="cursor: pointer;">
                                    <div class="task-header">
                                        <div class="task-name">\${escapeHtml(task.name)}</div>
                                        <div class="task-status \${task.status}">\${taskStatusTexts[task.status] || task.status}</div>
                                    </div>
                                    <div class="task-description">\${escapeHtml(task.description)}</div>
                                    <div class="progress-container">
                                        <div class="progress-text">
                                            <span>进度</span>
                                            <span>\${task.progress}%</span>
                                        </div>
                                        <div class="progress-bar">
                                            <div class="progress-fill" style="width: \${task.progress}%"></div>
                                        </div>
                                    </div>
                                    <div class="task-meta">
                                        <span>开始: \${formatDateTime(task.startTime)}</span>
                                        \${task.duration ? \`<span>耗时: \${formatDuration(task.duration)}</span>\` : ''}
                                    </div>
                                </div>
                            \`).join('');
                        }

                        // 更新系统信息
                        if (currentSystemInfo) {
                            const systemInfoGrid = document.getElementById('systemInfoGrid');
                            systemInfoGrid.innerHTML = \`
                                <div class="info-item">
                                    <div class="info-label">工作流根目录</div>
                                    <div class="info-value" title="\${escapeHtml(currentSystemInfo.workflowRoot)}">
                                        \${escapeHtml(currentSystemInfo.workflowRoot)}
                                    </div>
                                </div>
                                \${currentSystemInfo.pythonVersion ? \`
                                    <div class="info-item">
                                        <div class="info-label">Python版本</div>
                                        <div class="info-value">\${escapeHtml(currentSystemInfo.pythonVersion)}</div>
                                    </div>
                                \` : ''}
                                \${currentSystemInfo.powershellVersion ? \`
                                    <div class="info-item">
                                        <div class="info-label">PowerShell版本</div>
                                        <div class="info-value">\${escapeHtml(currentSystemInfo.powershellVersion)}</div>
                                    </div>
                                \` : ''}
                                <div class="info-item">
                                    <div class="info-label">备份数量</div>
                                    <div class="info-value">\${currentSystemInfo.backupCount || 0}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">模块状态</div>
                                    <div class="info-value">
                                        <span class="module-status \${currentSystemInfo.moduleStatus?.core ? 'healthy' : 'error'}"></span> Core
                                        <span class="module-status \${currentSystemInfo.moduleStatus?.stateManager ? 'healthy' : 'error'}"></span> State
                                        <span class="module-status \${currentSystemInfo.moduleStatus?.taskManager ? 'healthy' : 'error'}"></span> Task
                                        <span class="module-status \${currentSystemInfo.moduleStatus?.vscodeIntegration ? 'healthy' : 'error'}"></span> VS Code
                                        <span class="module-status \${currentSystemInfo.moduleStatus?.resetManager ? 'healthy' : 'error'}"></span> Reset
                                    </div>
                                </div>
                            \`;
                        }

                        // 更新最后更新时间
                        const lastUpdated = document.getElementById('lastUpdated');
                        lastUpdated.textContent = new Date().toLocaleTimeString('zh-CN');

                        // 显示内容
                        document.getElementById('loading').style.display = 'none';
                        document.getElementById('content').style.display = 'block';
                    }

                    function escapeHtml(text) {
                        const div = document.createElement('div');
                        div.textContent = text;
                        return div.innerHTML;
                    }

                    // 处理来自扩展的消息
                    window.addEventListener('message', event => {
                        const message = event.data;
                        switch (message.command) {
                            case 'updateStatus':
                                currentStatus = message.status;
                                currentTasks = message.tasks || [];
                                currentSystemInfo = message.systemInfo;
                                updateUI();
                                break;

                            case 'workflowStarted':
                                const button = document.getElementById('startBtn');
                                button.innerHTML = '<span>✅</span> 已启动';
                                setTimeout(() => {
                                    button.innerHTML = '<span>🚀</span> 启动工作流';
                                }, 2000);
                                refreshStatus();
                                break;

                            case 'workflowStartFailed':
                                const startBtn = document.getElementById('startBtn');
                                startBtn.innerHTML = '<span>❌</span> 启动失败';
                                setTimeout(() => {
                                    startBtn.innerHTML = '<span>🚀</span> 启动工作流';
                                }, 2000);
                                break;
                        }
                    });
                </script>
            </body>
            </html>
        `;
    }

    protected handleMessage(message: any): void {
        switch (message.command) {
            case 'refreshStatus':
                this.refreshStatus();
                break;

            case 'startWorkflow':
                this.startWorkflow();
                break;

            case 'showTaskDetails':
                vscode.commands.executeCommand('aii-workflow.showTaskDetails', message.taskId);
                break;
        }
    }

    protected afterPanelCreated(): void {
        // 面板创建后立即刷新状态
        setTimeout(() => {
            this.refreshStatus();
        }, 100);
    }

    private async refreshStatus(): Promise<void> {
        try {
            const status = this.statusMonitor.getStatus();
            const tasks = this.statusMonitor.getTasks();
            const systemInfo = this.statusMonitor.getSystemInfo();

            this.postMessage({
                command: 'updateStatus',
                status: status,
                tasks: tasks,
                systemInfo: systemInfo
            });
        } catch (error) {
            console.error('刷新状态失败:', error);
        }
    }

    private async startWorkflow(): Promise<void> {
        try {
            // 这里应该调用实际的启动工作流逻辑
            // 暂时模拟启动
            this.postMessage({
                command: 'workflowStarted'
            });

            // 延迟后刷新状态
            setTimeout(() => {
                this.refreshStatus();
            }, 2000);

        } catch (error) {
            console.error('启动工作流失败:', error);
            this.postMessage({
                command: 'workflowStartFailed'
            });
        }
    }
}