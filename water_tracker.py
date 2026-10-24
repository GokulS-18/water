"""
My Water Tracker - Streamlit app with drink types and a 7-day CSV report.
Run locally:  pip install streamlit pandas && streamlit run water_tracker.py
"""
import json
import random
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="My Water Tracker", page_icon="💧", layout="wide")
ss = st.session_state

LIQ = {"Water": ("💧", "#339af0"), "Juice": ("🧃", "#ff922b"), "Tender coconut": ("🥥", "#e6dfc0"),
       "Coffee": ("☕", "#6f4e37"), "Tea": ("🍵", "#c9772b")}
TODAY = str(date.today())
ss.setdefault("entries", [])      # every drink ever logged this session: id, d(ate), t(ime), ml, liq
ss.setdefault("goals", {})        # goal (ml) per date
ss.setdefault("goal", 2000)
ss.setdefault("nid", 0)
ss.setdefault("confirm", False)
ss.goals[TODAY] = ss.goal

MSGS = [(0, "Let’s start! Your first drink is waiting 💧"), (25, "Great start — keep sipping! 🌱"),
        (50, "Halfway there! You’re doing amazing 💪"), (75, "Almost done — just a little more! 🚀"),
        (100, "🎉 Goal reached! Fantastic hydration today! 🏆")]


def day(d=TODAY):
    return [e for e in ss.entries if e["d"] == d]


def total():
    return sum(e["ml"] for e in day())


def fmt(ml):
    return (f"{ml/1000:.2f}".rstrip("0").rstrip(".") + " L") if ml >= 1000 else f"{int(ml)} ml"


def rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def mix(a, b, t):
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(rgb(a), rgb(b)))


def shades(entries):
    """Colour of the water inside the body = volume-weighted blend of today's drinks."""
    tot = sum(e["ml"] for e in entries)
    col = LIQ["Water"][1]
    if tot:
        c = [sum(rgb(LIQ[e["liq"]][1])[k] * e["ml"] for e in entries) / tot for k in range(3)]
        col = "#%02x%02x%02x" % tuple(round(v) for v in c)
    light = mix(col, "#ffffff", .35)
    return [light, col, mix(col, "#000000", .35), light]


def add(ml):
    ml = int(ml)
    before, c0 = total(), shades(day())
    ss.entries.append({"id": ss.nid, "d": TODAY, "t": datetime.now().strftime("%H:%M"), "ml": ml, "liq": ss.liquid})
    ss.nid += 1
    ss.anim = {"ml": ml, "prev": before, "c0": c0, "liq": ss.liquid}
    if before < ss.goal <= total():
        ss.celebrate = True


def add_custom():
    add(ss.custom_ml)


def set_goal(ml):
    ss.goal = int(ml)


def remove(i):
    ss.entries = [e for e in ss.entries if e["id"] != i]


def do_reset(yes):
    if yes:
        ss.entries = [e for e in ss.entries if e["d"] != TODAY]
    ss.confirm = False


def demo():
    for back in range(1, 7):
        d = str(date.today() - timedelta(days=back))
        if day(d):
            continue
        for _ in range(random.randint(3, 8)):
            ss.entries.append({"id": ss.nid, "d": d, "t": f"{random.randint(7, 21):02d}:{random.choice(['00', '15', '30', '45'])}",
                               "ml": random.choice([100, 250, 250, 300, 500]), "liq": random.choice(list(LIQ))})
            ss.nid += 1
        ss.goals[d] = 2000


def report():
    rows = []
    for back in range(6, -1, -1):
        d = date.today() - timedelta(days=back)
        ds, es = str(d), day(str(d))
        row = {"Date": ds, "Day": d.strftime("%a")}
        for l in LIQ:
            row[f"{l} (ml)"] = sum(e["ml"] for e in es if e["liq"] == l)
        t, g = sum(e["ml"] for e in es), ss.goals.get(ds, 2000)
        row.update({"Total (ml)": t, "Drinks": len(es), "Goal (ml)": g, "Goal reached %": round(t / g * 100),
                    "Goal met": "Yes" if t >= g else "No"})
        rows.append(row)
    return pd.DataFrame(rows)


