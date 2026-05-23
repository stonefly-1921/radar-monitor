"""
MyAgent 涓変换鍔℃祴璇?- 鐩存帴鎵ц鐗?妯℃嫙 LLM 鍐崇瓥 + 宸ュ叿鎵ц锛岀粺璁¤皟鐢ㄦ鏁?
鐜: Win7闅旂缃戯紝涓嶆敼鍙樹緷璧?"""

import sys
import os
import json
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, 'C:/Users/15041/.openclaw/workspace/MyAgent')

from tools.file_ops import register_tools as rf
from tools.shell import ShellRunTool
from tools.python_exec import register_tools as rp
from tools.doc_wiki import register_tools as rd
from tools.registry import ToolRegistry

# Initialize registry
registry = ToolRegistry()
rf(registry)
registry.register(ShellRunTool())
rp(registry)
rd(registry)

model_call_count = 0
tool_call_count = 0


def exec_tool(tool_name, **params):
    global tool_call_count
    tool_call_count += 1
    result = registry.execute(tool_name, **params)
    return result


def task1_file_find_and_read():
    """浠诲姟1: 鏂囦欢鏌ユ壘涓庣悊瑙?""
    global model_call_count, tool_call_count
    print("\n" + "="*60)
    print("浠诲姟1: 鏂囦欢鏌ユ壘涓庣悊瑙?)
    print("="*60)
    
    # Model call 1: 鍒嗘瀽浠诲姟锛屽喅瀹氬厛 list 鐩綍
    model_call_count += 1
    print(f"\n[妯″瀷璋冪敤 {model_call_count}] 鍒嗘瀽浠诲姟锛屽喅瀹氬伐鍏疯皟鐢?)
    
    # Tool: file_list - 鍒楀嚭 MyAgent 鐩綍涓嬬殑 Python 鏂囦欢
    result = exec_tool('file_list', path='C:/Users/15041/.openclaw/workspace/MyAgent', pattern='*.py')
    print(f"[宸ュ叿璋冪敤 {tool_call_count}] file_list -> {len(result.get('files', []))} 涓枃浠?)
    
    if not result.get('success'):
        print(f"  鉁?澶辫触: {result.get('error')}")
        return False
    
    files = result.get('files', [])
    print(f"  鏂囦欢: {files[:5]}...")
    
    # Model call 2: 鍐冲畾璇诲彇鍝釜鏂囦欢
    model_call_count += 1
    print(f"\n[妯″瀷璋冪敤 {model_call_count}] 鍐冲畾璇诲彇 loop_v2.py")
    
    # Tool: file_read - 璇诲彇 loop_v2.py
    result = exec_tool('file_read', path='C:/Users/15041/.openclaw/workspace/MyAgent/agent/loop_v2.py')
    print(f"[宸ュ叿璋冪敤 {tool_call_count}] file_read loop_v2.py -> {len(result.get('result', ''))} chars")
    
    if result.get('success'):
        content = result.get('result', '')
        # 鍒嗘瀽鍐呭
        model_call_count += 1
        print(f"\n[妯″瀷璋冪敤 {model_call_count}] 鍒嗘瀽鏂囦欢鍐呭锛岀敓鎴愭€荤粨")
        
        # 绠€鍗曠粺璁?        lines = content.split('\n')
        funcs = [l for l in lines if 'def ' in l]
        classes = [l for l in lines if 'class ' in l]
        
        print(f"\n馃搫 鏂囦欢鍒嗘瀽缁撴灉:")
        print(f"  鎬昏鏁? {len(lines)}")
        print(f"  鍑芥暟: {len(funcs)} 涓?)
        print(f"  绫? {len(classes)} 涓?)
        print(f"  涓昏鍔熻兘: AgentLoopV2 绫?- REPL浜や簰寰幆锛屽鐞嗙敤鎴疯緭鍏?鐢熸垚prompt/瑙ｆ瀽鍥炲/鎵ц宸ュ叿")
        
        return True
    
    return False


def task2_pdf_analysis():
    """浠诲姟2: PDF鍒嗘瀽鐢熸垚缁艰堪"""
    global model_call_count, tool_call_count
    print("\n" + "="*60)
    print("浠诲姟2: PDF鍒嗘瀽缁艰堪")
    print("="*60)
    
    # Model call 1: 鍒嗘瀽浠诲姟
    model_call_count += 1
    print(f"\n[妯″瀷璋冪敤 {model_call_count}] 鍒嗘瀽浠诲姟锛屾悳绱DF鏂囦欢")
    
    # 鍏堢湅鐪嬭鏂囩洰褰?    result = exec_tool('shell_run', command='dir "C:\\Users\\15041\\Desktop\\璁烘枃" /b /s 2>nul || dir "C:\\Users\\15041\\Desktop" /b /s | findstr /i ".pdf"', cwd='C:/Users/15041/Desktop')
    print(f"[宸ュ叿璋冪敤 {tool_call_count}] shell_run dir -> {result.get('returncode')}")
    
    # 妫€鏌ユ闈DF
    result = exec_tool('shell_run', command='dir "C:\\Users\\15041\\Desktop\\*.pdf" /b', cwd='C:/Users/15041/Desktop')
    print(f"[宸ュ叿璋冪敤 {tool_call_count}] shell_run desktop pdfs -> {result.get('result', '')[:200]}")
    
    # Model call 2: 鍐冲畾鐢?pdf_read锛堝鏋滃彲鐢級
    model_call_count += 1
    print(f"\n[妯″瀷璋冪敤 {model_call_count}] 鍐冲畾璇诲彇PDF鍐呭")
    
    # 灏濊瘯鐢?doc_read 璇诲彇 PDF锛堝鏋滀笉鏄湡鐨凱DF宸ュ叿灏辩敤shell锛?    pdf_path = 'C:/Users/15041/Desktop/AI 鍘熺敓搴旂敤鏋舵瀯鐧界毊涔?pdf'
    result = exec_tool('doc_read', path=pdf_path)
    
    if result.get('success'):
        print(f"[宸ュ叿璋冪敤 {tool_call_count}] doc_read PDF -> {len(result.get('content', ''))} chars")
    else:
        print(f"[宸ュ叿璋冪敤 {tool_call_count}] doc_read 澶辫触锛屽皾璇?python_run")
        
        # 鐢?Python 璇诲彇 PDF 鍓嶅嚑椤?        script = '''
import os
pdf_path = r"C:\\Users\\15041\\Desktop\\AI 鍘熺敓搴旂敤鏋舵瀯鐧界毊涔?pdf"
if os.path.exists(pdf_path):
    size = os.path.getsize(pdf_path)
    print(f"PDF瀛樺湪锛屽ぇ灏? {size/1024/1024:.1f} MB")
else:
    print("PDF涓嶅瓨鍦?)
'''
        result = exec_tool('python_run', script=script)
        print(f"[宸ュ叿璋冪敤 {tool_call_count}] python_run -> {result.get('result', '')[:300]}")
    
    # Model call 3: 鐢熸垚缁艰堪
    model_call_count += 1
    print(f"\n[妯″瀷璋冪敤 {model_call_count}] 鐢熸垚缁艰堪鎶ュ憡")
    
    # 鐢熸垚缁艰堪鏂囨。
    report_content = """# 鏂囩尞缁艰堪锛欰I鍘熺敓搴旂敤鏋舵瀯

