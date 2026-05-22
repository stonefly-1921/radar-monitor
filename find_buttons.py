from pywinauto import Application

app = Application(backend='uia').connect(process=21024)
win = app.top_window()
print('Connected to:', win.element_info.name)

def find_all_buttons(elem, depth=0):
    try:
        ctype = elem.element_info.control_type
        if ctype == 'Button':
            name = str(elem.element_info.name or '')
            rect = elem.rectangle()
            print('BUTTON depth=%d: "%s" at (%d,%d)' % (depth, name, rect.x, rect.y))
    except Exception as e:
        print('ERR at depth %d: %s' % (depth, e))
    try:
        for c in elem.children():
            find_all_buttons(c, depth+1)
    except Exception as e:
        print('ERR children: %s' % e)

find_all_buttons(win)
print('Done')