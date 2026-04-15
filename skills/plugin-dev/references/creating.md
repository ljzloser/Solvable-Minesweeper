# 创建新插件流程

当用户请求创建新插件时，按以下步骤操作：

## 步骤 1：询问插件形式

使用 `ask_user_question` 工具询问：

```json
{
  "question": "请选择插件的形式?",
  "header": "插件形式",
  "options": [
    {"label": "单文件 (.py)", "description": "简单插件，一个文件搞定，适合快速开发"},
    {"label": "包形式 (目录)", "description": "复杂插件，支持多模块分离，适合大型插件"}
  ],
  "multiSelect": false
}
```

## 步骤 2：收集插件信息

依次询问以下信息：

### 基本信息
```json
{
  "question": "请输入插件名称（英文，下划线分隔，如 my_plugin）:",
  "header": "插件名称"
}
```

### 描述信息
```json
{
  "question": "请输入插件描述:",
  "header": "描述"
}
```

### 作者信息
```json
{
  "question": "请输入作者名称:",
  "header": "作者"
}
```

### 功能选项
```json
{
  "question": "插件需要哪些功能?",
  "header": "功能选项",
  "options": [
    {"label": "GUI 界面", "description": "插件需要一个可视化界面"},
    {"label": "订阅事件", "description": "监听游戏事件（如游戏结束）"},
    {"label": "发送指令", "description": "控制主进程（如开始新游戏）"},
    {"label": "配置系统", "description": "用户可配置的设置项"}
  ],
  "multiSelect": true
}
```

## 步骤 3：生成插件代码

根据收集的信息，使用 `write_file` 工具创建插件文件：

- **单文件插件**: 创建 `plugins/{plugin_name}.py`
- **包形式插件**: 创建 `plugins/{plugin_name}/__init__.py`

## 步骤 4：验证创建结果

创建完成后：
1. 使用 `python -m py_compile` 检查语法
2. 告知用户插件文件位置
3. 提醒用户重启插件管理器以加载新插件

## 示例交互流程

```
用户: 帮我创建一个新插件

助手: [使用 ask_user_question 询问插件形式]
用户选择: 单文件 (.py)

助手: [询问插件名称]
用户输入: auto_replay

助手: [询问描述]
用户输入: 自动回放功能

助手: [询问作者]
用户输入: developer

助手: [询问功能选项]
用户选择: GUI 界面, 订阅事件

助手: [使用 write_file 创建 plugins/auto_replay.py]
助手: [使用 py_compile 验证语法]
助手: 插件已创建，请重启插件管理器加载
```
