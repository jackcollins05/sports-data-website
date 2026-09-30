#!/usr/bin/env python3
"""Rebuild compact, verified editorial findings for the 2025 FBS report page."""
from __future__ import annotations
import csv, json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'football_2025'
BRAND_FILE = ROOT / 'data' / 'team_branding.json'
OUT = DATA / 'report_findings_2025.json'


def rows(name):
    with (DATA / name).open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def num(row, key):
    value = row.get(key, '')
    if value in (None, ''):
        return None
    try:
        x = float(value)
        return x if x == x and abs(x) != float('inf') else None
    except (TypeError, ValueError):
        return None

def fmt(x, digits=1):
    if x is None: return None
    return round(x, digits)

def sum_field(items, key):
    vals = [num(r, key) for r in items]
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None

def avg_field(items, key):
    vals = [num(r, key) for r in items]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None

def team_summaries(team_games):
    groups = defaultdict(list)
    for r in team_games: groups[r['team_id']].append(r)
    out=[]
    for team_id, rs in groups.items():
        def total(k): return sum_field(rs,k)
        def mean(k): return avg_field(rs,k)
        records=[r for r in rs if num(r,'points_scored') is not None and num(r,'points_allowed') is not None]
        wins=sum(num(r,'points_scored') > num(r,'points_allowed') for r in records)
        losses=sum(num(r,'points_scored') < num(r,'points_allowed') for r in records)
        ties=len(records)-wins-losses
        out.append({
            'team_id':team_id,'team':rs[0]['team'],'team_abbreviation':rs[0]['team_abbreviation'],
            'division':rs[0]['division'],'games':len(rs),'scored_games':len(records),
            'wins':wins,'losses':losses,'ties':ties,
            'record':f'{wins}-{losses}' + (f'-{ties}' if ties else ''),
            'points':total('points_scored'),'points_allowed':total('points_allowed'),
            'points_per_game': (sum_field(records,'points_scored')/len(records)) if records else None,
            'yards':total('total_yards'),'yards_per_game':mean('total_yards'),
            'pass_yards':total('net_passing_yards'),'pass_yards_per_game':mean('net_passing_yards'),
            'rush_yards':total('rushing_yards'),'rush_yards_per_game':mean('rushing_yards'),
            'rush_attempts':total('rushing_attempts'),'first_downs':total('first_downs'),
            'turnovers':total('turnovers'),'third_down_made':total('third_down_conversions'),
            'third_down_attempts':total('third_down_attempts'),
            'third_down_pct':(100*total('third_down_conversions')/total('third_down_attempts')) if total('third_down_attempts') else None,
            'fourth_down_made':total('fourth_down_conversions'),
            'fourth_down_attempts':total('fourth_down_attempts'),
            'fourth_down_pct':(100*total('fourth_down_conversions')/total('fourth_down_attempts')) if total('fourth_down_attempts') else None,
        })
    return out

def player_card(r, headshots):
    key=(r['team_id'],r['athlete_id'])
    h=headshots.get(key,{})
    return {
        'athlete_id':r['athlete_id'],'name':r['display_name'] or r['player_name'],
        'team_id':r['team_id'],'team':r['team'],'team_abbreviation':r['team_abbreviation'],
        'position':r['position_abbreviation'],'jersey':r['jersey'],
        'headshot_url':h.get('headshot_url',''),'games':int(num(r,'games_played') or 0),
        'passing_attempts':num(r,'passing_attempts'),'passing_completions':num(r,'passing_completions'),
        'passing_yards':num(r,'passing_yards'),'passing_touchdowns':num(r,'passing_touchdowns'),
        'passing_interceptions':num(r,'passing_interceptions'),'completion_pct':num(r,'passing_completion_pct'),
        'rushing_attempts':num(r,'rushing_attempts'),'rushing_yards':num(r,'rushing_yards'),
        'rushing_touchdowns':num(r,'rushing_touchdowns'),'rushing_yards_per_attempt':num(r,'rushing_yards_per_attempt'),
        'receptions':num(r,'receptions'),'receiving_yards':num(r,'receiving_yards'),
        'receiving_touchdowns':num(r,'receiving_touchdowns'),'receiving_yards_per_reception':num(r,'receiving_yards_per_reception'),
        'tackles':num(r,'defensive_total_tackles'),'sacks':num(r,'defensive_sacks'),
        'tfl':num(r,'defensive_tackles_for_loss'),'defensive_interceptions':num(r,'defensive_interceptions'),
        'passes_defended':num(r,'passes_defended'),'kicking_points':num(r,'total_kicking_points'),
    }

