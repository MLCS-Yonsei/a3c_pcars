import sys,os
import curses
import math
import redis

''' Init Redis '''
r = redis.StrictRedis(host='redis.hwanmoo.kr', port=6379, db=1)

class Screen:
    def __init__(self):
        self.k = 0
        self.cursor_x = 0
        self.cursor_y = 0

        def init_menu(stdscr):
            # Clear and refresh the screen for a blank canvas
            stdscr.clear()
            stdscr.refresh()

            # Start colors in curses
            curses.start_color()
            curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

            # Loop where k is the last character pressed
            # while (k != ord('q')):

            return stdscr

        self.stdscr = curses.wrapper(init_menu)

    def get_pos(self, num, flag, max_height, max_width, _str):
        _w = 30
        _h = 15

        _empty_str = ""
        for i in range(_w):
            _empty_str += " "

        if flag == 'worker_header':
            x = 0
            y = 1
        elif flag == 'print':
            x = 0
            y = 2
        elif flag == 'episode':
            x = 0
            y = 3
        elif flag == 'step':
            x = 0
            y = 4
        elif flag == 'distance':
            x = 0
            y = 6
        elif flag == 'd':
            x = 0
            y = 7
        elif flag == 'cos_a':
            x = 0
            y = 8
        elif flag == 'reward':
            x = 0
            y = 10
        elif flag == 'reset_amt':
            x = 0
            y = 11
        elif flag == 'reset_cnt':
            x = 0
            y = 12

        _raw_x = x + _w*(num)
        y = y + _h*(math.floor(_raw_x/max_width))
        x = _raw_x - max_width*(math.floor(_raw_x / max_width)) - (_raw_x % max_width) % _w

        self.stdscr.addstr(y, x, _empty_str[:max_width-1], curses.color_pair(1))

        return [y + 20, x, _str[:_w-2]]

    def clear(self, num, max_height, max_width):
        _w = 30
        _h = 15

        for x in range(20):
            for y in range(2,30):
                _raw_x = x + _w*(num)
                y = y + _h*(math.floor(_raw_x/max_width))
                x = _raw_x - max_width*(math.floor(_raw_x / max_width)) - (_raw_x % max_width) % _w
                
                self.stdscr.delch(y+20,x)


    def update(self, _str, num, flag):
        r.hset('log-'+str(num),flag,_str)

        _str = str(_str)
        # Initialization
        # self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        # self.clear(num, height, width)
        self.stdscr.refresh()

        if self.k == curses.KEY_DOWN:
            self.cursor_y = self.cursor_y + 1
        elif self.k == curses.KEY_UP:
            self.cursor_y = self.cursor_y - 1
        elif self.k == curses.KEY_RIGHT:
            self.cursor_x = self.cursor_x + 1
        elif self.k == curses.KEY_LEFT:
            self.cursor_x = self.cursor_x - 1

        self.cursor_x = max(0, self.cursor_x)
        self.cursor_x = min(width-1, self.cursor_x)

        self.cursor_y = max(0, self.cursor_y)
        self.cursor_y = min(height-1, self.cursor_y)

        # Declaration of strings        
        statusbarstr = "STATUS BAR | Pos: {}, {}".format(self.cursor_x, self.cursor_y)
        
        # Rendering some text
        pos = self.get_pos(num, flag, height, width, _str)
        self.stdscr.addstr(pos[0], pos[1], pos[2], curses.color_pair(1))

        # Render status bar
        self.stdscr.attron(curses.color_pair(3))
        self.stdscr.addstr(height-1, 0, statusbarstr)
        self.stdscr.addstr(height-1, len(statusbarstr), " " * (width - len(statusbarstr) - 1))
        self.stdscr.attroff(curses.color_pair(3))

        # # Turning on attributes for title
        # self.stdscr.attron(curses.color_pair(2))
        # self.stdscr.attron(curses.A_BOLD)

        # # Rendering title
        # self.stdscr.addstr(start_y, start_x_title, title)

        # # Turning off attributes for title
        # self.stdscr.attroff(curses.color_pair(2))
        # self.stdscr.attroff(curses.A_BOLD)

        # Print rest of text
        self.stdscr.move(self.cursor_y, self.cursor_x)

        # Refresh the screen
        self.stdscr.refresh()

        # Wait for next input
        # self.k = self.stdscr.getch()

    


def main():
    curses.wrapper(draw_menu)

if __name__ == "__main__":
    main()