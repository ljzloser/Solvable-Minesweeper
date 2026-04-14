# Level 6: 配置系统

## 配置系统概述

插件可以定义自己的配置项，这些配置会：
- 自动生成 UI 控件（在设置对话框中）
- 自动持久化到 `data/plugin_data/<plugin_name>/config.json`
- 支持配置变化事件通知

## 配置类型一览

| 类型 | UI 控件 | 用途示例 |
|------|---------|----------|
| `BoolConfig` | QCheckBox | 开关选项 |
| `IntConfig` | QSpinBox | 整数设置 |
| `FloatConfig` | QDoubleSpinBox | 浮点数设置 |
| `ChoiceConfig` | QComboBox | 下拉选择 |
| `TextConfig` | QLineEdit | 文本输入 |
| `ColorConfig` | 颜色按钮 | 颜色选择 |
| `FileConfig` | 文件对话框 | 文件路径 |
| `PathConfig` | 目录对话框 | 目录路径 |
| `LongTextConfig` | QTextEdit | 多行文本 |
| `RangeConfig` | 两个 QSpinBox | 数值范围 |

## 定义配置类

```python
from plugin_sdk import (
    OtherInfoBase, BoolConfig, IntConfig, FloatConfig,
    ChoiceConfig, TextConfig, ColorConfig,
)

class MyConfig(OtherInfoBase):
    """我的插件配置"""
    
    # 开关选项
    enable_feature = BoolConfig(
        default=True,
        label="启用功能",
        description="是否启用某功能",
    )
    
    # 整数设置
    max_count = IntConfig(
        default=100,
        label="最大数量",
        min_value=1,
        max_value=1000,
        step=10,
    )
    
    # 浮点数设置
    threshold = FloatConfig(
        default=0.5,
        label="阈值",
        min_value=0.0,
        max_value=1.0,
        decimals=2,
    )
    
    # 下拉选择
    theme = ChoiceConfig(
        default="dark",
        label="主题",
        choices=[
            ("light", "明亮"),
            ("dark", "暗黑"),
            ("auto", "跟随系统"),
        ],
    )
    
    # 文本输入
    player_name = TextConfig(
        default="",
        label="玩家名称",
        placeholder="输入名称...",
    )
    
    # 密码输入
    api_token = TextConfig(
        default="",
        label="API Token",
        password=True,  # 密码模式
    )
    
    # 颜色选择
    theme_color = ColorConfig(
        default="#1976d2",
        label="主题颜色",
    )
```

## 绑定配置到插件

```python
class MyPlugin(BasePlugin):
    
    @classmethod
    def plugin_info(cls) -> PluginInfo:
        return PluginInfo(
            name="my_plugin",
            description="我的插件",
            other_info=MyConfig,  # 👈 绑定配置类
        )
```

## 访问配置值

```python
def on_initialized(self):
    if self.other_info:
        enable = self.other_info.enable_feature
        max_count = self.other_info.max_count
        theme = self.other_info.theme
        self.logger.info(f"配置: enable={enable}, max_count={max_count}")

def _handle_event(self, event):
    if self.other_info and self.other_info.enable_feature:
        self._do_something(event)
```

## 监听配置变化

```python
def on_initialized(self):
    # 连接配置变化信号
    self.config_changed.connect(self._on_config_changed)

def _on_config_changed(self, name: str, value: Any):
    """配置变化时调用（在主线程执行）"""
    self.logger.info(f"配置变化: {name} = {value}")
    
    if name == "theme":
        self._apply_theme(value)
    elif name == "max_count":
        self._resize_buffer(value)
```

## 手动保存配置

```python
def on_shutdown(self):
    # 配置在设置对话框确认时自动保存
    # 也可以手动保存
    self.save_config()
```

## 配置存储位置

```
data/plugin_data/<plugin_name>/config.json
```

示例：
```json
{
  "enable_feature": true,
  "max_count": 100,
  "theme": "dark",
  "player_name": "Player1"
}
```

## 配置相关 API

| 属性/方法 | 说明 |
|-----------|------|
| `self.other_info` | 配置对象实例 |
| `self.config_changed` | 配置变化信号 |
| `self.save_config()` | 手动保存配置 |
| `self.other_info.to_dict()` | 导出为字典 |
| `self.other_info.from_dict(data)` | 从字典加载 |
| `self.other_info.reset_to_defaults()` | 重置为默认值 |
