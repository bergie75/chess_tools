import pygame
import sys
from piece_methods import Piece, load_fen, square_to_display_coordinates, request_engine_move
from piece_methods import (get_attack_color_coding, board_struggle, king_attackers,
                           legal_move_squares, restricted_pieces)
from piece_methods import square_to_display_coordinates, display_coordinates_to_square, get_abbrev_fen
from stockfish.models import Stockfish

# piece image citation: By Cburnett - Own work, CC BY-SA 3.0,
# https://commons.wikimedia.org/w/index.php?curid=1499808

# code to draw board from Medium article "How to Build a Chess Game
# with Pygame in Python"

# define square colors, globally accessible to all functions
white=pygame.Color(200,200,200)
black=pygame.Color(92,64,51)

def update_vis_cache(board, board_pieces, side_to_play, disp_mode, click_x=0, click_y=0):
    # computes all relevant maps to be stored
    attack_cc = get_attack_color_coding(board_pieces, side_to_play)
    board_strug = board_struggle(board_pieces)
    king_attacks = king_attackers(board_pieces, side_to_play)
    leg_moves = legal_move_squares(board_pieces, click_x, click_y)
    res_pieces = restricted_pieces(board_pieces, side_to_play)

    return [attack_cc, board_strug, king_attacks, leg_moves, res_pieces]


def display_processing(board, highlighted_squares, disp_mode):
    # code for 1-sided attack map
    if disp_mode == 0:
        for square in highlighted_squares.keys():
            x = int(square[0])
            y = int(square[1])
            color_level = min(int(120.0 / highlighted_squares[square]), 255)
            border_color = pygame.Color(0, 0, color_level)

            pygame.draw.rect(board, border_color, (x * 75, y * 75, 75, 75), 6)
    # for contested mapping
    elif disp_mode == 1:
        for square in highlighted_squares.keys():
            x = int(square[0])
            y = int(square[1])
            attack_strength = highlighted_squares[square]
            if attack_strength != 0.0:
                if attack_strength > 0:
                    color_level = min(int(120.0 / attack_strength), 255)
                    border_color = pygame.Color(0, 0, color_level)
                else:
                    color_level = min(int(-120.0 / attack_strength), 255)
                    border_color = pygame.Color(0, color_level, 0)

                pygame.draw.rect(board, border_color, (x * 75, y * 75, 75, 75), 6)
    # for king attackers
    elif disp_mode == 2:
        border_color = pygame.Color(200, 0, 0)

        for square in highlighted_squares:
            x = int(square[0])
            y = int(square[1])
            pygame.draw.rect(board, border_color, (x * 75, y * 75, 75, 75), 6)
    # to highlight a piece's legal moves
    elif disp_mode == 3:
        border_color = pygame.Color(238, 230, 0)

        for square in highlighted_squares:
            x = int(square[0])
            y = int(square[1])
            pygame.draw.rect(board, border_color, (x * 75, y * 75, 75, 75), 6)
    # to highlight restricted pieces
    elif disp_mode == 4:
        border_color = pygame.Color(200, 0, 0)

        for square in highlighted_squares:
            x = int(square[0])
            y = int(square[1])
            pygame.draw.rect(board, border_color, (x * 75, y * 75, 75, 75), 6)


def draw_board_and_pieces(board, screen, board_pieces, highlighted_squares, display_mode):
    board.fill(black)  # sets background color to designated color for black squares

    # add squares to board
    for x in range(0, 8, 2):
        for y in range(0, 8, 2):
            pygame.draw.rect(board, white, (x * 75, y * 75, 75, 75))
            pygame.draw.rect(board, white, ((x + 1) * 75, (y + 1) * 75, 75, 75))

    display_processing(board, highlighted_squares, display_mode)

    for piece in board_pieces:  # draw all of the acquired pieces
        piece.draw(board)

    # this contains a hard-coded value which may affect moving pieces
    screen.blit(board, (20, 20))  # blit is the command to put the board on screen, like plt.show?

# this move is called to allow the player to interact with the GUI
# as well as to allow the linked engine to make a move
# NOTE: auto-queening is turned on by default, prom_type only used by computer
# user_move is True if user is the one prompting a move

