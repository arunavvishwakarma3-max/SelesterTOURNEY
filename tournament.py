import math
import random
import database

def generate_initial_bracket(tournament_id: int):
    """
    Generates the initial round of matches/groups based on the tournament type and registered/checked-in teams.
    """
    tournament = database.get_tournament(tournament_id)
    if not tournament:
        return False
    
    # We only match teams that have checked_in (or registered if check-in was skipped)
    teams = database.get_tournament_teams(tournament_id)
    active_teams = [t for t in teams if t['status'] in ('checked_in', 'registered')]
    
    # Shuffle for random seeding
    random.shuffle(active_teams)
    
    t_type = tournament['type']
    
    if t_type == "Single Elimination":
        generate_single_elim_round(tournament_id, active_teams, round_num=1)
        database.update_tournament_stage(tournament_id, "Qualifiers")
        
    elif t_type == "Double Elimination":
        generate_double_elim_round_1(tournament_id, active_teams)
        database.update_tournament_stage(tournament_id, "Qualifiers")
        
    elif t_type == "Round Robin":
        generate_round_robin(tournament_id, active_teams)
        database.update_tournament_stage(tournament_id, "Group Stage")
        
    elif t_type == "Swiss Format":
        generate_swiss_round(tournament_id, active_teams, round_num=1)
        database.update_tournament_stage(tournament_id, "Qualifiers")
        
    elif t_type == "Group Stage + Playoffs":
        generate_group_stage_groups(tournament_id, active_teams)
        database.update_tournament_stage(tournament_id, "Group Stage")
        
    return True

# =====================================================================
# SINGLE ELIMINATION BRACKET GENERATION
# =====================================================================

def generate_single_elim_round(tournament_id: int, teams: list, round_num: int):
    """
    Generate matches for a Single Elimination round.
    If the number of teams is not a power of 2, create BYE matches.
    """
    n = len(teams)
    if n == 0:
        return
    
    if round_num == 1:
        # Calculate next power of 2 to handle BYEs
        next_pow = 2 ** math.ceil(math.log2(n)) if n > 0 else 0
        byes = next_pow - n
        
        # Select teams that get a BYE (advanced immediately)
        bye_teams = teams[:byes]
        match_teams = teams[byes:]
        
        # Create matches for active pairings
        for i in range(0, len(match_teams), 2):
            t1 = match_teams[i]
            t2 = match_teams[i+1] if (i + 1) < len(match_teams) else None
            
            if t2:
                database.create_match(tournament_id, "Qualifiers", t1['id'], t2['id'], round_num=round_num)
            else:
                # Odd team without match (practically a bye)
                match_id = database.create_match(tournament_id, "Qualifiers", t1['id'], None, round_num=round_num)
                database.update_match_result(match_id, 1, 0, t1['id'], 'completed')
                database.update_team_status(t1['id'], 'qualified')
                
        # Advance bye teams directly
        for t in bye_teams:
            # Create a completed match against None (BYE)
            match_id = database.create_match(tournament_id, "Qualifiers", t['id'], None, round_num=round_num)
            database.update_match_result(match_id, 1, 0, t['id'], 'completed')
            database.update_team_status(t['id'], 'qualified')
    else:
        # For later rounds, pair teams in order
        for i in range(0, len(teams), 2):
            t1 = teams[i]
            t2 = teams[i+1] if (i + 1) < len(teams) else None
            
            stage = "Qualifiers"
            if len(teams) <= 4:
                stage = "Semis"
            if len(teams) == 2:
                stage = "Finals"
                
            if t2:
                database.create_match(tournament_id, stage, t1['id'], t2['id'], round_num=round_num)
            else:
                match_id = database.create_match(tournament_id, stage, t1['id'], None, round_num=round_num)
                database.update_match_result(match_id, 1, 0, t1['id'], 'completed')
                database.update_team_status(t1['id'], 'qualified')

# =====================================================================
# DOUBLE ELIMINATION BRACKET GENERATION
# =====================================================================

