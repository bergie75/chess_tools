import pygame
import chess
from stockfish.models import Stockfish

# useful global dictionaries and values for various conversions
fen_dictionary = {"K":["white","king"], "k":["black","king"],
                  "Q":["white","queen"], "q":["black","queen"],
                  "R":["white","rook"], "r":["black","rook"],
                  "N":["white","knight"], "n":["black","knight"],
                  "B":["white","bishop"], "b":["black","bishop"],
                  "P":["white","pawn"], "p":["black","pawn"]}

inv_fen_dictionary = {f"{fen_dictionary[key][0]}_{fen_dictionary[key][1]}":key for key in fen_dictionary}
square_dict = dict(zip("abcdefgh","01234567"))
inv_square_dict = dict(zip("01234567", "abcdefgh"))
new_game_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# weights for how well a piece guards a square
# since a piece only guards a square if you are willing to recapture with it
attack_weights = {"pawn":0.9, "knight":0.6,
                  "bishop":0.6, "rook":0.4,
                  "queen":0.25, "king":0.1}

class Piece:
    def __init__(self,color,x,y,piece_type):
        self.color = color
        self.x = x
        self.y = y
        self.type = piece_type

    def draw(self, surface):
        img = pygame.image.load(f"piece_images/{self.color}_{self.type}.svg")
        scaled_img = pygame.transform.rotozoom(img,0,1.8)
        surface.blit(scaled_img, (self.x*75-2,self.y*75-2))

def load_fen(full_fen):
    fen = full_fen.split(" ")[0]
    ranks = fen.split("/")  # first element is the 8th rank
    ranks.reverse()
    curr_rank = 7  # reflects the comment above
    pieces = []  # this will hold all pieces
    for rank in ranks:

        file = 0  # start at the left-most end of the board

        for symbol in rank:
            if symbol.isdigit():
                # moves file by designated number of blank spaces
                file += int(symbol)
            else:
                piece_info = fen_dictionary[symbol]
                temp_piece = Piece(piece_info[0], file, curr_rank, piece_info[1])
                pieces.append(temp_piece)

                # updates file position
                file += 1

        curr_rank -= 1

    return pieces

# a helper function that uses the above and a new-game FEN to load a fresh game
def new_game():
    return load_fen(new_game_fen)

def get_abbrev_fen(pieces):
    ranks = [["_"]*8,["_"]*8,["_"]*8,["_"]*8,["_"]*8,["_"]*8,["_"]*8,["_"]*8]
    for piece in pieces:
        curr_rank = piece.y
        curr_file = piece.x
        key = f"{piece.color}_{piece.type}"
        ranks[curr_rank][curr_file] = inv_fen_dictionary[key]

    fen_array = []

    for rank in ranks:
        blank_counter = 0
        counting_blanks = False
        rank_string = ""
        for symbol in rank:
            if symbol == "_":
                blank_counter += 1
                counting_blanks = True
            elif counting_blanks:
                rank_string += f"{blank_counter}{symbol}"
                blank_counter = 0  # reset counter back to zero
                counting_blanks = False
            else:
                rank_string += symbol
        # if we have been counting blanks and reached end of row, append these blanks
        if blank_counter > 0:
            rank_string += f"{blank_counter}"

        # add the string for this rank to the fen we are building
        fen_array.append(rank_string)
    # join all rank strings with standard delimiter
    return "/".join(fen_array)


def get_pieces_at_squares(pieces):
    board_places = [["_"]*8,["_"]*8,["_"]*8,["_"]*8,["_"]*8,["_"]*8,["_"]*8,["_"]*8]
    for piece in pieces:
        rank = piece.y
        file = piece.x
        board_places[rank][file] = inv_fen_dictionary[f"{piece.color}_{piece.type}"]
    return board_places

def square_to_display_coordinates(square):
    file_coord = square_dict[square[0]]
    rank_coord = str(8-int(square[1]))
    return file_coord+rank_coord

def display_coordinates_to_square(coord):
    file_number = inv_square_dict[coord[0]]
    rank_number = str(8-int(coord[1]))
    return file_number+rank_number

# returns the squares a pawn attacks in display coordinates
def pawn_attacked_squares(pawn_x, pawn_y, color):
    neighbors = {0:[1], 1:[0,2],
                 2:[1,3], 3:[2,4],
                 4:[3,5], 5:[4,6],
                 6:[5,7], 7:[6]}
    if color:
        attacked_rank = pawn_y - 1
    else:
        attacked_rank = pawn_y + 1
    attacked_squares = [f"{file}{attacked_rank}" for file in neighbors[pawn_x]]
    return attacked_squares