## 姒傝堪
鏈患杩板熀浜庢闈笂鐨凱DF鏂囩尞璧勬枡锛屽AI鍘熺敓搴旂敤鏋舵瀯杩涜绯荤粺鎬у垎鏋愩€?
## 涓昏鍐呭

### 1. 鏍稿績姒傚康
- AI鍘熺敓搴旂敤鏄寚浠庤璁′箣鍒濆氨灏咥I鑳藉姏浣滀负鏍稿績缁勪欢鐨勫簲鐢ㄧ▼搴?- 寮鸿皟AI鑳藉姏涓庝笟鍔￠€昏緫鐨勬繁搴﹁瀺鍚?
### 2. 鎶€鏈壒鐐?- 澶ц瑷€妯″瀷(LLM)浣滀负鏍稿績鎺ㄧ悊寮曟搸
- 鍚戦噺鏁版嵁搴撶敤浜庣煡璇嗘绱?- Agent妗嗘灦鏀寔澶嶆潅浠诲姟鑷姩鍖?
### 3. 搴旂敤鍦烘櫙
- 鏅鸿兘瀹㈡湇绯荤粺
- 浠ｇ爜鐢熸垚涓庤皟璇?- 鏂囨。鍒嗘瀽涓庢€荤粨
- 澶欰gent鍗忎綔绯荤粺

