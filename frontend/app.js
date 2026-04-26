const API_URL = "http://localhost:8000";

function schafkopfApp() {
    return {
        tab: 'setup',
        state: {
            all_players: [],
            player_stats: {},
            session_players: [],
            active_players: [],
            session_history: [],
            t_sau: 10,
            t_solo: 20
        },
        newPlayerName: '',
        selectedPlayers: [],
        t_sau: 10,
        t_solo: 20,
        
        game: {
            game_type: 'Sauspiel',
            ansager: '',
            laufende: 0,
            status: 'Normal',
            winners: []
        },
        errorMsg: '',
        chart: null,

        async init() {
            await this.loadState();
        },

        async loadState() {
            try {
                const res = await fetch(`${API_URL}/state`);
                this.state = await res.json();
                if (this.state.session_players.length > 0) {
                    this.t_sau = this.state.t_sau;
                    this.t_solo = this.state.t_solo;
                }
                this.updateChart();
            } catch (err) {
                console.error("Failed to load state", err);
            }
        },

        async addPlayer() {
            if (!this.newPlayerName.trim()) return;
            try {
                await fetch(`${API_URL}/add_player`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: this.newPlayerName })
                });
                this.newPlayerName = '';
                await this.loadState();
            } catch (err) {
                alert("Fehler beim Hinzufügen des Spielers");
            }
        },

        async startSession() {
            if (this.selectedPlayers.length < 4) {
                alert("Ihr braucht mindestens 4 Leute am Tisch!");
                return;
            }
            try {
                await fetch(`${API_URL}/start_session`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        players: this.selectedPlayers,
                        t_sau: this.t_sau,
                        t_solo: this.t_solo
                    })
                });
                await this.loadState();
                if(this.state.active_players.length > 0) {
                    this.game.ansager = this.state.active_players[0];
                }
                this.tab = 'play';
            } catch (err) {
                alert("Fehler beim Starten der Session");
            }
        },

        async recordGame() {
            this.errorMsg = '';
            const g = this.game.game_type;
            const w = this.game.winners;
            
            if (g === "Sauspiel" && w.length !== 2) {
                this.errorMsg = "Beim Sauspiel gewinnen immer genau 2 Personen!";
                return;
            }
            if (["Solo", "Wenz", "Geier"].includes(g) && ![1, 3].includes(w.length)) {
                this.errorMsg = "Solo: 1 Haken (Sieg) oder 3 Haken (Verlust)!";
                return;
            }

            try {
                await fetch(`${API_URL}/record_game`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        game_type: this.game.game_type,
                        winners: this.game.winners,
                        ansager: this.game.ansager,
                        laufende: this.game.laufende,
                        status: this.game.status
                    })
                });
                
                // Reset form
                this.game.winners = [];
                this.game.laufende = 0;
                this.game.status = 'Normal';
                
                await this.loadState();
                
                if(this.state.active_players.length > 0) {
                    this.game.ansager = this.state.active_players[0];
                }
            } catch (err) {
                this.errorMsg = "Fehler beim Speichern";
            }
        },

        get sessionHistoryAggregated() {
            let cum = {};
            this.state.session_players.forEach(p => cum[p] = 0);
            
            return this.state.session_history.map(h => {
                let rowScores = {};
                for (const p of this.state.session_players) {
                    cum[p] += (h.scores[p] || 0);
                    rowScores[p] = cum[p];
                }
                return {
                    type: h.type,
                    scores: rowScores
                };
            });
        },

        get rankedPlayers() {
            return Object.entries(this.state.player_stats).map(([name, s]) => {
                const sq = s.soli_played > 0 ? Math.round((s.soli_won / s.soli_played) * 100) + '%' : '-';
                const wq = s.total_games_as_ansager > 0 ? Math.round((s.total_wins_as_ansager / s.total_games_as_ansager) * 100) + '%' : '-';
                return {
                    name,
                    score: s.global_score,
                    soliQuote: sq,
                    ansagerQuote: wq
                };
            }).sort((a, b) => b.score - a.score);
        },

        updateChart() {
            if (this.state.session_players.length === 0) return;
            
            const ctx = document.getElementById('scoreChart');
            if(!ctx) return;

            let pts = {};
            this.state.session_players.forEach(p => pts[p] = [0]);
            
            let cum = {};
            this.state.session_players.forEach(p => cum[p] = 0);
            
            let labels = ['Start'];
            
            this.state.session_history.forEach((h, i) => {
                labels.push(`Runde ${i+1}`);
                this.state.session_players.forEach(p => {
                    cum[p] += (h.scores[p] || 0);
                    pts[p].push(cum[p]);
                });
            });

            const datasets = this.state.session_players.map((p, i) => {
                const colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6'];
                return {
                    label: p,
                    data: pts[p],
                    borderColor: colors[i % colors.length],
                    backgroundColor: colors[i % colors.length],
                    tension: 0.1
                }
            });

            if (this.chart) {
                this.chart.data.labels = labels;
                this.chart.data.datasets = datasets;
                this.chart.update();
            } else {
                this.chart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: datasets
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                grid: {
                                    color: (ctx) => ctx.tick.value === 0 ? '#000' : 'rgba(0,0,0,0.1)',
                                    lineWidth: (ctx) => ctx.tick.value === 0 ? 2 : 1
                                }
                            }
                        }
                    }
                });
            }
        }
    }
}