def make_move(board_pieces, x, y, new_x, new_y, user_move=True, pr_type="empty"):

    # UCI promotion notation from full piece name for compatibility with display
    uci_prom = {"queen": "q", "knight": "n", "bishop": "b", "rook": "r", "empty": ""}

    # if piece is found at target square, remove temporarily from the board
    # then try to move piece to the square. If they are the same color,
    # reject the move and add the piece back to the list of active pieces
    temp_color = None
    if new_x != x or new_y != y:
        for piece in board_pieces:
            if piece.x == new_x and piece.y == new_y:
                temp_piece = piece
                temp_color = temp_piece.color
                board_pieces.remove(piece)
                break

        for piece in board_pieces:
            # checks to avoid null moves, which removes the piece from the board
            if piece.x == x and piece.y == y:
                # checks for illegal move capturing same color
                if piece.color != temp_color:
                    # checks for promotion
                    if piece.type == "pawn" and (new_y == 0 or new_y == 7):
                        prom_color = piece.color
                        # takes user input to determine promotion type
                        if user_move:
                            recognized_piece = False  # we wait until user correctly types a piece to promote to
                            while recognized_piece == False:
                                prom_type = input("Please input a piece to promote to: ")
                                recognized_piece = prom_type in ["queen", "rook", "knight", "bishop"]
                        # engine is making the move, all necessary info provided to function call
                        else:
                            prom_type = pr_type  # uses parameter exposed for engine
                        prom_piece = Piece(prom_color, new_x, new_y, prom_type)
                        # perform the prmotion
                        board_pieces.remove(piece)
                        board_pieces.append(prom_piece)
                    else:
                        piece.x = new_x
                        piece.y = new_y
                else:
                    board_pieces.append(temp_piece)  # reject illegal move capturing own piece

    origin_square = display_coordinates_to_square(f"{x}{y}")
    dest_square = display_coordinates_to_square(f"{new_x}{new_y}")

    return origin_square + dest_square + uci_prom[pr_type]


