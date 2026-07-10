import sqlite3
import os
from contextlib import contextmanager

DB_PATH = "tournament.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize the SQLite database with the required tables."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Guild Config Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            announcements_channel_id INTEGER,
            registration_channel_id INTEGER,
            chat_channel_id INTEGER,
            results_channel_id INTEGER,
            standings_channel_id INTEGER,
            history_channel_id INTEGER,
            staff_logs_channel_id INTEGER,
            bot_config_channel_id INTEGER,
            host_role_id INTEGER,
            staff_role_id INTEGER,
            referee_role_id INTEGER,
            participant_role_id INTEGER,
            qualified_role_id INTEGER,
            semi_role_id INTEGER,
            final_role_id INTEGER,
            champion_role_id INTEGER,
            current_season INTEGER DEFAULT 1
        )
        """)

        # 2. Tournaments Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            name TEXT NOT NULL,
            mode TEXT NOT NULL,       -- BUHC, FUHC, Skywars, Bedwars, Boxing, etc.
            format TEXT NOT NULL,     -- Solo (1v1), Doubles (2v2), Triples (3v3), Squads (4v4), Clan
            type TEXT NOT NULL,       -- Single Elimination, Double Elimination, Round Robin, Swiss, Group Stage + Playoffs
            stage TEXT NOT NULL,      -- Setup, Registration, Check-in, Group Stage, Qualifiers, Semis, Finals, Ended
            prize TEXT,
            host_id INTEGER,
            max_teams INTEGER DEFAULT 16,
            rules TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 3. Teams Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER,
            name TEXT NOT NULL,
            logo_url TEXT,
            captain_id INTEGER,
            player2_id INTEGER,
            player3_id INTEGER,
            player4_id INTEGER,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            seed INTEGER DEFAULT 0,
            status TEXT DEFAULT 'registered', -- registered, checked_in, qualified, eliminated, champion
            FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE
        )
        """)
        # Add seed column if missing (for existing databases)
        try:
            cursor.execute("ALTER TABLE teams ADD COLUMN seed INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        # 4. Matches Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER,
            stage TEXT NOT NULL,          -- Group Stage, Qualifiers, Semis, Finals
            group_name TEXT,              -- A, B, C, D (for Group Stage)
            team1_id INTEGER,
            team2_id INTEGER,
            score1 INTEGER DEFAULT 0,
            score2 INTEGER DEFAULT 0,
            winner_id INTEGER,
            round_num INTEGER DEFAULT 1,
            status TEXT DEFAULT 'pending', -- pending, active, completed, dq, cancelled
            proof_url TEXT,
            match_room_channel_id INTEGER,
            scheduled_time TEXT,
            FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
            FOREIGN KEY(team1_id) REFERENCES teams(id),
            FOREIGN KEY(team2_id) REFERENCES teams(id)
        )
        """)

        # 5. Player Stats Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            tournaments_played INTEGER DEFAULT 0,
            championships_won INTEGER DEFAULT 0,
            mvp_count INTEGER DEFAULT 0,
            season_points INTEGER DEFAULT 0
        )
        """)

        # 6. MVP Records Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mvp_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER,
            user_id INTEGER,
            votes INTEGER DEFAULT 0,
            FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE
        )
        """)

        # 7. Guild Extended Config (V3)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS guild_config_v3 (
            guild_id INTEGER PRIMARY KEY,
            tier_channel_id INTEGER,
            tier_results_channel_id INTEGER,
            tier_staff_role_id INTEGER,
            tier_tester_role_id INTEGER,
            ranked_queue_channel_id INTEGER,
            ranked_results_channel_id INTEGER,
            ranked_role_id INTEGER,
            welcome_channel_id INTEGER,
            rules_channel_id INTEGER,
            announcement_channel_id INTEGER,
            ticket_category_id INTEGER,
            ticket_support_role_id INTEGER,
            suggestion_channel_id INTEGER,
            giveaway_channel_id INTEGER,
            FOREIGN KEY(guild_id) REFERENCES guild_config(guild_id)
        )
        """)
        for col in ['ticket_support_role_id', 'suggestion_channel_id', 'giveaway_channel_id',
                     'music_channel_id', 'music_category_id', 'staff_apps_channel_id']:
            try:
                cursor.execute(f"ALTER TABLE guild_config_v3 ADD COLUMN {col} INTEGER")
            except sqlite3.OperationalError:
                pass
        try:
            cursor.execute("ALTER TABLE guild_config_v3 ADD COLUMN autorole_ids TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        for col in ['tier_queue_channel_id', 'tier_queue_message_id']:
            try:
                cursor.execute(f"ALTER TABLE guild_config_v3 ADD COLUMN {col} INTEGER")
            except sqlite3.OperationalError:
                pass
        for col in ['tier_message_id', 'tier_roles']:
            try:
                cursor.execute(f"ALTER TABLE guild_config_v3 ADD COLUMN {col} TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass

        # 8. Tier Test Tickets
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tier_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            channel_id INTEGER,
            user_id INTEGER,
            gamemode TEXT NOT NULL,
            ign TEXT DEFAULT '',
            time TEXT DEFAULT '',
            previous_tier TEXT,
            status TEXT DEFAULT 'open',
            claimed_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        for col in ['ign', 'time', 'previous_tier', 'discord_tag']:
            try:
                cursor.execute(f"ALTER TABLE tier_tickets ADD COLUMN {col} TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass

        # 9. Tier Test Results
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tier_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            ign TEXT,
            previous_tier TEXT,
            new_tier TEXT,
            gamemode TEXT DEFAULT '',
            note TEXT,
            tester_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        try:
            cursor.execute("ALTER TABLE tier_results ADD COLUMN gamemode TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

        # 10. Ranked Queue
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ranked_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            gamemode TEXT NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 11. Ranked Matches (V3)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ranked_matches_v3 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            player1_id INTEGER,
            player2_id INTEGER,
            gamemode TEXT NOT NULL,
            winner_id INTEGER,
            score1 INTEGER DEFAULT 0,
            score2 INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            channel_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 12. Ranked Leaderboard
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ranked_leaderboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            gamemode TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            UNIQUE(guild_id, user_id, gamemode)
        )
        """)

        # 13. Warnings
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            moderator_id INTEGER,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 14. Giveaways
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS giveaways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            channel_id INTEGER,
            prize TEXT,
            winners INTEGER DEFAULT 1,
            ends_at TIMESTAMP,
            host_id INTEGER,
            message_id INTEGER,
            status TEXT DEFAULT 'active'
        )
        """)

        # 15. Suggestions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            channel_id INTEGER,
            user_id INTEGER,
            content TEXT,
            status TEXT DEFAULT 'pending',
            message_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 16. General Tickets
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS general_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            channel_id INTEGER,
            user_id INTEGER,
            subject TEXT,
            status TEXT DEFAULT 'open',
            claimed_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 17. Reaction Roles
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reaction_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            channel_id INTEGER,
            message_id INTEGER,
            emoji TEXT,
            role_id INTEGER,
            UNIQUE(message_id, emoji)
        )
        """)

        # 18. Tournament History Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournament_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER,
            name TEXT,
            mode TEXT,
            format TEXT,
            type TEXT,
            champion_team_name TEXT,
            champion_captain_id INTEGER,
            champion_player2_id INTEGER,
            runner_up_team_name TEXT,
            season INTEGER,
            date_ended TEXT
        )
        """)

        # 19. Comp System Config
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS comp_config (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER
        )
        """)

        # 20. Comp Players
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS comp_players (
            user_id INTEGER,
            guild_id INTEGER,
            ign TEXT DEFAULT '',
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            matches_played INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )
        """)

        # 21. Comp Matches
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS comp_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            channel_id INTEGER,
            challenger_id INTEGER,
            opponent_id INTEGER,
            challenger_ign TEXT,
            opponent_ign TEXT,
            winner_id INTEGER,
            status TEXT DEFAULT 'pending',
            message_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 22. Staff Applications
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            ign TEXT NOT NULL,
            age TEXT NOT NULL,
            why TEXT NOT NULL,
            experience TEXT NOT NULL,
            hours TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            message_id INTEGER,
            reviewed_by INTEGER,
            review_note TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP
        )
        """)

        for col in ['application_type TEXT DEFAULT "staff"', 'application_data TEXT DEFAULT ""', 'channel_id INTEGER']:
            try:
                cursor.execute(f"ALTER TABLE staff_applications ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass

        # Add staff_apps_role_id to guild_config_v3 if missing
        for col in ['staff_apps_role_id', 'application_panel_channel_id', 'application_review_channel_id']:
            try:
                cursor.execute(f"ALTER TABLE guild_config_v3 ADD COLUMN {col} INTEGER")
            except sqlite3.OperationalError:
                pass

        conn.commit()

# =====================================================================
# GUILD CONFIGURATION METHODS
# =====================================================================

def get_guild_config(guild_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)).fetchone()
        return dict(row) if row else None

def save_guild_config(guild_id: int, data: dict):
    with get_db() as conn:
        # Check if config exists
        exists = conn.execute("SELECT 1 FROM guild_config WHERE guild_id = ?", (guild_id,)).fetchone()
        if exists:
            # Dynamic update query
            keys = list(data.keys())
            vals = [data[k] for k in keys]
            set_clause = ", ".join([f"{k} = ?" for k in keys])
            conn.execute(f"UPDATE guild_config SET {set_clause} WHERE guild_id = ?", vals + [guild_id])
        else:
            # Insert query
            keys = ["guild_id"] + list(data.keys())
            vals = [guild_id] + [data[k] for k in data.keys()]
            placeholders = ", ".join(["?"] * len(keys))
            conn.execute(f"INSERT INTO guild_config ({', '.join(keys)}) VALUES ({placeholders})", vals)
        conn.commit()

# =====================================================================
# TOURNAMENT METHODS
# =====================================================================

def create_tournament(guild_id: int, name: str, mode: str, format_str: str, type_str: str, prize: str, host_id: int, max_teams: int = 16, rules: str = None):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO tournaments (guild_id, name, mode, format, type, stage, prize, host_id, max_teams, rules)
        VALUES (?, ?, ?, ?, ?, 'Registration', ?, ?, ?, ?)
        """, (guild_id, name, mode, format_str, type_str, prize, host_id, max_teams, rules))
        conn.commit()
        return cursor.lastrowid

