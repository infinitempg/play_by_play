import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re
# from tqdm import tqdm_notebook as tqdm
from urllib.request import urlopen
import os

requestHead = {"User-Agent": "Chrome/47.0.2526.111"}

def getSeasonIDs(num,online = True,prefix = None,post=True):
    if online:
        if num < 10:
            strnum = '0' + str(num)
        elif num >= 10:
            strnum = str(num)
        if num < 24:
            url = "http://sim-football.com/indexes/NSFLS"+strnum+"/GameResults.html"
        else:
            url = "http://sim-football.com/indexes/ISFLS"+strnum+"/GameResults.html"
        page = requests.get(url, headers = requestHead)
        soup = BeautifulSoup(page.text,'html.parser')
    else:
        with open(prefix+'/GameResults.html') as f:
            soup = BeautifulSoup(f,'html.parser')
    
    if num > 24:
        preseason = 28
        postseason = 7
    elif num > 21:
        preseason=24
        postseason=7
    elif num > 15:
        preseason = 20
        postseason= 7
    elif num > 1:
        preseason = 16
        postseason= 3
    else:
        preseason = 12
        postseason= 3
        
    if num < 2:
        gpwk = 3
    elif num <= 15:
        gpwk = 4
    elif num <= 21:
        gpwk = 5
    elif num <= 24:
        gpwk = 6
    else:
        gpwk = 7
        
    if num <= 15:
        wks = 14
    elif num <= 22:
        wks = 13
    else:
        wks = 16
        
    wkList = np.repeat(range(1,wks+1),gpwk)
    if num <= 15:
        wkList = np.append(wkList,np.repeat(wks+1,postseason))
        wkList[-1] = wks+2
    else:
        wkList = np.append(wkList,np.repeat(wks+1,4))
        wkList = np.append(wkList,np.repeat(wks+2,3))
        wkList[-1] = wks+3
    
    pbplist = soup.find_all('a',href=re.compile('Logs'))
    pbpURLs = [p.get('href') for p in pbplist]
    if len(pbpURLs[preseason:-postseason]) == 55:
        preseason = preseason-1
    if post:
        idList = [p[5:].strip('.html') for p in pbpURLs[preseason:]]
    else:
        idList = [p[5:].strip('.html') for p in pbpURLs[preseason:-postseason]]
    return idList, dict(zip(idList,wkList))

def getTeams(S,teamID):
    if S < 5:
        teamIDs = {'1':'BAL','2':'YKW','3':'COL','4':'ARI','5':'OCO',
                   '6':'SJS','7':'PHI','8':'LV','9':'CHI','10':'AUS'}
    elif S == 5:
        teamIDs = {'1':'BAL','2':'YKW','3':'COL','4':'AZ','5':'OCO',
                   '6':'SJS','7':'PHI','8':'LV','9':'CHI','10':'AUS'}
    elif S <= 21:
        teamIDs = {'1':'BAL','2':'YKW','3':'COL','4':'AZ','5':'OCO',
                   '6':'SJS','7':'PHI','8':'NO','9':'CHI','10':'AUS'}
    elif S <= 24:
        teamIDs = {'1':'BAL','2':'YKW','3':'COL','4':'AZ','5':'OCO','6':'SJS',
                   '7':'PHI','8':'NO','9':'CHI','10':'AUS','11':'SAR','12':'HON'}
    else:
        teamIDs = {'1':'BAL','2':'YKW','3':'COL','4':'AZ','5':'OCO','6':'SJS',
                   '7':'PHI','8':'NO','9':'CHI','10':'AUS','11':'SAR','12':'HON',
                   '13':'BER','14':'NY'}
    return teamIDs[teamID]

def dist2goal(team,side,yard):
    if team == side:
        dist = 100 - int(yard)
    elif side != '':
        dist = int(yard)
    else:
        dist = ''
    return dist

def goal2go(distance,dist2goal):
    if distance == 'Goal':
        return int(dist2goal)
    elif distance == '':
        return ''
    elif distance == 'inches':
        return 1.
    else:
        return int(distance)

def getScore(boxDF,totTime):
    i = 0
    if int(totTime) > -901:
        while int(totTime) <= int(boxDF.loc[i+1]['totTime']):
            i += 1
        return boxDF.loc[i]['awayScore'],boxDF.loc[i]['homeScore']
    else:
        return boxDF.loc[len(boxDF)-1]['awayScore'],boxDF.loc[len(boxDF)-1]['homeScore']

