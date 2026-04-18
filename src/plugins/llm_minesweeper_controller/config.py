"""
llm_minesweeper_controller - 配置定义
"""
from __future__ import annotations

from plugin_sdk import OtherInfoBase, BoolConfig, IntConfig, TextConfig, ChoiceConfig


class LlmMinesweeperControllerConfig(OtherInfoBase):
    """插件配置"""

    # LLM API设置
    api_key = TextConfig(
        default="",
        label="API密钥",
    )

    api_base_url = TextConfig(
        default="https://api.openai.com/v1",
        label="API基础URL",
    )

    model_name = TextConfig(
        default="gpt-4o-mini",
        label="模型名称",
    )

    request_timeout = IntConfig(
        default=60,
        label="请求超时(秒)",
    )

    # 游戏设置
    default_difficulty = ChoiceConfig(
        default="medium",
        label="默认游戏难度",
        choices=[
            ("easy", "初级 (8x8, 10雷)"),
            ("medium", "中级 (16x16, 40雷)"),
            ("hard", "高级 (16x30, 99雷)"),
        ],
    )

    # 功能开关
    enable_auto_action = BoolConfig(
        default=False,
        label="自动执行LLM操作(否则需确认)",
    )

    temperature = IntConfig(
        default=30,
        label="温度参数(0-100)",
    )

    max_history_messages = IntConfig(
        default=20,
        label="上下文上限",
        description="超过此值时触发压缩",
    )

    min_history_messages = IntConfig(
        default=5,
        label="上下文下限",
        description="压缩后保留的最少消息数",
    )

    deep_thinking = ChoiceConfig(
        default="medium",
        label="深度思考",
        choices=[
            ("off", "关闭"),
            ("low", "低"),
            ("medium", "中"),
            ("high", "高"),
        ],
    )
