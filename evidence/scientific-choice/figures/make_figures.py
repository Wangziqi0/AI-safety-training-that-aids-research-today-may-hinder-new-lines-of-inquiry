"""Render the three Article figures from their portable companion CSV tables."""
import argparse
import csv
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np

WIDTH = 180 / 25.4
BLUE = "#246885"
ORANGE = "#AB542D"
DARK = "#202C33"
MIDDLE = "#526570"
LIGHT = "#CED8DB"
FAINT = "#E9EFF0"
BLACK = "#22282C"

mpl.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 7.5, "axes.labelsize": 7.5,
    "font.sans-serif": ["DejaVu Sans"], "mathtext.default": "regular",
    "axes.labelcolor": BLACK, "text.color": BLACK, "xtick.color": BLACK,
    "ytick.color": BLACK, "axes.edgecolor": MIDDLE, "axes.linewidth": 0.55,
    "xtick.major.size": 2.2, "ytick.major.size": 2.2, "xtick.major.width": 0.55,
    "ytick.major.width": 0.55, "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False, "legend.fontsize": 6.5, "legend.handlelength": 1.4,
    "legend.handletextpad": 0.45, "legend.columnspacing": 1.0, "legend.borderpad": 0,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
})


def table(directory, number):
    with (directory / f"fig{number}_source.csv").open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def heading(fig, x, y, letter, text):
    fig.text(x,y,letter,weight="bold",size=10,va="top",ha="left")
    fig.text(x+.034,y-.002,text,weight="bold",size=8.5,va="top",ha="left")


def export(fig, number, out):
    fig.savefig(out / f"fig{number}.pdf",metadata={"Title":f"Figure {number}"})
    fig.savefig(out / f"fig{number}.svg")
    fig.savefig(out / f"fig{number}.png",dpi=300)
    plt.close(fig)


def interval(rows, algo, mapping, metric):
    group=[r for r in rows if r["kind"]=="paired_seed_delta" and r["algorithm"]==algo
           and r["mapping"]==mapping and r["metric"]==metric]
    assert len(group)==len({r["seed"] for r in group})==24
    d=np.array([100*float(r["numerator"])/float(r["denominator"]) for r in group])
    return d.mean(),2.06866*d.std(ddof=1)/np.sqrt(len(d))


def figures_one(rows, out):
    fig=plt.figure(figsize=(WIDTH,4.40))
    heading(fig,.035,.965,"a","Protection and scientific work")
    heading(fig,.525,.965,"b","Current and later outcomes, by project")
    heading(fig,.035,.438,"c","Current calibration under each connection")
    heading(fig,.525,.438,"d","Later measurement under each connection")
    a=fig.add_axes([.189,.645,.274,.218])
    a.axvline(0,color=LIGHT,lw=.85,zorder=0)
    variables=["disclosure","current","later"]; algo_style=[("sft",BLUE,"o",.11),("reinforce",ORANGE,"^",-.11)]
    for algo,color,marker,jitter in algo_style:
        for i,metric in enumerate(variables):
            value,error=interval(rows,algo,"service" if metric=="disclosure" else "aligned",metric)
            a.errorbar(value,2-i+jitter,xerr=error,fmt=marker,color=color,ms=4.1,
                       markeredgewidth=.55,lw=.9,capsize=2)
    a.set(ylim=(-.42,2.42),xlim=(-55,20),xticks=[-50,-25,0,15],
          yticks=[2,1,0],yticklabels=["Restricted disclosure","Current calibration","Later measurement"],
          xlabel="A − H (percentage points)")
    a.tick_params(axis="y",length=0,pad=4)
    keys=[Line2D([],[],marker="o",color=BLUE,ls="none",ms=4,label="Supervised training"),
          Line2D([],[],marker="^",color=ORANGE,ls="none",ms=4,label="Online reinforcement learning")]
    fig.legend(handles=keys,loc="center left",bbox_to_anchor=(.049,.526),
               ncol=2,fontsize=6.6)
    b=fig.add_axes([.694,.616,.253,.278])
    for yi,cur in enumerate([1,0,-1]):
        for xi,late in enumerate([-1,0,1]):
            r=next(r for r in rows if r["kind"]=="contingency" and r["algorithm"]=="sft"
                   and int(r["change_current"])==cur and int(r["change_later"])==late)
            joint=cur==1 and late==-1
            b.add_patch(Rectangle((xi-.5,yi-.5),1,1,facecolor=BLUE if joint else FAINT,
                                  edgecolor="white",linewidth=2))
            b.text(xi,yi,f'{int(r["numerator"]):,}',ha="center",va="center",
                   color="white" if joint else DARK,weight="bold" if joint else "normal",size=8.2)
    b.set(xlim=(-.5,2.5),ylim=(2.5,-.5),xticks=[0,1,2],xticklabels=["Loss","Tie","Gain"],
          yticks=[0,1,2],yticklabels=["Gain","Tie","Loss"],xlabel="Later change",ylabel="Current change")
    b.tick_params(length=0,pad=3)
    for spine in b.spines.values():spine.set_visible(False)
    mappings=["reversed","cut","aligned"]
    for x,metric in [(.124,"current"),(.618,"later")]:
        ax=fig.add_axes([x,.126,.309,.237]);ax.axhline(0,lw=.75,color=LIGHT,zorder=0)
        for algo,color,marker,unused in algo_style:
            means,errors=zip(*(interval(rows,algo,mapping,metric) for mapping in mappings))
            pos=np.arange(3)+(-.065 if algo=="sft" else .065)
            ax.errorbar(pos,means,yerr=errors,fmt=marker,color=color,ms=4.2,markeredgewidth=.55,
                        lw=.9,capsize=2.2)
        ax.set(xlim=(-.35,2.35),xticks=[0,1,2],xticklabels=["Reversed","Cut","Positive"],
               ylim=(-18,18),yticks=[-15,0,15],ylabel="A − H (points)")
    export(fig,1,out)