def generate_double_elim_round_1(tournament_id: int, teams: list):
    """
    Initialize a Double Elimination bracket (Winners Round 1).
    Uses 'group_name' as 'winners' or 'losers' to differentiate brackets.
    """
    n = len(teams)
    next_pow = 2 ** math.ceil(math.log2(n)) if n > 0 else 0
    byes = next_pow - n
    
    bye_teams = teams[:byes]
    match_teams = teams[byes:]
    
    # Winners Bracket Round 1
    for i in range(0, len(match_teams), 2):
        t1 = match_teams[i]
        t2 = match_teams[i+1] if (i + 1) < len(match_teams) else None
        
        if t2:
            database.create_match(tournament_id, "Qualifiers", t1['id'], t2['id'], group_name="winners", round_num=1)
        else:
            match_id = database.create_match(tournament_id, "Qualifiers", t1['id'], None, group_name="winners", round_num=1)
            database.update_match_result(match_id, 1, 0, t1['id'], 'completed')
            database.update_team_status(t1['id'], 'qualified')
            
    for t in bye_teams:
        match_id = database.create_match(tournament_id, "Qualifiers", t['id'], None, group_name="winners", round_num=1)
        database.update_match_result(match_id, 1, 0, t['id'], 'completed')
        database.update_team_status(t['id'], 'qualified')

# =====================================================================
# ROUND ROBIN SCHEDULER
# =====================================================================

def generate_round_robin(tournament_id: int, teams: list, group_name: str = None, stage: str = "Group Stage"):
    """
    Generate all matches for a Round Robin format using the Circle Method.
    """
    n = len(teams)
    if n == 0:
        return
    
    # If odd, add a dummy team representing a BYE
    temp_teams = list(teams)
    if n % 2 != 0:
        temp_teams.append(None)
        
    num_rounds = len(temp_teams) - 1
    half_size = len(temp_teams) // 2
    
    for round_num in range(1, num_rounds + 1):
        for i in range(half_size):
            t1 = temp_teams[i]
            t2 = temp_teams[len(temp_teams) - 1 - i]
            
            if t1 and t2:
                database.create_match(tournament_id, stage, t1['id'], t2['id'], group_name=group_name, round_num=round_num)
            elif t1 and not t2:
                # t1 gets a bye in this round
                match_id = database.create_match(tournament_id, stage, t1['id'], None, group_name=group_name, round_num=round_num)
                database.update_match_result(match_id, 1, 0, t1['id'], 'completed')
            elif t2 and not t1:
                # t2 gets a bye in this round
                match_id = database.create_match(tournament_id, stage, None, t2['id'], group_name=group_name, round_num=round_num)
                database.update_match_result(match_id, 0, 1, t2['id'], 'completed')
                
        # Rotate teams (keep first fixed, rotate others)
        temp_teams = [temp_teams[0]] + [temp_teams[-1]] + temp_teams[1:-1]

# =====================================================================
# SWISS FORMAT MATCH GENERATION
# =====================================================================

def generate_swiss_round(tournament_id: int, teams: list, round_num: int):
    """
    Generate pairings for a Swiss round.
    Pairs teams with the same/similar score (points/wins) that haven't played each other.
    """
    # Sort teams by wins desc, points desc
    sorted_teams = sorted(teams, key=lambda x: (x['wins'], x['points']), reverse=True)
    
    # Fetch all previous matches to avoid duplicate pairings
    prev_matches = database.get_tournament_matches(tournament_id)
    played_pairs = set()
    for m in prev_matches:
        if m['team1_id'] and m['team2_id']:
            played_pairs.add((m['team1_id'], m['team2_id']))
            played_pairs.add((m['team2_id'], m['team1_id']))
            
    paired = set()
    matches_to_create = []
    
    for i in range(len(sorted_teams)):
        t1 = sorted_teams[i]
        if t1['id'] in paired:
            continue
            
        # Find partner
        partner = None
        for j in range(i + 1, len(sorted_teams)):
            t2 = sorted_teams[j]
            if t2['id'] in paired:
                continue
            # Check if they played before
            if (t1['id'], t2['id']) not in played_pairs:
                partner = t2
                break
                
        # If no partner found who they haven't played, pick the first unpaired team
        if not partner:
            for j in range(i + 1, len(sorted_teams)):
                t2 = sorted_teams[j]
                if t2['id'] not in paired:
                    partner = t2
                    break
                    
        paired.add(t1['id'])
        if partner:
            paired.add(partner['id'])
            matches_to_create.append((t1['id'], partner['id']))
        else:
            # Odd team gets a BYE
            matches_to_create.append((t1['id'], None))
            
    for t1_id, t2_id in matches_to_create:
        if t2_id:
            database.create_match(tournament_id, "Qualifiers", t1_id, t2_id, round_num=round_num)
        else:
            # Bye match
            match_id = database.create_match(tournament_id, "Qualifiers", t1_id, None, round_num=round_num)
            database.update_match_result(match_id, 1, 0, t1_id, 'completed')
            # Increase wins/points
            database.update_team_score(t1_id, 1, 0, 3)

