#!/usr/bin/env python3.2

"""
vlc_control: curses UI for *remote* control of VLC via RC interface

Remote control of VLC, including DVD navigation controls, is most readily
achieved using the RC interface.

Note that the RC interface accepts multiple connections at a time, but only
processes commands from the first connection, queuing up commands in the
later connections.  There's no way to sensibly detect this, since there's no
guaranteed response to any input.  So the best we can do is to connect for
each keypress, disconnect immediately, and hope that everyone else is so
considerate.

(We can check for results and block on I/O, but that's about it.)
"""

__author__ = 'syscomet@gmail.com (Phil Pennock)'

import argparse
import collections
import curses
import re
import socket
import sys

# For guidance on what's available, issue "help" for base commands and look
# at http://wiki.videolan.org/How_to_Use_Lirc for key names.

TOGGLE_STATES = {'interface': False}
def toggle(name, when_f, when_t):
  def doit():
    global TOGGLE_STATES
    if name not in TOGGLE_STATES:
      raise Error('Unknown toggle "%s"' % name)
    TOGGLE_STATES[name] = False if TOGGLE_STATES[name] else True
    return when_t if TOGGLE_STATES[name] else when_f
  return doit

COL_1, COL_2, COL_3, COL_4 = 0, 20, 40, 60

class Counter(object):
  def __init__(self, n):
    self.n = n
  def __int__(self):
    n = self.n
    self.n += 1
    return n
  def __repr__(self):
    return str(self.n)

COL_1_Y = Counter(2)
COL_2_Y = Counter(2)
COL_3_Y = Counter(2)
COL_4_Y = Counter(2)

KeyInfo = collections.namedtuple('KeyInfo',
    ('keychar', 'vlc_cmd', 'text', 'yoff', 'xoff', 'isquery'))
KEY_COMMANDS = dict(map(lambda l: (ord(l[0]), l), (
    KeyInfo('=', 'pause', 'Pause', int(COL_1_Y), COL_1, False),
    KeyInfo('␠', 'pause', 'Pause', int(COL_1_Y), COL_1, False),
    KeyInfo('<', 'chapter_p', 'Prev Chapter', int(COL_1_Y), COL_1, False),
    KeyInfo('>', 'chapter_n', 'Next Chapter', int(COL_1_Y), COL_1, False),
    KeyInfo('[', 'title_p', 'Prev Title', int(COL_1_Y), COL_1, False),
    KeyInfo(']', 'title_n', 'Next Title', int(COL_1_Y), COL_1, False),
    KeyInfo('{', 'prev', 'Prev in Playlist', int(COL_1_Y), COL_1, False),
    KeyInfo('}', 'next', 'Next in Playlist', int(COL_1_Y), COL_1, False),
    KeyInfo('w', 'key key-jump-long', 'Back long', int(COL_1_Y), COL_1, False),
    KeyInfo('e', 'key key-jump-medium', 'Back medium', int(COL_1_Y), COL_1, False),
    KeyInfo('r', 'key key-jump-short', 'Back short', int(COL_1_Y), COL_1, False),
    KeyInfo('t', 'key key-jump-extrashort', 'Back v.short', int(COL_1_Y), COL_1, False),
    KeyInfo('y', 'key key-jump+extrashort', 'Forw v.short', int(COL_1_Y), COL_1, False),
    KeyInfo('u', 'key key-jump+short', 'Forw short', int(COL_1_Y), COL_1, False),
    KeyInfo('i', 'key key-jump+medium', 'Forw medium', int(COL_1_Y), COL_1, False),
    KeyInfo('o', 'key key-jump+long', 'Forw long', int(COL_1_Y), COL_1, False),

    KeyInfo('+', 'volup', 'Volume Up', int(COL_2_Y), COL_2, False),
    KeyInfo('-', 'voldown', 'Volume Down', int(COL_2_Y), COL_2, False),
    KeyInfo('m', 'key key-vol-mute', 'Mute', int(COL_2_Y), COL_2, False),
    KeyInfo('a', 'key key-audio-track', 'Audio Track', int(COL_2_Y), COL_2, False),
    KeyInfo('s', 'key key-subtitle-track', 'Subtitles', int(COL_2_Y), COL_2, False),
    KeyInfo(',', 'slower', 'Rate: slower', int(COL_2_Y), COL_2, False),
    KeyInfo('.', 'normal', 'Rate: normal', int(COL_2_Y), COL_2, False),
    KeyInfo('/', 'faster', 'Rate: faster', int(COL_2_Y), COL_2, False),
    KeyInfo('F', 'frame', 'Rate: Frame', int(COL_2_Y), COL_2, False),

    KeyInfo('f', 'fullscreen', 'Fullscreen', int(COL_3_Y), COL_3, False),
    KeyInfo('M', 'key key-disc-menu', 'Menu', int(COL_3_Y), COL_3, False),
    KeyInfo('S', 'stats', 'Stats', int(COL_3_Y), COL_3, True),
    KeyInfo('T', ('get_title', 'get_time', 'get_length'), 'Title', int(COL_3_Y), COL_3, True),
    KeyInfo('I', 'info', 'Info', int(COL_3_Y), COL_3, True),
    KeyInfo('P', 'playlist', 'Playlist', int(COL_3_Y), COL_3, True),
    KeyInfo('?',
      toggle('interface', 'key key-intf-hide', 'key key-intf-show'),
      'Interface', int(COL_3_Y), COL_3, False),
    KeyInfo('Q', 'key key-quit', 'Quit VLC', int(COL_3_Y), COL_3, False),
    # This one just to have voluminous text for debugging pad display:
    #KeyInfo('H', 'help', 'Help Spam', int(COL_3_Y), COL_3, True),
    )
  ))