def puntSide(play,side,awayTeam,homeTeam):
    if 'Punt' in play:
        if side == awayTeam:
            return homeTeam
        else:
            return awayTeam
    else:
        return side

def puntPoss(play,teamPoss,awayTeam,homeTeam):
    if 'Punt' in play:
        if teamPoss == awayTeam:
            return homeTeam
        else:
            return awayTeam
    else:
        return teamPoss

def getGameData(S,gameID,idDict):
    if S < 10:
        strnum = '0' + str(S)
    elif S >= 10:
        strnum = str(S)
    
    if S < 24:
        url = "http://sim-football.com/indexes/NSFLS"+strnum
    else:
        url = "http://sim-football.com/indexes/ISFLS"+strnum
    
    pagePBP = requests.get('%s/Logs/%s.html'%(url,gameID),headers=requestHead)
    soupPBP = BeautifulSoup(pagePBP.content.decode('ISO-8859-1'),'lxml')
    tablePBP = soupPBP.find_all('table',class_='Grid')[0]
    
    q = -2
    pbpList = []

    for row in tablePBP.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) != 5:
            q += 1
        elif len(cols) == 5:
            team = cols[0].find_all('img')[0]['src'][16:].strip('_s.png')
            textTime = cols[1].text
            minutes,seconds = cols[1].text.strip().split(':')
            secondsLeft = int(minutes)*60 + int(seconds)
            totTime = 15*60*(4-q) + secondsLeft
            downDist = cols[2].text
            if downDist == '':
                down = ''
                dist = ''
            elif downDist == '---':
                down = ''
                dist = ''
            else:
                down = int(downDist[0])
                dist = downDist[8:]
            loc = cols[3].text
            if loc == '':
                side = yard = ''
            else:
    #             side = loc[:3]
    #             yard = int(loc[-2:])
                side, yard = loc.split(' - ')
            play = cols[4].text
            pbpList.append((team,q,textTime,totTime,down,dist,side,yard,play))

    pbpDF = pd.DataFrame(pbpList)
    pbpDF.columns = ['teamID','Q','time','totTime','down','distance','side','yard','play']
    pbpDF['gameID'] = gameID
    pbpDF['S'] = S
    pbpDF['W'] = idDict[gameID]
        
    teamList = list(pbpDF['side'].unique())
    teamList = [t for t in teamList if t != '']
    pbpDF['homeTeam'] = teamList[0]
    pbpDF['awayTeam'] = teamList[-1]
    
    pageBox = requests.get('%s/Boxscores/%s.html'%(url,gameID),headers=requestHead)
    soupBox = BeautifulSoup(pageBox.content.decode('ISO-8859-1'),'lxml')
    tableBox = soupBox.find_all('table',class_='Grid')[0]
    
    scoreList = [(3600,0,0)]

    q = 0
    for row in tableBox.find_all('tr')[1:]:
        cols = row.find_all('td')
        if len(cols) != 6:
            q += 1
        else:
            time = cols[-4].text.split(':')
            secondsLeft = int(time[0])*60 + int(time[1])
            totTime = 15*60*(4-q) + secondsLeft

            awayScore = int(cols[-2].text)
            homeScore = int(cols[-1].text)

            scoreList.append((totTime,awayScore,homeScore))

    scoreList.append((-901,awayScore,homeScore))
    
    boxDF = pd.DataFrame(scoreList)
    boxDF.columns = ['totTime','awayScore','homeScore']
    
    pbpDF['teamPoss'] = pbpDF.apply(lambda row: getTeams(S,row['teamID']),axis=1)
    pbpDF['dist2goal'] = pbpDF.apply(lambda row: dist2goal(row['teamPoss'],row['side'],row['yard']),axis=1)
    pbpDF['distance'] = pbpDF.apply(lambda row: goal2go(row['distance'],row['dist2goal']),axis=1)
    pbpDF['side'] = pbpDF.apply(lambda row: puntSide(row['play'],row['side'],row['awayTeam'],row['homeTeam']),axis=1)
    pbpDF['teamPoss'] = pbpDF.apply(lambda row: puntPoss(row['play'],row['teamPoss'],row['awayTeam'],row['homeTeam']),axis=1)
    pbpDF['awayScore'] = pbpDF.apply(lambda row : getScore(boxDF,row['totTime'])[0],axis=1)
    pbpDF['homeScore'] = pbpDF.apply(lambda row : getScore(boxDF,row['totTime'])[1],axis=1)
    if pbpDF.iloc[-1]['totTime'] < 0:
        pbpDF['awayScore'].iloc[-1] = boxDF['awayScore'].iloc[-1]
        pbpDF['homeScore'].iloc[-1] = boxDF['homeScore'].iloc[-1]
    
    return pbpDF