# =====================================================================
# GROUP STAGE + PLAYOFFS GENERATION
# =====================================================================

def generate_group_stage_groups(tournament_id: int, teams: list):
    """
    Split teams into Groups A, B, C, D and generate Round Robin matches within each group.
    """
    groups = {"A": [], "B": [], "C": [], "D": []}
    group_names = ["A", "B", "C", "D"]
    
    # Distribute teams round-robin into groups
    for idx, team in enumerate(teams):
        g_name = group_names[idx % 4]
        groups[g_name].append(team)
        
    for g_name, g_teams in groups.items():
        # Generate Round Robin for this group
        generate_round_robin(tournament_id, g_teams, group_name=g_name, stage="Group Stage")

# =====================================================================
# TOURNAMENT BRACKET ADVANCEMENT / RESOLUTION
# =====================================================================

def check_and_advance_stage(tournament_id: int):
    """
    Checks if all matches of the current stage are finished.
    If yes, advances the tournament to the next stage (e.g. Group Stage -> Qualifiers -> Semis -> Finals -> Ended).
    Returns a dictionary indicating what changed and any announcements to display.
    """
    tournament = database.get_tournament(tournament_id)
    if not tournament or tournament['stage'] == "Ended":
        return None
        
    stage = tournament['stage']
    t_type = tournament['type']
    
    # Get all matches for this tournament
    matches = database.get_tournament_matches(tournament_id)
    stage_matches = [m for m in matches if m['stage'] == stage]
    
    # If no matches created yet or some are pending, we can't advance
    if not stage_matches:
        return None
        
    if any(m['status'] == 'pending' or m['status'] == 'active' for m in stage_matches):
        return None # Still pending matches
        
    # All matches in current stage are completed! Let's advance
    if t_type == "Single Elimination":
        return advance_single_elim(tournament_id, stage, stage_matches)
        
    elif t_type == "Double Elimination":
        return advance_double_elim(tournament_id, stage, matches)
        
    elif t_type == "Round Robin":
        # Round Robin has no playoffs, the team with most points/wins is champion
        return end_round_robin_or_swiss(tournament_id)
        
    elif t_type == "Swiss Format":
        # Swiss typically runs 3 or 4 rounds, then we determine standings
        # Check if we reached max rounds. Let's say 3 rounds for <=8 teams, 4 rounds for <=16 teams.
        teams = database.get_tournament_teams(tournament_id)
        max_rounds = math.ceil(math.log2(len(teams))) if len(teams) > 0 else 3
        
        current_round = max(m['round_num'] for m in stage_matches)
        if current_round < max_rounds:
            # Generate next Swiss round
            generate_swiss_round(tournament_id, teams, round_num=current_round + 1)
            return {"action": "swiss_next_round", "round": current_round + 1}
        else:
            return end_round_robin_or_swiss(tournament_id)
            
    elif t_type == "Group Stage + Playoffs":
        return advance_group_stage_to_playoffs(tournament_id, stage, matches)
        
    return None

def advance_single_elim(tournament_id: int, current_stage: str, stage_matches: list):
    # Collect winners
    winners_ids = [m['winner_id'] for m in stage_matches if m['winner_id'] is not None]
    
    # Load corresponding team entities
    teams = [database.get_team(wid) for wid in winners_ids]
    
    # Reset team status to 'registered' for the next bracket round
    for t in teams:
        database.update_team_status(t['id'], 'registered')
        
    if len(winners_ids) <= 1:
        # Champion found!
        return declare_champion(tournament_id, winners_ids[0] if winners_ids else None)
        
    # Create next round matches
    next_round = max(m['round_num'] for m in stage_matches) + 1
    
    # Determine the next stage name
    if len(winners_ids) <= 2:
        next_stage = "Finals"
    elif len(winners_ids) <= 4:
        next_stage = "Semis"
    else:
        next_stage = "Qualifiers"
        
    # Generate pairings
    for i in range(0, len(winners_ids), 2):
        t1_id = winners_ids[i]
        t2_id = winners_ids[i+1] if (i + 1) < len(winners_ids) else None
        
        if t2_id:
            database.create_match(tournament_id, next_stage, t1_id, t2_id, round_num=next_round)
        else:
            # Bye match
            match_id = database.create_match(tournament_id, next_stage, t1_id, None, round_num=next_round)
            database.update_match_result(match_id, 1, 0, t1_id, 'completed')
            database.update_team_status(t1_id, 'qualified')
            
    database.update_tournament_stage(tournament_id, next_stage)
    return {"action": "stage_advanced", "stage": next_stage}