KEY_COMMANDS[curses.KEY_LEFT] = KeyInfo('←', 'key key-nav-left', 'Key Left', int(COL_4_Y), COL_4, False)
KEY_COMMANDS[curses.KEY_RIGHT] = KeyInfo('→', 'key key-nav-right', 'Key Right', int(COL_4_Y), COL_4, False)
KEY_COMMANDS[curses.KEY_UP] = KeyInfo('↑', 'key key-nav-up', 'Key Up', int(COL_4_Y), COL_4, False)
KEY_COMMANDS[curses.KEY_DOWN] = KeyInfo('↓', 'key key-nav-down', 'Key Down', int(COL_4_Y), COL_4, False)
KEY_COMMANDS[10] = KeyInfo('⏎', 'key key-nav-activate', 'Key Enter', int(COL_4_Y), COL_4, False)

KEY_COMMANDS[ord(' ')] = KEY_COMMANDS[ord('␠')]
del KEY_COMMANDS[ord('␠')]

INFO_OFFSET_DIGITS = (int(COL_3_Y)+2, COL_3)
for (digit, high) in (
    (1, '!'), (2, '@'), (3, '#'), (4, '$'), (5, '%'),
    (6, '^'), (7, '&'), (8, '*'), (9, '('), (0, ')')
    ):
  _bookmarki = '10' if digit == 0 else str(digit)
  voffset = 9 if digit == 0 else digit - 1
  KEY_COMMANDS[ord(str(digit))] = KeyInfo('   %d' % digit,
      'key key-play-bookmark%s' % _bookmarki,
      None, 0, 0, False)
  KEY_COMMANDS[ord(high)] = KeyInfo('Sh %d' % digit,
      'key key-set-bookmark%s' % _bookmarki,
      None, 0, 0, False)

DEBUGGING_OFFSET_START = (int(COL_1_Y)+1, 4)


class Error(Exception):
  """Base class for exceptions from vlc_control."""
  pass


class ServerInfo(object):
  def __init__(self, server_spec):
    if ':' not in server_spec:
      raise Error('Missing :port')
    host, port = server_spec.rsplit(':', 1)
    if host.startswith('[') and host.endswith(']'):
      host = host[1:-1]
    port = int(port)
    if not port or port < 0:
      raise Error('Port range problem')

    self.host = host
    self.port = port

  def socket_tuple(self):
    return (self.host, self.port)


class VLCCommand(object):
  def __init__(self, server_info, command):
    self._server_info = server_info
    if callable(command):
      command = command()
    elif not isinstance(command, str):
      command = '\n'.join(command)
    self._command = bytes('%s\nlogout\n' % command, 'ascii')

  def issue_cmd(self):
    s = socket.create_connection(self._server_info.socket_tuple())
    s.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
    to_send = self._command
    while len(to_send):
      sent = s.send(to_send)
      to_send = to_send[sent:]
    bufs = []
    while True:
      b = s.recv(4096)
      if not b:
        break
      bufs.append(b.decode('utf-8'))
    s.close()
    return ''.join(bufs)

  def __call__(self):
    return self.issue_cmd()


def info_layout(screen):
  """Reset screen layout to base."""
  screen.clear()
  screen.addstr(0, 2, 'VLC Control Interface', curses.A_BOLD)
  screen.addstr(0, 42, 'q/^C/^D quit menu program')
  for ki in KEY_COMMANDS.values():
    if ki.text is None:
      continue
    label = '%s %s' % (ki.keychar, ki.text)
    screen.addstr(ki.yoff, ki.xoff, label)
  screen.addstr(INFO_OFFSET_DIGITS[0], INFO_OFFSET_DIGITS[1],
      '1-9,0 to play bookmark 1-10')
  screen.addstr(INFO_OFFSET_DIGITS[0]+1, INFO_OFFSET_DIGITS[1],
      'Shift + 1-9,0 to set bookmarks')
  screen.addstr(INFO_OFFSET_DIGITS[0]+2, INFO_OFFSET_DIGITS[1],
      'Pause to stop frame-by-frame')
  screen.move(0, 0)
  screen.refresh()


