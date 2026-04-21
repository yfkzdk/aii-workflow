import * as vscode from 'vscode';
import { PowerShellExecutor } from './utils/psExecutor';
import { AIIWorkflowConfig } from '../extension';

export interface BackupInfo {
    Name: string;
    Path: string;
    LastWriteTime: string;
    Size: number;
    Info?: {
        BackupType: string;
        Timestamp: string;
        CreatedAt: string;
        Summary: {
            Items: Array<{
                Name: string;
                Source: string;
                Destination: string;
                Size: number;
                Status: string;
            }>;
            TotalSize: number;
            SuccessCount: number;
            FailedCount: number;
        };
        RootPath: string;
    };
}

export interface BackupOptions {
    backupType: 'manual' | 'auto' | 'reset' | 'repair';
}

export interface RestoreOptions {
    force: boolean;
}

export class BackupManager {
    constructor(
        private readonly context: vscode.ExtensionContext,
        private readonly config: AIIWorkflowConfig
    ) {}

    /**
     * 创建系统备份
     */
    public async createBackup(options?: Partial<BackupOptions>): Promise<void> {
        try {
            const backupOptions: BackupOptions = {
                backupType: options?.backupType || 'manual'
            };

            // 显示进度
            const progressOptions = {
                location: vscode.ProgressLocation.Notification,
                title: '创建系统备份',
                cancellable: false
            };

            const result = await vscode.window.withProgress(progressOptions, async (progress) => {
                progress.report({ message: '正在准备备份...', increment: 10 });
                const psExecutor = new PowerShellExecutor(this.config.workflowRoot, this.config.powershellPath);

                progress.report({ message: '正在创建备份...', increment: 60 });
                const output = await psExecutor.executeCommand(
                    `Backup-AIISystem -BackupType "${backupOptions.backupType}" | ConvertTo-Json -Depth 10`,
                    60000 // 1分钟超时
                );

                progress.report({ message: '正在解析备份结果...', increment: 20 });
                const result = JSON.parse(output);

                progress.report({ message: '备份完成', increment: 10 });
                return result;
            });

            if (result.Success) {
                vscode.window.showInformationMessage(
                    `✅ 系统备份创建成功\n` +
                    `备份位置: ${result.BackupDir}\n` +
                    `备份大小: ${Math.round(result.Summary.TotalSize / 1024 / 1024 * 100) / 100} MB\n` +
                    `成功项目: ${result.Summary.SuccessCount}\n` +
                    `失败项目: ${result.Summary.FailedCount}`,
                    '查看备份列表'
                ).then(selection => {
                    if (selection === '查看备份列表') {
                        this.showBackupList();
                    }
                });
            } else {
                vscode.window.showErrorMessage(`系统备份失败: ${result.Error || '未知错误'}`);
            }

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            vscode.window.showErrorMessage(`创建备份失败: ${errorMessage}`);
        }
    }

