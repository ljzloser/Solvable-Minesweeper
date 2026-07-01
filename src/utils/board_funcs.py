from random import shuffle, choice
from typing import List, Tuple

import ms_toollib as ms
from utils.safe_eval import safe_eval
from utils.app_logger import logger

from config.constants import CELL_UNOPENED, CELL_FLAGGED, CELL_MINE, ENU_LIMIT as EnuLimit


def choose_3BV(board_constraint, attempt_times_limit, params):
    def choose_3BV_laymine(laymine):
        if not board_constraint:
            b = laymine(params)
            if isinstance(b, tuple):
                b, success_flag = b
            else:
                success_flag = True
            return (b, success_flag)
        t = 0
        while t < attempt_times_limit:
            b = laymine(params)
            if isinstance(b, tuple):
                b, success_flag = b
            else:
                success_flag = True

            constraints = {}
            wrapper_b = ms.Board(b)
            if "bbbv" in board_constraint:
                constraints.update({"bbbv": wrapper_b.bbbv})
            if "op" in board_constraint:
                constraints.update({"op": wrapper_b.op})
            if "isl" in board_constraint:
                constraints.update({"isl": wrapper_b.isl})
            if "cell0" in board_constraint:
                constraints.update({"cell0": wrapper_b.cell0})
            if "cell1" in board_constraint:
                constraints.update({"cell1": wrapper_b.cell1})
            if "cell2" in board_constraint:
                constraints.update({"cell2": wrapper_b.cell2})
            if "cell3" in board_constraint:
                constraints.update({"cell3": wrapper_b.cell3})
            if "cell4" in board_constraint:
                constraints.update({"cell4": wrapper_b.cell4})
            if "cell5" in board_constraint:
                constraints.update({"cell5": wrapper_b.cell5})
            if "cell6" in board_constraint:
                constraints.update({"cell6": wrapper_b.cell6})
            if "cell7" in board_constraint:
                constraints.update({"cell7": wrapper_b.cell7})
            if "cell8" in board_constraint:
                constraints.update({"cell8": wrapper_b.cell8})
            try:
                expression_flag = safe_eval(
                    board_constraint, extra_globals=constraints)
            except Exception:
                logger.warning(
                    "board_constraint eval failed",
                    exc_info=True,
                )
                return (b, success_flag)
            if expression_flag:
                return (b, success_flag)
            t += 1
        return (b, success_flag)
    return choose_3BV_laymine


def laymine_solvable_thread(board_constraint, attempt_times_limit, params):
    @choose_3BV(board_constraint, attempt_times_limit, params)
    def board(pp):
        return ms.laymine_solvable_thread(*pp)
    return board


def laymine(board_constraint, attempt_times_limit, params):
    @choose_3BV(board_constraint, attempt_times_limit, params)
    def board(pp):
        return ms.laymine(*pp)
    return board


def laymine_op(board_constraint, attempt_times_limit, params):
    @choose_3BV(board_constraint, attempt_times_limit, params)
    def board(pp):
        return ms.laymine_op(*pp)
    return board


def laymine_solvable_adjust(board_constraint, attempt_times_limit, params):
    @choose_3BV(board_constraint, attempt_times_limit, params)
    def board(pp):
        return ms.laymine_solvable_adjust(*pp)
    return board


def get_mine_times_limit(row: int, column: int):
    area = row * column
    if area <= 64:
        return (int(area * 0.375) + 1, 100000)
    elif area <= 256:
        return (int(area * (-area * 0.00048828125 + 0.40625)) + 2, 100000)
    elif area <= 480:
        return (int(area * (-area * 0.00013950892857 + 0.3169642857136)) + 2, 100000)
    elif area <= 864:
        return (int(area * (-area * 4.8225308641979135e-05 + 0.27314814814814997)) + 2, 50000)
    elif area <= 6400:
        return (int(area * (-area * 5.686683793619943e-06 + 0.23639477627916763)) + 2, 20000)
    else:
        return (int(area * 0.2) + 2, 10000)


def laymine_solvable_auto(row, column, mine_num, x, y):
    (max_mine_num, max_times) = get_mine_times_limit(row, column)
    if mine_num <= max_mine_num:
        ans = ms.laymine_solvable_thread(
            row, column, mine_num, x, y, max_times)
        ans = ms.laymine_solvable_thread(
            row, column, mine_num, x, y, max_times)
        if ans[1]:
            return ans
    return ms.laymine_solvable_adjust(row, column, mine_num, x, y)


def laymine_solvable(board_constraint, attempt_times_limit, params):
    @choose_3BV(board_constraint, attempt_times_limit, params)
    def board(pp):
        return laymine_solvable_auto(*pp)
    return board

