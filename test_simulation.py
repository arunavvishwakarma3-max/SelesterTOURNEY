import database
import tournament

def run_lifecycle_simulation():
    print("==================================================")
    print("🚀 STARTING TOURNAMENT LIFE-CYCLE SIMULATION")
    print("==================================================")
    
    # 1. Initialize DB
    database.init_db()
    
    # Clean previous records for a fresh simulation
    with database.get_db() as conn:
        conn.execute("DELETE FROM guild_config")
        conn.execute("DELETE FROM tournaments")
        conn.execute("DELETE FROM teams")
        conn.execute("DELETE FROM matches")
        conn.execute("DELETE FROM player_stats")
        conn.execute("DELETE FROM tournament_history")
        conn.commit()
    print("🟢 Cleaned database tables successfully.")
    
    # 2. Setup Guild Config
    guild_id = 987654321
    config_data = {
        "announcements_channel_id": 101,
        "registration_channel_id": 102,
        "chat_channel_id": 103,
        "results_channel_id": 104,
        "standings_channel_id": 105,
        "history_channel_id": 106,
        "staff_logs_channel_id": 107,
        "bot_config_channel_id": 108,
        "host_role_id": 201,
        "staff_role_id": 202,
        "referee_role_id": 203,
        "participant_role_id": 204,
        "qualified_role_id": 205,
        "semi_role_id": 206,
        "final_role_id": 207,
        "champion_role_id": 208,
        "current_season": 1
    }
    database.save_guild_config(guild_id, config_data)
    print("🟢 Configured mock guild channels and roles.")
    
    # 3. Create Tournament
    t_id = database.create_tournament(
        guild_id=guild_id,
        name="Celestia BUHC Open Cup",
        mode="BUHC",
        format_str="Doubles (2v2)",
        type_str="Single Elimination",
        prize="1000 Coins + Champion Role",
        host_id=111,
        max_teams=4,
        rules="No hacking, respect rules."
    )
    print(f"🟢 Created Tournament: 'Celestia BUHC Open Cup' (ID: {t_id})")
    
    # 4. Register 4 Teams (Captains: 1001, 1002, 1003, 1004. Player 2s: 2001, 2002, 2003, 2004)
    team_data = [
        ("Antigravity MC", 1001, 2001),
        ("Zephyr MC", 1002, 2002),
        ("Apex Hunters", 1003, 2003),
        ("Vanguard", 1004, 2004)
    ]
    
    for name, cap, p2 in team_data:
        try:
            team_id = database.register_team(t_id, name, cap, p2)
            print(f"   Registered Team: {name} (ID: {team_id})")
        except ValueError as e:
            print(f"   ❌ Failed to register {name}: {e}")
            
    teams = database.get_tournament_teams(t_id)
    assert len(teams) == 4, f"Expected 4 teams, got {len(teams)}"
    print(f"🟢 Verified 4 teams successfully registered.")
    
    # 5. Transition to Check-in stage
    database.update_tournament_stage(t_id, "Check-in")
    t_updated = database.get_tournament(t_id)
    assert t_updated['stage'] == "Check-in", f"Expected stage 'Check-in', got {t_updated['stage']}"
    print("🟢 Advanced stage to 'Check-in'.")
    
    # 6. Check-in all teams
    for t in teams:
        database.update_team_status(t['id'], "checked_in")
    teams = database.get_tournament_teams(t_id)
    for t in teams:
        assert t['status'] == "checked_in", f"Team {t['name']} is status {t['status']}"
    print("🟢 Checked in all 4 teams successfully.")
    
    # 7. Start tournament (Generates Qualifiers matches)
    success = tournament.generate_initial_bracket(t_id)
    assert success is True, "Failed to generate initial bracket."
    
    t_updated = database.get_tournament(t_id)
    assert t_updated['stage'] == "Qualifiers", f"Expected stage 'Qualifiers', got {t_updated['stage']}"
    print("🟢 Generated initial brackets. Stage advanced to 'Qualifiers'.")
    
    matches = database.get_tournament_matches(t_id, stage="Qualifiers")
    assert len(matches) == 2, f"Expected 2 matches in Qualifiers, got {len(matches)}"
    print(f"🟢 Verified 2 matches generated for Qualifiers stage:")
    for m in matches:
        t1 = database.get_team(m['team1_id'])
        t2 = database.get_team(m['team2_id'])
        print(f"   Match #{m['id']}: {t1['name']} vs {t2['name']} (Round {m['round_num']}) - {m['status']}")
        
    # 8. Simulate Results for Qualifiers
    # Match 1: Team 1 beats Team 2 (Score: 2 - 1)
    m1 = matches[0]
    database.update_match_result(m1['id'], score1=2, score2=1, winner_id=m1['team1_id'], status='completed')
    print(f"🟢 Match #{m1['id']} complete. Winner: {database.get_team(m1['team1_id'])['name']}")
    
    # Check progress (should not advance since Match 2 is pending)
    res = tournament.check_and_advance_stage(t_id)
    assert res is None, "Should not advance stage while Match 2 is pending."
    
    # Match 2: Team 3 beats Team 4 (Score: 2 - 0)
    m2 = matches[1]
    database.update_match_result(m2['id'], score1=2, score2=0, winner_id=m2['team1_id'], status='completed')
    print(f"🟢 Match #{m2['id']} complete. Winner: {database.get_team(m2['team1_id'])['name']}")
    
    # Check progress (should advance to Finals)
    res = tournament.check_and_advance_stage(t_id)
    assert res is not None and res['action'] == 'stage_advanced', f"Expected stage_advanced, got {res}"
    assert res['stage'] == "Finals", f"Expected next stage 'Finals', got {res['stage']}"
    
    t_updated = database.get_tournament(t_id)
    assert t_updated['stage'] == "Finals", f"Expected stage 'Finals', got {t_updated['stage']}"
    print("🟢 All Qualifiers matches completed. Bracket auto-advanced to 'Finals'.")
    
    # 9. Verify Finals Match details
    finals_matches = database.get_tournament_matches(t_id, stage="Finals")
    assert len(finals_matches) == 1, f"Expected 1 match in Finals, got {len(finals_matches)}"
    fm = finals_matches[0]
    ft1 = database.get_team(fm['team1_id'])
    ft2 = database.get_team(fm['team2_id'])
    print(f"🟢 Verified Finals Match #{fm['id']}: {ft1['name']} vs {ft2['name']}")
    
    # 10. Simulate Finals result
    # Team 1 wins the finals (Score: 3 - 2)
    database.update_match_result(fm['id'], score1=3, score2=2, winner_id=fm['team1_id'], status='completed')
    print(f"🟢 Finals Match #{fm['id']} complete. Winner: {ft1['name']}")
    
    res = tournament.check_and_advance_stage(t_id)
    assert res is not None and res['action'] == 'tournament_ended', f"Expected tournament_ended, got {res}"
    print(f"🟢 Tournament ended. Champion: **{res['champion_team']['name']}** | Runner-up: **{res['runner_up_team']['name']}**")
    
    # 11. Verify History Logs
    history = database.get_history()
    assert len(history) == 1, f"Expected 1 history record, got {len(history)}"
    hist = history[0]
    assert hist['champion_team_name'] == ft1['name'], f"Expected champion {ft1['name']}, got {hist['champion_team_name']}"
    print(f"🟢 Verified history log: Champion '{hist['champion_team_name']}', Runner-up '{hist['runner_up_team_name']}' stored correctly.")
    
    # 12. Verify Player Statistics Updates
    p1_stats = database.get_player_stats(1001) # Captain of champion team
    assert p1_stats['tournaments_played'] == 1
    assert p1_stats['championships_won'] == 1
    # Match Wins: Qualifiers win (1) + Finals win (1) = 2.
    assert p1_stats['wins'] == 2, f"Expected 2 wins, got {p1_stats['wins']}"
    print(f"🟢 Verified champion stats: Wins = {p1_stats['wins']}, Played = {p1_stats['tournaments_played']}, Championships = {p1_stats['championships_won']}, Season Points = {p1_stats['season_points']}")
    
    p2_stats = database.get_player_stats(ft2['captain_id']) # Captain of runner-up team (1 match win, 1 loss)
    assert p2_stats['wins'] == 1
    assert p2_stats['losses'] == 1
    print(f"🟢 Verified runner-up stats: Wins = {p2_stats['wins']}, Losses = {p2_stats['losses']}, Season Points = {p2_stats['season_points']}")
    
    print("\n==================================================")
    print("🎉 ALL SIMULATION TESTS PASSED SUCCESSFULLY! 🎉")
    print("==================================================")

if __name__ == "__main__":
    run_lifecycle_simulation()
