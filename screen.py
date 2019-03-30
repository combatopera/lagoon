from system import screen

limit = 756

def stuff(session, window, text):
    for start in range(0, len(text), limit):
        screen('-S', session, '-p', window, '-X', 'stuff', text[start:start + limit])
