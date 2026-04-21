import * as vscode from 'vscode';
import * as path from 'path';

export interface WebviewPanelOptions {
    title: string;
    viewColumn?: vscode.ViewColumn;
    iconPath?: vscode.Uri;
    preserveFocus?: boolean;
}

export abstract class AIIWebviewPanel {
    protected panel: vscode.WebviewPanel | undefined;
    protected disposables: vscode.Disposable[] = [];

    constructor(
        protected readonly context: vscode.ExtensionContext,
        protected readonly viewType: string,
        protected readonly options: WebviewPanelOptions
    ) {}

    public show(): void {
        if (this.panel) {
            this.panel.reveal(this.options.viewColumn);
            return;
        }

        this.panel = vscode.window.createWebviewPanel(
            this.viewType,
            this.options.title,
            this.options.viewColumn || vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [
                    vscode.Uri.file(path.join(this.context.extensionPath, 'resources')),
                    vscode.Uri.file(path.join(this.context.extensionPath, 'webview'))
                ]
            }
        );

        if (this.options.iconPath) {
            this.panel.iconPath = this.options.iconPath;
        }

        this.panel.webview.html = this.getHtml();

        this.panel.onDidDispose(() => {
            this.dispose();
        }, null, this.disposables);

        this.panel.webview.onDidReceiveMessage(
            message => this.handleMessage(message),
            undefined,
            this.disposables
        );

        this.afterPanelCreated();
    }

    protected abstract getHtml(): string;
    protected abstract handleMessage(message: any): void;
    protected abstract afterPanelCreated(): void;

    protected postMessage(message: any): void {
        if (this.panel) {
            this.panel.webview.postMessage(message);
        }
    }

    protected getWebviewUri(...pathSegments: string[]): vscode.Uri {
        const resourcePath = vscode.Uri.file(
            path.join(this.context.extensionPath, ...pathSegments)
        );
        return this.panel?.webview.asWebviewUri(resourcePath) || resourcePath;
    }

    protected getNonce(): string {
        let text = '';
        const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        for (let i = 0; i < 32; i++) {
            text += possible.charAt(Math.floor(Math.random() * possible.length));
        }
        return text;
    }

    public dispose(): void {
        if (this.panel) {
            this.panel.dispose();
            this.panel = undefined;
        }

        while (this.disposables.length) {
            const disposable = this.disposables.pop();
            if (disposable) {
                disposable.dispose();
            }
        }
    }

    public isVisible(): boolean {
        return this.panel !== undefined;
    }

    public updateContent(): void {
        if (this.panel) {
            this.panel.webview.html = this.getHtml();
        }
    }
}

export class AIIWebviewManager {
    private panels: Map<string, AIIWebviewPanel> = new Map();

    constructor(private readonly context: vscode.ExtensionContext) {}

    public registerPanel(id: string, panel: AIIWebviewPanel): void {
        this.panels.set(id, panel);
    }

    public showPanel(id: string): void {
        const panel = this.panels.get(id);
        if (panel) {
            panel.show();
        }
    }

    public hidePanel(id: string): void {
        const panel = this.panels.get(id);
        if (panel) {
            panel.dispose();
            this.panels.delete(id);
        }
    }

    public postMessageToPanel(id: string, message: any): void {
        const panel = this.panels.get(id);
        if (panel) {
            (panel as any).postMessage(message);
        }
    }

    public updatePanel(id: string): void {
        const panel = this.panels.get(id);
        if (panel) {
            panel.updateContent();
        }
    }

    public dispose(): void {
        for (const panel of this.panels.values()) {
            panel.dispose();
        }
        this.panels.clear();
    }
}

// 导出具体的面板类
export { StatusPanel } from './statusPanel';
export { TaskPanel } from './taskPanel';