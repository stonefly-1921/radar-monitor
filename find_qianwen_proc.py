import psutil
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'qianwen' in p.info['name'].lower():
            print('PID=%d name=%s' % (p.info['pid'], p.info['name']))
            cmdline = p.info['cmdline']
            if cmdline:
                for arg in cmdline:
                    print('  arg: %s' % arg)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass