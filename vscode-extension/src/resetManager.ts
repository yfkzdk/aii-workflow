import * as vscode from 'vscode';
import { PowerShellExecutor } from './utils/psExecutor';
import { AIIWorkflowConfig } from '../extension';

export interface ResetOptions {
    force: boolean;
    keepConfig: boolean;
    keepTasks: boolean;
    daysToKeep: number;
}

export interface ResetResult {
    success: boolean;
    backup: any;
    cacheCleanup: any;
    backupCleanup: any;
    reinitialization: any;
    timestamp: string;
    error?: string;
}

export interface ValidationResult {
    checks: Array<{
        check: string;
        status: '通过' | '失败' | '警告';
        details: string;
    }>;
    passed: number;
    failed: number;
    warnings: number;
    status: '健康' | '警告' | '异常' | '验证失败' | '未知';
    error?: string;
}

export interface RepairResult {
    success: boolean;
    initialStatus: string;
    finalStatus: string;
    backupResult: any;
    repairResults: any;
    validation: ValidationResult;
    timestamp: string;
    error?: string;
}

export class ResetManager {
    constructor(
        private readonly context: vscode.ExtensionContext,
        private readonly config: AIIWorkflowConfig
    ) {}

    /**
     * 重置系统
     */
    public async resetSystem(options?: Partial<ResetOptions>): Promise<ResetResult> {
        try {
            const resetOptions: ResetOptions = {
                force: options?.force ?? true,
                keepConfig: options?.keepConfig ?? true,
                keepTasks: options?.keepTasks ?? false,
                daysToKeep: options?.daysToKeep ?? 7
            };

            // 确认重置操作
            if (!resetOptions.force) {
                const confirmation = await vscode.window.showWarningMessage(
                    '此操作将重置AII工作流系统，所有任务和状态将被清除。确认重置？',
                    { modal: true },
                    '确认重置', '取消'
                );

                if (confirmation !== '确认重置') {
                    return {
                        success: false,
                        backup: null,
                        cacheCleanup: null,
                        backupCleanup: null,
                        reinitialization: null,
                        timestamp: new Date().toISOString(),
                        error: '用户取消重置操作'
                    };
                }
            }

            // 显示进度
            const progressOptions = {
                location: vscode.ProgressLocation.Notification,
                title: '重置AII工作流系统',
                cancellable: false
            };

            const result = await vscode.window.withProgress(progressOptions, async (progress) => {
                progress.report({ message: '正在创建系统备份...', increment: 20 });
                const psExecutor = new PowerShellExecutor(this.config.workflowRoot, this.config.powershellPath);

                // 构建PowerShell命令
                let command = 'Reset-AIISystem -Force';
                if (resetOptions.keepConfig) {
                    command += ' -KeepConfig';
                }
                if (resetOptions.keepTasks) {
                    command += ' -KeepTasks';
                }
                if (resetOptions.daysToKeep !== 7) {
                    command += ` -DaysToKeep ${resetOptions.daysToKeep}`;
                }
                command += ' | ConvertTo-Json -Depth 10';

                progress.report({ message: '正在执行重置操作...', increment: 40 });
                const output = await psExecutor.executeCommand(command, 120000); // 2分钟超时

                progress.report({ message: '正在解析重置结果...', increment: 20 });
                const result = JSON.parse(output);

                progress.report({ message: '重置完成', increment: 20 });
                return result;
            });

            // 显示结果
            if (result.Success) {
                vscode.window.showInformationMessage(
                    `✅ 系统重置完成\n` +
                    `备份位置: ${result.Backup?.BackupDir || '无'}\n` +
                    `清理缓存: ${result.CacheCleanup?.DeletedFiles || 0} 个文件\n` +
                    `清理备份: ${result.BackupCleanup?.DeletedBackups || 0} 个旧备份`,
                    '查看详情'
                ).then(selection => {
                    if (selection === '查看详情') {
                        this.showResetResult(result);
                    }
                });
            } else {
                vscode.window.showErrorMessage(`系统重置失败: ${result.Error || '未知错误'}`);
            }

            return {
                success: result.Success || false,
                backup: result.Backup,
                cacheCleanup: result.CacheCleanup,
                backupCleanup: result.BackupCleanup,
                reinitialization: result.Reinitialization,
                timestamp: result.Timestamp || new Date().toISOString(),
                error: result.Error
            };

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            vscode.window.showErrorMessage(`系统重置失败: ${errorMessage}`);

            return {
                success: false,
                backup: null,
                cacheCleanup: null,
                backupCleanup: null,
                reinitialization: null,
                timestamp: new Date().toISOString(),
                error: errorMessage
            };
        }
    }