def get_tournament(tournament_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,)).fetchone()
        return dict(row) if row else None

def get_active_tournament(guild_id: int):
    with get_db() as conn:
        # Get the latest non-ended tournament in this guild
        row = conn.execute("""
            SELECT * FROM tournaments 
            WHERE guild_id = ? AND stage != 'Ended' AND status = 'active'
            ORDER BY id DESC LIMIT 1
        """, (guild_id,)).fetchone()
        return dict(row) if row else None

def get_all_tournaments(guild_id: int):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tournaments WHERE guild_id = ? ORDER BY id DESC", (guild_id,)).fetchall()
        return [dict(r) for r in rows]

def update_tournament_stage(tournament_id: int, stage: str):
    with get_db() as conn:
        conn.execute("UPDATE tournaments SET stage = ? WHERE id = ?", (stage, tournament_id))
        conn.commit()

def update_tournament_rules(tournament_id: int, rules: str):
    with get_db() as conn:
        conn.execute("UPDATE tournaments SET rules = ? WHERE id = ?", (rules, tournament_id))
        conn.commit()

def end_tournament(tournament_id: int):
    with get_db() as conn:
        conn.execute("UPDATE tournaments SET stage = 'Ended', status = 'archived' WHERE id = ?", (tournament_id,))
        conn.commit()