# side_to_play is a Boolean, True for white, False for black
# control type lists the pieces whose control we wish to visualize, defaults to all
def get_attack_color_coding(pieces, side_to_play,
                            con_types=["pawn", "bishop", "knight", "rook", "queen", "king"]):
    coloring_weights = {}
    # get fen from piece list, use this to generate a python-chess board to obtain legal moves
    board_fen = get_abbrev_fen(pieces)
    py_board = chess.Board(board_fen)

    if not side_to_play:
        py_board.push(chess.Move.null())  # if black to play, make a null move to get correct moveset

    # use moves of non-pawn pieces to find control
    moves = list(py_board.pseudo_legal_moves)
    for move in moves:
        string_move = str(move)[0:4]  # remove formatting and promotion from legal moves
        origin = string_move[0:2]  # starting square of the move
        destination = string_move[2:]
        piece_type = py_board.piece_at(chess.parse_square(origin)) # determine the type of piece moving
        piece_type = fen_dictionary[str(piece_type)][1]  # translate piece type to text

        weight = attack_weights[piece_type]
        attacked_square = square_to_display_coordinates(destination)
        if piece_type != "pawn" and piece_type in con_types:
            # add weight to target square, or create new entry if not yet attacked
            try:
                coloring_weights[attacked_square] += weight
            except:
                coloring_weights[attacked_square] = weight

    if "pawn" in con_types:
        for piece in pieces:
            if piece.type == "pawn" and (piece.color == "white") == side_to_play:
                pawn_x = piece.x
                pawn_y = piece.y
                pawn_squares = pawn_attacked_squares(pawn_x, pawn_y, side_to_play)
                for square in pawn_squares:
                    try:
                        coloring_weights[square] += weight
                    except:
                        coloring_weights[square] = weight

    return coloring_weights

def get_defended_pieces(pieces, defending_side):
    defense_array = [[0]*8,[0]*8,[0]*8,[0]*8,[0]*8,[0]*8,[0]*8,[0]*8]
    defense_values = {"king": 1, "queen": 1, "rook": 5, "bishop": 7, "knight": 7, "pawn": 10}

    # get fen from piece list, use this to generate a python-chess board to obtain legal moves
    board_fen = get_abbrev_fen(pieces)
    py_board = chess.Board(board_fen)

    for piece in pieces:
        piece_square_number = piece.x + (7-piece.y)*8
        if py_board.is_attacked_by(defending_side, piece_square_number) and ((piece.color == "white") == defending_side):
            defense_array[piece.x][piece.y] += defense_values[piece.type]

    return defense_array


# side_to_play is a Boolean, True for white, False for black
# control type lists the pieces whose control we wish to visualize, defaults to all
def get_attack_array(pieces, side_to_play,
                            con_types=["pawn", "bishop", "knight", "rook", "queen", "king"]):

    attack_array = [["_"]*8,["_"]*8,["_"]*8,["_"]*8,["_"]*8,["_"]*8,["_"]*8,["_"]*8]

    # get fen from piece list, use this to generate a python-chess board to obtain legal moves
    board_fen = get_abbrev_fen(pieces)
    py_board = chess.Board(board_fen)

    if not side_to_play:
        py_board.push(chess.Move.null())  # if black to play, make a null move to get correct moveset

    # use moves of non-pawn pieces to find control
    moves = list(py_board.pseudo_legal_moves)

    for move in moves:
        string_move = str(move)[0:4]  # remove formatting and promotion from legal moves
        origin = string_move[0:2]  # starting square of the move
        destination = string_move[2:]
        piece_type = py_board.piece_at(chess.parse_square(origin)) # determine the type of piece moving
        piece_type = fen_dictionary[str(piece_type)][1]  # translate piece type to text

        attacked_coords = square_to_display_coordinates(destination)
        attacked_x = int(attacked_coords[0])
        attacked_y = int(attacked_coords[1])
        if piece_type != "pawn" and piece_type in con_types:
            # add piece type to attack map
            attack_array[attacked_x][attacked_y] = piece_type

    if "pawn" in con_types:
        for piece in pieces:
            if "pawn" in con_types and piece.type == "pawn" and (piece.color == "white") == side_to_play:
                pawn_x = piece.x
                pawn_y = piece.y
                pawn_squares = pawn_attacked_squares(pawn_x, pawn_y, side_to_play)
                for square in pawn_squares:
                    attacked_x = int(square[0])
                    attacked_y = int(square[1])
                    attack_array[attacked_x][attacked_y] = "pawn"

    return attack_array

def board_struggle(pieces):
    white_attack = get_attack_color_coding(pieces, True)
    black_attack = get_attack_color_coding(pieces, False)

    contested_squares = set(list(white_attack.keys()) + list(black_attack.keys()))
    conflict_coding = {}
    for square in contested_squares:
        # check if white piece controls the square
        try:
            white_attack_strength = white_attack[square]
        except:
            white_attack_strength = 0.0
        # check if black piece controls the square
        try:
            black_attack_strength = black_attack[square]
        except:
            black_attack_strength = 0.0
        # save relative strength of attack from each player
        conflict_coding[square] = white_attack_strength - black_attack_strength

    return conflict_coding

