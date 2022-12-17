import json
import subprocess
import curses
from curses import wrapper
import os
import time
from pdb import set_trace
from pathlib import Path
import re
import random
from collections import namedtuple, OrderedDict
import logging

project_dir = os.path.abspath(os.path.dirname(__file__))

logging.basicConfig(filename=f'{project_dir}/stenos.log', filemode='w', encoding='utf-8', level=logging.DEBUG)

# Monkeypatch CTRL key codes
############################
curses.KEY_CTRL_A = 1
curses.KEY_CTRL_B = 2
curses.KEY_CTRL_C = 3
curses.KEY_CTRL_D = 4
curses.KEY_CTRL_E = 5
curses.KEY_CTRL_F = 6
curses.KEY_CTRL_G = 7
curses.KEY_CTRL_H = 8
curses.KEY_CTRL_I = 9
curses.KEY_CTRL_J = 10
curses.KEY_CTRL_K = 11
curses.KEY_CTRL_L = 12
curses.KEY_CTRL_M = 13
curses.KEY_CTRL_N = 14
curses.KEY_CTRL_O = 15
curses.KEY_CTRL_P = 16
curses.KEY_CTRL_Q = 17
curses.KEY_CTRL_R = 18
curses.KEY_CTRL_S = 19
curses.KEY_CTRL_T = 20
curses.KEY_CTRL_U = 21
curses.KEY_CTRL_V = 22
curses.KEY_CTRL_W = 23
curses.KEY_CTRL_X = 24
curses.KEY_CTRL_Y = 25
curses.KEY_CTRL_Z = 26

# DATA
######
steno_layout = (
"STPH   FPLTD\n"
"SKWR * RBGSZ\n"
"   AO EU")

steno_order = "#STKPWHRAO*EUFRPBLGTSD"

# Paths
#######
plover_config_dir = Path("/home/johannes/.local/share/plover")
dictionary_path = Path(f"{plover_config_dir}/main.json")
canonical_strokes_path = Path(f"{project_dir}/canonical_strokes.txt")
word_frequencies_path = Path(f"{project_dir}/word-frequencies.txt")
state_path = Path(f"{project_dir}/state.json")
history_path = Path(f"{project_dir}/history.json")
                         
for path in [state_path, history_path]:
    if not os.path.isfile(path):
        with open(path, "w+") as f:
            json.dump({}, f)

# LOAD DATA
###########
WordData = namedtuple('WordData', ['word', 'canon_stroke', 'n_occurences'])

with open(dictionary_path, "r") as f:
    dictionary = json.load(f)
    reverse_dictionary = {v:k for k,v in dictionary.items()}
    
with open(canonical_strokes_path, "r") as f:
    canonical_strokes = {}
    for l in f.readlines():
        word, strokes = l.strip().split(": ")
        if ", " in l:
            stroke = strokes.split(", ")[0]
        else:
            stroke = strokes
        stroke = re.sub(' \([0-9]*\)', "", stroke)
        canonical_strokes[word] = stroke

with open(word_frequencies_path, "r") as f:
    all_words = {}
    all_words_idx = []
    missing_canonical_stroke = []
    for i, l in enumerate(f.readlines()):
        l = l.strip()
        occurences, word = l.split(" ")
        if word in canonical_strokes.keys():
            all_words[word] = WordData(word, canonical_strokes[word], occurences)
            all_words_idx.append(WordData(word, canonical_strokes[word], occurences))
        else:
            missing_canonical_stroke.append(word)
    logging.info(f"No canonical stroke found for {len(missing_canonical_stroke)}/{i}.")
    
with open(state_path, "r") as f:
    state = json.load(f)
    
with open(history_path, "r") as f:
    history = json.load(f)

# LOGIC
#######

def clear_line(scr, n):
    y, x = curses.getsyx()
    scr.move(n, 0)
    scr.addstr(" "*curses.COLS)
    scr.move(y,x)
    
def get_new_words(prev_word=None):
    words = []
    target_words = all_words_idx[:4]
    assert len(target_words) > 1
    while True:
        new_word = random.choice(target_words)
        while new_word == prev_word:
            new_word = random.choice(target_words)
        if len(" ".join([x.word for x in words] + [new_word.word])) > curses.COLS:
            return words
        words.append(new_word)
        prev_word = new_word

        
# TODO
# - Create a system to only input for the "current active word". So you can't backspace beyond a word that is already correct. This is to make it easier to measure the time that you take to enter one word.
# - Measure the strokes per minute
# - Create saving of history of input (specifically how long it takes to enter a particular word).
# - Show words that you take long to enter with higher frequency
# - Add incremental adding of words, once you have achived X speed on the last N occurences of all currently targeted words.
# ^^^ MVP
# - Detect and discard time outliers. I.e. don't count entries that are further than one standard deviation away, when calculating how fast you are at entering a word. Don't even record them if they are 3 standard deviations away.
# - Instead of only weighting by how good you are at tying something, also weigh words by how long ago you typed them last (more likely if longer ago). Implement the Anki spaced repetition for this.
def main(stdscr):
    # curses.curs_set(False)
    words = get_new_words()
    word_rows = [words, get_new_words(words[-1])]
    l = ""
    display_stroke = True
    while True:
        # Draw target words
        pos = (1, 0)
        clear_line(stdscr, pos[0])
        stdscr.move(pos[0], pos[1])
        target_str = " ".join([x.word for x in words])
        for i in range(len(target_str)):
            if len(l) > i:
                if l[i] == target_str[i]:
                    stdscr.addstr(target_str[i], curses.A_UNDERLINE)
                else:
                    stdscr.addstr(target_str[i], curses.A_STANDOUT)
            else:
                stdscr.addstr(target_str[i])
                
        # Draw second target line
        pos = (2, 0)
        clear_line(stdscr, pos[0])
        stdscr.move(pos[0], pos[1])
        stdscr.addstr(" ".join([x.word for x in word_rows[1]]))
                
        # Draw Stroke
        pos = (4, 0)
        clear_line(stdscr, pos[0])
        if display_stroke:
            stdscr.move(pos[0], pos[1])
            stdscr.addstr(words[0].canon_stroke)

        # Draw Steno Keyboard
        pos = (6, 0)
        for i in range(3):
            clear_line(stdscr, pos[0] + i)
        if display_stroke:
            stdscr.move(pos[0], pos[1])
            stdscr.addstr(steno_layout, curses.A_DIM)
        
        # Draw input
        pos = (0, 0)
        clear_line(stdscr, pos[0])
        stdscr.move(pos[0], pos[1])
        stdscr.addstr(l)
        
        stdscr.refresh()
        
        k = stdscr.getch()
        if k == curses.KEY_BACKSPACE:
            l = l[:-1]
        elif k == curses.KEY_CTRL_S:
            display_stroke = not display_stroke
        else:
            l += chr(k)
            if l == " ":
                l = ""
        
        if l == " ".join([x.word for x in words]).strip():
            word_rows.pop(0)
            word_rows.append(get_new_words())
            words = word_rows[0]
            l = ""
            
logging.info("starting curses") 
wrapper(main)