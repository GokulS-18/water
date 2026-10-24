"""
My Water Tracker - animated desktop app (Python 3, Tkinter only, no extra installs).
Run:  python water_tracker.py

Tap Glass / Bottle / Sip (or a custom amount): the see-through human body lifts a glass,
drinks it, and the water level inside the body rises toward the daily goal.
Progress is saved next to this file (water_tracker_data.json) and resets each new day.
"""
import json, math, os, random, time, tkinter as tk
from collections import deque
from datetime import date, datetime

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "water_tracker_data.json")
BG, CARD, TX, MU = "#e7f5ff", "#ffffff", "#0b2540", "#5c7a99"
AC, AC2, OK, GLASS, WATER, HOV = "#1c7ed6", "#4dabf7", "#2f9e44", "#dcefff", "#339af0", "#cfe6fb"
W, H = 260, 360
S_R, S_L, L1, L2 = (138, 92), (62, 92), 42, 54          # shoulders, arm segment lengths
MSGS = [(0, "Let's start! Your first glass is waiting 💧"), (25, "Great start - keep sipping! 🌱"),
        (50, "Halfway there! You're doing amazing 💪"), (75, "Almost done - just a little more! 🚀"),
        (100, "🎉 Goal reached! Fantastic hydration today! 🏆")]