# ---------- animated see-through human body (HTML/SVG inside the app) ----------
BODY = """
<style>
body{margin:0;display:flex;justify-content:center;font-family:system-ui,sans-serif}
#box{position:relative;width:min(270px,92vw);animation:fl 4s ease-in-out infinite}
svg{width:100%;display:block;overflow:visible}
.hb{fill:#ffffff40;stroke:#4dabf7;stroke-width:4;stroke-linejoin:round}
.w1{animation:wv 2.2s linear infinite}.w2{animation:wv 3.6s linear infinite reverse}
#ua,#fa,#ga{transition:transform .9s ease-in-out,opacity .3s}#ga{opacity:0}
#plus{position:absolute;top:-4px;right:-6px;font:800 20px system-ui;color:#1c7ed6;opacity:0}
#plus.go{animation:pl 2.8s ease-out}.gulp svg{animation:gp .5s}
.bb{animation:rise 3.5s ease-in infinite}
@keyframes fl{50%{transform:translateY(-6px)}}@keyframes wv{to{transform:translateX(-100px)}}
@keyframes rise{to{transform:translateY(-70px);opacity:0}}@keyframes gp{40%{transform:scale(1.04)}}
@keyframes pl{0%{opacity:0;transform:translateY(20px) scale(.6)}15%{opacity:1;transform:scale(1.15)}80%{opacity:1}100%{opacity:0;transform:translateY(-30px)}}
</style>
<div id="box"><div id="plus"></div>
<svg viewBox="0 0 200 400" role="img" aria-label="Human body filling with water">
<defs><path id="bp" d="M86 66L114 66L114 78C130 79 140 84 144 94L144 190L146 260L138 380C137 392 116 392 114 380L106 270L100 250L94 270L86 380C84 392 63 392 62 380L54 260L56 190L54 126L46 192C44 202 31 200 32 190L40 108C44 88 60 80 86 78Z"/>
<circle id="hd" cx="100" cy="38" r="26"/><clipPath id="bc"><use href="#bp"/><use href="#hd"/></clipPath>
<linearGradient id="wg" x1="0" y1="0" x2="0" y2="1"><stop id="s1" offset="0" stop-color="#74c0fc"/><stop id="s2" offset=".5" stop-color="#339af0"/><stop id="s3" offset="1" stop-color="#1864ab"/></linearGradient>
<clipPath id="gc"><path d="M-10-30L10-30L7 2L-7 2Z"/></clipPath></defs>
<g fill="#ffffff40"><use href="#bp"/><use href="#hd"/></g>
<g clip-path="url(#bc)"><g id="wt" style="transform:translateY(388px)">
<g class="w2" opacity=".5"><path id="w2p" transform="translate(-30 -5)" fill="#74c0fc" d="M-200 0Q-175 -8 -150 0T-100 0T-50 0T0 0T50 0T100 0T150 0T200 0T250 0T300 0V420H-200Z"/></g>
<g class="w1"><path fill="url(#wg)" d="M-200 0Q-175 -8 -150 0T-100 0T-50 0T0 0T50 0T100 0T150 0T200 0T250 0T300 0V420H-200Z"/></g><g id="bubs"></g></g></g>
<g fill="none" stroke="#4dabf7" stroke-width="4" stroke-linejoin="round"><use href="#bp"/><use href="#hd"/></g>
<circle cx="91" cy="34" r="3" fill="#0b2540"/><circle cx="109" cy="34" r="3" fill="#0b2540"/>
<path d="M92 46Q100 53 108 46" fill="none" stroke="#0b2540" stroke-width="3" stroke-linecap="round"/>
<text id="pct" x="100" y="150" text-anchor="middle" font-size="28" font-weight="800" fill="#fff" stroke="#0a3a6acc" stroke-width="4" paint-order="stroke">0%</text>
<text x="100" y="170" text-anchor="middle" font-size="12" font-weight="700" fill="#fff" stroke="#0a3a6acc" stroke-width="4" paint-order="stroke">of __GOALTXT__</text>
<g transform="translate(140 92)"><g id="ua"><rect class="hb" x="-8" y="-8" width="16" height="50" rx="8"/><g transform="translate(0 42)"><g id="fa">
<rect class="hb" x="-7" y="-7" width="14" height="61" rx="7"/><g transform="translate(0 54)"><g id="ga"><g id="gq">
<path d="M-10-30L10-30L7 2L-7 2Z" fill="#ffffff66" stroke="#0b2540" stroke-width="1.5"/>
<g clip-path="url(#gc)"><rect id="gw" x="-10" y="-28" width="20" height="30" fill="#339af0" style="transform-box:fill-box;transform-origin:bottom"/></g>
</g></g></g></g></g></g></g></svg></div>
<script>
const P={prev:__PREV__,tot:__TOT__,goal:__GOAL__,ml:__ML__,c0:__C0__,c1:__C1__,gc:"__GC__",label:"__LABEL__"},$=s=>document.querySelector(s),
wait=ms=>new Promise(r=>setTimeout(r,ms)),lvl=t=>388-Math.min(1,t/P.goal)*376,pc=t=>Math.round(t/P.goal*100);
for(let i=0;i<12;i++){const c=document.createElementNS('http://www.w3.org/2000/svg','circle');c.setAttribute('class','bb');
c.setAttribute('cx',50+Math.random()*100);c.setAttribute('cy',60+Math.random()*300);c.setAttribute('r',1.5+Math.random()*3);
c.setAttribute('fill','#fff');c.setAttribute('fill-opacity','.6');c.style.animationDelay=Math.random()*3.5+'s';$('#bubs').appendChild(c)}
const wt=$('#wt');function setcol(c,t){['s1','s2','s3','w2p'].forEach((id,i)=>{const e=$('#'+id);e.style.transition='stop-color '+t+'s,fill '+t+'s';e.style.stopColor=c[i];e.style.fill=c[i]})}setcol(P.c0,0);wt.style.transform='translateY('+lvl(P.prev)+'px)';$('#pct').textContent=pc(P.prev)+'%';
function fill(){setcol(P.c1,1.4);wt.style.transition='transform 1.4s cubic-bezier(.3,1.2,.5,1)';wt.style.transform='translateY('+lvl(P.tot)+'px)';
const f=pc(P.prev),t=pc(P.tot),t0=performance.now();(function s(n){const k=Math.min(1,(n-t0)/1200);$('#pct').textContent=Math.round(f+(t-f)*k)+'%';if(k<1)requestAnimationFrame(s)})(t0)}
function tf(id,d,t){const e=$(id);e.style.transition='transform '+t+'s ease-in-out,opacity .3s';e.style.transform='rotate('+d+'deg)'}
async function run(){const s=.7+Math.min(P.ml,500)/500*.7,gw=$('#gw'),ga=$('#ga'),pl=$('#plus');
$('#gq').style.transform='scale('+s+')';gw.setAttribute('fill',P.gc);pl.textContent='+'+P.ml+' ml '+P.label;pl.classList.add('go');
await wait(400);ga.style.opacity=1;tf('#ua',27,.9);tf('#fa',143,.9);tf('#ga',-170,.9);await wait(950);
gw.style.transition='transform 1.6s linear';gw.style.transform='scaleY(0)';tf('#ga',-210,.7);await wait(1750);
fill();$('#box').classList.add('gulp');await wait(400);tf('#ga',0,.9);tf('#ua',0,.9);tf('#fa',0,.9);await wait(950);ga.style.opacity=0}
if(P.ml>0)run();else fill();
</script>
"""