def posStatDF(S,gameID,boxList,index,homeTeam,awayTeam,name,idDict):
    away = boxList[index].iloc[1:]
    away.columns = ['Player'] + list(boxList[index].iloc[0][1:])
    away['Team'] = awayTeam
    
    home = boxList[index+1].iloc[1:]
    home.columns = ['Player'] + list(boxList[index].iloc[0][1:])
    home['Team'] = homeTeam
    
    cols = ['Team'] + list(home.columns[:-1])
    stats = pd.concat([home,away])
    stats = stats[cols]
    stats = stats.rename(columns={'TD':'%s_TD'%name})
    stats['Player'] = stats['Player'].str.replace(r" \(.*?\)","").str.replace(r"\(.*?\) ","")
    stats = stats.set_index('Player')
    
    if index == 8:
        cpatList = [int(x.strip('[]').split('/')[0]) for x in stats['Cp/At']]
        stats['Cmp'] = cpatList[0]
        stats['Att'] = cpatList[1]
        stats = stats.drop(columns=['Cp/At'])
    elif index == 14:        
        kickList = ['FG < 20','20-29','30-39','40-49','50+']
        for k in kickList:
            stats['%sM'%k] = [int(x.strip('[]').split('/')[0]) for x in stats[k]]
            stats['%sA'%k] = [int(x.strip('[]').split('/')[1]) for x in stats[k]]
        stats = stats.drop(columns=kickList)
    elif index == 18:
        stats = stats.iloc[:,:9]
        stats.columns = ['Team','KR','KRYds','PRYds','KRLng','PRLng','KR_TD','PR_TD','PR']
    elif index == 20:
        fumList = [int(x.strip('[]').split('/')[0]) for x in stats['FF/FR']]
        stats['FF'] = fumList[0]
        stats['FR'] = fumList[1]
        blkList = [int(x.strip('[]').split('/')[0]) for x in stats['Blk P/XP/FG']]
        stats['Blk P'] = blkList[0]
        stats['Blk XP'] = blkList[1]
        stats['Blk FG'] = blkList[2]
        stats = stats.drop(columns=['FF/FR','Blk P/XP/FG'])
        
    
    stats['W'] = str(idDict[gameID])
    stats['S'] = str(S)
    stats.to_csv('Boxscores/S%s/%s/%sStats.csv'%(S,gameID,name))
    return stats

