"""
MyAgent UI 自动化测试 - 10 个通用任务（增强版）
================================================
新增：文档撰写、表格处理等复杂任务

任务列表：
1. 计算任务 - Python 脚本执行
2. 文件操作 - 列出目录 + 读文件
3. 弹道仿真 - 找 AFSIM 源码 + 计算
4. 代码审查 - 分析 Python 文件
5. Wiki 操作 - 搜索 + 读取页面
6. 文档撰写 - 创建 Markdown 文档
7. 表格处理 - 创建 Excel + 写入数据
8. Shell 命令 - 执行系统命令
9. 多步骤工作流 - 组合工具
10. 综合任务 - 文档 + 表格 + 代码组合

测试文件：run_10_tests.py
测试文档：docs/10_test_cases.md
"""
import time, json, subprocess, urllib.request, os
from pywinauto import Application
import pywinauto.keyboard as kb

MYAGENT_DIR = r'C:\Users\15041\.openclaw\workspace\MyAgent'
IO_DIR = rf'{MYAGENT_DIR}\io'


def get_api_key():
    result = subprocess.run(
        ['powershell', '-Command', "[Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')"],
        capture_output=True, text=True, encoding='utf-8'
    )
    return result.stdout.strip()

API_KEY = ***


# ============ 10 个测试任务（增强版）============