def advance_double_elim(tournament_id: int, current_stage: str, all_matches: list):
    """
    Advanced logic for Double Elimination brackets.
    Tracks 'winners' and 'losers' groups, creates upper and lower matches.
    """
    # Double elimination progresses by rounds. Let's find the current max round in each bracket.
    # To keep it simple, we can run a check:
    # 1. Who is still active in Winner's Bracket?
    # 2. Who is still active in Loser's Bracket?
    # 3. Create matches for next round of Winner's and Loser's bracket.
    
    # Gather all teams
    teams = database.get_tournament_teams(tournament_id)
    
    # Let's count wins/losses for each team in matches to see who is eliminated (2 losses).
    # Wait, we can track this simply by evaluating matches:
    # A team is eliminated if it loses twice.
    # A team is in Winners Bracket if it has 0 losses.
    # A team is in Losers Bracket if it has exactly 1 loss.
    losses = {t['id']: 0 for t in teams}
    for m in all_matches:
        if m['status'] == 'completed':
            w_id = m['winner_id']
            l_id = m['team1_id'] if m['team2_id'] == w_id else m['team2_id']
            if l_id:
                losses[l_id] = losses.get(l_id, 0) + 1
                
    winners_active = [t['id'] for t in teams if losses[t['id']] == 0]
    losers_active = [t['id'] for t in teams if losses[t['id']] == 1]
    
    # Print status
    if len(winners_active) == 0:
        # Technically shouldn't happen unless double-DQ, but champion is last active loser
        if len(losers_active) == 1:
            return declare_champion(tournament_id, losers_active[0])
        elif len(losers_active) == 0:
            return declare_champion(tournament_id, None)
            
    if len(winners_active) == 1 and len(losers_active) == 1:
        # Grand Finals!
        # Check if the final match is already played.
        grand_finals = [m for m in all_matches if m['stage'] == "Finals"]
        if not grand_finals:
            # Create Grand Final Match
            database.create_match(tournament_id, "Finals", winners_active[0], losers_active[0], group_name="grand_finals")
            database.update_tournament_stage(tournament_id, "Finals")
            return {"action": "stage_advanced", "stage": "Finals"}
        else:
            # Grand final was played.
            gf = grand_finals[-1]
            if gf['winner_id'] == losers_active[0]:
                # Bracket reset! Loser's champ won, so they both have 1 loss now.
                # Check if bracket reset match is already created.
                if len(grand_finals) == 1:
                    database.create_match(tournament_id, "Finals", winners_active[0], losers_active[0], group_name="bracket_reset")
                    return {"action": "bracket_reset"}
                else:
                    # Bracket reset match complete.
                    br = grand_finals[-1]
                    return declare_champion(tournament_id, br['winner_id'])
            else:
                # Winner's champ won. Champion!
                return declare_champion(tournament_id, gf['winner_id'])
                
    if len(winners_active) == 1 and len(losers_active) == 0:
        # Winner's champ is the only one left.
        return declare_champion(tournament_id, winners_active[0])
        
    # Otherwise, progress brackets
    # Winners Bracket progresses: pair winners_active.
    # Losers Bracket progresses: pair losers_active.
    # Wait, we need to generate matches. Let's delete pending and make new matches.
    # Standard double elimination scheduling can be complex, but we can do a simplified progressive pairing:
    # For Winners: pair in order.
    # For Losers: pair in order.
    # Let's verify we only pair teams that aren't already scheduled.
    # Since we are advancing, all previous matches are completed.
    # Let's create next round matches.
    next_round = max(m['round_num'] for m in all_matches) + 1
    
    # Winners Round Matches (only if we have >1 winner)
    if len(winners_active) > 1:
        for i in range(0, len(winners_active), 2):
            t1 = winners_active[i]
            t2 = winners_active[i+1] if (i+1) < len(winners_active) else None
            if t2:
                database.create_match(tournament_id, "Qualifiers", t1, t2, group_name="winners", round_num=next_round)
            else:
                # Bye
                match_id = database.create_match(tournament_id, "Qualifiers", t1, None, group_name="winners", round_num=next_round)
                database.update_match_result(match_id, 1, 0, t1, 'completed')
                
    # Losers Round Matches
    if len(losers_active) > 1:
        for i in range(0, len(losers_active), 2):
            t1 = losers_active[i]
            t2 = losers_active[i+1] if (i+1) < len(losers_active) else None
            if t2:
                database.create_match(tournament_id, "Qualifiers", t1, t2, group_name="losers", round_num=next_round)
            else:
                # Bye
                match_id = database.create_match(tournament_id, "Qualifiers", t1, None, group_name="losers", round_num=next_round)
                database.update_match_result(match_id, 1, 0, t1, 'completed')
                
    database.update_tournament_stage(tournament_id, "Qualifiers")
    return {"action": "stage_advanced", "stage": "Qualifiers"}