    /**
     * 从备份恢复系统
     */
    public async restoreBackup(backupDir: string, options?: Partial<RestoreOptions>): Promise<void> {
        try {
            const restoreOptions: RestoreOptions = {
                force: options?.force || false
            };

            // 确认恢复操作
            if (!restoreOptions.force) {
                const backupInfo = await this.getBackupInfo(backupDir);
                if (!backupInfo) {
                    vscode.window.showErrorMessage('无法读取备份信息');
                    return;
                }

                const backupSize = backupInfo.Size ? `${Math.round(backupInfo.Size / 1024 / 1024 * 100) / 100} MB` : '未知大小';
                const backupTime = backupInfo.LastWriteTime ? new Date(backupInfo.LastWriteTime).toLocaleString() : '未知时间';

                const confirmation = await vscode.window.showWarningMessage(
                    `确定要从备份恢复系统吗？\n\n` +
                    `备份名称: ${backupInfo.Name}\n` +
                    `备份时间: ${backupTime}\n` +
                    `备份大小: ${backupSize}\n\n` +
                    `此操作将覆盖当前系统状态。`,
                    { modal: true, detail: '恢复前会自动创建当前状态的备份。' },
                    '确认恢复', '取消'
                );

                if (confirmation !== '确认恢复') {
                    return;
                }
            }

            // 显示进度
            const progressOptions = {
                location: vscode.ProgressLocation.Notification,
                title: '从备份恢复系统',
                cancellable: false
            };

            const result = await vscode.window.withProgress(progressOptions, async (progress) => {
                progress.report({ message: '正在准备恢复...', increment: 10 });
                const psExecutor = new PowerShellExecutor(this.config.workflowRoot, this.config.powershellPath);

                const forceFlag = restoreOptions.force ? '-Force' : '';
                progress.report({ message: '正在恢复备份...', increment: 60 });
                const output = await psExecutor.executeCommand(
                    `Restore-AIISystem -BackupDir "${backupDir}" ${forceFlag} | ConvertTo-Json -Depth 10`,
                    120000 // 2分钟超时
                );

                progress.report({ message: '正在解析恢复结果...', increment: 20 });
                const result = JSON.parse(output);

                progress.report({ message: '恢复完成', increment: 10 });
                return result;
            });

            if (result.Success) {
                vscode.window.showInformationMessage(
                    `✅ 系统恢复成功\n` +
                    `从备份恢复: ${backupDir}\n` +
                    `当前状态备份: ${result.CurrentBackup?.BackupDir || '无'}\n` +
                    `恢复项目数: ${result.RestoreResult?.RestoredItems?.length || 0}`,
                    '查看详情'
                ).then(selection => {
                    if (selection === '查看详情') {
                        this.showRestoreResult(result);
                    }
                });
            } else {
                vscode.window.showErrorMessage(`系统恢复失败: ${result.Error || '未知错误'}`);
            }

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            vscode.window.showErrorMessage(`恢复备份失败: ${errorMessage}`);
        }
    }

    /**
     * 显示备份列表
     */
    public async showBackupList(): Promise<void> {
        try {
            const backups = await this.listBackups();

            if (backups.length === 0) {
                vscode.window.showInformationMessage('暂无系统备份');
                return;
            }

            // 创建Webview面板显示备份列表
            const panel = vscode.window.createWebviewPanel(
                'aiiBackupList',
                '系统备份列表',
                vscode.ViewColumn.One,
                {
                    enableScripts: true,
                    retainContextWhenHidden: false
                }
            );

            panel.webview.html = this.getBackupListHtml(backups);

            // 处理Webview消息
            panel.webview.onDidReceiveMessage(
                async message => {
                    switch (message.command) {
                        case 'restoreBackup':
                            await this.restoreBackup(message.backupPath);
                            panel.dispose();
                            break;

                        case 'deleteBackup':
                            await this.deleteBackup(message.backupPath);
                            // 刷新列表
                            const updatedBackups = await this.listBackups();
                            panel.webview.html = this.getBackupListHtml(updatedBackups);
                            break;

                        case 'refreshList':
                            const refreshedBackups = await this.listBackups();
                            panel.webview.html = this.getBackupListHtml(refreshedBackups);
                            break;

                        case 'createBackup':
                            await this.createBackup();
                            const newBackups = await this.listBackups();
                            panel.webview.html = this.getBackupListHtml(newBackups);
                            break;
                    }
                },
                undefined,
                this.context.subscriptions
            );

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            vscode.window.showErrorMessage(`显示备份列表失败: ${errorMessage}`);
        }
    }

    /**
     * 列出所有备份
     */
    private async listBackups(): Promise<BackupInfo[]> {
        try {
            const psExecutor = new PowerShellExecutor(this.config.workflowRoot, this.config.powershellPath);
            const output = await psExecutor.executeCommand('Get-AIIBackups | ConvertTo-Json -Depth 10', 30000);
            return JSON.parse(output) || [];
        } catch (error) {
            console.error('列出备份失败:', error);
            return [];
        }
    }

