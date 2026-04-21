import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';

export interface PowerShellResult {
    success: boolean;
    output: string;
    error?: string;
    exitCode?: number;
}

export class PowerShellExecutor {
    private workflowRoot: string;
    private powershellPath: string;

    constructor(workflowRoot: string, powershellPath?: string) {
        this.workflowRoot = workflowRoot;

        // 自动检测PowerShell路径
        if (powershellPath && powershellPath.trim() !== '') {
            this.powershellPath = powershellPath;
        } else {
            this.powershellPath = this.detectPowerShellPath();
        }
    }

    private detectPowerShellPath(): string {
        // 优先使用PowerShell Core (pwsh)，回退到Windows PowerShell
        const candidates = [
            'pwsh',        // PowerShell Core
            'powershell',  // Windows PowerShell
            'C:\\Program Files\\PowerShell\\7\\pwsh.exe',
            'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe'
        ];

        for (const candidate of candidates) {
            try {
                cp.execSync(`${candidate} -Command "Write-Host 'PowerShell found'"`, {
                    stdio: 'pipe',
                    timeout: 5000
                });
                return candidate;
            } catch {
                continue;
            }
        }

        // 如果找不到，返回默认值
        return 'powershell';
    }

    /**
     * 执行PowerShell命令
     */
    public async executeCommand(command: string, timeout: number = 30000): Promise<string> {
        return new Promise((resolve, reject) => {
            // 构建完整的命令，包括导入AII Workflow模块
            const fullCommand = this.buildCommand(command);

            const child = cp.exec(fullCommand, {
                cwd: this.workflowRoot,
                timeout: timeout,
                maxBuffer: 10 * 1024 * 1024 // 10MB
            }, (error, stdout, stderr) => {
                if (error) {
                    reject(new Error(`PowerShell命令执行失败: ${error.message}\n${stderr}`));
                    return;
                }

                // 清理输出
                const cleanOutput = this.cleanOutput(stdout);
                resolve(cleanOutput);
            });

            // 设置超时处理
            const timeoutId = setTimeout(() => {
                child.kill('SIGTERM');
                reject(new Error(`PowerShell命令执行超时 (${timeout}ms)`));
            }, timeout);

            child.on('exit', () => {
                clearTimeout(timeoutId);
            });
        });
    }

    /**
     * 执行PowerShell脚本文件
     */
    public async executeScript(scriptPath: string, args: string[] = [], timeout: number = 60000): Promise<string> {
        const argsString = args.map(arg => `"${arg.replace(/"/g, '\\"')}"`).join(' ');
        const command = `& "${scriptPath}" ${argsString}`;

        return this.executeCommand(command, timeout);
    }

    /**
     * 执行带交互的命令
     */
    public async executeInteractiveCommand(command: string): Promise<void> {
        // 创建一个新的终端
        const terminal = vscode.window.createTerminal({
            name: 'AII Workflow PowerShell',
            shellPath: this.powershellPath,
            cwd: this.workflowRoot
        });

        terminal.show();

        // 写入命令
        const fullCommand = this.buildCommand(command);
        terminal.sendText(fullCommand);
    }

    /**
     * 构建完整的PowerShell命令
     */
    private buildCommand(command: string): string {
        // 导入AII Workflow模块
        const modulePath = path.join(this.workflowRoot, 'powershell', 'AIIWorkflow.psd1');

        return `& {
            # 设置执行策略
            $ErrorActionPreference = "Stop"
            $WarningPreference = "Continue"

            # 设置工作目录
            Set-Location "${this.workflowRoot.replace(/\\/g, '\\\\')}"

            # 导入模块
            try {
                Import-Module "${modulePath.replace(/\\/g, '\\\\')}" -Force -ErrorAction Stop
                Write-Verbose "AII Workflow模块导入成功"
            } catch {
                Write-Error "无法导入AII Workflow模块: $_"
                exit 1
            }

            # 初始化工作流
            try {
                Initialize-AIIWorkflow -ErrorAction SilentlyContinue
            } catch {
                Write-Warning "工作流初始化失败: $_"
            }

            # 执行用户命令
            ${command}
        }`;
    }