    /**
     * 验证系统完整性
     */
    public async validateSystem(): Promise<ValidationResult> {
        try {
            const psExecutor = new PowerShellExecutor(this.config.workflowRoot, this.config.powershellPath);
            const output = await psExecutor.executeCommand('Test-AIISystem | ConvertTo-Json -Depth 10', 30000);

            const result = JSON.parse(output);

            // 显示验证结果
            this.showValidationResult(result);

            return {
                checks: result.Checks || [],
                passed: result.Passed || 0,
                failed: result.Failed || 0,
                warnings: result.Warnings || 0,
                status: result.Status || '未知',
                error: result.Error
            };

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            vscode.window.showErrorMessage(`系统验证失败: ${errorMessage}`);

            return {
                checks: [],
                passed: 0,
                failed: 1,
                warnings: 0,
                status: '验证失败',
                error: errorMessage
            };
        }
    }

    /**
     * 修复系统
     */
    public async repairSystem(): Promise<RepairResult> {
        try {
            // 确认修复操作
            const confirmation = await vscode.window.showWarningMessage(
                '此操作将尝试自动修复AII工作流系统问题。确认继续？',
                { modal: true },
                '确认修复', '取消'
            );

            if (confirmation !== '确认修复') {
                return {
                    success: false,
                    initialStatus: '未知',
                    finalStatus: '未知',
                    backupResult: null,
                    repairResults: null,
                    validation: {
                        checks: [],
                        passed: 0,
                        failed: 0,
                        warnings: 0,
                        status: '未知'
                    },
                    timestamp: new Date().toISOString(),
                    error: '用户取消修复操作'
                };
            }

            // 显示进度
            const progressOptions = {
                location: vscode.ProgressLocation.Notification,
                title: '修复AII工作流系统',
                cancellable: false
            };

            const result = await vscode.window.withProgress(progressOptions, async (progress) => {
                progress.report({ message: '正在验证系统状态...', increment: 10 });
                const psExecutor = new PowerShellExecutor(this.config.workflowRoot, this.config.powershellPath);

                progress.report({ message: '正在执行修复操作...', increment: 60 });
                const output = await psExecutor.executeCommand('Repair-AIISystem | ConvertTo-Json -Depth 10', 90000); // 1.5分钟超时

                progress.report({ message: '正在解析修复结果...', increment: 20 });
                const result = JSON.parse(output);

                progress.report({ message: '修复完成', increment: 10 });
                return result;
            });

            // 显示结果
            if (result.Success) {
                vscode.window.showInformationMessage(
                    `✅ 系统修复完成\n` +
                    `修复前状态: ${result.InitialStatus || '未知'}\n` +
                    `修复后状态: ${result.FinalStatus || '未知'}\n` +
                    `修复问题数: ${result.RepairResults?.FixedIssues?.length || 0}`,
                    '查看详情'
                ).then(selection => {
                    if (selection === '查看详情') {
                        this.showRepairResult(result);
                    }
                });
            } else {
                vscode.window.showWarningMessage(
                    `⚠️ 系统修复部分完成\n` +
                    `修复前状态: ${result.InitialStatus || '未知'}\n` +
                    `修复后状态: ${result.FinalStatus || '未知'}\n` +
                    `仍有问题需要手动处理`
                );
            }

            return {
                success: result.Success || false,
                initialStatus: result.InitialStatus || '未知',
                finalStatus: result.FinalStatus || '未知',
                backupResult: result.BackupResult,
                repairResults: result.RepairResults,
                validation: result.Validation || {
                    checks: [],
                    passed: 0,
                    failed: 0,
                    warnings: 0,
                    status: '未知'
                },
                timestamp: result.Timestamp || new Date().toISOString(),
                error: result.Error
            };

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            vscode.window.showErrorMessage(`系统修复失败: ${errorMessage}`);

            return {
                success: false,
                initialStatus: '未知',
                finalStatus: '未知',
                backupResult: null,
                repairResults: null,
                validation: {
                    checks: [],
                    passed: 0,
                    failed: 0,
                    warnings: 0,
                    status: '未知'
                },
                timestamp: new Date().toISOString(),
                error: errorMessage
            };
        }
    }