    /**
     * 获取备份信息
     */
    private async getBackupInfo(backupDir: string): Promise<BackupInfo | undefined> {
        try {
            const backups = await this.listBackups();
            return backups.find(backup => backup.Path === backupDir);
        } catch (error) {
            console.error('获取备份信息失败:', error);
            return undefined;
        }
    }

    /**
     * 删除备份
     */
    private async deleteBackup(backupDir: string): Promise<boolean> {
        try {
            const confirmed = await vscode.window.showWarningMessage(
                `确定要删除备份吗？\n${backupDir}`,
                { modal: true },
                '确认删除', '取消'
            );

            if (confirmed !== '确认删除') {
                return false;
            }

            const psExecutor = new PowerShellExecutor(this.config.workflowRoot, this.config.powershellPath);

            // 使用PowerShell删除目录
            await psExecutor.executeCommand(`Remove-Item -Path "${backupDir}" -Recurse -Force -ErrorAction Stop`, 30000);

            vscode.window.showInformationMessage('备份删除成功');
            return true;

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            vscode.window.showErrorMessage(`删除备份失败: ${errorMessage}`);
            return false;
        }
    }

    /**
     * 生成备份列表HTML
     */
    private getBackupListHtml(backups: BackupInfo[]): string {
        return `
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>系统备份列表</title>
                <style>
                    body {
                        font-family: var(--vscode-font-family);
                        padding: 20px;
                        background-color: var(--vscode-editor-background);
                        color: var(--vscode-editor-foreground);
                    }

                    .header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 20px;
                        padding-bottom: 15px;
                        border-bottom: 1px solid var(--vscode-panel-border);
                    }

                    .title {
                        font-size: 18px;
                        font-weight: bold;
                    }

                    .action-buttons {
                        display: flex;
                        gap: 10px;
                    }

                    .action-button {
                        background-color: var(--vscode-button-background);
                        color: var(--vscode-button-foreground);
                        border: none;
                        padding: 6px 12px;
                        border-radius: 2px;
                        cursor: pointer;
                        font-size: 12px;
                        display: flex;
                        align-items: center;
                        gap: 5px;
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

                    .backup-list {
                        display: flex;
                        flex-direction: column;
                        gap: 15px;
                    }

                    .backup-item {
                        background-color: var(--vscode-input-background);
                        border: 1px solid var(--vscode-panel-border);
                        border-radius: 6px;
                        padding: 15px;
                        transition: all 0.2s ease;
                    }

                    .backup-item:hover {
                        border-color: var(--vscode-focusBorder);
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                    }

                    .backup-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: flex-start;
                        margin-bottom: 10px;
                    }

                    .backup-name {
                        font-weight: bold;
                        font-size: 14px;
                        color: var(--vscode-foreground);
                    }

                    .backup-type {
                        display: inline-block;
                        padding: 2px 8px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: bold;
                        margin-left: 8px;
                    }

                    .type-manual { background-color: #007acc; color: white; }
                    .type-auto { background-color: #388a34; color: white; }
                    .type-reset { background-color: #d67e00; color: white; }
                    .type-repair { background-color: #6e6e6e; color: white; }

                    .backup-meta {
                        display: flex;
                        gap: 15px;
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
                        margin-bottom: 10px;
                    }

                    .backup-details {
                        margin-top: 10px;
                        padding-top: 10px;
                        border-top: 1px solid var(--vscode-panel-border);
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
                    }

                    .details-grid {
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                        gap: 10px;
                        margin-top: 10px;
                    }

                    .detail-item {
                        background-color: var(--vscode-editor-background);
                        padding: 8px;
                        border-radius: 4px;
                    }

                    .detail-label {
                        font-weight: bold;
                        margin-bottom: 2px;
                    }

                    .detail-value {
                        color: var(--vscode-descriptionForeground);
                    }

                    .backup-actions {
                        display: flex;
                        gap: 8px;
                        margin-top: 15px;
                        justify-content: flex-end;
                    }

                    .backup-button {
                        background-color: var(--vscode-button-background);
                        color: var(--vscode-button-foreground);
                        border: none;
                        padding: 4px 10px;
                        border-radius: 2px;
                        cursor: pointer;
                        font-size: 11px;
                    }

                    .backup-button:hover {
                        background-color: var(--vscode-button-hoverBackground);
                    }

                    .backup-button.restore {
                        background-color: var(--vscode-button-secondaryBackground);
                    }

                    .backup-button.restore:hover {
                        background-color: var(--vscode-button-secondaryHoverBackground);
                    }

                    .backup-button.delete {
                        background-color: var(--vscode-errorForeground);
                        color: white;
                    }

                    .backup-button.delete:hover {
                        background-color: var(--vscode-inputValidation-errorBackground);
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
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <div class="title">系统备份列表 (${backups.length}个)</div>
                    <div class="action-buttons">
                        <button class="action-button" onclick="refreshList()">
                            <span>🔄</span> 刷新
                        </button>
                        <button class="action-button primary" onclick="createBackup()">
                            <span>💾</span> 创建备份
                        </button>
                    </div>
                </div>

                ${backups.length === 0 ? `
                    <div class="empty-state">
                        <div class="empty-icon">📂</div>
                        <div class="empty-text">暂无系统备份</div>
                        <button class="action-button primary" onclick="createBackup()">
                            <span>💾</span> 创建第一个备份
                        </button>
                    </div>
                ` : `
                    <div class="backup-list">
                        ${backups.map((backup, index) => `
                            <div class="backup-item">
                                <div class="backup-header">
                                    <div>
                                        <span class="backup-name">${this.escapeHtml(backup.Name)}</span>
                                        <span class="backup-type type-${backup.Info?.BackupType || 'manual'}">
                                            ${this.getBackupTypeText(backup.Info?.BackupType || 'manual')}
                                        </span>
                                    </div>
                                </div>

                                <div class="backup-meta">
                                    <div>📅 ${new Date(backup.LastWriteTime).toLocaleString()}</div>
                                    <div>📦 ${this.formatFileSize(backup.Size)}</div>
                                    ${backup.Info?.Summary ? `
                                        <div>✅ ${backup.Info.Summary.SuccessCount} 成功</div>
                                        <div>❌ ${backup.Info.Summary.FailedCount} 失败</div>
                                    ` : ''}
                                </div>

                                ${backup.Info ? `
                                    <div class="backup-details">
                                        <div><strong>备份详情:</strong></div>
                                        <div class="details-grid">
                                            <div class="detail-item">
                                                <div class="detail-label">备份类型</div>
                                                <div class="detail-value">${this.getBackupTypeText(backup.Info.BackupType)}</div>
                                            </div>
                                            <div class="detail-item">
                                                <div class="detail-label">创建时间</div>
                                                <div class="detail-value">${backup.Info.CreatedAt}</div>
                                            </div>
                                            <div class="detail-item">
                                                <div class="detail-label">备份大小</div>
                                                <div class="detail-value">${this.formatFileSize(backup.Info.Summary.TotalSize)}</div>
                                            </div>
                                            <div class="detail-item">
                                                <div class="detail-label">项目总数</div>
                                                <div class="detail-value">${backup.Info.Summary.Items.length}</div>
                                            </div>
                                        </div>
                                    </div>
                                ` : ''}

                                <div class="backup-actions">
                                    <button class="backup-button restore" onclick="restoreBackup('${this.escapeHtml(backup.Path)}')">
                                        恢复
                                    </button>
                                    <button class="backup-button delete" onclick="deleteBackup('${this.escapeHtml(backup.Path)}')">
                                        删除
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `}

                <script>
                    const vscode = acquireVsCodeApi();

                    function refreshList() {
                        vscode.postMessage({
                            command: 'refreshList'
                        });
                    }

                    function createBackup() {
                        vscode.postMessage({
                            command: 'createBackup'
                        });
                    }

                    function restoreBackup(backupPath) {
                        const confirmed = confirm('确定要从此备份恢复系统吗？此操作将覆盖当前系统状态。');
                        if (confirmed) {
                            vscode.postMessage({
                                command: 'restoreBackup',
                                backupPath: backupPath
                            });
                        }
                    }

                    function deleteBackup(backupPath) {
                        const confirmed = confirm('确定要删除此备份吗？此操作不可恢复。');
                        if (confirmed) {
                            vscode.postMessage({
                                command: 'deleteBackup',
                                backupPath: backupPath
                            });
                        }
                    }
                </script>
            </body>
            </html>
        `;
    }

    /**
     * 显示恢复结果
     */
    private showRestoreResult(result: any): void {
        const panel = vscode.window.createWebviewPanel(
            'aiiRestoreResult',
            '系统恢复结果',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: false
            }
        );

        panel.webview.html = this.getRestoreResultHtml(result);
    }

    /**
     * 生成恢复结果HTML
     */
    private getRestoreResultHtml(result: any): string {
        return `
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>系统恢复结果</title>
                <style>
                    body {
                        font-family: var(--vscode-font-family);
                        padding: 20px;
                        background-color: var(--vscode-editor-background);
                        color: var(--vscode-editor-foreground);
                    }

                    .result-header {
                        text-align: center;
                        margin-bottom: 30px;
                        padding: 20px;
                        border-radius: 8px;
                        background-color: ${result.Success ? 'var(--vscode-input-background)' : 'var(--vscode-inputValidation-errorBackground)'};
                    }

                    .result-title {
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 10px;
                        color: ${result.Success ? 'var(--vscode-foreground)' : 'var(--vscode-errorForeground)'};
                    }

                    .result-icon {
                        font-size: 48px;
                        margin: 20px 0;
                    }

                    .result-summary {
                        margin: 20px 0;
                        line-height: 1.6;
                    }

                    .result-details {
                        margin-top: 30px;
                    }

                    .detail-section {
                        margin-bottom: 20px;
                        padding: 15px;
                        background-color: var(--vscode-input-background);
                        border-radius: 4px;
                    }

                    .section-title {
                        font-size: 16px;
                        font-weight: bold;
                        margin-bottom: 10px;
                        color: var(--vscode-foreground);
                        border-left: 3px solid var(--vscode-focusBorder);
                        padding-left: 8px;
                    }

                    .detail-item {
                        margin-bottom: 8px;
                        font-size: 13px;
                    }

                    .detail-label {
                        font-weight: bold;
                        color: var(--vscode-foreground);
                        display: inline-block;
                        min-width: 150px;
                    }

                    .detail-value {
                        color: var(--vscode-descriptionForeground);
                    }

                    .restored-items {
                        margin-top: 10px;
                        max-height: 200px;
                        overflow-y: auto;
                        border: 1px solid var(--vscode-panel-border);
                        border-radius: 4px;
                        padding: 10px;
                        background-color: var(--vscode-editor-background);
                    }

                    .restored-item {
                        padding: 5px;
                        border-bottom: 1px solid var(--vscode-panel-border);
                        font-size: 12px;
                    }

                    .restored-item:last-child {
                        border-bottom: none;
                    }

                    .error-message {
                        margin-top: 20px;
                        padding: 15px;
                        background-color: var(--vscode-inputValidation-errorBackground);
                        color: var(--vscode-errorForeground);
                        border-radius: 4px;
                        border-left: 4px solid var(--vscode-errorForeground);
                    }
                </style>
            </head>
            <body>
                <div class="result-header">
                    <div class="result-title">
                        ${result.Success ? '✅ 系统恢复成功' : '❌ 系统恢复失败'}
                    </div>
                    <div class="result-icon">
                        ${result.Success ? '🔄' : '😞'}
                    </div>
                    <div class="result-summary">
                        恢复时间: ${new Date(result.Timestamp).toLocaleString()}<br>
                        ${result.BackupInfo?.BackupDir ? `从备份恢复: ${this.escapeHtml(result.BackupInfo.BackupDir)}<br>` : ''}
                        ${result.CurrentBackup?.BackupDir ? `当前状态备份: ${this.escapeHtml(result.CurrentBackup.BackupDir)}` : ''}
                    </div>
                </div>

                ${result.Success ? `
                    <div class="result-details">
                        ${result.BackupInfo ? `
                            <div class="detail-section">
                                <div class="section-title">备份信息</div>
                                <div class="detail-item">
                                    <span class="detail-label">备份类型:</span>
                                    <span class="detail-value">${this.escapeHtml(result.BackupInfo.BackupType || '未知')}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">备份时间:</span>
                                    <span class="detail-value">${this.escapeHtml(result.BackupInfo.CreatedAt || '未知')}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">备份大小:</span>
                                    <span class="detail-value">${result.BackupInfo.Summary?.TotalSize ? this.formatFileSize(result.BackupInfo.Summary.TotalSize) : '未知'}</span>
                                </div>
                            </div>
                        ` : ''}

                        ${result.RestoreResult ? `
                            <div class="detail-section">
                                <div class="section-title">恢复结果</div>
                                <div class="detail-item">
                                    <span class="detail-label">恢复项目总数:</span>
                                    <span class="detail-value">${result.RestoreResult.TotalItems || 0}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">成功恢复:</span>
                                    <span class="detail-value">${result.RestoreResult.RestoredItems?.length || 0}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">恢复失败:</span>
                                    <span class="detail-value">${result.RestoreResult.FailedItems?.length || 0}</span>
                                </div>

                                ${result.RestoreResult.RestoredItems?.length > 0 ? `
                                    <div class="restored-items">
                                        <strong>成功恢复的项目:</strong>
                                        ${result.RestoreResult.RestoredItems.map((item: any) => `
                                            <div class="restored-item">
                                                ✅ ${this.escapeHtml(item.Name || '未知')} → ${this.escapeHtml(item.Destination || '未知')}
                                            </div>
                                        `).join('')}
                                    </div>
                                ` : ''}

                                ${result.RestoreResult.FailedItems?.length > 0 ? `
                                    <div class="restored-items">
                                        <strong>恢复失败的项目:</strong>
                                        ${result.RestoreResult.FailedItems.map((item: any) => `
                                            <div class="restored-item">
                                                ❌ ${this.escapeHtml(item.Name || '未知')}: ${this.escapeHtml(item.Error || '未知错误')}
                                            </div>
                                        `).join('')}
                                    </div>
                                ` : ''}
                            </div>
                        ` : ''}

                        ${result.Reinitialization ? `
                            <div class="detail-section">
                                <div class="section-title">重新初始化</div>
                                <div class="detail-item">
                                    <span class="detail-label">状态:</span>
                                    <span class="detail-value">${result.Reinitialization.Success ? '成功' : '失败'}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">消息:</span>
                                    <span class="detail-value">${this.escapeHtml(result.Reinitialization.Message || '无')}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">重置时间:</span>
                                    <span class="detail-value">${this.escapeHtml(result.Reinitialization.ResetTime || '未知')}</span>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                ` : ''}

                ${result.Error ? `
                    <div class="error-message">
                        <strong>错误信息:</strong><br>
                        ${this.escapeHtml(result.Error)}
                    </div>
                ` : ''}
            </body>
            </html>
        `;
    }

    /**
     * 获取备份类型文本
     */
    private getBackupTypeText(type: string): string {
        const typeMap: { [key: string]: string } = {
            manual: '手动备份',
            auto: '自动备份',
            reset: '重置备份',
            repair: '修复备份'
        };
        return typeMap[type] || type;
    }

    /**
     * 格式化文件大小
     */
    private formatFileSize(bytes: number): string {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
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
     * 清理资源
     */
    public dispose(): void {
        // 当前类没有需要清理的资源
    }
}