    /**
     * 清理输出字符串
     */
    private cleanOutput(output: string): string {
        // 移除常见的PowerShell提示信息
        let cleaned = output
            .replace(/PS .*?> /g, '')  // 移除PowerShell提示符
            .replace(/\r\n/g, '\n')     // 统一换行符
            .replace(/\n{3,}/g, '\n\n') // 压缩多余空行
            .trim();

        // 移除ANSI转义序列（颜色代码等）
        cleaned = cleaned.replace(/\u001b\[[0-9;]*m/g, '');

        return cleaned;
    }

    /**
     * 测试PowerShell环境
     */
    public async testEnvironment(): Promise<boolean> {
        try {
            const result = await this.executeCommand('Write-Host "PowerShell环境测试成功"', 5000);
            return result.includes('PowerShell环境测试成功');
        } catch {
            return false;
        }
    }

    /**
     * 测试AII Workflow模块
     */
    public async testAIIModule(): Promise<boolean> {
        try {
            const result = await this.executeCommand('Get-Command -Module AIIWorkflow', 10000);
            return result.includes('Get-AIIWorkflowRoot') || result.includes('Start-AIIWorkflow');
        } catch {
            return false;
        }
    }

    /**
     * 获取工作流状态
     */
    public async getWorkflowStatus(): Promise<any> {
        try {
            const result = await this.executeCommand('Get-AIIStatus | ConvertTo-Json -Depth 10', 15000);
            return JSON.parse(result);
        } catch (error) {
            throw new Error(`获取工作流状态失败: ${error}`);
        }
    }

    /**
     * 启动工作流
     */
    public async startWorkflow(): Promise<boolean> {
        try {
            const result = await this.executeCommand('Start-AIIWorkflow', 30000);
            return result.includes('Workflow started successfully') || result.includes('工作流启动成功');
        } catch {
            return false;
        }
    }

    /**
     * 创建新任务
     */
    public async createTask(description: string): Promise<any> {
        try {
            const result = await this.executeCommand(
                `New-AIITask -Description "${description.replace(/"/g, '\\"')}" | ConvertTo-Json -Depth 10`,
                30000
            );
            return JSON.parse(result);
        } catch (error) {
            throw new Error(`创建任务失败: ${error}`);
        }
    }

    /**
     * 列出任务
     */
    public async listTasks(): Promise<any[]> {
        try {
            const result = await this.executeCommand('Get-AIITaskList | ConvertTo-Json -Depth 10', 15000);
            return JSON.parse(result);
        } catch (error) {
            throw new Error(`列出任务失败: ${error}`);
        }
    }

    /**
     * 重置系统
     */
    public async resetSystem(force: boolean = true, keepConfig: boolean = true, keepTasks: boolean = false): Promise<any> {
        const forceFlag = force ? '-Force' : '';
        const keepConfigFlag = keepConfig ? '-KeepConfig' : '';
        const keepTasksFlag = keepTasks ? '-KeepTasks' : '';

        try {
            const result = await this.executeCommand(
                `Reset-AIISystem ${forceFlag} ${keepConfigFlag} ${keepTasksFlag} | ConvertTo-Json -Depth 10`,
                60000
            );
            return JSON.parse(result);
        } catch (error) {
            throw new Error(`重置系统失败: ${error}`);
        }
    }

    /**
     * 验证系统
     */
    public async validateSystem(): Promise<any> {
        try {
            const result = await this.executeCommand('Test-AIISystem | ConvertTo-Json -Depth 10', 20000);
            return JSON.parse(result);
        } catch (error) {
            throw new Error(`验证系统失败: ${error}`);
        }
    }

    /**
     * 修复系统
     */
    public async repairSystem(): Promise<any> {
        try {
            const result = await this.executeCommand('Repair-AIISystem | ConvertTo-Json -Depth 10', 30000);
            return JSON.parse(result);
        } catch (error) {
            throw new Error(`修复系统失败: ${error}`);
        }
    }

    /**
     * 列出备份
     */
    public async listBackups(): Promise<any[]> {
        try {
            const result = await this.executeCommand('Get-AIIBackups | ConvertTo-Json -Depth 10', 15000);
            return JSON.parse(result);
        } catch (error) {
            throw new Error(`列出备份失败: ${error}`);
        }
    }

    /**
     * 创建备份
     */
    public async createBackup(backupType: string = 'manual'): Promise<any> {
        try {
            const result = await this.executeCommand(
                `Backup-AIISystem -BackupType "${backupType}" | ConvertTo-Json -Depth 10`,
                30000
            );
            return JSON.parse(result);
        } catch (error) {
            throw new Error(`创建备份失败: ${error}`);
        }
    }

    /**
     * 恢复备份
     */
    public async restoreBackup(backupDir: string, force: boolean = false): Promise<any> {
        const forceFlag = force ? '-Force' : '';

        try {
            const result = await this.executeCommand(
                `Restore-AIISystem -BackupDir "${backupDir.replace(/\\/g, '\\\\')}" ${forceFlag} | ConvertTo-Json -Depth 10`,
                60000
            );
            return JSON.parse(result);
        } catch (error) {
            throw new Error(`恢复备份失败: ${error}`);
        }
    }

    /**
     * 清理资源
     */
    public dispose(): void {
        // 当前类没有需要清理的资源
    }
}