def king_attackers(pieces, side_to_play):
    # set up board to obtain legal moves
    board_fen = get_abbrev_fen(pieces)
    py_board = chess.Board(board_fen)
    if not side_to_play:  # it is black's move, push a null move
        py_board.push(chess.Move.null())

    moves = list(py_board.pseudo_legal_moves)  # a lsit of all legal moves in the position

    # find coordinates of enemy king
    for piece in pieces:
        if piece.type == "king" and (side_to_play != (piece.color == "white")):
            king_x = piece.x
            king_y = piece.y
            break

    # find surrounding squares of enemy king
    increments = [-1,0,1]
    king_domain = [[min(max(king_x+dx,0),7), min(max(king_y+dy,0),7)] for dx in increments for dy in increments]
    king_dom_squares = {display_coordinates_to_square(f"{dsp[0]}{dsp[1]}") for dsp in king_domain}

    squares_to_highlight = set()
    for move in moves:
        string_move = str(move)[0:4]  # remove formatting and promotion from legal moves
        origin = string_move[0:2]  # starting square of the move
        destination = string_move[2:]
        if destination in king_dom_squares:
            squares_to_highlight.add(square_to_display_coordinates(origin))

    for piece in pieces:
        if piece.type == "pawn" and (piece.color == "white") == side_to_play:
            pawn_x = piece.x
            pawn_y = piece.y
            pawn_attack_coords = pawn_attacked_squares(pawn_x, pawn_y, side_to_play)
            for coords in pawn_attack_coords:
                pawn_square = display_coordinates_to_square(coords)
                if pawn_square in king_dom_squares:
                    squares_to_highlight.add(f"{pawn_x}{pawn_y}")

    return squares_to_highlight

def legal_move_squares(board_pieces, x, y):
    fen = get_abbrev_fen(board_pieces)
    py_board = chess.Board(fen)
    piece_square = display_coordinates_to_square(f"{x}{y}")  # square that the piece originates on

    side_to_play = True  # added so program fails gracefully if there is no piece on a target square
    # identify color of piece on the target square
    for piece in board_pieces:
        if piece.x == x and piece.y == y:
            side_to_play = piece.color == "white"

    # modify whose move it is on py_board
    if not side_to_play:
        py_board.push(chess.Move.null())

    moves = list(py_board.legal_moves)
    legal_squares = set()

    for move in moves:
        origin_square = str(move)[0:2]
        if origin_square == piece_square:
            dest_square = str(move)[2:4]
            legal_squares.add(square_to_display_coordinates(dest_square))

    return legal_squares

# a method to find which pieces have very few (pseudo)moves available
def restricted_pieces(board_pieces, side_to_play):

    # a dictionary representing when pieces have "not a lot of moves"
    restriction_dict = {"queen": 9, "rook": 5, "bishop": 3, "knight": 2}
    # standard board setup
    fen = get_abbrev_fen(board_pieces)
    py_board = chess.Board(fen)

    # we use this to see which squares an opposing piece controls
    attack_array = get_attack_array(board_pieces, not side_to_play)
    def_array = get_defended_pieces(board_pieces, not side_to_play)

    # side adjustment
    if not side_to_play:
        py_board.push(chess.Move.null())

    moves = list(py_board.pseudo_legal_moves)
    restricted_piece_squares = []

    for piece in board_pieces:
        num_moves = 0  # a counter to hold the number of legal moves for a given piece
        piece_square = display_coordinates_to_square(f"{piece.x}{piece.y}")
        piece_type = piece.type
        if piece_type != "pawn" and piece_type != "king" and ((piece.color == "white") == side_to_play):
            for move in moves:
                origin_square = str(move)[0:2]
                if piece_square == origin_square:
                    # we must now check to see if destination square is defended by opponent
                    dest_square = str(move)[2:4]
                    dest_coords = square_to_display_coordinates(dest_square)

                    dest_x = int(dest_coords[0])
                    dest_y = int(dest_coords[1])

                    if attack_array[dest_x][dest_y] == "_" and def_array[dest_x][dest_y] == 0:
                        num_moves += 1
            # check if we have less than the alloted number of moves
            if num_moves <= restriction_dict[piece_type]:
                restricted_piece_squares.append(f"{piece.x}{piece.y}")

    return restricted_piece_squares

def request_engine_move(engine):
    # UCI promotion notation to full piece name for compatibility with display
    uci_prom = {"q": "queen", "n": "knight", "b": "bishop", "r": "rook"}

    # pull best move from engine
    result = engine.get_best_move()

    # take origin square, convert to display, split to give to move function
    origin_coord = square_to_display_coordinates(result[0:2])
    x = int(origin_coord[0])
    y = int(origin_coord[1])

    # process destination square as above
    dest_coord = square_to_display_coordinates(result[2:4])
    new_x = int(dest_coord[0])
    new_y = int(dest_coord[1])

    try:
        # if the move is a promotion, final character specifies piece
        prom_type = uci_prom[result[-1]]
    except:
        prom_type = "empty"  # value for no promotion

    # return move information in a way that is most useful for display
    return x, y, new_x, new_y, prom_type