def figures_two(rows, out):
    fig=plt.figure(figsize=(WIDTH,4.50))
    heading(fig,.035,.967,"a","Two worlds share the same observations")
    heading(fig,.530,.967,"b","How many projects link all events?")
    heading(fig,.035,.445,"c","Does the same direction count?")
    heading(fig,.530,.445,"d","Forecasting a 1.5B weight displacement")
    a=fig.add_axes([.164,.601,.294,.267])
    metrics=["protected","current","later_success","used"]
    regimes=[("H","ineligible"),("A","natural"),("A","offered")]
    for yi,metric in enumerate(metrics):
        for xi,(group,condition) in enumerate(regimes):
            q=next(r for r in rows if r["panel"]=="a" and r["metric"]==metric and
                   r["group"]==group and r["condition"]==condition)
            value=int(q["value"]); color=mpl.colors.to_rgba(BLUE,alpha=.08+.55*value/8)
            a.add_patch(Rectangle((xi-.5,yi-.5),1,1,facecolor=color,edgecolor="white",linewidth=2))
            a.text(xi,yi,str(value),va="center",ha="center",weight="bold",fontsize=8.1)
    a.set(xlim=(-.5,2.5),ylim=(3.5,-.5),xticks=[0,1,2],xticklabels=["H ordinary","A ordinary","A + offer"],
          yticks=range(4),yticklabels=["Protected","Current use","Later success","Direction used"])
    a.tick_params(length=0,pad=2.8,labelsize=7)
    for spine in a.spines.values():spine.set_visible(False)
    a.set_xlabel("Projects per regime (out of 8)",labelpad=5)
    b=fig.add_axes([.653,.643,.300,.166])
    for j,group in enumerate(["world_I","world_II"]):
        r=next(r for r in rows if r["panel"]=="b" and r["group"]==group)
        val,total=int(r["value"]),int(r["total"]); y=1-j
        for i in range(total):
            b.scatter(i,y,s=37,marker="o",facecolor=BLUE if i<val else "white",
                      edgecolor=BLUE if i<val else MIDDLE,linewidth=.7)
        b.text(8.1,y,f"{val}/{total}",ha="left",va="center",size=7.5,weight="bold")
    b.set(xlim=(-.45,9.5),ylim=(-.45,1.45),xticks=[],yticks=[1,0],yticklabels=["World I","World II"])
    b.tick_params(length=0,pad=4)
    for spine in b.spines.values():spine.set_visible(False)
    b.set_xlabel("Each circle counts one project",labelpad=8)
    c=fig.add_axes([.169,.127,.290,.202])
    for y,metric in [(1,"sharp"),(0,"identity_ignored")]:
        r=next(r for r in rows if r["panel"]=="c" and r["metric"]==metric)
        lo,hi=[int(r[key]) for key in ("low","high")]
        color=BLUE if metric=="sharp" else MIDDLE
        c.plot([lo,hi],[y,y],color=color,lw=2.6,solid_capstyle="round")
        c.scatter([lo,hi],[y,y],s=19,color=color)
        c.text((lo+hi)/2,y+.14,f"{lo}–{hi}",ha="center",va="bottom",fontsize=7.5)
    c.set(xlim=(0,20),ylim=(-.35,1.56),yticks=[1,0],yticklabels=["Matched direction","Identity omitted"],
          xticks=[0,5,10,15,20],xlabel="Possible linked projects (out of 20)")
    c.tick_params(axis="y",length=0,pad=4)
    d=fig.add_axes([.695,.120,.256,.226])
    order=[("local",.25),("local",1),("transfer",.25),("transfer",1)]
    labels=["Local, ¼ dose","Local, full","Transfer, ¼ dose","Transfer, full"]
    for yi,(method,dose) in enumerate(order):
        left=0
        for metric,color in [("agreed",BLUE),("missed",ORANGE),("abstained",LIGHT)]:
            r=next(r for r in rows if r["panel"]=="d" and r["group"]==method
                   and float(r["condition"])==dose and r["metric"]==metric)
            v=int(r["value"]);y=3-yi
            d.barh(y,v,left=left,color=color,height=.66)
            d.text(left+v/2,y,str(v),ha="center",va="center",size=6.6,
                   color="white" if metric!="abstained" else DARK)
            left+=v
        assert left==35
    d.set(xlim=(0,35),ylim=(-.55,3.55),xticks=[0,10,20,30,35],yticks=[3,2,1,0],yticklabels=labels,
          xlabel="Endpoint × training stream")
    d.tick_params(axis="y",length=0,pad=3,labelsize=7)
    key=[Rectangle((0,0),1,1,facecolor=c,label=s) for s,c in
         [("Agreed",BLUE),("Missed",ORANGE),("Abstained",LIGHT)]]
    fig.legend(handles=key,loc="center",bbox_to_anchor=(.773,.030),ncol=3,fontsize=6.4)
    export(fig,2,out)


