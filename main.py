import os
import sys
import re
import time
import random

from colored import fore, back, style

from api import GremlinsAPI, Sneknet
from logger import log


increment = 1
REDDIT_TOKEN = os.environ.get("REDDIT_TOKEN", None)
if not REDDIT_TOKEN:
    print(back.RED + fore.BLACK)
    print('\n\nYOU MUST SET "REDDIT_TOKEN"\n\n')
    print(style.RESET, end='')
    sys.exit(0)

SNEKNET_TOKEN = os.environ.get("SNEKNET_TOKEN", None)

re_csrf = re.compile(r"<gremlin-app\n\s*csrf=\"(.*)\"")
re_notes_ids = re.compile(r"<gremlin-note id=\"(.*)\"")
re_notes = re.compile(r"<gremlin-note id=\".*\">\n\s*(.*)")
re_plswait = re.compile(r"<gremlin-prompt>\n.*<h1>(.*)</h1>\n.*<p>Please try again in a moment.</p>")

sneknet = Sneknet(SNEKNET_TOKEN)
gremlins = GremlinsAPI(REDDIT_TOKEN)

print(fore.GREEN_YELLOW)
print('🐍  https://snakeroom.org/sneknet 🐍')
print(style.RESET)


try:
    from gpt2 import Roberta
    print("Initalizing GPT-2...", end='\r')
    roberta = Roberta()
    print('GPT-2 Model Initialzed')
except:
    roberta = None


def cool_algo_name(notes):
    if roberta:
        datas = {k: roberta.query(v)[0] for k, v in notes.items()}
        val = max(datas.values())
        _id = list(datas.keys())[list(datas.values()).index(val)]
        log.debug(f'GPT2 {val} "{notes[_id]}" {datas=} {notes=}')

        if val >= .8:
            print(f'[{fore.ORANGE_1} GPT {(val)*100:.0f}% {style.RESET}][{len(notes)}]', end='')
            return _id

    longest = max(notes.values(), key=len)
    _id = list(notes.keys())[list(notes.values()).index(longest)]
    log.debug(f'Selected longest {longest}, {_id=} from {notes.values()=}')
    print(f'[{fore.YELLOW} LONGEST {style.RESET}][{len(notes)}]', end='')

    return _id

status = gremlins.status()

games_played: int = status['games_played']
games_won: int = status['games_won']

while True:
    log.debug('='*50)
    room = gremlins.room()

    plswait = re_plswait.findall(room.text)
    if plswait:
        for i in range(5):
            print(f'{back.WHITE}{fore.BLACK}{plswait[0]}' + ('' if i % 2 == 0 else back.BLACK) + ' ' + style.RESET, end='\r')
            time.sleep(1)
        continue

    print('', end='')

    csrf = re_csrf.findall(room.text)[0]
    ids = re_notes_ids.findall(room.text)
    notes_content = re_notes.findall(room.text)

    notes = {ids[i]: notes_content[i] for i in range(len(ids))}

    # Query Sneknet for known, and remove known humans from the notes
    known = sneknet.query(notes_content)
    if True in known.values():
        print(f'[{fore.CYAN}  IMPOSTER  {style.RESET}]', end='')
        # Sneknet doesnt return a full dict and it FUCKS my shit
        vals = [known.get(k, False) for k in range(5)]
        _id = ids[vals.index(True)]
        log.debug(f'Confirmed imposter from Sneknet {known=} {_id=} "{notes[_id]}"')

    else:
        if len(known) == 5:
            log.error(f'Zero length notes?!?!?! {notes=} {known=}')
            _id = cool_algo_name(notes)

        else:
            for i, v in known.items():
                del notes[ids[i]]
                log.debug(f'Dropped known human from notes {ids[i]=}')

            if len(notes) == 1:
                print(f'[{fore.CYAN}  IMPOSTER  {style.RESET}]', end='')
                _id = list(notes.keys())[0]
                log.debug(f'Confirmed imposter from last note {_id=} "{notes[_id]}"')

            else:
                _id = cool_algo_name(notes)

    text = notes[_id]

    print(f'[ {text:110} ]', end='')

    is_correct = gremlins.submit_guess(_id, csrf)

    log.debug(f'{is_correct=}')

    if is_correct:
        print(f'[{fore.LIGHT_GREEN} W {style.RESET}]', end='')
        games_won += 1
    else:
        print(f'[{fore.RED} L {style.RESET}]', end='')

    games_played += 1


    if len(notes) == 2:
        log.debug(f'50% chance "{notes[_id]}" {is_correct=}')
        del notes[_id] # delete the one we know
        options = [
            {
                "message": text,
                "correct": is_correct
            },
            {
                "message": notes[list(notes.keys())[0]],
                "correct": not is_correct
            }
        ]

    else:
        options = [
            {
                "message": text,
                "correct": True
            },
            *[{
                "message": content,
                "correct": False
            } for i, content in notes.items() if i != _id]
        ] if is_correct else [
            {
                "message": text,
                "correct": False
            }
        ]

    seen = sneknet.submit(options)

    log.debug(f'{seen=}')

    if seen:
        print(f'[{fore.CYAN}  SEEN  {style.RESET}]', end='')
    else:
        print(f'[{fore.MAGENTA} UNSEEN {style.RESET}]', end='')
    print(f'[{fore.DARK_ORANGE_3A} {increment} {style.RESET}]', end='')
    increment += 1

    print(f'[{(games_won/games_played)*100:.1f}%]', end='')

    if (True in known.values() and not is_correct):
        print(f'[{back.RED}{fore.WHITE} WRONG {style.RESET}]', end='')
        log.warning(f'IMPOSTER MISMATCH: "{notes[_id]}" {text=} {_id=} {known=} {notes=}')

    print('')
