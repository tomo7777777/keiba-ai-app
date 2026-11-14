import pandas as pd, numpy as np
exec(open('ana_split.py').read().split("print(line('全体',O))")[0])
def ex(g,r,p):
    top=g[r].sort_values(ascending=False).iloc[:3].sum(); return (g[r].sum()-top)/(g[p].sum()*100 if p!='one' else len(g)*100)*100
ndays=O.race_id.str[:4].nunique()
for th in [0.785,0.79,0.794,0.797,0.80,0.81,0.82,0.85]:
    g=O[O.winev>=th]; print(line(f'winev>={th}',g), f" 除3 ワ{ex(g,'w_ret','w_pts'):.0f} 3単{ex(g,'t_ret','t_pts'):.0f}  1日{len(g)/364:.1f}R")
for th in [0.794,0.80]:
  for c,cond in [('pop>=6',O['pop']>=6),('pop<=6',O['pop']<=6),('ratio>=1.3',O.ratio>=1.3),('n>=11',O.n>=11),('aodds<=40',O.aodds<=40)]:
    g=O[(O.winev>=th)&cond]; print(line(f'winev>={th}&{c}',g), f" 除3 ワ{ex(g,'w_ret','w_pts'):.0f} 3単{ex(g,'t_ret','t_pts'):.0f} 1日{len(g)/364:.1f}R")
print(O.winev.describe(percentiles=[.5,.8,.9,.95]))