def advance_group_stage_to_playoffs(tournament_id: int, current_stage: str, all_matches: list):
    """
    Transition from Group Stage to single-elimination Playoff bracket.
    Top 2 teams from each of Groups A, B, C, D advance.
    Total 8 teams (Quarter-Finals / Qualifiers).
    """
    if current_stage != "Group Stage":
        return None
        
    teams = database.get_tournament_teams(tournament_id)
    
    # Calculate group standings
    # Sort teams in each group by points desc, wins desc, losses asc
    groups = {"A": [], "B": [], "C": [], "D": []}
    
    # Let's compute points for teams based on matches in Group Stage
    team_stats = {t['id']: {"points": 0, "wins": 0, "losses": 0, "team": t} for t in teams}
    for m in all_matches:
        if m['stage'] == "Group Stage" and m['status'] == 'completed':
            w = m['winner_id']
            t1 = m['team1_id']
            t2 = m['team2_id']
            
            if w == t1:
                team_stats[t1]['wins'] += 1
                team_stats[t1]['points'] += 3
                if t2:
                    team_stats[t2]['losses'] += 1
            elif w == t2:
                team_stats[t2]['wins'] += 1
                team_stats[t2]['points'] += 3
                if t1:
                    team_stats[t1]['losses'] += 1
                    
    # Distribute teams back to groups and update their points in DB
    for t_id, stat in team_stats.items():
        database.update_team_score(t_id, stat['wins'], stat['losses'], stat['points'])
        # Read updated team to get team details
        updated_team = database.get_team(t_id)
        # Determine group
        # Wait, we need to know which group they were in. We can know from the matches they played.
        group_name = None
        for m in all_matches:
            if m['stage'] == "Group Stage" and (m['team1_id'] == t_id or m['team2_id'] == t_id):
                group_name = m['group_name']
                break
        if group_name in groups:
            groups[group_name].append(updated_team)
            
    # Sort teams in each group
    advancing_teams = []
    # Structure of pairings:
    # A1 vs B2, B1 vs A2, C1 vs D2, D1 vs C2
    group_leaders = {}
    for g_name, g_teams in groups.items():
        sorted_g = sorted(g_teams, key=lambda x: (x['points'], x['wins']), reverse=True)
        # Mark status in database
        for idx, t in enumerate(sorted_g):
            if idx < 2: # Top 2 advance
                database.update_team_status(t['id'], 'qualified')
                group_leaders[f"{g_name}{idx+1}"] = t['id']
            else:
                database.update_team_status(t['id'], 'eliminated')
                
    # Create Playoff bracket (Quarter finals / Qualifiers stage)
    # Matchups:
    # QF1: A1 vs B2
    # QF2: B1 vs A2
    # QF3: C1 vs D2
    # QF4: D1 vs C2
    playoff_pairings = [
        ("A1", "B2"),
        ("B1", "A2"),
        ("C1", "D2"),
        ("D1", "C2")
    ]
    
    for t1_key, t2_key in playoff_pairings:
        t1_id = group_leaders.get(t1_key)
        t2_id = group_leaders.get(t2_key)
        if t1_id or t2_id:
            database.create_match(tournament_id, "Qualifiers", t1_id, t2_id, round_num=1)
            
    database.update_tournament_stage(tournament_id, "Qualifiers")
    return {"action": "stage_advanced", "stage": "Qualifiers"}

