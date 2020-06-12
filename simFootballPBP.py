import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re
from tqdm import tqdm_notebook as tqdm
from urllib.request import urlopen

requestHead = {"User-Agent": "Chrome/47.0.2526.111"}

def getSeasonIDs(num):
    if num < 10:
        strnum = '0' + str(num)
    elif num >= 10:
        strnum = str(num)
    url = "http://sim-football.com/indexes/NSFLS%s/GameResults.html"%strnum
    page = requests.get(url,headers=requestHead)
    soup = BeautifulSoup(page.text,'html.parser')
    
    if num > 21:
        preseason = 24
        postseason = 7
    elif num > 15:
        preseason = 20
        postseason = 7
    elif num > 1:
        preseason = 16
        postseason = 3
    else:
        preseason = 12
        postseason = 3
    
    pbplist = soup.find_all('a',href = re.compile('Logs'))
    pbpURLs = [p.get('href') for p in pbplist]
    
    if len(pbpURLs[preseason:-postseason]) == 55:
        preseason = preseason - 1
        
    idList = [p[5:].strip('.html') for p in pbpURLs[preseason:]]
    
    return idList

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
    else:
        teamIDs = {'1':'BAL','2':'YKW','3':'COL','4':'AZ','5':'OCO','6':'SJS',
                   '7':'PHI','8':'NO','9':'CHI','10':'AUS','11':'SAR','12':'HON'}
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

def getGameData(S,gameID):
    if S < 10:
        strnum = '0' + str(S)
    elif S >= 10:
        strnum = str(S)
    
    pagePBP = requests.get('http://sim-football.com/indexes/NSFLS%s/Logs/%s.html'%(strnum,gameID),headers=requestHead)
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
        
    teamList = list(pbpDF['side'].unique())
    teamList = [t for t in teamList if t != '']
    pbpDF['homeTeam'] = teamList[0]
    pbpDF['awayTeam'] = teamList[-1]
    
    pageBox = requests.get('http://sim-football.com/indexes/NSFLS%s/Boxscores/%s.html'%(strnum,gameID),headers=requestHead)
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