def delete_tournament(tournament_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM tournaments WHERE id = ?", (tournament_id,))
        conn.commit()

# =====================================================================
# TEAM & REGISTRATION METHODS
# =====================================================================

def register_team(tournament_id: int, name: str, captain_id: int, p2: int = None, p3: int = None, p4: int = None, logo_url: str = None):
    with get_db() as conn:
        # Check team name uniqueness in this tournament
        exists = conn.execute("SELECT 1 FROM teams WHERE tournament_id = ? AND LOWER(name) = LOWER(?)", (tournament_id, name)).fetchone()
        if exists:
            raise ValueError(f"Team name '{name}' is already registered.")

        # Check player duplicate registration
        players = [p for p in [captain_id, p2, p3, p4] if p is not None]
        for p in players:
            chk = conn.execute("""
                SELECT name FROM teams 
                WHERE tournament_id = ? AND (captain_id = ? OR player2_id = ? OR player3_id = ? OR player4_id = ?)
            """, (tournament_id, p, p, p, p)).fetchone()
            if chk:
                raise ValueError(f"Player <@{p}> is already registered in team '{chk['name']}'.")

        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO teams (tournament_id, name, logo_url, captain_id, player2_id, player3_id, player4_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'registered')
        """, (tournament_id, name, logo_url, captain_id, p2, p3, p4))
        conn.commit()
        return cursor.lastrowid

def get_team(team_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()
        return dict(row) if row else None

def get_team_by_player(tournament_id: int, player_id: int):
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM teams 
            WHERE tournament_id = ? AND (captain_id = ? OR player2_id = ? OR player3_id = ? OR player4_id = ?)
        """, (tournament_id, player_id, player_id, player_id, player_id)).fetchone()
        return dict(row) if row else None

def get_tournament_teams(tournament_id: int):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM teams WHERE tournament_id = ? ORDER BY id ASC", (tournament_id,)).fetchall()
        return [dict(r) for r in rows]