def split_line(time, values):
    """Keep unobserved gaps visually distinct from observed time spans."""
    gap=np.where(np.diff(time)>.15)[0]+1
    return np.insert(time,gap,np.nan),np.insert(values,gap,np.nan)


def figures_three(rows, out):
    fig=plt.figure(figsize=(WIDTH,4.95))
    heading(fig,.035,.967,"a","Forecasting PG 1520+525")
    heading(fig,.526,.967,"b","What the ordinary chain recovered")
    heading(fig,.035,.441,"c","Assignments and resulting measurements")
    heading(fig,.526,.441,"d","What a transmitted period contributed")
    a=fig.add_axes([.108,.648,.360,.231])
    observations=[r for r in rows if r["panel"]=="a"]
    time=np.array([float(r["time_day"]) for r in observations])
    time=time-time[0]; assert len(time)==98 and np.all(np.diff(time)>0)
    light=np.array([float(r["observed_e_s"]) for r in observations])
    a.scatter(time,light,s=5,facecolor=MIDDLE,edgecolor="none",label="Observed flux",zorder=1)
    for var,color,label,style in [("constant_e_s",DARK,"Constant",":"),
                                  ("downstream_only_e_s",ORANGE,"Receiver alone","--"),
                                  ("all_channel_e_s",BLUE,"With early period","-")]:
        values=np.array([float(r[var]) for r in observations])
        x,y=split_line(time,values)
        error=np.mean(np.abs(values-light))
        a.plot(x,y,color=color,lw=1,ls=style,label=f"{label} ({error:.3f})")
    a.set(ylabel="Flux (electrons/s)",xlabel="Days since first held-out hour")
    a.margins(x=.02,y=.09); a.tick_params(labelsize=7)
    handles,labels=a.get_legend_handles_labels()
    fig.legend(handles,labels,loc="center",bbox_to_anchor=(.277,.513),ncol=2,fontsize=6.4,
               title="Mean absolute error (electrons/s)",title_fontsize=6.5,labelspacing=.25)
    b=fig.add_axes([.704,.601,.249,.280])
    fields=sorted({r["field"] for r in rows if r["panel"]=="b"})
    field_names=[]
    for i,field in enumerate(fields):
        data={r["group"]:r for r in rows if r["panel"]=="b" and r["field"]==field}
        field_names.append(data["all_channels"]["label"]);y=7-i
        actual=float(data["all_channels"]["value"])
        for group,color,mark,dy in [("downstream_only",BLUE,"o",.13),("ordinary_chain",ORANGE,"x",-.13)]:
            difference=float(data[group]["value"])-actual
            if difference>1e-12:b.plot([0,difference],[y+dy,y+dy],color=color,lw=.9)
            b.scatter(difference,y+dy,s=16,color=color,marker=mark,linewidth=.9,zorder=2)
    b.set(ylim=(-.6,7.6),yticks=list(range(7,-1,-1)),yticklabels=field_names,xticks=[0,.05,.10,.15],
          xlim=(-.011,.158),xlabel="Reduction in scaled error")
    b.tick_params(axis="y",length=0,pad=3,labelsize=6.9)
    key=[Line2D([],[],ls="none",marker="o",ms=3.6,color=BLUE,label="Versus receiver alone"),
         Line2D([],[],ls="none",marker="x",ms=4,color=ORANGE,label="Versus ordinary chain")]
    fig.legend(handles=key,loc="center",bbox_to_anchor=(.752,.491),ncol=2,fontsize=6.2)
    c=fig.add_axes([.050,.090,.418,.279])
    c.set_xlim(0,1); c.set_ylim(0,1); c.axis("off")
    xs=[.50,.71,.93]
    for x,recipe in zip(xs,["Ordinary\nhelp","Request\nsafety","Field\nsafety"]):
        c.text(x,.96,recipe,ha="center",va="top",fontsize=7.3)
    for interface,title,top in [("menu","Fixed menu",.71),("open","Open brief",.32)]:
        c.plot([0,1],[top+.064,top+.064],color=LIGHT,lw=.65)
        c.text(0,top,title,ha="left",va="center",weight="bold",fontsize=7.6)
        for metric,display,dy in [("active_assignments","Active assignments",.123),
                                  ("products_total","Measured products",.237)]:
            y=top-dy
            c.text(.015,y,display,ha="left",va="center",fontsize=7)
            for x,group in zip(xs,"HAB"):
                r=next(row for row in rows if row["panel"]=="c" and row["interface"]==interface
                       and row["group"]==group and row["metric"]==metric)
                value=int(r["value"]);total=int(r["total"])
                text=f"{value}/{total}" if metric=="active_assignments" else str(value)
                c.text(x,y,text,ha="center",va="center",fontsize=7.4,weight="normal")
    d=fig.add_axes([.704,.135,.247,.233])
    categories=[("none","No handoff"),("A","A handoff"),("H","H handoff"),("H_term_removed","H, period omitted"),("constant","Constant")]
    vals=[]
    for j,(group,label) in enumerate(categories):
        r=next(r for r in rows if r["panel"]=="d" and r["group"]==group);val=float(r["value"])
        vals.append(val);y=4-j
        d.scatter(val,y,color=BLUE if group in ["H","H_term_removed"] else MIDDLE,s=18,marker="s" if group=="constant" else "o")
        d.text(val+.038,y,f"{val:.5f}",ha="left",va="center",fontsize=6.6)
    d.set(xlim=(9.95,11.42),ylim=(-.5,4.55),yticks=range(4,-1,-1),yticklabels=[x[1] for x in categories],
          xlabel="AMU 1 mean absolute error (electrons/s)",xticks=[10,10.5,11])
    d.tick_params(axis="y",length=0,pad=3,labelsize=7)
    export(fig,3,out)


def main():
    here=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data",type=Path,default=here)
    parser.add_argument("--out",type=Path,default=here)
    parser.add_argument("--figure",type=int,choices=(1,2,3),help="render a single figure")
    args=parser.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    for number,draw in [(1,figures_one),(2,figures_two),(3,figures_three)]:
        if args.figure in (None,number):
            draw(table(args.data,number),args.out)


if __name__=="__main__":
    main()