def fmt(ml):
    return (f"{ml/1000:.2f}".rstrip("0").rstrip(".") + " L") if ml >= 1000 else f"{int(round(ml))} ml"


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ell(cx, cy, rx, ry, n=48):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def rrect(x1, y1, x2, y2, r, n=8):
    pts = []
    for cx, cy, a0 in ((x2 - r, y1 + r, -90), (x2 - r, y2 - r, 0), (x1 + r, y2 - r, 90), (x1 + r, y1 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def clip(pts, L, below=True):
    """Keep the part of a polygon with y >= L (below) or y <= L (above)."""
    keep = (lambda p: p[1] >= L) if below else (lambda p: p[1] <= L)
    out = []
    for i, a in enumerate(pts):
        b = pts[(i + 1) % len(pts)]
        if keep(a):
            out.append(a)
        if keep(a) != keep(b):
            t = (L - a[1]) / (b[1] - a[1])
            out.append((a[0] + t * (b[0] - a[0]), L))
    return out


def flat(pts):
    return [v for p in pts for v in p]


SHAPES = [ell(100, 38, 26, 26), rrect(62, 64, 138, 176, 28), rrect(68, 160, 98, 330, 13), rrect(102, 160, 132, 330, 13)]
GLASS_PTS = [(-10, -30), (10, -30), (7, 2), (-7, 2)]


class App:
    def __init__(self, root):
        self.root = root
        root.title("My Water Tracker 💧")
        root.configure(bg=BG)
        root.minsize(760, 560)
        self.goal, self.entries = 2000, []
        self.load()
        self.disp, self.level = 0.0, 0.0
        self.queue, self.anim, self.parts = deque(), None, []
        self.bubbles = [[random.uniform(70, 130), random.uniform(100, 320), random.uniform(1.5, 3.5), random.uniform(.3, 1)] for _ in range(14)]
        self.plus = ("", 0.0)
        self.gulp_t, self.last_msg, self.arm_job = -9, "", None
        self.build()
        self.refresh_log()
        self.t0 = time.time()
        try:
            root.attributes("-alpha", 0.0)
            self.fade_in(0.0)
        except tk.TclError:
            pass
        self.tick()

    # ---------- data ----------
    def total(self):
        return sum(e["ml"] for e in self.entries)

    def load(self):
        try:
            with open(DATA) as f:
                d = json.load(f)
            self.goal = d.get("goal", 2000)
            if d.get("date") == str(date.today()):
                self.entries = d.get("entries", [])
        except Exception:
            pass

    def save(self):
        try:
            with open(DATA, "w") as f:
                json.dump({"goal": self.goal, "date": str(date.today()), "entries": self.entries}, f)
        except OSError:
            pass

    # ---------- UI ----------
    def btn(self, parent, text, cmd, bg=CARD, fg=TX, **kw):
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, relief="flat", bd=0, padx=12, pady=8,
                      font=("Segoe UI", 10, "bold"), cursor="hand2", activebackground=AC2, **kw)
        b.base = bg
        b.bind("<Enter>", lambda e: b.config(bg=HOV if b.base == CARD else AC2))
        b.bind("<Leave>", lambda e: b.config(bg=b.base))
        return b

    def card(self, parent):
        return tk.Frame(parent, bg=CARD, padx=16, pady=14, highlightbackground="#cfe3f5", highlightthickness=1)

    def build(self):
        r = self.root
        r.columnconfigure(1, weight=1)
        r.rowconfigure(0, weight=1)
        left = self.card(r)
        left.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="ns")
        tk.Label(left, text="💧 My Water Tracker", bg=CARD, fg=TX, font=("Segoe UI", 16, "bold")).pack()
        tk.Label(left, text=datetime.now().strftime("%A, %B %d"), bg=CARD, fg=MU).pack()
        self.cv = tk.Canvas(left, width=W, height=H, bg=CARD, highlightthickness=0)
        self.cv.pack(pady=8)
        self.bar = tk.Canvas(left, width=W, height=18, bg=CARD, highlightthickness=0)
        self.bar.pack()

        right = self.card(r)
        right.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="nsew")
        stats = tk.Frame(right, bg=CARD)
        stats.pack(fill="x")
        self.sv = {}
        for i, (k, name) in enumerate((("tot", "Drunk"), ("rem", "Remaining"), ("cnt", "Drinks"))):
            f = tk.Frame(stats, bg=BG, padx=6, pady=8)
            f.grid(row=0, column=i, padx=4, sticky="ew")
            stats.columnconfigure(i, weight=1)
            self.sv[k] = tk.Label(f, text="0", bg=BG, fg=TX, font=("Segoe UI", 18, "bold"))
            self.sv[k].pack()
            tk.Label(f, text=name, bg=BG, fg=MU, font=("Segoe UI", 9)).pack()
        self.msg = tk.Label(right, text="", bg=BG, fg=TX, font=("Segoe UI", 11, "bold"), pady=12, wraplength=420)
        self.msg.pack(fill="x", pady=10)

        self.head(right, "ADD WATER")
        row = tk.Frame(right, bg=CARD)
        row.pack(fill="x")
        for i, (txt, ml) in enumerate((("🥛 Glass\n250 ml", 250), ("🍶 Bottle\n500 ml", 500), ("💦 Sip\n100 ml", 100))):
            self.btn(row, txt, lambda m=ml: self.add(m), bg=CARD).grid(row=0, column=i, padx=4, sticky="ew")
            row.columnconfigure(i, weight=1)
        row = tk.Frame(right, bg=CARD)
        row.pack(fill="x", pady=6)
        self.cus = tk.Entry(row, width=10, font=("Segoe UI", 11), relief="solid", bd=1)
        self.cus.pack(side="left", padx=4, ipady=4)
        self.cus.bind("<Return>", lambda e: self.add_custom())
        tk.Label(row, text="custom ml", bg=CARD, fg=MU).pack(side="left")
        self.btn(row, "＋ Add", self.add_custom, bg=AC, fg="white").pack(side="left", padx=8)

        self.head(right, "DAILY GOAL")
        row = tk.Frame(right, bg=CARD)
        row.pack(fill="x")
        self.chips = {}
        for g in (1500, 2000, 2500, 3000):
            b = self.btn(row, f"{g/1000:g} L", lambda v=g: self.set_goal(v))
            b.pack(side="left", padx=3)
            self.chips[g] = b
        row = tk.Frame(right, bg=CARD)
        row.pack(fill="x", pady=6)
        self.gin = tk.Entry(row, width=8, font=("Segoe UI", 11), relief="solid", bd=1)
        self.gin.pack(side="left", padx=4, ipady=4)
        self.gin.bind("<Return>", lambda e: self.custom_goal())
        tk.Label(row, text="litres", bg=CARD, fg=MU).pack(side="left")
        self.btn(row, "Set goal", self.custom_goal, bg=AC, fg="white").pack(side="left", padx=8)
        self.rst = self.btn(row, "↺ Reset day", self.reset)
        self.rst.pack(side="left")

        self.head(right, "TODAY'S LOG")
        lf = tk.Frame(right, bg=CARD)
        lf.pack(fill="both", expand=True)
        self.lb = tk.Listbox(lf, height=5, font=("Segoe UI", 10), relief="flat", bg=BG, fg=TX, selectbackground=AC2, activestyle="none")
        self.lb.pack(side="left", fill="both", expand=True)
        self.btn(lf, "✕ Remove\nselected", self.remove).pack(side="left", padx=6)

    def head(self, p, t):
        tk.Label(p, text=t, bg=CARD, fg=MU, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 4))

    def fade_in(self, a):
        a = min(1.0, a + 0.06)
        self.root.attributes("-alpha", a)
        if a < 1:
            self.root.after(20, lambda: self.fade_in(a))

    def shake(self, w):
        def step(i=0):
            w.pack_configure(padx=(4 + (6 if i % 2 else 0)) if i < 6 else 4)
            if i < 6:
                self.root.after(35, lambda: step(i + 1))
        step()

    # ---------- actions ----------
    def add(self, ml):
        self.queue.append(int(ml))

    def add_custom(self):
        try:
            v = int(float(self.cus.get()))
            assert 0 < v <= 2000
        except Exception:
            self.shake(self.cus)
            return
        self.cus.delete(0, "end")
        self.add(v)

    def set_goal(self, g):
        self.goal = int(g)
        self.save()

    def custom_goal(self):
        try:
            g = int(float(self.gin.get()) * 1000)
            assert 500 <= g <= 10000
        except Exception:
            self.shake(self.gin)
            return
        self.gin.delete(0, "end")
        self.set_goal(g)

    def reset(self):
        if self.arm_job is None:
            self.rst.config(text="Click again to confirm", bg="#e03131", fg="white")
            self.rst.base = "#e03131"
            self.arm_job = self.root.after(3000, self.unarm)
            return
        self.unarm()
        self.entries.clear()
        self.save()
        self.refresh_log()

    def unarm(self):
        if self.arm_job:
            self.root.after_cancel(self.arm_job)
        self.arm_job = None
        self.rst.config(text="↺ Reset day", fg=TX, bg=CARD)
        self.rst.base = CARD

    def remove(self):
        sel = self.lb.curselection()
        if sel:
            del self.entries[len(self.entries) - 1 - sel[0]]
            self.save()
            self.refresh_log()

    def refresh_log(self):
        self.lb.delete(0, "end")
        for e in reversed(self.entries):
            self.lb.insert("end", f"  💧 {fmt(e['ml'])}   ·   {e['t']}")

    def commit(self, ml):                      # called at the moment of the gulp
        before = self.total()
        self.entries.append({"ml": ml, "t": datetime.now().strftime("%H:%M")})
        self.save()
        self.refresh_log()
        self.gulp_t = time.time()
        if before < self.goal <= self.total():
            self.parts += [[random.uniform(20, W - 20), -10, random.uniform(-2, 2), random.uniform(2, 5),
                            random.choice([AC2, "#51cf66", "#ffd43b", "#ff8787", "#b197fc"])] for _ in range(90)]

    # ---------- animation ----------
    def pose(self):
        """Return (ua, fa, ga, glass_visible, water_fraction) for the drinking arm."""
        a = self.anim
        if not a:
            return 0, 0, 0, False, 1
        t = time.time() - a["t0"]
        if t < 0.9:
            e = smooth(t / 0.9)
            return 27 * e, 143 * e, -170 * e, True, 1
        if t < 2.65:
            tilt = smooth((t - 0.9) / 0.7)
            return 27, 143, -170 - 25 * tilt, True, 1 - max(0, min(1, (t - 0.9) / 1.6))
        if not a["done"]:
            a["done"] = True
            self.commit(a["ml"])
        if t < 3.0:
            return 27, 143, -195, True, 0
        e = 1 - smooth((t - 3.0) / 0.9)
        if t > 3.9:
            self.anim = None
        return 27 * e, 143 * e, -195 * e, t < 3.35, 0

    def limbs(self, S, ua, fa):
        a1 = math.radians(ua)
        E = (S[0] - L1 * math.sin(a1), S[1] + L1 * math.cos(a1))
        a2 = a1 + math.radians(fa)
        return E, (E[0] - L2 * math.sin(a2), E[1] + L2 * math.cos(a2)), a2

    def draw(self):
        c, now = self.cv, time.time()
        c.delete("all")
        ly = 330 - self.level * 318 + math.sin(now * 3) * 1.2
        for s in SHAPES:
            c.create_polygon(flat(s), fill=GLASS, outline="")
        if self.level > 0.003:
            for s in SHAPES:
                p = clip(s, ly)
                if len(p) > 2:
                    c.create_polygon(flat(p), fill=WATER, outline="")
                    band = clip(p, ly + 5, below=False)
                    if len(band) > 2:
                        c.create_polygon(flat(band), fill="#74c0fc", outline="")
            for b in self.bubbles:
                b[1] -= b[3]
                inside = (66 < b[0] < 134 and 64 < b[1] < 176) or (70 < b[0] < 96 or 104 < b[0] < 130) and 160 < b[1] < 330
                if b[1] < ly or not inside:
                    b[0], b[1] = random.uniform(72, 128), random.uniform(max(ly, 70) + 10, 320)
                c.create_oval(b[0] - b[2], b[1] - b[2], b[0] + b[2], b[1] + b[2], outline="white", width=1)
        pulse = 2 * math.sin(min(1, (now - self.gulp_t) / 0.5) * math.pi) if now - self.gulp_t < 0.5 else 0
        for s in SHAPES:
            c.create_polygon(flat(s), fill="", outline=AC2, width=3 + pulse)
        c.create_oval(87, 31, 93, 37, fill=TX, outline="")
        c.create_oval(107, 31, 113, 37, fill=TX, outline="")
        c.create_arc(90, 36, 110, 52, start=200, extent=140, style="arc", outline=TX, width=2)
        pct = int(round(self.disp / self.goal * 100)) if self.goal else 0
        for dx, dy, col in ((1, 1, "#0a3a6a"), (0, 0, "white")):
            c.create_text(100 + dx, 132 + dy, text=f"{min(pct, 999)}%", fill=col, font=("Segoe UI", 22, "bold"))
            c.create_text(100 + dx, 154 + dy, text=f"of {fmt(self.goal)}", fill=col, font=("Segoe UI", 9, "bold"))
        # arms
        ua, fa, ga, show, wf = self.pose()
        E, Hd, a2 = self.limbs(S_R, ua, fa)
        segs = [(S_L, (S_L[0], S_L[1] + 98)), (S_R, E), (E, Hd)]
        for w, col in ((19, AC2), (12, "#f1f9ff")):
            for p, q in segs:
                c.create_line(*p, *q, width=w, fill=col, capstyle="round")
        if show and self.anim:
            s = 0.7 + min(self.anim["ml"], 500) / 500 * 0.7
            ang = a2 + math.radians(ga)
            tr = lambda pts: flat([(Hd[0] + (x * s) * math.cos(ang) - (y * s) * math.sin(ang),
                                    Hd[1] + (x * s) * math.sin(ang) + (y * s) * math.cos(ang)) for x, y in pts])
            top = -28 + 30 * (1 - wf)
            wp = clip([(-9, -29), (9, -29), (6.4, 1), (-6.4, 1)], top)
            if wf > 0.01 and len(wp) > 2:
                c.create_polygon(tr(wp), fill=WATER, outline="")
            c.create_polygon(tr(GLASS_PTS), fill="", outline=TX, width=2)
        # +ml label
        txt, t0 = self.plus
        if txt and now - t0 < 2.8:
            k = (now - t0) / 2.8
            c.create_text(215, 28 - 28 * k, text=txt, fill=AC, font=("Segoe UI", 14, "bold"))
        # confetti
        for p in self.parts:
            p[0] += p[2]; p[1] += p[3]; p[3] += 0.06
            c.create_rectangle(p[0], p[1], p[0] + 6, p[1] + 9, fill=p[4], outline="")
        self.parts = [p for p in self.parts if p[1] < H + 20]

    def draw_bar(self, pct):
        b = self.bar
        b.delete("all")
        b.create_polygon(flat(rrect(1, 1, W - 1, 17, 8)), fill="#cfe3f5", outline="", smooth=False)
        w = (W - 2) * min(1, pct / 100)
        if w > 12:
            col = OK if pct >= 100 else AC2
            b.create_polygon(flat(rrect(1, 1, 1 + w, 17, 8)), fill=col, outline="")
            x = ((time.time() * 90) % (w + 40)) - 20
            if 8 < x < w - 8:
                b.create_rectangle(x, 4, min(x + 14, w - 6), 14, fill="#ffffff", stipple="gray50", outline="")

    def tick(self):
        if self.anim is None and self.queue:
            ml = self.queue.popleft()
            self.anim = {"t0": time.time(), "ml": ml, "done": False}
            self.plus = (f"+{ml} ml", time.time())
        tot = self.total()
        self.disp += (tot - self.disp) * 0.1
        if abs(tot - self.disp) < 1:
            self.disp = tot
        self.level += (min(1, tot / self.goal) - self.level) * 0.05
        if abs(self.level - min(1, tot / self.goal)) < 0.001:
            self.level = min(1, tot / self.goal)
        self.sv["tot"].config(text=fmt(self.disp))
        self.sv["rem"].config(text=fmt(max(0, self.goal - self.disp)))
        self.sv["cnt"].config(text=str(len(self.entries)))
        pct = tot / self.goal * 100
        m = [x for x in MSGS if pct >= x[0]][-1][1] + (f" (+{fmt(tot - self.goal)} bonus!)" if tot > self.goal else "")
        if m != self.last_msg:
            self.last_msg = m
            win = pct >= 100
            self.msg.config(text=m, bg=OK if win else AC2, fg="white" if win else TX)
            self.root.after(350, lambda: self.msg.config(bg=OK if win else BG))
        for g, b in self.chips.items():
            want = AC if g == self.goal else CARD
            if b.base != want:
                b.base = want
                b.config(bg=want, fg="white" if want == AC else TX)
        self.draw()
        self.draw_bar(self.disp / self.goal * 100)
        self.root.after(16, self.tick)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