def remove_team(tournament_id: int, team_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM teams WHERE tournament_id = ? AND id = ?", (tournament_id, team_id))
        conn.commit()

def update_team_status(team_id: int, status: str):
    with get_db() as conn:
        conn.execute("UPDATE teams SET status = ? WHERE id = ?", (status, team_id))
        conn.commit()

def update_team_seed(team_id: int, seed: int):
    with get_db() as conn:
        conn.execute("UPDATE teams SET seed = ? WHERE id = ?", (seed, team_id))
        conn.commit()

def update_team_score(team_id: int, wins: int, losses: int, points: int):
    with get_db() as conn:
        conn.execute("UPDATE teams SET wins = wins + ?, losses = losses + ?, points = points + ? WHERE id = ?", 
                     (wins, losses, points, team_id))
        conn.commit()

def reset_tournament_teams_score(tournament_id: int):
    with get_db() as conn:
        conn.execute("UPDATE teams SET wins = 0, losses = 0, points = 0, status = 'registered' WHERE tournament_id = ?", (tournament_id,))
        conn.commit()

# =====================================================================
# MATCH METHODS
# =====================================================================

def create_match(tournament_id: int, stage: str, team1_id: int, team2_id: int, group_name: str = None, round_num: int = 1):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO matches (tournament_id, stage, team1_id, team2_id, group_name, round_num, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (tournament_id, stage, team1_id, team2_id, group_name, round_num))
        conn.commit()
        return cursor.lastrowid

def get_match(match_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
        return dict(row) if row else None

def get_tournament_matches(tournament_id: int, stage: str = None, group_name: str = None):
    query = "SELECT * FROM matches WHERE tournament_id = ?"
    params = [tournament_id]
    
    if stage:
        query += " AND stage = ?"
        params.append(stage)
    if group_name:
        query += " AND group_name = ?"
        params.append(group_name)
        
    query += " ORDER BY round_num ASC, id ASC"
    
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

def update_match_result(match_id: int, score1: int, score2: int, winner_id: int, status: str = 'completed', proof_url: str = None):
    with get_db() as conn:
        # Fetch current match info to check previous status and teams
        match = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
        if not match:
            return
            
        was_completed = match['status'] == 'completed'
        t1_id = match['team1_id']
        t2_id = match['team2_id']
        
        # Update match details
        conn.execute("""
            UPDATE matches 
            SET score1 = ?, score2 = ?, winner_id = ?, status = ?, proof_url = ?
            WHERE id = ?
        """, (score1, score2, winner_id, status, proof_url, match_id))
        
        if status == 'completed':
            old_winner_id = match['winner_id'] if was_completed else None
            
            if old_winner_id != winner_id:
                # Revert old results if correcting a previously completed match
                if was_completed and old_winner_id:
                    old_loser_id = t2_id if old_winner_id == t1_id else t1_id
                    conn.execute("UPDATE teams SET wins = wins - 1, points = points - 3 WHERE id = ?", (old_winner_id,))
                    if old_loser_id:
                        conn.execute("UPDATE teams SET losses = losses - 1 WHERE id = ?", (old_loser_id,))
                
                # Apply new wins/losses and points
                if winner_id == t1_id:
                    conn.execute("UPDATE teams SET wins = wins + 1, points = points + 3 WHERE id = ?", (t1_id,))
                    if t2_id:
                        conn.execute("UPDATE teams SET losses = losses + 1 WHERE id = ?", (t2_id,))
                elif winner_id == t2_id:
                    conn.execute("UPDATE teams SET wins = wins + 1, points = points + 3 WHERE id = ?", (t2_id,))
                    if t1_id:
                        conn.execute("UPDATE teams SET losses = losses + 1 WHERE id = ?", (t1_id,))
                        
        conn.commit()

def update_match_schedule(match_id: int, scheduled_time: str):
    with get_db() as conn:
        conn.execute("UPDATE matches SET scheduled_time = ? WHERE id = ?", (scheduled_time, match_id))
        conn.commit()

def update_match_channel(match_id: int, channel_id: int):
    with get_db() as conn:
        conn.execute("UPDATE matches SET match_room_channel_id = ? WHERE id = ?", (channel_id, match_id))
        conn.commit()

def delete_matches_by_stage(tournament_id: int, stage: str):
    with get_db() as conn:
        conn.execute("DELETE FROM matches WHERE tournament_id = ? AND stage = ?", (tournament_id, stage))
        conn.commit()

# =====================================================================
# PLAYER STATS & MVP METHODS
# =====================================================================

def update_player_stat(user_id: int, username: str, wins: int = 0, losses: int = 0, played: int = 0, champion: int = 0, mvp: int = 0, points: int = 0):
    with get_db() as conn:
        exists = conn.execute("SELECT 1 FROM player_stats WHERE user_id = ?", (user_id,)).fetchone()
        if exists:
            conn.execute("""
                UPDATE player_stats 
                SET username = ?, wins = wins + ?, losses = losses + ?, tournaments_played = tournaments_played + ?, 
                    championships_won = championships_won + ?, mvp_count = mvp_count + ?, season_points = season_points + ?
                WHERE user_id = ?
            """, (username, wins, losses, played, champion, mvp, points, user_id))
        else:
            conn.execute("""
                INSERT INTO player_stats (user_id, username, wins, losses, tournaments_played, championships_won, mvp_count, season_points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, wins, losses, played, champion, mvp, points))
        conn.commit()

def get_player_stats(user_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM player_stats WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

def get_season_leaderboard(limit: int = 10):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM player_stats ORDER BY season_points DESC, championships_won DESC, wins DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

def vote_mvp(tournament_id: int, user_id: int):
    with get_db() as conn:
        exists = conn.execute("SELECT 1 FROM mvp_records WHERE tournament_id = ? AND user_id = ?", (tournament_id, user_id)).fetchone()
        if exists:
            conn.execute("UPDATE mvp_records SET votes = votes + 1 WHERE tournament_id = ? AND user_id = ?", (tournament_id, user_id))
        else:
            conn.execute("INSERT INTO mvp_records (tournament_id, user_id, votes) VALUES (?, ?, 1)", (tournament_id, user_id))
        conn.commit()

def get_mvp_leaderboard(tournament_id: int):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT m.user_id, m.votes, p.username 
            FROM mvp_records m 
            LEFT JOIN player_stats p ON m.user_id = p.user_id
            WHERE m.tournament_id = ? 
            ORDER BY m.votes DESC
        """, (tournament_id,)).fetchall()
        return [dict(r) for r in rows]

# =====================================================================
# HISTORY METHODS
# =====================================================================

def add_tournament_history(tournament_id: int, name: str, mode: str, format_str: str, type_str: str, champion_team_name: str, champion_captain_id: int, champion_player2_id: int, runner_up_team_name: str, season: int, date_ended: str):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO tournament_history (tournament_id, name, mode, format, type, champion_team_name, champion_captain_id, champion_player2_id, runner_up_team_name, season, date_ended)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tournament_id, name, mode, format_str, type_str, champion_team_name, champion_captain_id, champion_player2_id, runner_up_team_name, season, date_ended))
        conn.commit()

def get_history(limit: int = 10):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tournament_history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

# =====================================================================
# V3: GUILD CONFIG EXTENDED
# =====================================================================

