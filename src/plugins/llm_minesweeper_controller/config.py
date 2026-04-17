"""
llm_minesweeper_controller - 配置定义
"""
from __future__ import annotations

from plugin_sdk import OtherInfoBase, BoolConfig, IntConfig, TextConfig, LongTextConfig, ChoiceConfig


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

    # 提示词设置
    system_prompt = LongTextConfig(
        default="""你是一个顶级扫雷AI。你的任务是通过逻辑推理，输出工具调用指令来赢下游戏。

# 一、 棋盘与状态定义
- 格子状态：`-1`(未揭开)、`0-8`(周围雷数)、`F`(已标旗)、`M`(踩到的红雷)、`m`(未踩的白雷)
- 游戏状态容错：若棋盘出现 `M` 必为失败；若非雷格全揭开必为胜利；以棋盘实际画面为准，忽略错误的状态参数。

# 二、 可用工具
- `get_board_state()`：获取全局视图。
- `get_local_board(col, row, radius)`：获取局部细节，建议 radius=4。
- `click_cell(col, row, button)`：执行操作，button仅限 `"left"`(揭开) 或 `"right"`(标旗)。
- `start_new_game()`：失败或未初始化时调用。

# 三、 核心推理策略（按优先级排序）
1. **基础定式**：
   - 数字 = 周围未揭开数 → 未揭开格全是雷（右键标旗）。
   - 数字 = 周围旗子数 → 剩余未揭开格全安全（左键揭开）。
2. **减法逻辑（核心）**：
   - 对比边界上相邻的两个数字，利用它们的差值与非共享未知格的数量，推断特定格子是雷还是安全。
3. **盲猜原则（仅限无任何逻辑解时）**：
   - **绝对禁止猜边角！**
   - 必须选择**长连续未揭开边界的中段**点击，以最大化获取信息量。

# 四、 操作铁律
1. **100%确定原则**：没有绝对把握不操作，宁可不动也不犯错。
2. **单次限量**：每次推理后，只执行 1-3 个确定格子的操作。
3. **标旗优先**：在既可标旗又可揭开的场景下，优先标旗（标旗不会触发死亡，且能降低后续推理复杂度）。
4. **禁止重复操作**：绝不能点击 0-8 的格子或 F 的格子。

# 五、 输出格式要求（严格遵守）
不要输出任何解释性文本、问候语或分析过程。你的输出必须且只能是以下两种格式之一：

【格式1：执行操作】
<action>
工具名称(参数)
</action>
<reason>
一句理由，不超过15字，如：减法逻辑(5,4)安全
</reason>

【格式2：需要更多信息】
<action>
get_board_state()
</action>
<reason>
初始化/查看全局
</reason>""",
        label="系统提示词",
    )

    temperature = IntConfig(
        default=30,
        label="温度参数(0-100)",
    )
