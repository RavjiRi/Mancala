import tkinter
import tkinter.filedialog
import sys, os

root = tkinter.Tk()
root.withdraw() # stop empty popup window
root.focus_force()
file = tkinter.filedialog.askopenfile(parent=root, initialdir=os.getcwd()+'/gamemodes',
            title='Please select a directory', filetypes=[("Python files", ".py")])

root.destroy()
sys.stdout.write(file.name)
sys.stdout.flush()
file.close()
sys.exit(0)