def get_guild_config_v3(guild_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM guild_config_v3 WHERE guild_id = ?", (guild_id,)).fetchone()
        return dict(row) if row else None

def save_guild_config_v3(guild_id: int, data: dict):
    with get_db() as conn:
        exists = conn.execute("SELECT 1 FROM guild_config_v3 WHERE guild_id = ?", (guild_id,)).fetchone()
        if exists:
            keys = list(data.keys())
            vals = [data[k] for k in keys]
            set_clause = ", ".join([f"{k} = ?" for k in keys])
            conn.execute(f"UPDATE guild_config_v3 SET {set_clause} WHERE guild_id = ?", vals + [guild_id])
        else:
            keys = ["guild_id"] + list(data.keys())
            vals = [guild_id] + [data[k] for k in data.keys()]
            placeholders = ", ".join(["?"] * len(keys))
            conn.execute(f"INSERT INTO guild_config_v3 ({', '.join(keys)}) VALUES ({placeholders})", vals)
        conn.commit()

# =====================================================================
# V3: TIER TEST SYSTEM
# =====================================================================

def create_tier_ticket(guild_id: int, channel_id: int, user_id: int, gamemode: str, ign: str = '', time: str = '', discord_tag: str = ''):
    previous = get_tier_results_for_user(guild_id, user_id)
    prev_tier = previous[0]['new_tier'] if previous else None
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tier_tickets (guild_id, channel_id, user_id, gamemode, ign, time, previous_tier, discord_tag, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')
        """, (guild_id, channel_id, user_id, gamemode, ign, time, prev_tier, discord_tag))
        conn.commit()
        return cursor.lastrowid

def get_tier_ticket(channel_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tier_tickets WHERE channel_id = ?", (channel_id,)).fetchone()
        return dict(row) if row else None

def get_tier_ticket_by_id(ticket_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tier_tickets WHERE id = ?", (ticket_id,)).fetchone()
        return dict(row) if row else None

def claim_tier_ticket(ticket_id: int, claimed_by: int):
    with get_db() as conn:
        conn.execute("UPDATE tier_tickets SET claimed_by = ?, status = 'claimed' WHERE id = ?", (claimed_by, ticket_id))
        conn.commit()

def close_tier_ticket(ticket_id: int):
    with get_db() as conn:
        conn.execute("UPDATE tier_tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
        conn.commit()

def complete_tier_ticket(ticket_id: int, ign: str, new_tier: str, note: str, tester_id: int, previous_tier: str = None):
    with get_db() as conn:
        ticket = conn.execute("SELECT * FROM tier_tickets WHERE id = ?", (ticket_id,)).fetchone()
        if not ticket:
            return
        prev = previous_tier if previous_tier is not None else ticket['previous_tier']
        conn.execute("""
            INSERT INTO tier_results (guild_id, user_id, ign, previous_tier, new_tier, gamemode, note, tester_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticket['guild_id'], ticket['user_id'], ign, prev, new_tier, ticket['gamemode'], note, tester_id))
        conn.execute("UPDATE tier_tickets SET status = 'completed' WHERE id = ?", (ticket_id,))
        conn.commit()

def save_tier_result(guild_id: int, user_id: int, ign: str, previous_tier: str, new_tier: str, note: str, tester_id: int, gamemode: str = ''):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO tier_results (guild_id, user_id, ign, previous_tier, new_tier, gamemode, note, tester_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (guild_id, user_id, ign, previous_tier, new_tier, gamemode, note, tester_id))
        conn.commit()

def get_tier_results(guild_id: int, limit: int = 10):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tier_results WHERE guild_id = ? ORDER BY id DESC LIMIT ?", (guild_id, limit)).fetchall()
        return [dict(r) for r in rows]

def get_tier_results_for_user(guild_id: int, user_id: int):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM tier_results WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 1",
            (guild_id, user_id)
        ).fetchall()
        return [dict(r) for r in rows]

# Tier role mapping
def set_tier_role(guild_id: int, tier: str, role_id: int):
    import json
    cfg = get_guild_config_v3(guild_id) or {}
    raw = cfg.get('tier_roles') or '{}'
    mapping = json.loads(raw) if isinstance(raw, str) else raw
    mapping[tier.upper()] = role_id
    save_guild_config_v3(guild_id, {'tier_roles': json.dumps(mapping)})

def unset_tier_role(guild_id: int, tier: str):
    import json
    cfg = get_guild_config_v3(guild_id) or {}
    raw = cfg.get('tier_roles') or '{}'
    mapping = json.loads(raw) if isinstance(raw, str) else raw
    mapping.pop(tier.upper(), None)
    save_guild_config_v3(guild_id, {'tier_roles': json.dumps(mapping)})

def get_tier_roles(guild_id: int) -> dict:
    import json
    cfg = get_guild_config_v3(guild_id)
    if not cfg or not cfg.get('tier_roles'):
        return {}
    raw = cfg['tier_roles']
    return json.loads(raw) if isinstance(raw, str) else raw

# =====================================================================
# V3: TIER TICKET DISPLAY
# =====================================================================

def get_tier_ticket_summary(guild_id: int):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT gamemode, COUNT(*) as count FROM tier_tickets WHERE guild_id = ? AND status = 'open' GROUP BY gamemode ORDER BY gamemode",
            (guild_id,)
        ).fetchall()
        return {r['gamemode']: r['count'] for r in rows}

def get_tier_tickets_by_gamemode(guild_id: int, gamemode: str):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM tier_tickets WHERE guild_id = ? AND gamemode = ? AND status = 'open' ORDER BY created_at ASC",
            (guild_id, gamemode)
        ).fetchall()
        return [dict(r) for r in rows]

def get_open_tier_tickets_count(guild_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as count FROM tier_tickets WHERE guild_id = ? AND status = 'open'",
            (guild_id,)
        ).fetchone()
        return row['count'] if row else 0