# opens analysis board, no visualizations, white to play in new game
def analysis_board(fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                   disp=9999, sp=True):

    # initialize engine instance
    # adjust engine settings, depth at least 18 preferred
    stockfish = Stockfish(path="stockfish\stockfish-windows-x86-64-avx2.exe", depth=18)
    stockfish.update_engine_parameters({"Hash": 2 * 1024, "Threads": 4})

    # check if FEN is valid. Note this doesn't prevent nonsensical positions, which may lead
    # to crashes. E.g. white to move while black is in check. Gee, I wonder how I came up with
    # such a specific example? -_-
    if stockfish.is_fen_valid(fen):
        stockfish.set_fen_position(fen)
    else:
        raise Exception("Invalid FEN encountered")

    # start pygame
    pygame.init()

    # creating the window
    size = (640,640)  # dimensions of window
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption('Python Analysis Board')

    # create board and initialize control variables
    board = pygame.Surface((600,600))
    board_pieces = load_fen(fen)

    side_playing = sp
    display_mode = disp
    x = 0
    y = 0
    new_visualization_needed = False  # this variable controls when we refresh our highlights

    # compute relevant modes for highlighting
    vis_cache = update_vis_cache(board, board_pieces, side_playing, display_mode, x, y)
    highlighted_squares = vis_cache[min(display_mode, len(vis_cache) - 1)]


    draw_board_and_pieces(board, screen, board_pieces, highlighted_squares, display_mode)
    pygame.display.flip()  # must be called to actually show the frames of the game


    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                new_visualization_needed = True
                if event.key == pygame.K_SPACE:
                    new_visualization_needed = True  # sides have switched, this impacts visuals
                    side_playing = not side_playing

                    stock_fen = stockfish.get_fen_position().split(" ")
                    # change player indicator in FEN and update engine
                    if stock_fen[1] == "w":
                        stock_fen[1] = "b"
                    elif stock_fen[1] == "b":
                        stock_fen[1] = "w"
                    stockfish.set_fen_position(" ".join(stock_fen))

                if event.key == pygame.K_0:
                    display_mode = 0
                    print("Now viewing one-sided attack map.")

                if event.key == pygame.K_1:
                    display_mode = 1
                    print("Now viewing contested squares.")

                if event.key == pygame.K_2:
                    display_mode = 2
                    print("Now viewing king attackers.")

                if event.key == pygame.K_3:
                    display_mode = 3
                    print("Click a piece to see its legal moves")

                if event.key == pygame.K_4:
                    display_mode = 4
                    print("Now viewing restricted pieces")

                if event.key == pygame.K_TAB:
                    display_mode = 9999
                    print("All visualizations disabled")

                if event.key == pygame.K_a:
                    new_visualization_needed = True  # more pieces affects visualizations
                    add_piece_type = input("Please input a piece to add to the board: ")
                    add_square = input("Please input a square to drop the piece: ")
                    add_square = square_to_display_coordinates(add_square)
                    if side_playing:
                        add_piece_color = "white"
                    else:
                        add_piece_color = "black"

                    piece_to_drop = Piece(add_piece_color,int(add_square[0]),
                                          int(add_square[1]),add_piece_type)
                    board_pieces.append(piece_to_drop)
                    # update engine after piece is dropped
                    stock_fen = stockfish.get_fen_position().split(" ")
                    stock_tail = " ".join(stock_fen[1:])
                    abbrev_fen = get_abbrev_fen(board_pieces)
                    full_fen = abbrev_fen + " " + stock_tail
                    stockfish.set_fen_position(full_fen)

                if event.key == pygame.K_r:
                    new_visualization_needed = True  # engine move will impact the board
                    print("Engine move requested.")
                    # e prefix to indicate "engine"
                    # we play for the opponent of the current player
                    # NOTE: we currently do not have a way to activate castling rights or en passant.
                    # Only use during the middlegame or later!
                    (e_x, e_y, e_new_x,
                     e_new_y, e_prom_type) = request_engine_move(stockfish)
                    # apply engine request to the board
                    uci_move_eng = make_move(board_pieces, e_x, e_y, e_new_x,
                              e_new_y, user_move=False, pr_type=e_prom_type)
                    print(f"Engine has played {uci_move_eng}")
                    stockfish.make_moves_from_current_position([uci_move_eng])

            if event.type == pygame.MOUSEBUTTONDOWN:
                new_visualization_needed = True
                # get click position
                pos = pygame.mouse.get_pos()
                # find clicked square
                x = (pos[0]-20) // 75
                y = (pos[1]-20) // 75

            if event.type == pygame.MOUSEBUTTONUP:
                new_visualization_needed = True
                new_pos = pygame.mouse.get_pos()
                new_x = (new_pos[0] - 20) // 75
                new_y = (new_pos[1] - 20) // 75

                uci_move_player = make_move(board_pieces, x, y, new_x, new_y)
                # get this information before engine crashes from illegal move
                stock_fen = stockfish.get_fen_position().split(" ")
                stock_tail = " ".join(stock_fen[1:])
                try:
                    stockfish.make_moves_from_current_position([uci_move_player])
                except:
                    abbrev_fen = get_abbrev_fen(board_pieces)
                    full_fen = abbrev_fen + " " + stock_tail
                    stockfish.set_fen_position(full_fen)

            # if commands have altered our displays, update them
            if new_visualization_needed:
                vis_cache = update_vis_cache(board, board_pieces, side_playing, display_mode, x, y)
                highlighted_squares = vis_cache[min(display_mode, len(vis_cache) - 1)]  # disp_mode can=9999

            # once we have updated visuals, draw board and set new_visualization to False
            draw_board_and_pieces(board, screen, board_pieces, highlighted_squares, display_mode)
            new_visualization_needed = False
            pygame.display.update()

if __name__ == "__main__":
    import argparse as ag
    parser = ag.ArgumentParser()
    # command line program controls
    parser.add_argument("-f", "--fen", dest="fen",
                        default="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                        help="Game FEN")
    parser.add_argument("-d", "--disp", dest="disp", default=9999,
                        help="display modes are numeric values 0-3")
    parser.add_argument("-s", "--side", dest="sp", default=True,
                        help="1: white to play, 0: black to play")

    # read command line and run analysis board
    args = parser.parse_args()
    analysis_board(args.fen, int(args.disp), int(args.sp)>0)
