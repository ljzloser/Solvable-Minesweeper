from random import shuffle, choice
from typing import List, Tuple

import ms_toollib as ms
from safe_eval import safe_eval
from app_logger import logger

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


def enumerateChangeBoard(board: ms.EvfVideo | List[List[int]],
                         game_board: List[List[int]],
                         poses: List[Tuple[int, int]]) -> Tuple[List[List[int]], bool]:
    if not isinstance(board, list):
        board = board.into_vec_vec()
    if all(board[x][y] != CELL_MINE for x, y in poses):
        return board, True
    for i in range(len(board)):
        for j in range(len(board[0])):
            if game_board[i][j] == CELL_FLAGGED:
                game_board[i][j] = CELL_UNOPENED
    game_board = ms.mark_board(game_board, remark=True)
    if any(game_board[x][y] == CELL_FLAGGED for x, y in poses):
        return board, False
    poses = list(filter(lambda xy: game_board[xy[0]][xy[1]] == CELL_UNOPENED, poses))

    type_board = [[1 for i in range(len(board[0]))] for j in range(len(board))]
    rand_mine_num = 0
    rand_blank_num = 0
    constraint_mine_num = 0
    constraint_blank_num = 0

    matrix_ases, matrix_xses, matrix_bses = ms.refresh_matrixses(game_board)
    for idb, block in enumerate(matrix_xses):
        for idl, line in enumerate(block):
            if poses[0] in line:
                if len(line) >= EnuLimit:
                    return board, False
                matrix_a = matrix_ases[idb][idl]
                matrix_x = matrix_xses[idb][idl]
                matrix_b = matrix_bses[idb][idl]
                constraint_mine_num = [board[x][y]
                                       for x, y in matrix_x].count(CELL_MINE)
                constraint_blank_num = len(matrix_x) - constraint_mine_num
                for (i, j) in line:
                    type_board[i][j] = 2
            else:
                for (i, j) in line:
                    type_board[i][j] = 0
    for idr, row in enumerate(board):
        for idc, cell in enumerate(row):
            if game_board[idr][idc] == CELL_UNOPENED and type_board[idr][idc] == 1:
                if board[idr][idc] == CELL_MINE:
                    rand_mine_num += 1
                else:
                    rand_blank_num += 1
    if constraint_mine_num == 0:
        if rand_blank_num >= 1:
            rand_blank_num -= 1
            (p, q) = poses[0]
            board[p][q] = 0
            type_board[p][q] = 0
        else:
            return board, False
    else:
        constraint_mine_num_max = min(constraint_mine_num + constraint_blank_num - len(poses),
                                      constraint_mine_num + rand_mine_num)
        constraint_mine_num_min = max(constraint_mine_num - rand_blank_num, 0)
        all_solution = ms.cal_all_solution(matrix_a, matrix_b)
        idposes = [matrix_x.index(pos) for pos in poses]
        all_solution = filter(lambda x: constraint_mine_num_min <= x.count(1) <=
                              constraint_mine_num_max and
                              all([x[idpos] != 1 for idpos in idposes]),
                              all_solution)
        all_solution = list(all_solution)
        if not all_solution:
            return board, False
    if constraint_mine_num > 0:
        solution = choice(all_solution)
        for idx, (x, y) in enumerate(matrix_x):
            board[x][y] = -solution[idx]
        constraint_mine_num_new = solution.count(1)
        delta = constraint_mine_num_new - constraint_mine_num
        rand_mine_num = rand_mine_num - delta
        rand_blank_num = rand_blank_num + delta
    rand_board = rand_mine_num * [CELL_MINE] + rand_blank_num * [0]
    shuffle(rand_board)
    k = 0
    for i in range(len(board)):
        for j in range(len(board[0])):
            if game_board[i][j] == CELL_UNOPENED and type_board[i][j] == 1:
                board[i][j] = rand_board[k]
                k += 1
            if board[i][j] >= 0:
                board[i][j] = 0
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