def enumerate_change_board(board: ms.EvfVideo | List[List[int]],
                         game_board: List[List[int]],
                         poses: List[Tuple[int, int]]) -> Tuple[List[List[int]], bool]:
    """重排雷局，使指定格子(poses)都变成安全格。

    算法概要：
    1. 用 mark_board 从已开数字推导出所有必然的雷和非雷（标记为 11/12）。
    2. 排除已被判为雷的 pose（直接失败）；已判为空的 pose 无需处理。
    3. 将剩余未开格划分为两类：
       - 约束区：受周边已开数字约束，必须求解线性方程组（AX=B, x∈{0,1}）。
       - 随机区：自由布雷区域，用于补偿约束区的雷数变化。
    4. 当一个约束块过大（≥EnuLimit）时，枚举不可行，直接失败。
    5. 枚举约束方程的全部 0/1 解，过滤条件：
       a) 总雷数在允许范围内（原雷数 ± 随机区的吸收/释放能力）。
       b) 所有 pose 对应的变量必须为 0（安全）。
    6. 无可行解时返回 False；有解时随机选一个写入，并重算全盘数字。

    Args:
        board: 原始雷局（二维列表）或 EvfVideo 对象
        game_board: 玩家当前看到的局面（10=未开, 11=标雷, 0~8=已开数字）
        poses: 需要变为安全的格子坐标列表

    Returns:
        (new_board, success) — success=True 时 new_board 是重排后的雷局；
        success=False 时保留原 board。
    """
    # ── 前置处理 ────────────────────────────────────────

    # 如果传入的是 EvfVideo 等对象，转为二维列表
    if not isinstance(board, list):
        board = board.into_vec_vec()

    # 所有 pose 在原始雷局中均非雷 → 无需重排
    if all(board[x][y] != CELL_MINE for x, y in poses):
        return board, True

    # ── 清理用户标记 → 从数字约束重新推导 ────────────────

    # 清空玩家手动标旗，让求解器只依据已开数字推导约束
    for i in range(len(board)):
        for j in range(len(board[0])):
            if game_board[i][j] == CELL_FLAGGED:
                game_board[i][j] = CELL_UNOPENED
    game_board = ms.mark_board(game_board)

    # 若重新标记后任一个 pose 被判定必为雷 → 无法在维持
    # 已揭示数字的前提下把它变安全，直接失败
    if any(game_board[x][y] == CELL_FLAGGED for x, y in poses):
        return board, False

    # 已打开的 pose 无需参与排雷，仅保留 UNOPENED 的 pose
    poses = list(filter(lambda xy: game_board[xy[0]][xy[1]] == CELL_UNOPENED, poses))

    # ── 分类未开格：约束区域 vs 自由随机区域 ─────────────

    # type_board 标记所有未开格的角色：
    #   2 = 属于包含 pose 的约束块（受周边数字约束）
    #   0 = 属于其他约束块（不受当前 pose 影响）
    #   1 = 不属于任何约束块，可在随机区自由布雷
    type_board = [[1 for i in range(len(board[0]))] for j in range(len(board))]
    rand_mine_num = 0      # 随机格中的雷数
    rand_blank_num = 0     # 随机格中的空数
    constraint_mine_num = 0   # 约束块中的雷数
    constraint_blank_num = 0  # 约束块中的空数

    # refresh_matrixses 将 game_board 分解为约束方程组：
    #   matrix_a(idb,idl) — 系数矩阵 (AX = B)
    #   matrix_x(idb,idl) — 变量列表（约束块内的未开格坐标）
    #   matrix_b(idb,idl) — 常数矩阵
    # block = 一组独立连通的约束， line = 一个约束等式
    matrix_ases, matrix_xses, matrix_bses = ms.refresh_matrixses(game_board)
    for idb, block in enumerate(matrix_xses):
        for idl, line in enumerate(block):
            if poses[0] in line:
                # ── 找到包含第一个 pose 的约束行 ──
                if len(line) >= EnuLimit:
                    # 约束规模过大，枚举不可行
                    return board, False
                matrix_a = matrix_ases[idb][idl]
                matrix_x = matrix_xses[idb][idl]
                matrix_b = matrix_bses[idb][idl]
                # 统计约束块当前已有的雷数和空数
                constraint_mine_num = [board[x][y]
                                       for x, y in matrix_x].count(CELL_MINE)
                constraint_blank_num = len(matrix_x) - constraint_mine_num
                for (i, j) in line:
                    type_board[i][j] = 2
            else:
                # 其他约束行标记为 0，不参与本 pose 的求解
                for (i, j) in line:
                    type_board[i][j] = 0

    # 扫描全盘，统计随机格（type_board == 1 && 未开/未知安全）中
    # 原始有多少雷和空（值 12 是 mark_board 判定的「已知安全」格）
    for idr, row in enumerate(board):
        for idc, cell in enumerate(row):
            if game_board[idr][idc] in (CELL_UNOPENED, 12) and type_board[idr][idc] == 1:
                if board[idr][idc] == CELL_MINE:
                    rand_mine_num += 1
                else:
                    rand_blank_num += 1

    # ── 分支 1：约束块中原来一颗雷都没有 ─────────────────

    if constraint_mine_num == 0:
        # 约束块全空 → 只需确保 pose 为空，然后把多余的雷
        # 移到随机格中（从随机空位扣一个来抵雷）
        if rand_blank_num >= 1:
            rand_blank_num -= 1
            (p, q) = poses[0]
            board[p][q] = 0
            type_board[p][q] = 0
        else:
            # 随机区全是雷，没有空位来吸收这颗额外的雷
            return board, False

    # ── 分支 2：约束块中有雷 → 用枚举法找可行解 ───────────

    else:
        # 可行解的总雷数范围：
        #   下限 = 约束块原雷数 − 随机区空位数（最多能把这么多雷换到随机区）
        #   上限 = 约束块原雷数 + 随机区雷数（最多能把这么多空变成雷）
        # 再减去 pose 数量（它们必须空，消耗空位）
        constraint_mine_num_max = min(constraint_mine_num + constraint_blank_num - len(poses),
                                      constraint_mine_num + rand_mine_num)
        constraint_mine_num_min = max(constraint_mine_num - rand_blank_num, 0)

        # 枚举约束方程 AX = B 的全部 0/1 解（1=雷, 0=空）
        all_solution = ms.cal_all_solution(matrix_a, matrix_b)

        # 过滤条件：
        #   1) 总雷数在 [min, max] 范围内
        #   2) 所有 pose 对应的变量不能是 1（必须空）
        idposes = [matrix_x.index(pos) for pos in poses]
        all_solution = filter(lambda x: constraint_mine_num_min <= x.count(1) <=
                              constraint_mine_num_max and
                              all([x[idpos] != 1 for idpos in idposes]),
                              all_solution)
        all_solution = list(all_solution)
        if not all_solution:
            return board, False

    # ── 写入结果 ────────────────────────────────────────

    if constraint_mine_num > 0:
        # 从可行解中随机选一个，更新约束块的雷局
        solution = choice(all_solution)
        for idx, (x, y) in enumerate(matrix_x):
            board[x][y] = -solution[idx]
        # 约束块雷数变化量 delta 由随机区补偿，保持总雷数不变
        constraint_mine_num_new = solution.count(1)
        delta = constraint_mine_num_new - constraint_mine_num
        rand_mine_num = rand_mine_num - delta
        rand_blank_num = rand_blank_num + delta

    # 在随机区均匀散布雷和空（保持总数不变）
    rand_board = rand_mine_num * [CELL_MINE] + rand_blank_num * [0]
    shuffle(rand_board)
    k = 0
    for i in range(len(board)):
        for j in range(len(board[0])):
            if game_board[i][j] in (CELL_UNOPENED, 12) and type_board[i][j] == 1:
                board[i][j] = rand_board[k]
                k += 1
            # 清零所有数字格，后面统一重算
            if board[i][j] >= 0:
                board[i][j] = 0

    # 根据最终雷位重算所有数字
    board = ms.cal_board_numbers(board)
    return board, True

def board_list_to_bytes(board: List[List[int]]) -> bytes:
    if not board:
        return b''
    rows = len(board)
    cols = len(board[0])
    raw_data = bytearray()
    current_byte = 0
    bit_ptr = 0
    for i in range(rows):
        row = board[i]
        for j in range(cols):
            current_byte <<= 1
            val = row[j]
            if val == CELL_MINE:
                current_byte |= 1
            bit_ptr += 1
            if bit_ptr == 8:
                raw_data.append(current_byte)
                current_byte = 0
                bit_ptr = 0
    if bit_ptr > 0:
        current_byte <<= (8 - bit_ptr)
        raw_data.append(current_byte)
    return bytes(raw_data)


def board_bytes_to_board(rows: int, cols: int, board_bytes: bytes) -> list[list[int]]:
    total = rows * cols
    result = [[0] * cols for _ in range(rows)]
    for i in range(total):
        byte_idx = i // 8
        if byte_idx < len(board_bytes):
            is_mine = (board_bytes[byte_idx] >> (7 - i % 8)) & 1
        else:
            is_mine = 0
        if is_mine:
            result[i // cols][i % cols] = -1
    return ms.cal_board_numbers(result)