# =====================================================================
# V3: RANKED SYSTEM
# =====================================================================

def add_to_ranked_queue(guild_id: int, user_id: int, gamemode: str):
    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM ranked_queue WHERE guild_id = ? AND user_id = ? AND gamemode = ?",
            (guild_id, user_id, gamemode)
        ).fetchone()
        if not exists:
            conn.execute("INSERT INTO ranked_queue (guild_id, user_id, gamemode) VALUES (?, ?, ?)", (guild_id, user_id, gamemode))
            conn.commit()
            return True
        return False

def remove_from_ranked_queue(guild_id: int, user_id: int, gamemode: str):
    with get_db() as conn:
        conn.execute("DELETE FROM ranked_queue WHERE guild_id = ? AND user_id = ? AND gamemode = ?", (guild_id, user_id, gamemode))
        conn.commit()

def find_ranked_match(guild_id: int, gamemode: str, user_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM ranked_queue WHERE guild_id = ? AND gamemode = ? AND user_id != ? ORDER BY joined_at ASC LIMIT 1",
            (guild_id, gamemode, user_id)
        ).fetchone()
        return dict(row) if row else None

def get_ranked_queue_count(guild_id: int, gamemode: str):
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM ranked_queue WHERE guild_id = ? AND gamemode = ?", (guild_id, gamemode)).fetchone()
        return row['cnt'] if row else 0

def create_ranked_match(guild_id: int, player1_id: int, player2_id: int, gamemode: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ranked_matches_v3 (guild_id, player1_id, player2_id, gamemode, status)
            VALUES (?, ?, ?, ?, 'pending')
        """, (guild_id, player1_id, player2_id, gamemode))
        conn.commit()
        return cursor.lastrowid

def get_ranked_match(match_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM ranked_matches_v3 WHERE id = ?", (match_id,)).fetchone()
        return dict(row) if row else None

def complete_ranked_match(match_id: int, winner_id: int, score1: int, score2: int, channel_id: int = None):
    with get_db() as conn:
        conn.execute("""
            UPDATE ranked_matches_v3 SET winner_id = ?, score1 = ?, score2 = ?, status = 'completed', channel_id = ?
            WHERE id = ?
        """, (winner_id, score1, score2, channel_id, match_id))
        conn.commit()

def get_ranked_stats(guild_id: int, user_id: int, gamemode: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM ranked_leaderboard WHERE guild_id = ? AND user_id = ? AND gamemode = ?",
            (guild_id, user_id, gamemode)
        ).fetchone()
        return dict(row) if row else None

def update_ranked_stats(guild_id: int, user_id: int, gamemode: str, points: int, win: bool):
    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM ranked_leaderboard WHERE guild_id = ? AND user_id = ? AND gamemode = ?",
            (guild_id, user_id, gamemode)
        ).fetchone()
        if exists:
            if win:
                conn.execute("""
                    UPDATE ranked_leaderboard SET points = points + ?, wins = wins + 1
                    WHERE guild_id = ? AND user_id = ? AND gamemode = ?
                """, (points, guild_id, user_id, gamemode))
            else:
                conn.execute("""
                    UPDATE ranked_leaderboard SET points = points + ?, losses = losses + 1
                    WHERE guild_id = ? AND user_id = ? AND gamemode = ?
                """, (points, guild_id, user_id, gamemode))
        else:
            if win:
                conn.execute("""
                    INSERT INTO ranked_leaderboard (guild_id, user_id, gamemode, points, wins, losses)
                    VALUES (?, ?, ?, ?, 1, 0)
                """, (guild_id, user_id, gamemode, points))
            else:
                conn.execute("""
                    INSERT INTO ranked_leaderboard (guild_id, user_id, gamemode, points, wins, losses)
                    VALUES (?, ?, ?, ?, 0, 1)
                """, (guild_id, user_id, gamemode, points))
        conn.commit()

def get_ranked_leaderboard(guild_id: int, gamemode: str = None, limit: int = 10):
    with get_db() as conn:
        if gamemode:
            rows = conn.execute("""
                SELECT * FROM ranked_leaderboard
                WHERE guild_id = ? AND gamemode = ?
                ORDER BY points DESC, wins DESC
                LIMIT ?
            """, (guild_id, gamemode, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM ranked_leaderboard
                WHERE guild_id = ?
                ORDER BY points DESC, wins DESC
                LIMIT ?
            """, (guild_id, limit)).fetchall()
        return [dict(r) for r in rows]

# =====================================================================
# V3: WARNINGS
# =====================================================================

def add_warning(guild_id: int, user_id: int, moderator_id: int, reason: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
                       (guild_id, user_id, moderator_id, reason))
        conn.commit()
        return cursor.lastrowid

def get_warnings(guild_id: int, user_id: int):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC", (guild_id, user_id)).fetchall()
        return [dict(r) for r in rows]