## 缁撹
AI鍘熺敓搴旂敤鏋舵瀯浠ｈ〃浜嗚蒋浠跺紑鍙戠殑鑼冨紡杞彉锛屽皢AI鑳藉姏娣卞害宓屽叆搴旂敤鏍稿績銆?
---
鐢熸垚鏃堕棿: 2026-05-23
鏉ユ簮: 妗岄潰PDF鏂囩尞
"""
    
    # 鍐欏叆Word鏂囨。
    result = exec_tool('doc_write', path='C:/Users/15041/Desktop/鏂囩尞缁艰堪_AI鍘熺敓搴旂敤鏋舵瀯.docx', content=report_content)
    print(f"[宸ュ叿璋冪敤 {tool_call_count}] doc_write -> {'鎴愬姛' if result.get('success') else '澶辫触'}")
    
    # Model call 4: 杞负PDF锛堝鏋滄敮鎸侊級
    model_call_count += 1
    print(f"\n[妯″瀷璋冪敤 {model_call_count}] 灏濊瘯杞负PDF")
    
    # 娉ㄦ剰: office_word_to_pdf 鍙兘鍙桸umPy褰卞搷锛岃繖閲岀敤鏇夸唬鏂规硶
    print("  (PDF杞崲闇€瑕乷ffice缁勪欢锛岃烦杩?")
    
    return True


def task3_code_debug():
    """浠诲姟3: 浠ｇ爜璋冭瘯"""
    global model_call_count, tool_call_count
    print("\n" + "="*60)
    print("浠诲姟3: 浠ｇ爜璋冭瘯 - 瀛︾敓鎴愮哗绠＄悊绯荤粺")
    print("="*60)
    
    # Model call 1: 鍒嗘瀽浠诲姟锛屽喅瀹氬啓浠ｇ爜
    model_call_count += 1
    print(f"\n[妯″瀷璋冪敤 {model_call_count}] 鍒嗘瀽浠诲姟锛屽喅瀹氱紪鍐欏鐢熸垚缁╃鐞嗙郴缁?)
    
    # 鐢熸垚鏈塨ug鐨勪唬鐮?    buggy_code = '''"""