def take(items, metric, n=8, descending=True):
    return sorted([x for x in items if x.get(metric) is not None], key=lambda x:(x[metric],x['team']), reverse=descending)[:n]

def main():
    brand_doc=json.loads(BRAND_FILE.read_text(encoding='utf-8'))
    brand_by_id={v['id']:{**v,'team_name':name} for name,v in brand_doc['teams'].items()}
    players=rows('fbs_player_season_stats_2025.csv')
    player_roster=rows('fbs_players_2025.csv')
    team_games=rows('fbs_team_game_stats_2025.csv')
    games=rows('fbs_games_2025.csv')
    polls=rows('ap_top25_2025.csv')
    trends=rows('ap_top25_trends_2025.csv')
    headshots={(r['team_id'],r['athlete_id']):{'headshot_url':r['headshot_url']} for r in player_roster}
    teams=team_summaries(team_games)
    # Conservative minimum opportunity thresholds keep rate leaders interpretable.
    qbs=[player_card(r,headshots) for r in players if r['position_abbreviation']=='QB' and (num(r,'passing_attempts') or 0)>=100 and not (num(r,'passing_unmapped_games') or 0)]
    rushers=[player_card(r,headshots) for r in players if r['position_abbreviation'] in {'RB','FB','QB'} and (num(r,'rushing_attempts') or 0)>=100]
    receivers=[player_card(r,headshots) for r in players if (num(r,'receptions') or 0)>=40]
    defenders=[player_card(r,headshots) for r in players if (num(r,'games_played') or 0)>=8]
    team_min=[t for t in teams if t['games']>=8]
    team_ppg=take(team_min,'points_per_game',8)
    team_yards=take(team_min,'yards_per_game',8)
    third_down=[t for t in team_min if (t['third_down_attempts'] or 0)>=80]
    third_down=take(third_down,'third_down_pct',8)

    # AP rank swing is strictly a comparison between actual preseason and final polls.
    by_team_poll=defaultdict(dict)
    for r in polls: by_team_poll[r['team_id']][r['poll_label']]=r
    preseason_final=[]
    for tid, pp in by_team_poll.items():
        a=pp.get('Preseason'); z=pp.get('Final Rankings')
        if a and z:
            preseason_final.append({'team_id':tid,'team':z['team_name'],'team_abbreviation':z['team_abbreviation'],
                'conference':z['conference'],'preseason_rank':int(a['rank']),'final_rank':int(z['rank']),
                'movement':int(a['rank'])-int(z['rank']),'best_rank':min(int(x['rank']) for x in pp.values()),
                'weeks_ranked':sum(1 for x in pp.values() if x['poll_stage']=='regular')})
    biggest_risers=take(preseason_final,'movement',6)
    biggest_fallers=take(preseason_final,'movement',6,descending=False)
    final_poll=sorted([r for r in polls if r['poll_label']=='Final Rankings'],key=lambda r:int(r['rank']))
    preseason=sorted([r for r in polls if r['poll_label']=='Preseason'],key=lambda r:int(r['rank']))
    poll_periods=[]
    for order in sorted({int(r['poll_order']) for r in polls}):
        pp=[r for r in polls if int(r['poll_order'])==order]
        poll_periods.append({'poll_order':order,'poll_stage':pp[0]['poll_stage'],'poll_week':pp[0]['poll_week'],
            'poll_label':pp[0]['poll_label'],'poll_date':pp[0]['poll_date'],'ranked_teams':len(pp)})
    # Weekly entrant/departure totals; the first period has no previous snapshot.
    transitions=[]
    for period in poll_periods[1:]:
        rows_for=[r for r in trends if int(r['poll_order'])==period['poll_order']]
        transitions.append({**period,'entered':sum(r['entered_poll']=='true' for r in rows_for),
            'dropped':sum(r['dropped_from_previous_poll']=='true' for r in rows_for),
            'retained_from_prior':sum(r['is_ranked']=='true' and r['previous_rank']!='' for r in rows_for)})

    complete_games=[]
    for g in games:
        h,w=num(g,'home_score'),num(g,'away_score')
        if h is None or w is None: continue
        margin=abs(h-w)
        complete_games.append({'game_id':g['game_id'],'week':int(g['week'] or 0),'season_type':g['season_type'],'date':g['game_date'],
            'home_team':g['home_team'],'home_team_id':g['home_team_id'],'home_division':g['home_division'],
            'home_score':h,'away_team':g['away_team'],'away_team_id':g['away_team_id'],
            'away_division':g['away_division'],'away_score':w,'combined':h+w,'margin':margin,
            'venue':g['venue'],'neutral_site':g['neutral_site']=='true'})
    high_score=max(complete_games,key=lambda g:g['combined']) if complete_games else None
    closest=sorted([g for g in complete_games if g['margin']<=3],key=lambda g:(g['margin'],-g['combined']))
    most_points=sorted(complete_games,key=lambda g:g['combined'],reverse=True)[:8]

    # Schedule week numbers repeat inside ESPN postseason type 3 (often as 1),
    # so regular-season trend lines deliberately use type 2 only.
    weekly=defaultdict(list)
    for r in team_games:
        if r['season_type']=='2' and num(r,'points_scored') is not None:
            weekly[int(r['week'])].append(r)
    weekly_rows=[]
    for week, rr in sorted(weekly.items()):
        weekly_rows.append({'week':week,'team_games':len(rr),'points':sum_field(rr,'points_scored'),
          'points_per_team_game':avg_field(rr,'points_scored'),'yards_per_team_game':avg_field(rr,'total_yards'),
          'passing_yards_per_team_game':avg_field(rr,'net_passing_yards'),'rushing_yards_per_team_game':avg_field(rr,'rushing_yards')})
    weekly_peak=max(weekly_rows,key=lambda r:r['points_per_team_game']) if weekly_rows else None
    weekly_floor=min(weekly_rows,key=lambda r:r['points_per_team_game']) if weekly_rows else None

    # Editorial findings are assembled here from the source-derived rows so the
    # page can render verified values rather than hard-coded leaderboard copy.
    def p_name(x): return f"{x['name']} ({x['team_abbreviation']})"
    def team_name(x): return x['team']
    top_qb=qbs and take(qbs,'passing_yards',1)[0]
    top_rb=rushers and take(rushers,'rushing_yards',1)[0]
    top_wr=receivers and take(receivers,'receiving_yards',1)[0]
    next_wr=receivers[1] if len(receivers)>1 else None
    top_sacker=defenders and take(defenders,'sacks',1)[0]
    top_tackler=defenders and take(defenders,'tackles',1)[0]
    top_scoring=team_ppg[0] if team_ppg else None
    top_yards=team_yards[0] if team_yards else None
    top_third=third_down[0] if third_down else None
    touchdowns=[x for x in qbs if x['passing_touchdowns'] is not None]
    top_pass_td=take(touchdowns,'passing_touchdowns',1)[0] if touchdowns else None
    team_scores_chart=[{'label':x['team'],'team_id':x['team_id'],'team_abbreviation':x['team_abbreviation'],
        'value':fmt(x['points_per_game'],2),'detail':x['record'],'games':x['scored_games']} for x in team_ppg]
    team_yards_chart=[{'label':x['team'],'team_id':x['team_id'],'team_abbreviation':x['team_abbreviation'],
        'value':fmt(x['yards_per_game'],1),'pass':fmt(x['pass_yards_per_game'],1),
        'rush':fmt(x['rush_yards_per_game'],1),'detail':x['record'],'games':x['games']} for x in team_yards]
    stories=[
      {'id':'poll-climbers','kicker':'AP TOP 25 / PRESEASON TO FINAL',
       'title':f"{biggest_risers[0]['team']} climbed {biggest_risers[0]['movement']} places to finish No. {biggest_risers[0]['final_rank']}" if biggest_risers else 'The AP poll tracked a season of movement',
       'copy':f"Among the {len(preseason_final)} teams ranked in both the AP preseason and final polls, {biggest_risers[0]['team']} made the largest rise, moving from No. {biggest_risers[0]['preseason_rank']} to No. {biggest_risers[0]['final_rank']}. {biggest_fallers[0]['team']} had the largest drop among those same teams, from No. {biggest_fallers[0]['preseason_rank']} to No. {biggest_fallers[0]['final_rank']}. These are AP poll positions, not a ranking calculated from game statistics.",
       'kind':'movement','data':{'risers':biggest_risers,'fallers':biggest_fallers}},
      {'id':'passing','kicker':'AIR ATTACK / PASSING',
       'title':f"{p_name(top_qb)} led the FBS in passing yards" if top_qb else 'The passing leaderboard',
       'copy':f"With at least 100 pass attempts, {top_qb['name']} of {top_qb['team']} led these prepared season totals with {int(top_qb['passing_yards']):,} yards, {int(top_qb['passing_touchdowns'] or 0)} passing touchdowns, and a {top_qb['completion_pct']:.1f}% completion rate across {top_qb['games']} games. The 100-attempt floor keeps the comparison focused on quarterbacks with a meaningful workload." if top_qb else 'No qualifying quarterback passing line was available.',
       'kind':'players','metric':'passing_yards','unit':'PASSING YARDS','data':take(qbs,'passing_yards',8)},
      {'id':'rushing','kicker':'GROUND GAME / RUSHING',
       'title':f"{p_name(top_rb)} topped the rushing chart" if top_rb else 'The rushing leaderboard',
       'copy':f"{top_rb['name']} of {top_rb['team']} led the 100-attempt rushing cohort with {int(top_rb['rushing_yards']):,} yards on {int(top_rb['rushing_attempts']):,} carries, {top_rb['rushing_yards_per_attempt']:.2f} yards per carry, and {int(top_rb['rushing_touchdowns'] or 0)} rushing touchdowns. The average is recomputed from season yards divided by season attempts." if top_rb else 'No qualifying rushing line was available.',
       'kind':'players','metric':'rushing_yards','unit':'RUSHING YARDS','data':take(rushers,'rushing_yards',8)},
      {'id':'receiving','kicker':'PASS CATCHERS / RECEIVING',
       'title':f"{p_name(top_wr)} led in receiving yards" if top_wr else 'The receiving leaderboard',
       'copy':(f"With at least 40 receptions, {top_wr['name']} of {top_wr['team']} led the receiving cohort with {int(top_wr['receiving_yards']):,} yards on {int(top_wr['receptions'])} catches, averaging {top_wr['receiving_yards_per_reception']:.2f} yards per reception, with {int(top_wr['receiving_touchdowns'] or 0)} receiving touchdowns. " + (f"That was {int(top_wr['receiving_yards']-next_wr['receiving_yards']):,} yards ahead of {next_wr['name']}, the next player in the same qualifying group." if next_wr else '')) if top_wr else 'No qualifying receiving line was available.',
       'kind':'players','metric':'receiving_yards','unit':'RECEIVING YARDS','data':take(receivers,'receiving_yards',8)},
      {'id':'defense','kicker':'DEFENSE / SACK PRODUCTION',
       'title':f"{p_name(top_sacker)} paced the sack leaders" if top_sacker else 'Sack production across the FBS',
       'copy':f"Among defenders appearing in at least eight games, {top_sacker['name']} of {top_sacker['team']} recorded {top_sacker['sacks']:.1f} sacks. The same games-played threshold applies to this chart. {top_tackler['name']} of {top_tackler['team']} led the qualifying tackle total with {int(top_tackler['tackles']):,} tackles." if top_sacker and top_tackler else 'Defensive production is displayed from reported individual box-score totals.',
       'kind':'players','metric':'sacks','unit':'SACKS','data':take(defenders,'sacks',8)},
      {'id':'scoring-teams','kicker':'SCOREBOARD / POINTS PER GAME',
       'title':f"{team_name(top_scoring)} averaged {top_scoring['points_per_game']:.1f} points per game" if top_scoring else 'Team scoring leaders',
       'copy':f"{top_scoring['team']} led teams with at least eight team-game rows, averaging {top_scoring['points_per_game']:.2f} points across {top_scoring['scored_games']} games with a reported score. Their recorded season line was {top_scoring['record']}. Points per game is total nonmissing points divided by scored team-game rows; FBS games against FCS opponents remain in the sample." if top_scoring else 'Team score data was not available.',
       'kind':'teams','metric':'points_per_game','unit':'POINTS / GAME','data':team_scores_chart},
      {'id':'team-yardage','kicker':'TEAM OFFENSE / TOTAL YARDS',
       'title':f"{team_name(top_yards)} averaged {top_yards['yards_per_game']:.1f} yards per game" if top_yards else 'Team yardage leaders',
       'copy':f"{top_yards['team']} led the teams with at least eight games in average total offense, at {top_yards['yards_per_game']:.1f} yards per game across {top_yards['games']} team-game rows. The bars separate reported net passing yards and rushing yards per game; they are source box-score fields and may not sum exactly to total yards." if top_yards else 'Team yardage data was not available.',
       'kind':'stacked-teams','metric':'yards_per_game','unit':'YARDS / GAME','data':team_yards_chart},
      {'id':'third-down','kicker':'SITUATIONAL FOOTBALL / THIRD DOWN',
       'title':f"{top_third['team']} converted {top_third['third_down_pct']:.1f}% of third downs" if top_third else 'Third-down performance',
       'copy':f"Among teams with at least 80 recorded third-down attempts and eight or more games, {top_third['team']} converted {int(top_third['third_down_made'])} of {int(top_third['third_down_attempts'])} chances ({top_third['third_down_pct']:.1f}%). The rate uses summed conversions divided by summed attempts, not an average of game percentages." if top_third else 'Third-down attempts were not available for a qualifying comparison.',
       'kind':'third-down','metric':'third_down_pct','unit':'THIRD-DOWN CONVERSION','data':[{**x,'value':fmt(x['third_down_pct'],2)} for x in third_down]},
      {'id':'close-games','kicker':'FINAL MINUTES / ONE-SCORE FINISHES',
       'title':f"{len(closest)} FBS-involving games finished within three points",
       'copy':f"Of {len(complete_games)} FBS-involving games with both final scores present, {len(closest)} ended with a margin of three points or fewer. The narrowest result in the source schedule was {closest[0]['home_team']} {int(closest[0]['home_score'])}, {closest[0]['away_team']} {int(closest[0]['away_score'])} in Week {closest[0]['week']}. This uses the schedule’s home/away score labels, including neutral-site games.",
       'kind':'games','data':{'close_count':len(closest),'close':closest[:6],'high_scoring':most_points[:5]}},
      {'id':'weekly-scoring','kicker':'SEASON RHYTHM / REGULAR SEASON',
       'title':f"Week {weekly_peak['week']} produced the highest regular-season scoring average" if weekly_peak else 'Scoring volume changed week by week across the regular season',
       'copy':f"Week {weekly_peak['week']} averaged {weekly_peak['points_per_team_game']:.2f} points per team-game, compared with {weekly_floor['points_per_team_game']:.2f} in Week {weekly_floor['week']}. This timeline includes schedule season-type 2 only. ESPN schedule week numbers restart at 1 for postseason games, so bowl and playoff games are not merged into regular-season Week 1. Rates use nonmissing team score rows in each week." if weekly_peak and weekly_floor else 'Regular-season scoring totals are shown from nonmissing team-game scores.',
       'kind':'weekly','unit':'POINTS / TEAM-GAME','data':weekly_rows},
      {'id':'poll-churn','kicker':'AP TOP 25 / POLL TURNOVER',
       'title':f"The Top 25 changed by {sum(x['entered'] for x in transitions)} entries and {sum(x['dropped'] for x in transitions)} exits across available weekly polls",
       'copy':f"Across the {len(transitions)} transitions after the first captured snapshot, teams entered the AP Top 25 {sum(x['entered'] for x in transitions)} times and dropped out {sum(x['dropped'] for x in transitions)} times. These are team-poll transitions, so a program may enter or leave more than once. A departure is shown as unranked in that poll period; the trend data never assigns an invented No. 26.",
       'kind':'churn','unit':'TEAMS PER POLL TRANSITION','data':transitions},
    ]

    # A game view is complete only when both side scores exist.
    wins=sum(1 for g in complete_games if g['home_score']!=g['away_score'])
    fbs_game_ids={g['game_id'] for g in games}
    outputs={
      'brand': {'name':'GRIDIRON PULSE','tagline':'Explore the 2025 College Football Season'},
      'overview': {'fbs_teams':len({r['team_id'] for r in player_roster}),
        'players':len(player_roster),'player_team_season_rows':len(players),'fbs_games':len(games),
        'completed_games':len(complete_games),'team_game_rows':len(team_games),'poll_snapshots':len(poll_periods),
        'regular_polls':sum(p['poll_stage']=='regular' for p in poll_periods),
        'ranked_appearances':len(polls),'fbs_points_scored':sum_field(team_games,'points_scored'),
        'scored_team_games':sum(num(r,'points_scored') is not None for r in team_games),
        'season_weeks':sorted({int(r['week']) for r in games if r['week'] and r['season_type']=='2'}),
        'postseason_games':sum(r['season_type']=='3' for r in games),
        'poll_weeks_available':[int(p['poll_week']) for p in poll_periods if p['poll_stage']=='regular'],
        'schedule_games_without_player_stats':len(fbs_game_ids-{r['game_id'] for r in rows('fbs_player_game_stats_2025.csv')})},
      'leaderboards': {'passing':take(qbs,'passing_yards',8),'rushing':take(rushers,'rushing_yards',8),
        'receiving':take(receivers,'receiving_yards',8),'tackles':take(defenders,'tackles',8),
        'sacks':take(defenders,'sacks',8),'interceptions':take(defenders,'defensive_interceptions',8),
        'team_scoring':team_ppg,'team_yards':team_yards,'third_down':third_down},
      'rankings': {'periods':poll_periods,'preseason':preseason,'final':final_poll,
        'preseason_final_comparable':preseason_final,'biggest_risers':biggest_risers,
        'biggest_fallers':biggest_fallers,'transitions':transitions,
        'stable_through_final':sum(1 for r in preseason_final if r['movement']==0),
        'teams_ranked_both_preseason_final':len(preseason_final)},
      'games': {'completed':len(complete_games),'close_margin_at_most_3':len(closest),
        'closest_games':closest[:8],'highest_scoring':most_points,'highest_total_game':high_score,
        'home_wins':sum(g['home_score']>g['away_score'] for g in complete_games),
        'away_wins':sum(g['away_score']>g['home_score'] for g in complete_games),
        'neutral_site_games':sum(g['neutral_site'] for g in complete_games)},
      'weekly':weekly_rows,
      'stories':stories,
      'team_summaries':teams,
      'methodology': {'team_min_games':8,'qb_min_pass_attempts':100,'rusher_min_rush_attempts':100,
        'receiver_min_receptions':40,'third_down_min_attempts':80,'defender_min_games':8,
        'rate_definitions': {'completion_pct':'completions / pass attempts × 100',
          'yards_per_attempt':'season yards / season attempts',
          'points_per_game':'sum of nonmissing team points / team-game rows with nonmissing points',
          'third_down_pct':'sum of third-down conversions / sum of third-down attempts × 100',
          'ranking_movement':'previous rank minus current rank; positive means moved up',
          'AP_weeks_ranked':'count of regular-season polls in which a team appears in the Top 25'}}
    }
    # Keep the homepage payload lean: source-derived narrative, supporting chart
    # values, headline counts, and definitions only. Full source tables stay in CSV.
    outputs={key:outputs[key] for key in ('brand','overview','stories','methodology')}
    OUT.write_text(json.dumps(outputs,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'{OUT.relative_to(ROOT)}: {OUT.stat().st_size} bytes')
    print(json.dumps({'overview':outputs['overview'],'story_count':len(outputs['stories']),
      'story_headlines':[story['title'] for story in outputs['stories']]},indent=2))

if __name__=='__main__': main()