def pad_for_text(text):
  if not text:
    return (None, 0, 0)
  lines = text.split('\n')
  if not lines[-1]:
    lines.pop()
  ysize = len(lines) + 2
  xsize = len(max(lines, key=len)) + 2
  pad = curses.newpad(ysize, xsize)
  pad.box()
  for y, l in enumerate(lines):
    pad.addstr(y+1, 1, l)
  return (pad, ysize, xsize)


def show_results(charcode, screen, results):
  """Show results screen layout, wait for keypress."""
  screen.clear()
  screen.addstr(0, 2, 'VLC Control Interface', curses.A_BOLD)
  screen.addstr(0, 40, 'Press a key when done')
  screen.addstr(1, 4, KEY_COMMANDS[charcode].text)
  screen.addstr(2, 35, 'PageUp/Down to scroll long results')
  (pad, pad_y_max, pad_x_max) = pad_for_text(results)
  if pad is None:
    screen.addstr(4,4, 'No results from server')
    screen.move(0, 0)
    screen.getch()
    info_layout(screen)
    return None
  screen.refresh()

  top_y, top_x = 4, 0
  bot_y, bot_x = map(lambda n: n-1, screen.getmaxyx())

  page_y_delta = (bot_y - top_y) // 2
  pad_y = 0
  pad.refresh(pad_y,0, top_y,top_x, bot_y,bot_x)
  screen.move(0, 0)

  ch = -1
  while ch in (-1, curses.KEY_PPAGE, curses.KEY_NPAGE):
    ch = screen.getch()
    if ch not in (curses.KEY_PPAGE, curses.KEY_NPAGE):
      break
    if ch == curses.KEY_PPAGE:
      pad_y -= page_y_delta
      if pad_y < 0:
        pad_y = 0
    elif ch == curses.KEY_NPAGE:
      pad_y += page_y_delta
      if pad_y > pad_y_max - (1 + bot_y - top_y):
        pad_y = pad_y_max - (1 + bot_y - top_y)
    pad.refresh(pad_y,0, top_y,top_x, bot_y, bot_x)
    screen.move(0, 0)

  info_layout(screen)


def process_command(charcode, server, screen, debugging):
  """Dispatch on character-press."""
  if charcode not in KEY_COMMANDS:
    return False
  cmd = KEY_COMMANDS[charcode].vlc_cmd
  results = VLCCommand(server, cmd)()
  if KEY_COMMANDS[charcode].isquery:
    show_results(charcode, screen, results)
    return True
  if debugging:
    (pad, pad_y_max, pad_x_max) = pad_for_text(results)
    if pad is not None:
      bot_y, bot_x = map(lambda n: n-1, screen.getmaxyx())
      pad.refresh(0,0, DEBUGGING_OFFSET_START[0], DEBUGGING_OFFSET_START[1], bot_y, bot_x)
      screen.move(0, 0)
  return True


def main_app(screen, server, debugging):
  """Main command-loop, to be run within curses.wrapper."""
  curses.raw()
  screen.nodelay(0)
  info_layout(screen)
  stale = False
  while True:
    ch = screen.getch()
    if stale or debugging:
      info_layout(screen)
      stale = False
    if ch in (-1, 3, 4, ord('q')):
      # We forcibly use ^C and ^D, even if stty has remapped intr & eof
      break
    if ch == 12:  # ^L
      screen.refresh()
      continue
    if ch == ord('D'):
      debugging = False if debugging else True
      screen.addstr(1, 10, 'Debugging %s' % ('enabled' if debugging else 'disabled'))
      screen.move(0, 0)
      stale = True
      continue
    handled = process_command(ch, server, screen, debugging)
    if debugging and not handled:
      screen.addstr(1, 10, 'Character %d  %s' % (ch, curses.keyname(ch)))
      screen.move(0, 0)
      stale = True


def _main(args, argv0):
  parser = argparse.ArgumentParser()
  parser.add_argument('-d', '--debug',
                      action='store_true', default=False,
                      help='Debug: show server responses')
  parser.add_argument('-s', '--server',
                      type=str, help='Server to connect to (hostname:port)')
  options = parser.parse_args(args=args)

  if not options.server:
    print('Need a server to connect to', file=sys.stderr)
    return 1
  try:
    server = ServerInfo(options.server)
  except Error as e:
    print(str(e), file=sys.stderr)
    return 1

  print('Attempting test connection; if we hang here, look for open conn elsewhere', file=sys.stderr)
  VLCCommand(server, 'help')()
  print('Test complete', file=sys.stderr)

  try:
    r = curses.wrapper(main_app, server, options.debug)
  except curses.error as e:
    print('Curses failure; screen too small?\n%s' % e, file=sys.stderr)
    r = 1

  return r

if __name__ == '__main__':
  argv0 = sys.argv[0].rsplit('/')[-1]
  rv = _main(sys.argv[1:], argv0=argv0)
  sys.exit(rv)

# vim: set ft=python sw=2 expandtab :
