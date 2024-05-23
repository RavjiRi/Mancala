"""
Popup file selector.

This file creates a popup file explorer to select .py files

Author: Ritesh Ravji
"""

from os import getcwd
from tkinter import Tk
from sys import stdout, exit as _exit
from tkinter.filedialog import askopenfile

root = Tk()  # new window
root.withdraw()  # stop empty popup window
root.focus_force()  # focus tkinter window
file = askopenfile(parent=root,
                   initialdir=getcwd()+'/gamemodes',
                   title='Please select a directory',
                   filetypes=[("Python files", ".py")])

root.destroy()
stdout.write(file.name)  # write to stdin
stdout.flush()
file.close()
_exit(0)