    /**
     * 显示验证结果
     */
    private showValidationResult(result: ValidationResult): void {
        const panel = vscode.window.createWebviewPanel(
            'aiiValidationResult',
            '系统验证结果',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: false
            }
        );

        panel.webview.html = this.getValidationResultHtml(result);
    }

    /**
     * 显示重置结果
     */
    private showResetResult(result: ResetResult): void {
        const panel = vscode.window.createWebviewPanel(
            'aiiResetResult',
            '系统重置结果',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: false
            }
        );

        panel.webview.html = this.getResetResultHtml(result);
    }

    /**
     * 显示修复结果
     */
    private showRepairResult(result: RepairResult): void {
        const panel = vscode.window.createWebviewPanel(
            'aiiRepairResult',
            '系统修复结果',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: false
            }
        );

        panel.webview.html = this.getRepairResultHtml(result);
    }

    /**
     * 生成验证结果HTML
     */
    private getValidationResultHtml(result: ValidationResult): string {
        const statusColor = result.status === '健康' ? '#388a34' :
                           result.status === '警告' ? '#d67e00' :
                           result.status === '异常' ? '#f14c4c' :
                           '#6e6e6e';

        return `
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>系统验证结果</title>
                <style>
                    body {
                        font-family: var(--vscode-font-family);
                        padding: 20px;
                        background-color: var(--vscode-editor-background);
                        color: var(--vscode-editor-foreground);
                    }

                    .status-header {
                        text-align: center;
                        margin-bottom: 30px;
                        padding: 20px;
                        border-radius: 8px;
                        background-color: var(--vscode-input-background);
                    }

                    .status-title {
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 10px;
                    }

                    .status-badge {
                        display: inline-block;
                        padding: 6px 16px;
                        border-radius: 20px;
                        color: white;
                        font-weight: bold;
                        font-size: 14px;
                        margin: 10px 0;
                    }

                    .stats {
                        display: flex;
                        justify-content: center;
                        gap: 30px;
                        margin: 20px 0;
                    }

                    .stat-item {
                        text-align: center;
                    }

                    .stat-value {
                        font-size: 28px;
                        font-weight: bold;
                        margin-bottom: 5px;
                    }

                    .stat-label {
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
                    }

                    .checks-list {
                        margin-top: 30px;
                    }

                    .check-item {
                        display: flex;
                        align-items: center;
                        padding: 10px;
                        margin-bottom: 8px;
                        background-color: var(--vscode-input-background);
                        border-radius: 4px;
                        border-left: 4px solid;
                    }

                    .check-status {
                        margin-right: 10px;
                        font-weight: bold;
                        min-width: 40px;
                    }

                    .check-name {
                        flex: 1;
                        font-weight: bold;
                    }

                    .check-details {
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
                        margin-top: 4px;
                    }

                    .status-passed { color: #388a34; border-left-color: #388a34; }
                    .status-failed { color: #f14c4c; border-left-color: #f14c4c; }
                    .status-warning { color: #d67e00; border-left-color: #d67e00; }
                </style>
            </head>
            <body>
                <div class="status-header">
                    <div class="status-title">系统验证结果</div>
                    <div class="status-badge" style="background-color: ${statusColor}">${result.status}</div>

                    <div class="stats">
                        <div class="stat-item">
                            <div class="stat-value" style="color: #388a34">${result.passed}</div>
                            <div class="stat-label">通过</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" style="color: #f14c4c">${result.failed}</div>
                            <div class="stat-label">失败</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" style="color: #d67e00">${result.warnings}</div>
                            <div class="stat-label">警告</div>
                        </div>
                    </div>
                </div>

                <div class="checks-list">
                    <h3>详细检查结果 (${result.checks.length}项)</h3>
                    ${result.checks.map((check, index) => `
                        <div class="check-item">
                            <div class="check-status status-${check.status === '通过' ? 'passed' : check.status === '失败' ? 'failed' : 'warning'}">
                                ${check.status}
                            </div>
                            <div style="flex: 1;">
                                <div class="check-name">${this.escapeHtml(check.check)}</div>
                                ${check.details ? `<div class="check-details">${this.escapeHtml(check.details)}</div>` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>

                ${result.error ? `
                    <div style="margin-top: 20px; padding: 15px; background-color: var(--vscode-inputValidation-errorBackground); color: var(--vscode-errorForeground); border-radius: 4px;">
                        <strong>错误信息:</strong><br>
                        ${this.escapeHtml(result.error)}
                    </div>
                ` : ''}
            </body>
            </html>
        `;
    }

    /**
     * 生成重置结果HTML
     */
    private getResetResultHtml(result: ResetResult): string {
        return `
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>系统重置结果</title>
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
                        background-color: ${result.success ? 'var(--vscode-input-background)' : 'var(--vscode-inputValidation-errorBackground)'};
                    }

                    .result-title {
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 10px;
                        color: ${result.success ? 'var(--vscode-foreground)' : 'var(--vscode-errorForeground)'};
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
                        ${result.success ? '✅ 系统重置成功' : '❌ 系统重置失败'}
                    </div>
                    <div class="result-icon">
                        ${result.success ? '🎉' : '😞'}
                    </div>
                    <div class="result-summary">
                        重置时间: ${new Date(result.timestamp).toLocaleString()}<br>
                        ${result.backup?.BackupDir ? `备份位置: ${this.escapeHtml(result.backup.BackupDir)}<br>` : ''}
                        ${result.cacheCleanup?.DeletedFiles ? `清理缓存文件: ${result.cacheCleanup.DeletedFiles} 个<br>` : ''}
                        ${result.backupCleanup?.DeletedBackups ? `清理旧备份: ${result.backupCleanup.DeletedBackups} 个` : ''}
                    </div>
                </div>

                ${result.success ? `
                    <div class="result-details">
                        ${result.backup ? `
                            <div class="detail-section">
                                <div class="section-title">备份信息</div>
                                <div class="detail-item">
                                    <span class="detail-label">备份类型:</span>
                                    <span class="detail-value">${this.escapeHtml(result.backup.BackupType || '未知')}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">备份时间:</span>
                                    <span class="detail-value">${this.escapeHtml(result.backup.CreatedAt || '未知')}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">备份大小:</span>
                                    <span class="detail-value">${result.backup.Summary?.TotalSize ? `${Math.round(result.backup.Summary.TotalSize / 1024 / 1024 * 100) / 100} MB` : '未知'}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">成功项目:</span>
                                    <span class="detail-value">${result.backup.Summary?.SuccessCount || 0}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">失败项目:</span>
                                    <span class="detail-value">${result.backup.Summary?.FailedCount || 0}</span>
                                </div>
                            </div>
                        ` : ''}

                        ${result.cacheCleanup ? `
                            <div class="detail-section">
                                <div class="section-title">缓存清理</div>
                                <div class="detail-item">
                                    <span class="detail-label">删除文件数:</span>
                                    <span class="detail-value">${result.cacheCleanup.DeletedFiles || 0}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">删除目录数:</span>
                                    <span class="detail-value">${result.cacheCleanup.DeletedDirs || 0}</span>
                                </div>
                                ${result.cacheCleanup.KeptConfig !== undefined ? `
                                    <div class="detail-item">
                                        <span class="detail-label">保留配置:</span>
                                        <span class="detail-value">${result.cacheCleanup.KeptConfig ? '是' : '否'}</span>
                                    </div>
                                ` : ''}
                                ${result.cacheCleanup.KeptTasks !== undefined ? `
                                    <div class="detail-item">
                                        <span class="detail-label">保留任务:</span>
                                        <span class="detail-value">${result.cacheCleanup.KeptTasks ? '是' : '否'}</span>
                                    </div>
                                ` : ''}
                            </div>
                        ` : ''}

                        ${result.backupCleanup ? `
                            <div class="detail-section">
                                <div class="section-title">备份清理</div>
                                <div class="detail-item">
                                    <span class="detail-label">删除备份数:</span>
                                    <span class="detail-value">${result.backupCleanup.DeletedBackups || 0}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">保留备份数:</span>
                                    <span class="detail-value">${result.backupCleanup.KeptBackups || 0}</span>
                                </div>
                            </div>
                        ` : ''}

                        ${result.reinitialization ? `
                            <div class="detail-section">
                                <div class="section-title">重新初始化</div>
                                <div class="detail-item">
                                    <span class="detail-label">状态:</span>
                                    <span class="detail-value">${result.reinitialization.Success ? '成功' : '失败'}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">消息:</span>
                                    <span class="detail-value">${this.escapeHtml(result.reinitialization.Message || '无')}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">重置时间:</span>
                                    <span class="detail-value">${this.escapeHtml(result.reinitialization.ResetTime || '未知')}</span>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                ` : ''}

                ${result.error ? `
                    <div class="error-message">
                        <strong>错误信息:</strong><br>
                        ${this.escapeHtml(result.error)}
                    </div>
                ` : ''}
            </body>
            </html>
        `;
    }

    /**
     * 生成修复结果HTML
     */
    private getRepairResultHtml(result: RepairResult): string {
        return `
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>系统修复结果</title>
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
                        background-color: ${result.success ? 'var(--vscode-input-background)' : 'var(--vscode-inputValidation-warningBackground)'};
                    }

                    .result-title {
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 10px;
                        color: ${result.success ? 'var(--vscode-foreground)' : 'var(--vscode-warningForeground)'};
                    }

                    .result-icon {
                        font-size: 48px;
                        margin: 20px 0;
                    }

                    .result-summary {
                        margin: 20px 0;
                        line-height: 1.6;
                    }

                    .status-comparison {
                        display: flex;
                        justify-content: center;
                        gap: 40px;
                        margin: 20px 0;
                    }

                    .status-item {
                        text-align: center;
                    }

                    .status-value {
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 5px;
                    }

                    .status-label {
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
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

                    .fixed-issues-list {
                        margin-top: 10px;
                        padding-left: 20px;
                    }

                    .fixed-issue {
                        margin-bottom: 5px;
                        list-style-type: disc;
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
                        ${result.success ? '✅ 系统修复成功' : '⚠️ 系统修复部分完成'}
                    </div>
                    <div class="result-icon">
                        ${result.success ? '🔧' : '⚠️'}
                    </div>

                    <div class="status-comparison">
                        <div class="status-item">
                            <div class="status-value" style="color: ${this.getStatusColor(result.initialStatus)}">
                                ${result.initialStatus}
                            </div>
                            <div class="status-label">修复前状态</div>
                        </div>
                        <div class="status-item">
                            <div style="font-size: 24px;">→</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value" style="color: ${this.getStatusColor(result.finalStatus)}">
                                ${result.finalStatus}
                            </div>
                            <div class="status-label">修复后状态</div>
                        </div>
                    </div>

                    <div class="result-summary">
                        修复时间: ${new Date(result.timestamp).toLocaleString()}<br>
                        ${result.repairResults?.FixedIssues?.length ? `修复问题数: ${result.repairResults.FixedIssues.length}` : '无修复问题'}
                    </div>
                </div>

                ${result.repairResults?.FixedIssues?.length ? `
                    <div class="detail-section">
                        <div class="section-title">修复的问题</div>
                        <ul class="fixed-issues-list">
                            ${result.repairResults.FixedIssues.map((issue: string) => `
                                <li class="fixed-issue">${this.escapeHtml(issue)}</li>
                            `).join('')}
                        </ul>
                    </div>
                ` : ''}

                ${result.repairResults ? `
                    <div class="detail-section">
                        <div class="section-title">修复统计</div>
                        ${result.repairResults.CreatedDirs ? `
                            <div class="detail-item">
                                <span class="detail-label">创建目录数:</span>
                                <span class="detail-value">${result.repairResults.CreatedDirs}</span>
                            </div>
                        ` : ''}
                        ${result.repairResults.CreatedFiles ? `
                            <div class="detail-item">
                                <span class="detail-label">创建文件数:</span>
                                <span class="detail-value">${result.repairResults.CreatedFiles}</span>
                            </div>
                        ` : ''}
                    </div>
                ` : ''}

                ${result.validation ? `
                    <div class="detail-section">
                        <div class="section-title">验证结果</div>
                        <div class="detail-item">
                            <span class="detail-label">总体状态:</span>
                            <span class="detail-value" style="color: ${this.getStatusColor(result.validation.status)}">
                                ${result.validation.status}
                            </span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">通过检查:</span>
                            <span class="detail-value">${result.validation.passed}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">失败检查:</span>
                            <span class="detail-value">${result.validation.failed}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">警告检查:</span>
                            <span class="detail-value">${result.validation.warnings}</span>
                        </div>
                    </div>
                ` : ''}

                ${result.error ? `
                    <div class="error-message">
                        <strong>错误信息:</strong><br>
                        ${this.escapeHtml(result.error)}
                    </div>
                ` : ''}
            </body>
            </html>
        `;
    }

    /**
     * 获取状态颜色
     */
    private getStatusColor(status: string): string {
        switch (status) {
            case '健康':
                return '#388a34';
            case '警告':
                return '#d67e00';
            case '异常':
            case '验证失败':
                return '#f14c4c';
            default:
                return '#6e6e6e';
        }
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