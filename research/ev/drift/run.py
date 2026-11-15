import sys, pickle, itertools, numpy as np
sys.path.insert(0,'/home/user/workspace/keiba-ai-app/scripts')
import evwide as EVW, myomi as MY
races,WO,PAY,COEF=pickle.load(open('/tmp/sim/base.pkl','rb'))
PAIRS={}
for rid,fold,um,o,b in races:
    I=[];J=[];OF=[]
    for i,j in itertools.combinations(range(len(um)),2):
        of=WO[rid].get(f'{um[i]}-{um[j]}')
        if of and of>1: I.append(i);J.append(j);OF.append(of)
    PAIRS[rid]=(np.array(I,int),np.array(J,int),np.array(OF,float))
SW,SR,SL=0.6,0.415,0.55   # 発走15分前→確定 の実測（地方）：単勝 log 比 sd、ワイド残差 sd、単勝ずれへの連動
def run(scale, seed, hon_th=1.2, ana_th=1.0, minev=1.0, fav_min=2.5):
    rng=np.random.default_rng(seed); out=[]
    for rid,fold,um,o,b in races:
        n=len(um); e=rng.normal(0,SW*scale,n); oe=np.maximum(o*np.exp(-e),1.0)
        q=1/oe; q/=q.sum(); _,m3=MY.harville(q); m3=np.clip(m3,1e-6,1-1e-6)
        p3=1/(1+np.exp(-(np.log(m3/(1-m3))+b))); adj=p3/m3
        _,Wm=EVW.probs(q,0.85,0.75); wa=q*adj; wa/=wa.sum(); _,Wa=EVW.probs(wa,0.85,0.75)
        ic,cf=COEF[fold]; I,Jx,OF=PAIRS[rid]
        ow=np.maximum(OF*np.exp(-(SL*(e[I]+e[Jx])/2+rng.normal(0,SR*scale,len(I)))),1.0)
        lmc=np.log(1/ow); adjp=adj[I]*adj[Jx]
        Xm=np.c_[lmc,np.log(Wm[I,Jx]),np.log(Wa[I,Jx]),np.log(adjp),np.log(np.maximum(adj[I],adj[Jx])),np.log(np.minimum(adj[I],adj[Jx])),np.log(np.minimum(oe[I],oe[Jx])),np.log(np.maximum(oe[I],oe[Jx])),np.full(len(I),np.log(n)),lmc*np.log(adjp)]
        ev=ow/(1+np.exp(-(ic+Xm@cf)))
        tk=[(f'{um[i]}-{um[j]}',v,um[i],um[j]) for i,j,v in zip(I[ev>=minev],Jx[ev>=minev],ev[ev>=minev])]
        if not tk: continue
        sc={}
        for k,ev,a,c in tk: sc[a]=sc.get(a,0)+ev-1; sc[c]=sc.get(c,0)+ev-1
        A={u:adj[t] for t,u in enumerate(um)}; sc={u:v for u,v in sc.items() if A[u]>=1.0}
        if not sc: continue
        J=max(sc,key=sc.get); order=np.argsort(oe); pop=int(np.where(um[order]==J)[0][0])+1
        kind='hon' if pop<=3 else 'ana'
        if kind=='ana' and oe.min()<fav_min: continue
        th=hon_th if kind=='hon' else ana_th
        t=sorted([x for x in tk if J in (x[2],x[3]) and x[1]>=th],key=lambda x:-x[1])[:5]
        if not t: continue
        pay=PAY[rid]; wp={k:v for k,v in pay.get('ワイド',[])}
        wret=sum(wp.get(k,0) for k,*_ in t)
        tret=None; tpts=0
        K=4 if kind=='hon' else 3
        if kind=='hon' or n>=12:
            ai=[u for u in um[np.argsort(-p3)] if u!=J][:K]; tp={k:v for k,v in pay.get('三連単',[])}
            tret=sum(tp.get(f'{J}-{a}-{c}',0) for a,c in itertools.permutations(ai,2)); tpts=K*(K-1)
        out.append((rid,fold,kind,len(t),wret,tpts,tret or 0))
    return out
if __name__=='__main__':
    import pandas as pd
    scale=float(sys.argv[1]); seed=int(sys.argv[2]); extra=dict(a.split('=') for a in sys.argv[3:])
    extra={k:float(v) for k,v in extra.items()}
    O=pd.DataFrame(run(scale,seed,**extra),columns=['race_id','fold','kind','pts','wret','tpts','tret'])
    tag='_'.join([str(scale),str(seed)]+[f'{k}{v}' for k,v in extra.items()])
    O.to_pickle(f'/tmp/sim/o_{tag}.pkl')
    N=len(races)
    for k,g in O.groupby('kind'):
        tt=g[g.tpts>0]
        print(f'{tag} {k}: {len(g)}R ({len(g)/N*100:.1f}%) wide {g.wret.sum()/g.pts.sum()/1:.1f}% hit{(g.wret>0).mean()*100:.0f}% | tan {len(tt)}R {tt.tret.sum()/max(tt.tpts.sum(),1):.1f}%',flush=True)