# ---------- page ----------
st.markdown("<h1 style='margin-bottom:0'>💧 My Water Tracker</h1>", unsafe_allow_html=True)
st.caption(datetime.now().strftime("%A, %B %d") + " · stay hydrated!")

anim = ss.pop("anim", None)                      # consumed so other reruns don't replay it
tot, goal = total(), ss.goal
left, right = st.columns([1, 1.25], gap="large")

with left:
    c1_ = shades(day())
    html = (BODY.replace("__PREV__", str(anim["prev"] if anim else tot)).replace("__TOT__", str(tot))
            .replace("__GOAL__", str(goal)).replace("__ML__", str(anim["ml"] if anim else 0))
            .replace("__GOALTXT__", fmt(goal)).replace("__C0__", json.dumps(anim["c0"] if anim else c1_))
            .replace("__C1__", json.dumps(c1_)).replace("__GC__", LIQ[anim["liq"]][1] if anim else LIQ["Water"][1])
            .replace("__LABEL__", anim["liq"] if anim else ""))
    components.html(html, height=470)
    st.progress(min(1.0, tot / goal), text=f"{min(100, round(tot / goal * 100))}% of your daily goal")

with right:
    c1, c2, c3 = st.columns(3)
    c1.metric("Drunk", fmt(tot))
    c2.metric("Remaining", fmt(max(0, goal - tot)))
    c3.metric("Drinks", len(day()))

    pct = tot / goal * 100
    msg = [m for p, m in MSGS if pct >= p][-1] + (f" (+{fmt(tot - goal)} bonus!)" if tot > goal else "")
    (st.success if pct >= 100 else st.info)(msg)
    if ss.pop("celebrate", False):
        st.balloons()

    st.subheader("What are you drinking?")
    st.radio("Drink type", list(LIQ), key="liquid", horizontal=True, label_visibility="collapsed",
             format_func=lambda l: f"{LIQ[l][0]} {l}")
    b1, b2, b3 = st.columns(3)
    b1.button("🥛 Glass · 250 ml", on_click=add, args=(250,), use_container_width=True)
    b2.button("🍶 Bottle · 500 ml", on_click=add, args=(500,), use_container_width=True)
    b3.button("💦 Sip · 100 ml", on_click=add, args=(100,), use_container_width=True)
    n1, n2 = st.columns([2, 1])
    n1.number_input("Custom amount (ml)", 10, 2000, 300, 50, key="custom_ml", label_visibility="collapsed")
    n2.button("＋ Add custom", on_click=add_custom, use_container_width=True)

    st.subheader("Daily goal")
    g = st.columns(4)
    for col, v in zip(g, (1500, 2000, 2500, 3000)):
        col.button(f"{v/1000:g} L", on_click=set_goal, args=(v,), use_container_width=True,
                   type="primary" if goal == v else "secondary", key=f"g{v}")
    k1, k2 = st.columns([2, 1])
    custom = k1.number_input("Custom goal (litres)", 0.5, 10.0, goal / 1000, 0.1, label_visibility="collapsed")
    k2.button("Set goal", on_click=lambda: set_goal(round(custom * 1000)), use_container_width=True)

    st.subheader("Today’s log")
    if not day():
        st.caption("No drinks yet today")
    for e in reversed(day()):
        a, b = st.columns([5, 1])
        a.write(f"{LIQ[e['liq']][0]} **{fmt(e['ml'])}** {e['liq']} · {e['t']}")
        b.button("✕", key=f"rm{e['id']}", on_click=remove, args=(e["id"],))

    st.divider()
    if ss.confirm:
        st.warning("Reset today’s progress?")
        y, n = st.columns(2)
        y.button("Yes, reset", on_click=do_reset, args=(True,), use_container_width=True, type="primary")
        n.button("Cancel", on_click=do_reset, args=(False,), use_container_width=True)
    else:
        st.button("↺ Reset day", on_click=lambda: ss.update(confirm=True))

