from pywinauto import Application

# Try connecting differently
app = Application(backend='uia')
app.connect(process=21024)
print('Connected, process:', 21024)

# Try accessing the main window
try:
    win = app.window(title='千问')
    print('Window found:', win.element_info.name)
except:
    print('Window() failed')

# Try top_window()
try:
    win2 = app.top_window()
    print('top_window:', win2.element_info.name, win2.element_info.rectangle)
except Exception as e:
    print('top_window failed:', e)

# Try direct handle
try:
    from pywinauto import Application
    app2 = Application(backend='uia').connect(hwnd=133298)
    win3 = app2.top_window()
    print('direct hwnd:', win3.element_info.name)
except Exception as e:
    print('direct hwnd failed:', e)