import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Dateiname für die Datenbank
DATA_FILE = "schafkopf_daten_final.json"


class SchafkopfData:
    def __init__(self):
        self.data = self.load_data()
        self.session_players = []
        self.active_players = []
        self.rotation_index = 0
        self.session_history = []

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    if "players" not in d: d = {"players": {}, "global_history": []}
                    return d
            except:
                pass
        return {"players": {}, "global_history": []}

    def save_data(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    def add_player(self, name):
        name = name.strip()
        if name and name not in self.data["players"]:
            self.data["players"][name] = {
                "global_score": 0, "soli_played": 0, "soli_won": 0,
                "total_games_as_ansager": 0, "total_wins_as_ansager": 0
            }
            self.save_data()
            return True
        return False

    def get_all_players(self):
        return sorted(list(self.data["players"].keys()))

    def record_game(self, game_type, winners, base_points, ansager, laufende, status):
        # Initialisiere Scores für ALLE Session-Teilnehmer mit 0
        round_scores = {p: 0 for p in self.session_players}
        laufende_val = int(laufende)

        # 1. Multiplikator berechnen
        if status == "Sie (Alle Stiche)":
            multiplier = (1 + 4 + 2) * 2
        elif status == "Schwarz":
            multiplier = 1 + laufende_val + 2
        elif status == "Schneider":
            multiplier = 1 + laufende_val + 1
        else:
            multiplier = 1 + laufende_val

        total_points = multiplier * base_points

        # WICHTIG: Wir berechnen nur für die 4 aktiven Spieler am Tisch!
        # Wer nicht in 'winners' ist, aber in 'active_players', ist ein Verlierer am Tisch.
        losers_at_table = [p for p in self.active_players if p not in winners]

        # 2. Spezielle Logik für RAMSCH
        if game_type == "Ramsch":
            if len(winners) == 3:  # Einer verliert (der nicht angehakt ist)
                verlierer = losers_at_table[0]
                round_scores[verlierer] = -base_points * 3
                for w in winners: round_scores[w] = base_points
            elif len(winners) == 1:  # Durchmarsch (Einer gewinnt)
                gewinner = winners[0]
                round_scores[gewinner] = base_points * 3
                for l in losers_at_table: round_scores[l] = -base_points

        # 3. Logik für SOLO / WENZ / GEIER
        elif game_type in ["Solo", "Wenz", "Geier"]:
            is_win = (ansager in winners)
            if is_win:
                round_scores[ansager] = total_points * 3
                # Nur die 3 Verlierer AM TISCH zahlen
                for l in losers_at_table: round_scores[l] = -total_points
            else:
                round_scores[ansager] = -total_points * 3
                # Nur die 3 Gewinner AM TISCH bekommen Punkte
                for w in winners: round_scores[w] = total_points

            # Statistik
            p = self.data["players"][ansager]
            p["total_games_as_ansager"] += 1
            p["soli_played"] += 1
            if is_win:
                p["total_wins_as_ansager"] += 1
                p["soli_won"] += 1

        # 4. Logik für SAUSPIEL
        else:
            for w in winners: round_scores[w] = total_points
            for l in losers_at_table: round_scores[l] = -total_points

            # Statistik für Ansager
            p = self.data["players"][ansager]
            p["total_games_as_ansager"] += 1
            if ansager in winners: p["total_wins_as_ansager"] += 1

        # Global speichern
        for p, score in round_scores.items():
            if p in self.data["players"]:
                self.data["players"][p]["global_score"] += score

        self.session_history.append({"type": game_type, "scores": round_scores, "ansager": ansager})
        self.save_data()
        self.rotate_players()

    def rotate_players(self):
        n = len(self.session_players)
        if n > 4:
            self.rotation_index = (self.rotation_index + 1) % n
        self.active_players = [self.session_players[(self.rotation_index + i) % n] for i in range(4)]


class SchafkopfApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Schafkopf Tracker Deluxe v5.5")
        self.root.geometry("1200x900")
        self.db = SchafkopfData()

        self.nb = ttk.Notebook(root)
        self.nb.pack(expand=True, fill='both', padx=10, pady=10)

        self.tab_setup = ttk.Frame(self.nb)
        self.tab_session = ttk.Frame(self.nb)
        self.tab_stats = ttk.Frame(self.nb)

        self.nb.add(self.tab_setup, text=' ⚙ 1. Setup & Spieler ')
        self.nb.add(self.tab_session, text=' 🂠 2. Aktuelles Spiel ')
        self.nb.add(self.tab_stats, text=' 📊 3. Ranking & Verlauf ')

        self.build_setup()
        self.build_session()
        self.build_stats()
        self.update_ui()

    def build_setup(self):
        f = ttk.Frame(self.tab_setup, padding=20)
        f.pack(fill='both', expand=True)

        ttk.Label(f, text="--- NEUEN SPIELER ANLEGEN ---", font=("Arial", 10, "bold")).pack()
        self.new_p_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.new_p_var).pack(fill='x', pady=5)
        ttk.Button(f, text="In Datenbank speichern", command=self.add_p).pack(pady=5)

        ttk.Label(f, text="--- SPIELER FÜR DIESE RUNDE WÄHLEN ---", font=("Arial", 10, "bold")).pack(pady=(20, 0))
        self.lb = tk.Listbox(f, selectmode='multiple', font=("Arial", 12), height=8)
        self.lb.pack(fill='both', expand=True, pady=10)

        ttk.Label(f, text="--- TARIFE (Punkte pro Verlierer) ---", font=("Arial", 10, "bold")).pack()
        t_f = ttk.Frame(f)
        t_f.pack(pady=10)
        self.t_sau = tk.IntVar(value=10)
        self.t_solo = tk.IntVar(value=20)
        ttk.Label(t_f, text="Sauspiel/Ramsch:").grid(row=0, column=0, padx=5)
        ttk.Spinbox(t_f, from_=1, to=100, textvariable=self.t_sau, width=5).grid(row=0, column=1)
        ttk.Label(t_f, text=" Solo/Wenz:").grid(row=0, column=2, padx=5)
        ttk.Spinbox(t_f, from_=1, to=100, textvariable=self.t_solo, width=5).grid(row=0, column=3)

        ttk.Button(f, text="SESSION JETZT STARTEN", command=self.start, style="TButton").pack(fill='x', ipady=10)

    def build_session(self):
        self.info = ttk.Label(self.tab_session, text="Bitte erst Spieler im Setup wählen!", font=("Arial", 12, "bold"),
                              foreground="red")
        self.info.pack(pady=10)

        in_f = ttk.LabelFrame(self.tab_session, text=" RUNDENDATEN EINGEBEN ", padding=15)
        in_f.pack(fill='x', padx=10)

        ttk.Label(in_f, text="Spielart:").grid(row=0, column=0)
        self.g_type = tk.StringVar(value="Sauspiel")
        ttk.Combobox(in_f, textvariable=self.g_type, values=["Sauspiel", "Solo", "Wenz", "Geier", "Ramsch"],
                     state="readonly", width=12).grid(row=0, column=1)

        ttk.Label(in_f, text="Ansager:").grid(row=0, column=2, padx=10)
        self.ans_var = tk.StringVar()
        self.ans_combo = ttk.Combobox(in_f, textvariable=self.ans_var, state="readonly", width=12)
        self.ans_combo.grid(row=0, column=3)

        ttk.Label(in_f, text="Laufende:").grid(row=1, column=0, pady=10)
        self.lauf = tk.Spinbox(in_f, from_=0, to=15, width=5)
        self.lauf.grid(row=1, column=1)

        ttk.Label(in_f, text="Ergebnis:").grid(row=1, column=2)
        self.stat_var = tk.StringVar(value="Normal")
        ttk.OptionMenu(in_f, self.stat_var, "Normal", "Normal", "Schneider", "Schwarz", "Sie (Alle Stiche)").grid(row=1,
                                                                                                                  column=3)

        self.win_vars = [tk.BooleanVar() for _ in range(4)]
        self.win_chks = []
        chk_f = ttk.LabelFrame(self.tab_session, text=" WER HAT GEWONNEN? (Häkchen setzen) ", padding=10)
        chk_f.pack(fill='x', padx=10, pady=10)
        for i in range(4):
            c = ttk.Checkbutton(chk_f, text=f"Spieler {i + 1}", variable=self.win_vars[i])
            c.pack(side='left', padx=20)
            self.win_chks.append(c)

        ttk.Button(self.tab_session, text="ERGEBNIS SPEICHERN & GEBER WECHSELN", command=self.record).pack(fill='x',
                                                                                                           padx=10,
                                                                                                           ipady=5)

        self.tree = ttk.Treeview(self.tab_session, show='headings')
        self.tree.pack(fill='both', expand=True, padx=10, pady=10)

    def build_stats(self):
        top_f = ttk.Frame(self.tab_stats)
        top_f.pack(fill='both', expand=True)

        self.rank_tree = ttk.Treeview(top_f, columns=("N", "P", "S", "W"), show='headings', height=8)
        for id, txt in [("N", "Name"), ("P", "Gesamtpunkte"), ("S", "Soli-Quote"), ("W", "Ansager-Quote")]:
            self.rank_tree.heading(id, text=txt)
            self.rank_tree.column(id, anchor="center")
        self.rank_tree.pack(fill='x', padx=10, pady=5)

        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_stats)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)

    def add_p(self):
        if self.db.add_player(self.new_p_var.get()):
            self.new_p_var.set("")
            self.update_ui()

    def start(self):
        sel = self.lb.curselection()
        if len(sel) < 4:
            messagebox.showwarning("Stopp", "Ihr braucht mindestens 4 Leute am Tisch!")
            return
        self.db.session_players = [self.lb.get(i) for i in sel]
        self.db.rotation_index = 0
        self.db.active_players = self.db.session_players[:4]

        cols = ["Nr", "Typ"] + self.db.session_players
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor="center", width=80)

        self.nb.select(self.tab_session)
        self.update_ui()

    def record(self):
        if not self.db.active_players: return
        win_names = [self.db.active_players[i] for i, v in enumerate(self.win_vars) if v.get()]
        ans = self.ans_var.get()
        g = self.g_type.get()

        # Validierung
        if g == "Sauspiel" and len(win_names) != 2:
            return messagebox.showerror("Fehler", "Beim Sauspiel gewinnen immer genau 2 Personen!")
        if g in ["Solo", "Wenz", "Geier"] and len(win_names) not in [1, 3]:
            return messagebox.showerror("Fehler", "Solo: 1 Haken (Sieg) oder 3 Haken (Verlust)!")

        base = self.t_solo.get() if g in ["Solo", "Wenz", "Geier"] else self.t_sau.get()

        # Geänderter Aufruf: Wir brauchen nur die Gewinner, die Verlierer am Tisch errechnet die Klasse selbst
        self.db.record_game(g, win_names, base, ans, self.lauf.get(), self.stat_var.get())

        for v in self.win_vars: v.set(False)
        self.update_ui()

    def update_ui(self):
        self.lb.delete(0, tk.END)
        for p in self.db.get_all_players(): self.lb.insert(tk.END, p)

        for i in self.rank_tree.get_children(): self.rank_tree.delete(i)
        players = sorted(self.db.data["players"].items(), key=lambda x: x[1]['global_score'], reverse=True)
        for n, s in players:
            sq = f"{(s['soli_won'] / s['soli_played'] * 100):.0f}%" if s.get('soli_played', 0) > 0 else "-"
            wq = f"{(s['total_wins_as_ansager'] / s['total_games_as_ansager'] * 100):.0f}%" if s.get(
                'total_games_as_ansager', 0) > 0 else "-"
            self.rank_tree.insert("", tk.END, values=(n, s['global_score'], sq, wq))

        if self.db.session_players:
            self.info.config(text=f"AKTIV AM TISCH: {', '.join(self.db.active_players)}", foreground="green")
            self.ans_combo['values'] = self.db.active_players
            for i, p in enumerate(self.db.active_players): self.win_chks[i].config(text=p)

            for i in self.tree.get_children(): self.tree.delete(i)
            cum = {p: 0 for p in self.db.session_players}
            plot_pts = {p: [0] for p in self.db.session_players}

            for i, g in enumerate(self.db.session_history):
                for p in self.db.session_players:
                    val = g["scores"].get(p, 0)
                    cum[p] += val
                    plot_pts[p].append(cum[p])
                self.tree.insert("", tk.END, values=[i + 1, g["type"]] + [cum[p] for p in self.db.session_players])

            self.ax.clear()
            for p in self.db.session_players:
                self.ax.plot(plot_pts[p], label=p, marker='o')
            self.ax.axhline(0, color='black', lw=1, ls='--')
            self.ax.legend(loc='upper left', fontsize='x-small')
            self.ax.set_title("Punkteverlauf (Session)")
            self.canvas.draw()


if __name__ == "__main__":
    r = tk.Tk();
    app = SchafkopfApp(r);
    r.mainloop()