def clear_warnings(guild_id: int, user_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        conn.commit()

# =====================================================================
# V3: GIVEAWAYS
# =====================================================================

def create_giveaway(guild_id: int, channel_id: int, prize: str, winners: int, ends_at: str, host_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO giveaways (guild_id, channel_id, prize, winners, ends_at, host_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (guild_id, channel_id, prize, winners, ends_at, host_id))
        conn.commit()
        return cursor.lastrowid

def get_active_giveaways(guild_id: int):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM giveaways WHERE guild_id = ? AND status = 'active'", (guild_id,)).fetchall()
        return [dict(r) for r in rows]

def get_giveaway(message_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM giveaways WHERE message_id = ?", (message_id,)).fetchone()
        return dict(row) if row else None

def end_giveaway(giveaway_id: int):
    with get_db() as conn:
        conn.execute("UPDATE giveaways SET status = 'ended' WHERE id = ?", (giveaway_id,))
        conn.commit()

def set_giveaway_message(giveaway_id: int, message_id: int):
    with get_db() as conn:
        conn.execute("UPDATE giveaways SET message_id = ? WHERE id = ?", (message_id, giveaway_id))
        conn.commit()

# =====================================================================
# V3: SUGGESTIONS
# =====================================================================

def create_suggestion(guild_id: int, channel_id: int, user_id: int, content: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO suggestions (guild_id, channel_id, user_id, content)
            VALUES (?, ?, ?, ?)
        """, (guild_id, channel_id, user_id, content))
        conn.commit()
        return cursor.lastrowid

def get_suggestion(message_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM suggestions WHERE message_id = ?", (message_id,)).fetchone()
        return dict(row) if row else None

def update_suggestion_status(message_id: int, status: str):
    with get_db() as conn:
        conn.execute("UPDATE suggestions SET status = ? WHERE message_id = ?", (status, message_id))
        conn.commit()

def set_suggestion_message(suggestion_id: int, message_id: int):
    with get_db() as conn:
        conn.execute("UPDATE suggestions SET message_id = ? WHERE id = ?", (message_id, suggestion_id))
        conn.commit()

# =====================================================================
# V3: GENERAL TICKETS
# =====================================================================

def create_general_ticket(guild_id: int, channel_id: int, user_id: int, subject: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO general_tickets (guild_id, channel_id, user_id, subject)
            VALUES (?, ?, ?, ?)
        """, (guild_id, channel_id, user_id, subject))
        conn.commit()
        return cursor.lastrowid

def get_general_ticket(channel_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM general_tickets WHERE channel_id = ?", (channel_id,)).fetchone()
        return dict(row) if row else None

def claim_general_ticket(ticket_id: int, claimed_by: int):
    with get_db() as conn:
        conn.execute("UPDATE general_tickets SET claimed_by = ?, status = 'claimed' WHERE id = ?", (claimed_by, ticket_id))
        conn.commit()

def close_general_ticket(ticket_id: int):
    with get_db() as conn:
        conn.execute("UPDATE general_tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
        conn.commit()

# =====================================================================
# V3: REACTION ROLES
# =====================================================================

def add_reaction_role(guild_id: int, channel_id: int, message_id: int, emoji: str, role_id: int):
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO reaction_roles (guild_id, channel_id, message_id, emoji, role_id)
            VALUES (?, ?, ?, ?, ?)
        """, (guild_id, channel_id, message_id, emoji, role_id))
        conn.commit()

def remove_reaction_role(message_id: int, emoji: str):
    with get_db() as conn:
        conn.execute("DELETE FROM reaction_roles WHERE message_id = ? AND emoji = ?", (message_id, emoji))
        conn.commit()

def get_reaction_roles(message_id: int):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM reaction_roles WHERE message_id = ?", (message_id,)).fetchall()
        return [dict(r) for r in rows]

def get_reaction_role(message_id: int, emoji: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM reaction_roles WHERE message_id = ? AND emoji = ?", (message_id, emoji)).fetchone()
        return dict(row) if row else None

def get_all_reaction_roles(guild_id: int):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM reaction_roles WHERE guild_id = ?", (guild_id,)).fetchall()
        return [dict(r) for r in rows]

# =====================================================================
# V3: AUTO-ROLE
# =====================================================================

def get_autorole_ids(guild_id: int) -> list:
    cfg = get_guild_config_v3(guild_id)
    if not cfg or not cfg.get('autorole_ids'):
        return []
    raw = cfg['autorole_ids']
    if not raw:
        return []
    return [int(x) for x in raw.split(',') if x.strip().isdigit()]

def save_autorole_ids(guild_id: int, role_ids: list):
    cfg = get_guild_config_v3(guild_id) or {}
    cfg['autorole_ids'] = ','.join(str(r) for r in role_ids)
    save_guild_config_v3(guild_id, cfg)

# =====================================================================
# V3: COMP SYSTEM
# =====================================================================

def get_comp_config(guild_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM comp_config WHERE guild_id = ?", (guild_id,)).fetchone()
        return dict(row) if row else None

def set_comp_channel(guild_id: int, channel_id: int):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO comp_config (guild_id, channel_id) VALUES (?, ?)", (guild_id, channel_id))
        conn.commit()

def get_or_create_comp_player(user_id: int, guild_id: int, ign: str = ''):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM comp_players WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)).fetchone()
        if row:
            return dict(row)
        conn.execute("INSERT INTO comp_players (user_id, guild_id, ign) VALUES (?, ?, ?)", (user_id, guild_id, ign))
        conn.commit()
        row = conn.execute("SELECT * FROM comp_players WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)).fetchone()
        return dict(row) if row else None

def update_comp_player_ign(user_id: int, guild_id: int, ign: str):
    with get_db() as conn:
        conn.execute("UPDATE comp_players SET ign = ? WHERE user_id = ? AND guild_id = ?", (ign, user_id, guild_id))
        conn.commit()

def create_comp_match(guild_id: int, channel_id: int, challenger_id: int, opponent_id: int, challenger_ign: str, opponent_ign: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO comp_matches (guild_id, channel_id, challenger_id, opponent_id, challenger_ign, opponent_ign)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (guild_id, channel_id, challenger_id, opponent_id, challenger_ign, opponent_ign))
        conn.commit()
        return cursor.lastrowid

def get_comp_match(match_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM comp_matches WHERE id = ?", (match_id,)).fetchone()
        return dict(row) if row else None

def update_comp_match_status(match_id: int, status: str, winner_id: int = None):
    with get_db() as conn:
        if winner_id:
            conn.execute("UPDATE comp_matches SET status = ?, winner_id = ? WHERE id = ?", (status, winner_id, match_id))
        else:
            conn.execute("UPDATE comp_matches SET status = ? WHERE id = ?", (status, match_id))
        conn.commit()

def award_comp_points(user_id: int, guild_id: int, points_delta: int, ign: str = ''):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM comp_players WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)).fetchone()
        if not row:
            conn.execute("INSERT INTO comp_players (user_id, guild_id, ign, points) VALUES (?, ?, ?, ?)",
                         (user_id, guild_id, ign, max(0, points_delta)))
        else:
            conn.execute("UPDATE comp_players SET points = points + ?, matches_played = matches_played + 1 WHERE user_id = ? AND guild_id = ?",
                         (points_delta, user_id, guild_id))
        conn.commit()

def record_comp_win(user_id: int, guild_id: int, ign: str = ''):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM comp_players WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)).fetchone()
        if not row:
            conn.execute("INSERT INTO comp_players (user_id, guild_id, ign, wins) VALUES (?, ?, ?, 1)",
                         (user_id, guild_id, ign))
        else:
            conn.execute("UPDATE comp_players SET wins = wins + 1 WHERE user_id = ? AND guild_id = ?",
                         (user_id, guild_id))
        conn.commit()

def record_comp_loss(user_id: int, guild_id: int, ign: str = ''):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM comp_players WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)).fetchone()
        if not row:
            conn.execute("INSERT INTO comp_players (user_id, guild_id, ign, losses) VALUES (?, ?, ?, 1)",
                         (user_id, guild_id, ign))
        else:
            conn.execute("UPDATE comp_players SET losses = losses + 1 WHERE user_id = ? AND guild_id = ?",
                         (user_id, guild_id))
        conn.commit()

def get_comp_leaderboard(guild_id: int, limit: int = 10):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM comp_players WHERE guild_id = ? ORDER BY points DESC, wins DESC LIMIT ?",
            (guild_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]

def get_comp_player(user_id: int, guild_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM comp_players WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)).fetchone()
        return dict(row) if row else None

def get_pending_comp_match_for_user(user_id: int, guild_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM comp_matches WHERE guild_id = ? AND opponent_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1",
            (guild_id, user_id)
        ).fetchone()
        return dict(row) if row else None

# =====================================================================
# V3: STAFF APPLICATIONS
# =====================================================================

def create_staff_application(guild_id: int, user_id: int, ign: str, age: str, why: str, experience: str, hours: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO staff_applications (guild_id, user_id, ign, age, why, experience, hours)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (guild_id, user_id, ign, age, why, experience, hours))
        conn.commit()
        return cursor.lastrowid

def get_staff_application(app_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM staff_applications WHERE id = ?", (app_id,)).fetchone()
        return dict(row) if row else None

def get_pending_staff_application(guild_id: int, user_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM staff_applications WHERE guild_id = ? AND user_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1",
            (guild_id, user_id)
        ).fetchone()
        return dict(row) if row else None

def get_staff_applications(guild_id: int, status: str = None, limit: int = 20):
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM staff_applications WHERE guild_id = ? AND status = ? ORDER BY id DESC LIMIT ?",
                (guild_id, status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM staff_applications WHERE guild_id = ? ORDER BY id DESC LIMIT ?",
                (guild_id, limit)
            ).fetchall()
        return [dict(r) for r in rows]

def update_staff_application_status(app_id: int, status: str, reviewed_by: int = None, review_note: str = ''):
    with get_db() as conn:
        import datetime
        conn.execute(
            "UPDATE staff_applications SET status = ?, reviewed_by = ?, review_note = ?, reviewed_at = ? WHERE id = ?",
            (status, reviewed_by, review_note, datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), app_id)
        )
        conn.commit()

def set_staff_application_message(app_id: int, message_id: int):
    with get_db() as conn:
        conn.execute("UPDATE staff_applications SET message_id = ? WHERE id = ?", (message_id, app_id))
        conn.commit()

def update_staff_application_type(app_id: int, app_type: str):
    with get_db() as conn:
        conn.execute("UPDATE staff_applications SET application_type = ? WHERE id = ?", (app_type, app_id))
        conn.commit()

def update_staff_application_data(app_id: int, data: str):
    with get_db() as conn:
        conn.execute("UPDATE staff_applications SET application_data = ? WHERE id = ?", (data, app_id))
        conn.commit()

def set_staff_application_channel(app_id: int, channel_id: int):
    with get_db() as conn:
        conn.execute("UPDATE staff_applications SET channel_id = ? WHERE id = ?", (channel_id, app_id))
        conn.commit()