def end_round_robin_or_swiss(tournament_id: int):
    """
    End of Round Robin or Swiss tournament. Determine champion based on final standings.
    """
    teams = database.get_tournament_teams(tournament_id)
    # Sort teams by points desc, wins desc, losses asc
    sorted_teams = sorted(teams, key=lambda x: (x['points'], x['wins'], -x['losses']), reverse=True)
    
    if sorted_teams:
        champ_id = sorted_teams[0]['id']
        return declare_champion(tournament_id, champ_id)
    else:
        return declare_champion(tournament_id, None)

def declare_champion(tournament_id: int, champion_team_id: int):
    """
    Mark the tournament as ended, register the champion and runner up, and save to history.
    """
    tournament = database.get_tournament(tournament_id)
    teams = database.get_tournament_teams(tournament_id)
    
    champ_team = None
    runner_up_team = None
    
    if champion_team_id:
        champ_team = database.get_team(champion_team_id)
        database.update_team_status(champion_team_id, "champion")
        
        # Determine runner up (who did they beat in finals, or #2 team)
        # If single-elim: find the final match
        matches = database.get_tournament_matches(tournament_id)
        finals = [m for m in matches if m['stage'] == "Finals"]
        if finals:
            f = finals[-1]
            ru_id = f['team1_id'] if f['winner_id'] == f['team2_id'] else f['team2_id']
            if ru_id:
                runner_up_team = database.get_team(ru_id)
                database.update_team_status(ru_id, "eliminated")
        else:
            # Round Robin/Swiss: runner up is #2 sorted
            sorted_teams = sorted(teams, key=lambda x: (x['points'], x['wins']), reverse=True)
            if len(sorted_teams) > 1:
                runner_up_team = sorted_teams[1]
                
    database.end_tournament(tournament_id)
    
    # Save to history
    import datetime
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    champ_name = champ_team['name'] if champ_team else "N/A"
    champ_cap = champ_team['captain_id'] if champ_team else None
    champ_p2 = champ_team['player2_id'] if champ_team else None
    ru_name = runner_up_team['name'] if runner_up_team else "N/A"
    
    # Get current season
    config = database.get_guild_config(tournament['guild_id'])
    season = config['current_season'] if config else 1
    
    database.add_tournament_history(
        tournament_id=tournament_id,
        name=tournament['name'],
        mode=tournament['mode'],
        format_str=tournament['format'],
        type_str=tournament['type'],
        champion_team_name=champ_name,
        champion_captain_id=champ_cap,
        champion_player2_id=champ_p2,
        runner_up_team_name=ru_name,
        season=season,
        date_ended=date_str
    )
    
    # Award season points & win stats to champion players
    if champ_team:
        players = [champ_team['captain_id'], champ_team['player2_id'], champ_team['player3_id'], champ_team['player4_id']]
        for p in players:
            if p:
                # Find username
                # In main bot we'll fetch user object, let's just record it. We'll set username as empty for now or update it in commands.
                database.update_player_stat(user_id=p, username="", wins=0, losses=0, played=0, champion=1, mvp=0, points=10) # 10 pts for champ
                
    if runner_up_team:
        players = [runner_up_team['captain_id'], runner_up_team['player2_id'], runner_up_team['player3_id'], runner_up_team['player4_id']]
        for p in players:
            if p:
                database.update_player_stat(user_id=p, username="", wins=0, losses=0, played=0, champion=0, mvp=0, points=5) # 5 pts for runner up
                
    # Update stats for all participants
    for t in teams:
        players = [t['captain_id'], t['player2_id'], t['player3_id'], t['player4_id']]
        for p in players:
            if p:
                # Add tournament played + wins/losses
                p_wins = t['wins']
                p_losses = t['losses']
                # Don't duplicate tournament_played if they were already counted, but since it ends now we count +1 played
                database.update_player_stat(user_id=p, username="", wins=p_wins, losses=p_losses, played=1, points=p_wins * 2) # 2 pts per match win
                
    return {
        "action": "tournament_ended",
        "champion_team": champ_team,
        "runner_up_team": runner_up_team,
        "mode": tournament['mode']
    }
