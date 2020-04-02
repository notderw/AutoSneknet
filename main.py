import os
import sys
import re
import time
import random

from colored import fore, back, style

from api import GremlinsAPI, Sneknet
from logger import log

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

sneknet = Sneknet(SNEKNET_TOKEN)
gremlins = GremlinsAPI(REDDIT_TOKEN)

print(fore.GREEN_YELLOW)
print('🐍  https://snakeroom.org/sneknet 🐍')
print(style.RESET)

while True:
    log.debug('='*50)
    room = gremlins.room()

    csrf = re_csrf.findall(room.text)[0]
    ids = re_notes_ids.findall(room.text)
    notes_content = re_notes.findall(room.text)

    notes = {ids[i]: notes_content[i] for i in range(len(ids))}

    # Query Sneknet for known, and remove known humans from the notes
    known = sneknet.query(notes_content)
    if True in known.values():
        print(f'[{fore.CYAN} IMPOSTER  {style.RESET}]', end='')
        # Sneknet doesnt return a full dict and it FUCKS my shit
        vals = [known.get(k, False) for k in range(5)]
        _id = ids[vals.index(True)]
        log.debug(f'Confirmed imposter from Sneknet {known=} {_id=} "{notes[_id]}"')

    else:
        for i, v in known.items():
            del notes[ids[i]]
            log.debug(f'Dropped known human from notes {ids[i]=}')

        if len(notes) == 1:
            print(f'[{fore.CYAN} IMPOSTER  {style.RESET}]', end='')
            _id = list(notes.keys())[0]
            log.debug(f'Confirmed imposter from last note {_id=} "{notes[_id]}"')

        else:
            print(f'[{fore.YELLOW} RANDOM {style.RESET}][{len(notes)}]', end='')
            _id = random.choice(list(notes.keys()))
            log.debug(f'Picking random from {len(notes)} options, {_id=}, {notes=}, "{notes[_id]}"')

    text = notes[_id]

    print(f'[ {text:110} ]', end='')

    is_correct = gremlins.submit_guess(_id, csrf)

    log.debug(f'{is_correct=}')

    if is_correct:
        print(f'[{fore.LIGHT_GREEN} W {style.RESET}]', end='')
    else:
        print(f'[{fore.RED} L {style.RESET}]', end='')


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

    if (True in known.values() and not is_correct):
        print(back.RED + fore.BLACK)
        print(f'\n\nOOH SHIT THIS SHOULD NEVER HAPPEN\n\n')
        print(f'{notes_content=} {known=}')
        print('\n')
        print(f'{notes[_id]} WAS WRONG!!!!')
        print(style.RESET)

    print('')

    # You might need this but I dont
    # time.sleep(.1)
