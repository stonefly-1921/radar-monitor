"""找 MyAgent 窗口"""
from pywinauto import findwindows

# 找所有 python 进程相关的窗口
print('[所有 python 窗口]')
windows = findwindows.find_windows(process=28112)
for w in windows:
    print(f'  {w}')

print('\n[尝试用 class_name 找]')
windows = findwindows.find_windows(class_name='TkTopLevel')
for w in windows:
    print(f'  {w}')

print('\n[尝试用 title 模糊匹配]')
windows = findwindows.find_windows(title_re='MyAgent.*')
for w in windows:
    print(f'  {w}')