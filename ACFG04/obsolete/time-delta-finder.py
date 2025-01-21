import datetime
import re
import sys

pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}'
t1 = None
t2 = None

with open('out.log', 'w') as outf:
    with open(sys.argv[1], 'r') as f:
        for line in f:
            match = re.search(pattern, line)[0]
            t2 = datetime.datetime.strptime(match, "%Y-%m-%d %H:%M:%S,%f")
            if t1 is None:
                t1 = t2
            delta = (t2 - t1).total_seconds()
            # print(f"[+] Delta is :{t2} - {t1} == {delta}")
            if delta > 5:
                print(f"[+] Delta is :{t2} - {t1} == {delta}")
                outf.write(f"[+] Delta is :{t2} - {t1} == {delta}\n")
            t1 = t2