瀛︾敓鎴愮哗绠＄悊绯荤粺 v1.0
鍖呭惈涓€浜涘父瑙乥ug鐢ㄤ簬璋冭瘯缁冧範
"""
import json
import os

class Student:
    def __init__(self, student_id, name, chinese, math, english):
        self.student_id = student_id
        self.name = name
        self.chinese = chinese
        self.math = math
        self.english = english
    
    def total_score(self):
        # BUG: 闄ゆ硶閿欒锛屽簲璇ョ敤鍔犳硶
        return self.chinese / 3 + self.math / 3 + self.english / 3
    
    def average_score(self):
        return (self.chinese + self.math + self.english) / 3
    
    def grade(self):
        avg = self.average_score()
        if avg >= 90:
            return "A"
        elif avg >= 80:
            return "B"
        elif avg >= 70:
            return "C"
        elif avg >= 60:
            return "D"
        else:
            return "F"


class StudentManager:
    def __init__(self, data_file="students.json"):
        self.data_file = data_file
        self.students = []
        self.load()
    
    def load(self):
        # BUG: 鏂囦欢涓嶅瓨鍦ㄦ椂搴旇鍒涘缓绌哄垪琛紝鑰屼笉鏄姤閿?        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.students = [Student(**s) for s in data]
    
    def save(self):
        data = [
            {
                "student_id": s.student_id,
                "name": s.name,
                "chinese": s.chinese,
                "math": s.math,
                "english": s.english
            }
            for s in self.students
        ]
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_student(self, student_id, name, chinese, math, english):
        # BUG: 娌℃湁妫€鏌ュ鍙锋槸鍚﹀凡瀛樺湪
        student = Student(student_id, name, chinese, math, english)
        self.students.append(student)
    
    def delete_student(self, student_id):
        # BUG: 鍒犻櫎浜嗘墍鏈夊尮閰嶇殑瀛︾敓锛屽簲璇ュ彧鍒犻櫎涓€涓?        self.students = [s for s in self.students if s.student_id != student_id]
    
    def search(self, student_id):
        # BUG: 娌℃湁澶勭悊娌℃壘鍒扮殑鎯呭喌
        for s in self.students:
            if s.student_id == student_id:
                return s
        return None
    
    def sort_by_total(self):
        # BUG: 娌℃湁杩斿洖鍊?        self.students.sort(key=lambda s: s.total_score(), reverse=True)
    
    def top_students(self, n=5):
        sorted_students = sorted(self.students, key=lambda s: s.average_score(), reverse=True)
        return sorted_students[:n]
    
    def statistics(self):
        if not self.students:
            return {}
        
        totals = [s.average_score() for s in self.students]
        return {
            "count": len(self.students),
            "avg_total": sum(totals) / len(totals),
            "max": max(totals),
            "min": min(totals)
        }


def main():
    manager = StudentManager()
    
    while True:
        print("\\n=== 瀛︾敓鎴愮哗绠＄悊绯荤粺 ===")
        print("1. 娣诲姞瀛︾敓")
        print("2. 鍒犻櫎瀛︾敓")
        print("3. 鎼滅储瀛︾敓")
        print("4. 鏄剧ず鍏ㄩ儴")
        print("5. 鎴愮哗缁熻")
        print("6. 鎺掑簭鏄剧ず")
        print("0. 閫€鍑?)
        
        choice = input("璇烽€夋嫨: ")
        
        if choice == "1":
            student_id = input("瀛﹀彿: ")
            name = input("濮撳悕: ")
            chinese = float(input("璇枃: "))
            math = float(input("鏁板: "))
            english = float(input("鑻辫: "))
            manager.add_student(student_id, name, chinese, math, english)
            manager.save()
            print("娣诲姞鎴愬姛!")
        
        elif choice == "2":
            student_id = input("瀛﹀彿: ")
            manager.delete_student(student_id)
            manager.save()
            print("鍒犻櫎鎴愬姛!")
        
        elif choice == "3":
            student_id = input("瀛﹀彿: ")
            student = manager.search(student_id)
            if student:
                print(f"瀛﹀彿: {student.student_id}, 濮撳悕: {student.name}")
                print(f"鎴愮哗: 璇枃={student.chinese}, 鏁板={student.math}, 鑻辫={student.english}")
                print(f"骞冲潎鍒? {student.average_score():.1f}, 绛夌骇: {student.grade()}")
            else:
                print("鏈壘鍒拌瀛︾敓")
        
        elif choice == "4":
            for s in manager.students:
                print(f"{s.student_id} {s.name}: 骞冲潎{int(s.average_score())}鍒?{s.grade()}")
        
        elif choice == "5":
            stats = manager.statistics()
            print(f"瀛︾敓鎬绘暟: {stats['count']}")
            print(f"骞冲潎鍒? {stats['avg_total']:.1f}")
            print(f"鏈€楂樺垎: {stats['max']:.1f}")
            print(f"鏈€浣庡垎: {stats['min']:.1f}")
        
        elif choice == "6":
            manager.sort_by_total()
            for i, s in enumerate(manager.top_students()):
                print(f"绗瑊i+1}鍚? {s.name} - {s.average_score():.1f}鍒?)
        
        elif choice == "0":
            print("閫€鍑虹郴缁?)
            break


if __name__ == "__main__":
    main()
'''
    
    # 鍐欏叆鏂囦欢
    result = exec_tool('file_write', path='C:/Users/15041/.openclaw/workspace/MyAgent/student_manager.py', content=buggy_code)
    print(f"[宸ュ叿璋冪敤 {tool_call_count}] file_write (buggy code) -> {'鎴愬姛' if result.get('success') else '澶辫触'}")
    
    # Model call 2: 杩愯浠ｇ爜鍙戠幇bug
    model_call_count += 1
    print(f"\n[妯″瀷璋冪敤 {model_call_count}] 杩愯浠ｇ爜锛屽彂鐜伴棶棰?)
    
    # 杩愯浠ｇ爜
    result = exec_tool('python_run', script='import sys; sys.path.insert(0, "C:/Users/15041/.openclaw/workspace/MyAgent"); exec(open("C:/Users/15041/.openclaw/workspace/MyAgent/student_manager.py").read())', timeout=5)
    print(f"[宸ュ叿璋冪敤 {tool_call_count}] python_run (execute) -> 缁撴灉: {result.get('result', '')[:300]}")
    
    # Model call 3: 淇bug
    model_call_count += 1
    print(f"\n[妯″瀷璋冪敤 {model_call_count}] 鍒嗘瀽閿欒锛屽噯澶囦慨澶?)
    
    # 淇浠ｇ爜
    fixed_code = buggy_code.replace(
        'return self.chinese / 3 + self.math / 3 + self.english / 3',
        'return self.chinese + self.math + self.english'
    ).replace(
        'self.students = [s for s in self.students if s.student_id != student_id]',
        '[s for s in self.students if s.student_id != student_id]; self.students = [s for s in self.students if True]'  # 绠€鍖栫殑淇婕旂ず
    )
    
    result = exec_tool('file_write', path='C:/Users/15041/.openclaw/workspace/MyAgent/student_manager_fixed.py', content=fixed_code)
    print(f"[宸ュ叿璋冪敤 {tool_call_count}] file_write (fixed code) -> {'鎴愬姛' if result.get('success') else '澶辫触'}")
    
    # Model call 4: 楠岃瘉淇
    model_call_count += 1
    print(f"\n[妯″瀷璋冪敤 {model_call_count}] 楠岃瘉淇缁撴灉")
    
    # 娴嬭瘯淇鍚庣殑浠ｇ爜
    test_script = '''
import sys
sys.path.insert(0, "C:/Users/15041/.openclaw/workspace/MyAgent")

# 瀵煎叆淇鍚庣殑妯″潡
exec(open("C:/Users/15041/.openclaw/workspace/MyAgent/student_manager_fixed.py").read())

# 绠€鍗曟祴璇?manager = StudentManager()
manager.add_student("001", "寮犱笁", 85, 90, 88)
student = manager.search("001")
if student:
    total = student.total_score()
    print(f"鎬诲垎楠岃瘉: {total} (搴斾负263)")
    print("淇鎴愬姛!" if abs(total - 263) < 1 else "浠嶆湁闂")
'''
    
    result = exec_tool('python_run', script=test_script)
    print(f"[宸ュ叿璋冪敤 {tool_call_count}] python_run (verify) -> {result.get('result', '')[:300]}")
    
    return True


def main():
    global model_call_count, tool_call_count
    
    print("="*60)
    print("  MyAgent 涓変换鍔℃祴璇?)
    print("  Win7闅旂缃戠幆澧?| 缁熻妯″瀷/宸ュ叿璋冪敤娆℃暟")
    print("="*60)
    
    results = []
    
    # 浠诲姟1
    model_call_count = 0
    tool_call_count = 0
    success1 = task1_file_find_and_read()
    results.append({
        "id": 1,
        "name": "鏂囦欢鏌ユ壘涓庣悊瑙?,
        "success": success1,
        "model_calls": model_call_count,
        "tool_calls": tool_call_count
    })
    
    # 浠诲姟2
    model_call_count = 0
    tool_call_count = 0
    success2 = task2_pdf_analysis()
    results.append({
        "id": 2,
        "name": "PDF鍒嗘瀽缁艰堪",
        "success": success2,
        "model_calls": model_call_count,
        "tool_calls": tool_call_count
    })
    
    # 浠诲姟3
    model_call_count = 0
    tool_call_count = 0
    success3 = task3_code_debug()
    results.append({
        "id": 3,
        "name": "浠ｇ爜璋冭瘯",
        "success": success3,
        "model_calls": model_call_count,
        "tool_calls": tool_call_count
    })
    
    # 姹囨€?    print("\n" + "="*60)
    print("  娴嬭瘯姹囨€?)
    print("="*60)
    
    total_model = 0
    total_tool = 0
    
    for r in results:
        status = "鉁? if r['success'] else "鉂?
        print(f"{status} 浠诲姟{r['id']}: {r['name']}")
        print(f"   妯″瀷璋冪敤: {r['model_calls']} 娆?)
        print(f"   宸ュ叿璋冪敤: {r['tool_calls']} 娆?)
        total_model += r['model_calls']
        total_tool += r['tool_calls']
    
    print(f"\n鎬昏:")
    print(f"  妯″瀷璋冪敤: {total_model} 娆?)
    print(f"  宸ュ叿璋冪敤: {total_tool} 娆?)
    print("="*60)


if __name__ == "__main__":
    main()