TASKS = [
    {
        'id': 1,
        'name': '计算任务',
        'task': '请用 python_run 工具计算 1+1 等于几，结果直接输出',
        'expected_tools': ['python_run'],
    },
    {
        'id': 2,
        'name': '文件操作',
        'task': '''请完成以下操作：
1. 用 file_list 工具列出 MyAgent 目录下的所有 .py 文件
2. 用 file_read 读取任意一个 .py 文件的前 20 行
3. 统计该文件有多少行代码（用 python_run 执行：打开刚才读取的文件，统计总行数）
4. 输出文件路径和行数''',
        'expected_tools': ['file_list', 'file_read', 'python_run'],
    },
    {
        'id': 3,
        'name': '弹道仿真',
        'task': '''请完成以下弹道计算任务：

1. 用 grep 工具在 MyAgent 目录下搜索包含 "fires" 或 "ballistic" 关键词的 .cpp 或 .py 文件
2. 找到相关文件后，用 file_read 读取内容，找出弹道导弹的关键参数（初速度、射角等）
3. 用 python_run 计算：从北京（经度116.4°E，纬度39.9°N）到台北（经度121.5°E，纬度25°N）的理论弹道，假设初速度 3000m/s，射角 45°
4. 输出弹道参数（飞行时间、最大高度、射程）和最终结果''',
        'expected_tools': ['grep', 'file_read', 'python_run'],
    },
    {
        'id': 4,
        'name': '代码审查',
        'task': '''请完成代码审查任务：
1. 用 file_list 工具列出 MyAgent/agent 目录下的所有 .py 文件
2. 选取任意 2 个 .py 文件，用 file_read 读取完整内容
3. 用 grep 工具搜索每个文件中包含 "def " 的行（函数定义）
4. 用 python_run 统计：每个文件有多少个函数，总共多少个
5. 列出所有函数名及其所在行号''',
        'expected_tools': ['file_list', 'file_read', 'grep', 'python_run'],
    },
    {
        'id': 5,
        'name': 'Wiki 操作',
        'task': '''请完成 Wiki 知识库操作：
1. 用 wiki_search 搜索 "弹道导弹" 相关内容
2. 查看搜索结果，找到至少 2 条相关内容
3. 用 wiki_read 读取其中一条的详细内容
4. 用 python_run 根据读取的内容计算：弹道导弹的典型飞行时间（假设射程 1000km，速度 2km/s）''',
        'expected_tools': ['wiki_search', 'wiki_read', 'python_run'],
    },
    {
        'id': 6,
        'name': '文档撰写',
        'task': '''请完成技术文档撰写任务：
1. 用 python_run 执行以下 Python 代码生成一份测试报告：
```python
report = """
# 弹道导弹仿真测试报告

## 1. 任务概述
本报告记录弹道仿真测试结果。

## 2. 测试数据
- 发射点：北京（116.4°E, 39.9°N）
- 目标点：台北（121.5°E, 25°N）
- 初速度：3000 m/s
- 射角：45°

## 3. 计算结果
- 飞行时间：约 300 秒
- 最大高度：约 230 km
- 射程：约 350 km

## 4. 结论
测试完成，结果符合预期。
'''
print(report)
```

2. 用 file_write 将报告写入 MyAgent/io/test_report.txt
3. 用 file_read 读取验证文件已正确写入''',
        'expected_tools': ['python_run', 'file_write', 'file_read'],
    },
    {
        'id': 7,
        'name': '表格处理',
        'task': '''请完成 Excel 表格创建任务：
1. 用 xlsx_create 工具创建一个新的 Excel 文件，文件名为 "test_data.xlsx"
2. 用 xlsx_write 工具写入以下数据：
   - Sheet1 工作表
   - 第一行（表头）：姓名, 年龄, 城市, 职业
   - 第二行：张三, 28, 北京, 工程师
   - 第三行：李四, 35, 上海, 设计师
   - 第四行：王五, 42, 深圳, 经理
3. 用 xlsx_read 读取文件验证数据已正确写入''',
        'expected_tools': ['xlsx_create', 'xlsx_write', 'xlsx_read'],
    },
    {
        'id': 8,
        'name': 'Shell 命令',
        'task': '''请完成系统命令执行任务：
1. 用 shell_run 工具执行 "python --version" 命令，查看 Python 版本
2. 用 shell_run 执行 "dir C:\\Users\\15041\\.openclaw\\workspace\\MyAgent" 查看目录内容
3. 用 shell_run 执行 "powershell -Command \\"Get-Date\\"" 获取当前系统时间
4. 综合以上结果，用 python_run 计算：如果每天执行 10 次命令，100 天共执行多少次''',
        'expected_tools': ['shell_run', 'python_run'],
    },
    {
        'id': 9,
        'name': '多步骤工作流',
        'task': '''请完成多步骤自动化工作流：
1. file_list 列出 MyAgent/io 目录内容
2. 统计目录中有多少个 .txt 文件
3. 统计目录中有多少个 .json 文件
4. 用 python_run 计算：.txt 文件数量乘以 10，加上 .json 文件数量乘以 5，总和是多少
5. 输出每个步骤的结果''',
        'expected_tools': ['file_list', 'python_run'],
    },
    {
        'id': 10,
        'name': '综合任务（文档+表格+代码）',
        'task': '''请完成综合任务，包含文档撰写、表格处理和代码执行：

步骤1 - 创建数据表格：
用 xlsx_create 创建 "comprehensive_test.xlsx"
用 xlsx_write 写入：
  表头：项目, 数值, 说明
  第1行：圆周率, 3.14159, 圆周率常量
  第2行：自然对数, 2.71828, 自然常数
  第3行：黄金比例, 1.61803, 黄金分割

步骤2 - 执行计算：
用 python_run 计算：
  - 圆周率乘以半径 10 的平方 (π * 10²)
  - 自然对数乘以 100
  - 黄金比例乘以 50

步骤3 - 生成报告：
用 python_run 生成 Markdown 格式报告：
```
# 综合测试报告

## 数据表格
已创建 comprehensive_test.xlsx，包含 3 行数据。

## 计算结果
- π × 10² = [计算结果]
- e × 100 = [计算结果]
- φ × 50 = [计算结果]

## 结论
综合测试完成，所有计算结果已验证。
```

步骤4 - 保存报告：
用 file_write 将报告写入 MyAgent/io/comprehensive_report.txt

步骤5 - 验证：
用 file_read 读取报告内容，确认所有数据正确''',
        'expected_tools': ['xlsx_create', 'xlsx_write', 'python_run', 'file_write', 'file_read'],
    },
]


# ============ UI 自动化函数 ============

def find_myagent():
    from pywinauto import findwindows
    windows = findwindows.find_windows(title_re='MyAgent.*')
    return windows[0] if windows else None


def connect_ui():
    hwnd = find_myagent()
    if not hwnd:
        return None
    app = Application(backend='win32').connect(handle=hwnd)
    return app.window(handle=hwnd)


def find_controls_by_pos(win):
    controls = {}
    for c in win.children():
        try:
            r = c.rectangle()
            x, y = r.left, r.top
            if 200 < x < 300 and 200 < y < 300:
                controls['task_input'] = c
            elif 200 < x < 300 and 340 < y < 380:
                controls['start_btn'] = c
            elif 900 < x < 1100 and 900 < y < 1050:
                controls['response_input'] = c
            elif 900 < x < 1100 and 1550 < y < 1620:
                controls['submit_btn'] = c
        except:
            pass
    return controls


def ui_paste(ctrl, text):
    ctrl.click_input()
    time.sleep(0.3)
    kb.send_keys('^a')
    time.sleep(0.1)
    kb.send_keys('{DELETE}')
    for i in range(0, len(text), 500):
        try:
            subprocess.run(
                ['powershell', '-Command', f'Set-Clipboard -Value "{text[i:i+500]}"'],
                capture_output=True, timeout=5
            )
        except:
            pass
        time.sleep(0.3)
        kb.send_keys('^v')
        time.sleep(0.3)


def click_btn(ctrl):
    ctrl.click_input()


def call_llm(prompt_text):
    url = 'https://api.minimaxi.com/anthropic/v1/messages'
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01',
    }
    payload = {
        'model': 'MiniMax-M2.7',
        'messages': [{'role': 'user', 'content': prompt_text}],
        'max_tokens': 8192,
        'temperature': 0.7
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        for item in result.get('content', []):
            if item.get('type') == 'text':
                text = item.get('text', '').strip()
                if text:
                    try:
                        return json.loads(text)
                    except:
                        return {'action': 'final', 'answer': text}


def clean_io():
    for f in ['input.txt', 'response.txt', 'tool_result.json', 'final_answer.txt']:
        p = os.path.join(IO_DIR, f)
        if os.path.exists(p):
            open(p, 'w', encoding='utf-8').write('')


def get_session_final():
    session_file = os.path.join(IO_DIR, 'session.json')
    if os.path.exists(session_file) and os.path.getsize(session_file) > 0:
        try:
            data = json.loads(open(session_file, encoding='utf-8').read())
            turns = data.get('turns', [])
            for turn in reversed(turns):
                if 'final_answer' in turn and turn['final_answer']:
                    return turn['final_answer']
        except:
            pass
    return None


def wait_for_final_answer(old_session_size, timeout=30):
    session_file = os.path.join(IO_DIR, 'session.json')
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(session_file):
            size = os.path.getsize(session_file)
            if size > old_session_size:
                final = get_session_final()
                if final:
                    return final
        time.sleep(0.5)
    return None


# ============ 单任务执行 ============

def run_single_task(task_info, win, controls, max_turns=10):
    task_id = task_info['id']
    task_name = task_info['name']
    task_text = task_info['task']
    
    print(f'\n{"="*60}')
    print(f'任务 {task_id}/10: {task_name}')
    print(f'{"="*60}')
    
    clean_io()
    
    # 输入任务
    print(f'[输入] 任务到 UI...')
    ui_paste(controls['task_input'], task_text)
    time.sleep(0.5)
    
    # 点击开始
    print(f'[开始] 点击开始任务...')
    click_btn(controls['start_btn'])
    
    # 等待 prompt
    prompt_path = os.path.join(IO_DIR, 'prompt.txt')
    for i in range(20):
        time.sleep(1)
        if os.path.exists(prompt_path) and os.path.getsize(prompt_path) > 100:
            break
    else:
        print(f'  [失败] prompt 生成超时')
        return False
    
    # 多轮循环
    current_prompt = open(prompt_path, encoding='utf-8').read().strip()
    old_session_size = os.path.getsize(os.path.join(IO_DIR, 'session.json')) if os.path.exists(os.path.join(IO_DIR, 'session.json')) else 0
    last_prompt_len = len(current_prompt)
    
    for turn in range(1, max_turns + 1):
        # 调用 LLM
        result = call_llm(current_prompt)
        if not result:
            print(f'  [失败] LLM 调用失败 Turn {turn}')
            return False
        
        action = result.get('action', '?')
        response_json = json.dumps(result, ensure_ascii=False)
        
        # 写 response.txt
        open(os.path.join(IO_DIR, 'response.txt'), 'w', encoding='utf-8').write(response_json)
        
        # 粘贴到 UI
        ui_paste(controls['response_input'], response_json)
        time.sleep(0.3)
        
        # 点击提交
        click_btn(controls['submit_btn'])
        
        # 等待处理
        time.sleep(6)
        
        # 检查 final_answer
        final = get_session_final()
        if final:
            print(f'  [成功] Turn {turn} 完成')
            display = final[:150].replace('\n', ' ')
            print(f'  结果: {display}...')
            return True
        
        # 等待新 prompt
        new_prompt = ''
        for _ in range(10):
            time.sleep(1)
            if os.path.exists(prompt_path):
                new_prompt = open(prompt_path, encoding='utf-8').read().strip()
                if new_prompt and len(new_prompt) != last_prompt_len:
                    break
        
        if new_prompt and len(new_prompt) != last_prompt_len:
            current_prompt = new_prompt
            last_prompt_len = len(current_prompt)
        else:
            resp_size = os.path.getsize(os.path.join(IO_DIR, 'response.txt')) if os.path.exists(os.path.join(IO_DIR, 'response.txt')) else 0
            if resp_size > 0:
                print(f'  [继续] Turn {turn} response.txt={resp_size}B 未被读取')
            else:
                print(f'  [结束] Turn {turn} 无新 prompt 且 response.txt 已清空')
                break
    
    print(f'  [警告] 达到最大轮次 {max_turns}')
    return False


# ============ 主流程 ============

print('=' * 60)
print('MyAgent UI 自动化测试 - 10 个通用任务（增强版）')
print('=' * 60)

# 连接 UI
print('[连接] MyAgent UI...')
win = connect_ui()
if not win:
    print('  [失败] 未找到 MyAgent UI')
    print('  请先启动 MyAgent UI (python agent/ui.py)')
    exit(1)
print('  连接成功')

controls = find_controls_by_pos(win)
print(f'  找到控件: {list(controls.keys())}')

# 统计
passed = 0
failed = 0
results = []

for i, task_info in enumerate(TASKS):
    ok = run_single_task(task_info, win, controls, max_turns=8)
    if ok:
        passed += 1
        results.append(f'✓ 任务{i+1}: {task_info["name"]}')
    else:
        failed += 1
        results.append(f'✗ 任务{i+1}: {task_info["name"]}')

print('\n' + '=' * 60)
print('测试报告')
print('=' * 60)
for r in results:
    print(f'  {r}')
print(f'\n通过: {passed}/10, 失败: {failed}/10')

if passed == 10:
    print('\n🎉 全部通过！')
elif passed >= 7:
    print('\n✅ 大部分通过')
else:
    print('\n⚠️ 需要进一步调试')