# ---------- 7-day report ----------
st.divider()
st.subheader("📊 Last 7 days report")
df = report()
st.dataframe(df, hide_index=True, use_container_width=True)
cols = [f"{l} (ml)" for l in LIQ]
st.bar_chart(df.set_index("Date")[cols], color=[v[1] for v in LIQ.values()])
d1, d2 = st.columns(2)
d1.download_button("⬇ Download 7-day report (CSV)", df.to_csv(index=False).encode("utf-8"),
                   file_name=f"water_report_{TODAY}.csv", mime="text/csv", use_container_width=True)
det = pd.DataFrame([{"date": e["d"], "time": e["t"], "liquid": e["liq"], "ml": e["ml"]} for e in ss.entries],
                   columns=["date", "time", "liquid", "ml"]).sort_values(["date", "time"])
d2.download_button("⬇ Download all drinks (detailed CSV)", det.to_csv(index=False).encode("utf-8"),
                   file_name="water_drinks_detailed.csv", mime="text/csv", use_container_width=True)

with st.expander("Keep your history between visits (data is stored only in this browser session)"):
    st.caption("Download the detailed CSV, then upload it here next time to restore your history.")
    up = st.file_uploader("Restore history (detailed CSV)", type="csv")
    if up is not None and ss.get("imp") != up.file_id:
        ss.imp = up.file_id
        try:
            have = {(e["d"], e["t"], e["liq"], e["ml"]) for e in ss.entries}
            for r in pd.read_csv(up).itertuples():
                k = (str(r.date), str(r.time), str(r.liquid), int(r.ml))
                if k not in have and k[2] in LIQ:
                    ss.entries.append({"id": ss.nid, "d": k[0], "t": k[1], "liq": k[2], "ml": k[3]})
                    ss.nid += 1
            st.rerun()
        except Exception as ex:
            st.error(f"Could not read that file: {ex}")
    st.button("Fill the previous 6 days with demo data", on_click=demo)