def getGameBox(S,gameID,idDict):
    if not os.path.exists('Boxscores/S%s/%s'%(S,gameID)):
        os.makedirs('Boxscores/S%s/%s'%(S,gameID))
        
    if S < 10:
        strnum = '0' + str(S)
    else:
        strnum = str(S)
    
    sIDList, sIDDict = getSeasonIDs(S)
    
    if S < 24:
        leagueName = 'NSFL'
    else:
        leagueName = 'ISFL'
    
    boxList = pd.read_html('https://index.sim-football.com/%sS%s/Boxscores/%s.html'%(leagueName,strnum,gameID))
    
    # BOX SCORE 
    boxScore = boxList[2].iloc[:-1,:-1]
    boxScore.to_csv('Boxscores/S%s/%s/Boxscore.csv'%(S,gameID))
    
    # SCORING SUMMARY
    scoreSum = boxList[5]
    homeTeam = scoreSum['Scoring Summary.5'].iloc[0]
    awayTeam = scoreSum['Scoring Summary.4'].iloc[0]
    scoreSum = scoreSum.rename(columns = {'Scoring Summary':'Quarter','Scoring Summary.1':'Score Type','Scoring Summary.2':'Time Remaining',
                                          'Scoring Summary.3':'Play','Scoring Summary.4':awayTeam,'Scoring Summary.5':homeTeam})

    isnull = scoreSum['Quarter'].isnull()
    partitions = (isnull != isnull.shift()).cumsum()

    gb = scoreSum[isnull].groupby(partitions)

    q = 0
    offset = 0
    qD = {}
    for i in range(1,len(isnull)):
        if isnull[i] == True and isnull[i-1] == False:
            q += 1
            qD[q] = (q-offset)*2
        elif isnull[i] == False and isnull[i-1] == False:
            q += 1
            offset += 1

    qL = []
    for i in qD.keys():
    #     print(i)
        p1 = gb.get_group(qD[i]).iloc[:,1:]
        p1['Q'] = i
        qL.append(p1)
    scoring = pd.concat(qL)
    cols = ['Q'] + list(scoring.columns[:-1])
    scoring = scoring[cols]
    scoring.to_csv('Boxscores/S%s/%s/Scoring.csv'%(S,gameID))
    
    # TEAM STATS
    teamStats = boxList[6].iloc[1:]
    teamStats.columns = ['Stat'] + list(boxList[6].iloc[0][1:])

    teamStatsDF = teamStats.copy()

    def pct(teamStats,iloc1,iloc2):
        num = int(teamStats.iloc[iloc1,iloc2].split('/')[0])
        denom = int(teamStats.iloc[iloc1,iloc2].split('/')[1])
        if denom != 0:
            return num/denom
        else:
            return 0

    for op in [1,2,5]:
        teamStatsDF.iloc[op,1] = pct(teamStats,op,1)
        teamStatsDF.iloc[op,2] = pct(teamStats,op,2)

    aComp = int(teamStats.iloc[5,1].split('/')[0])
    aAtt = int(teamStats.iloc[5,1].split('/')[1])
    hComp = int(teamStats.iloc[5,2].split('/')[0])
    hAtt = int(teamStats.iloc[5,2].split('/')[1])
    aPen = int(teamStats.iloc[10,1].split('-')[0])
    aPenY = int(teamStats.iloc[10,1].split('-')[1])
    hPen = int(teamStats.iloc[10,2].split('-')[0])
    hPenY = int(teamStats.iloc[10,2].split('-')[1])
    aFum = int(teamStats.iloc[12,1].split(' (')[0])
    aFumL = int(teamStats.iloc[12,1].split(' (')[1][:-1])
    hFum = int(teamStats.iloc[12,2].split(' (')[0])
    hFumL = int(teamStats.iloc[12,2].split(' (')[1][:-1])

    arr = [['Completions',aComp,hComp],
           ['Attempts',aAtt,hAtt],
           ['Penalties',aPen,hPen],
           ['Penalty Yards',aPenY,hPenY],
           ['Fumbles',aFum,hFum],
           ['Fumbles Lost',aFumL,hFumL]]

    extraDF = pd.DataFrame(arr, columns = teamStats.columns)
    extraDF

    teamStatsDF2 = pd.concat([teamStatsDF.iloc[:5],extraDF.iloc[:2],teamStatsDF.iloc[6:10],
                              extraDF.iloc[2:4],teamStatsDF.iloc[11:12],extraDF[4:],teamStatsDF.iloc[13:]])
    teamStatsDF2[awayTeam] = pd.to_numeric(teamStatsDF2[awayTeam],errors='ignore')
    teamStatsDF2[homeTeam] = pd.to_numeric(teamStatsDF2[homeTeam],errors='ignore')
    teamStatsDF2.to_csv('Boxscores/S%s/%s/TeamStats.csv'%(S,gameID))
    
    # POSITION STATS
    passStats = posStatDF(S,gameID,boxList,8,homeTeam,awayTeam,"pass",idDict)
    rushStats = posStatDF(S,gameID,boxList,10,homeTeam,awayTeam,'rush',idDict)
    recStats = posStatDF(S,gameID,boxList,12,homeTeam,awayTeam,'rec',idDict)
    kickStats = posStatDF(S,gameID,boxList,14,homeTeam,awayTeam,'kick',idDict)
    puntStats = posStatDF(S,gameID,boxList,16,homeTeam,awayTeam,'punt',idDict)
    specStats = posStatDF(S,gameID,boxList,18,homeTeam,awayTeam,'spec',idDict)
    defStats = posStatDF(S,gameID,boxList,20,homeTeam,awayTeam,'def',idDict)
    othStats = posStatDF(S,gameID,boxList,22,homeTeam,awayTeam,'oth',idDict)
    
    return