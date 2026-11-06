"""Publish an agent-reviewed issue with durable, conservative duplicate protection."""
import hashlib
import html
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from naver_cafe import access_token, publish, transport, CafeError

KST = timezone(timedelta(hours=9))
HISTORY = Path('state/history.json')
EMOJI = {'종합':'🤖','영상':'🎬','이미지':'🎨','음악':'🎵','기타':'🛠️'}

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def canonical(url):
    p = urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username:
        raise ValueError('Official source must be an HTTPS URL')
    query = [(k,v) for k,v in parse_qsl(p.query) if not k.startswith('utm_')]
    return urlunsplit(('https',p.netloc.lower(),p.path.rstrip('/'),urlencode(query),p.fragment))

def stamp():
    return datetime.now(KST).isoformat()

def save(state):
    HISTORY.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    subprocess.run(['git','add',str(HISTORY)],check=True)
    diff = subprocess.run(['git','diff','--cached','--quiet','--',str(HISTORY)])
    if diff.returncode == 1:
        subprocess.run(['git','commit','-m','Record newsletter publication state'],check=True)
    elif diff.returncode != 0:
        raise ValueError('Cannot inspect durable history changes')
    subprocess.run(['git','push','origin','HEAD:main'],check=True)

def board(config):
    rows, seen = [], set()
    cafe = config['cafe']
    for page in range(1,1001):
        url = f"https://apis.naver.com/cafe-web/cafe-boardlist-api/v1/cafes/{cafe['club_id']}/menus/{cafe['menu_id']}/articles?page={page}&perPage=50"
        result = json.loads(transport(url))['result']
        for row in result['articleList']:
            item = row.get('item',row)
            if 'articleId' not in item or 'subject' not in item:
                raise ValueError('Unexpected board item; cannot verify duplicates')
            aid = str(item['articleId'])
            if aid not in seen:
                seen.add(aid)
                rows.append({'article_id':aid,'title':html.unescape(item['subject'])})
        info = result['pageInfo']
        if page >= info['lastNavigationPageNumber'] and not info['visibleNextButton']:
            return rows
    raise ValueError('Board scan incomplete')

def fresh_items(items,state):
    result=[]
    known={(x['event_id'],x['revision']) for x in state['announcements']}
    for item in items:
        key=(item['event_id'],item['revision'])
        if key in known:
            continue
        previous=[x for x in state['announcements'] if x['event_id']==item['event_id']]
        if previous and (not item.get('change') or item.get('previous_url') not in {x['article_url'] for x in previous}):
            raise ValueError('A follow-up requires the previous article and explicit change')
        # Canonical article URLs are aliases; a changelog URL can contain many events.
        aliases={canonical(s['url']) for s in item['sources'] if not s.get('entry')}
        for old in state['announcements']:
            if old['event_id'] != item['event_id'] and aliases.intersection(old.get('article_source_aliases',[])):
                raise ValueError('Source already belongs to another event; reconcile event IDs')
        result.append(item)
        known.add(key)
    return result

def render(category,items,date):
    title=f"[{date:%m.%d}] {EMOJI[category]} {category} AI 뉴스레터 — " + items[0]['headline']
    if len(items)>1:
        title+=f" 외 {len(items)-1}건"
    body=f'<p>{date:%Y년 %m월 %d일} 발행 | 최근 공식 발표 중 주요 소식</p>'
    for index,item in enumerate(items,1):
        body+=f'<h2>{index}. {html.escape(item["headline"])}</h2>'
        body+=f'<p>공식 발표일: {html.escape(item["announced_on"])}</p><ul>'
        body+=''.join('<li>'+html.escape(b)+'</li>' for b in item['bullets'])+'</ul>'
        body+='<p><strong>이용 조건</strong><br>'+html.escape(item['conditions'])+'</p>'
        if item.get('outlook'):
            body+='<p><strong>회사 발표의 향후 계획</strong><br>'+html.escape(item['outlook'])+'</p>'
        if item.get('change'):
            body+='<p><strong>후속 변경</strong><br>'+html.escape(item['change'])+'</p>'
            body+='<p>이전 글: '+html.escape(item['previous_url'])+'</p>'
        for s in item['sources']:
            body+='<p>공식 원문: '+html.escape(s['label'])+' — '+html.escape(s['url'])+'</p>'
    body+='<p>성능·효과에 관한 설명은 각 회사의 공식 발표를 요약한 내용입니다.</p>'
    return {'subject':title,'content':body}

def record(state,pending,aid,config,recovered=False):
    url=f"https://cafe.naver.com/f-e/cafes/{config['cafe']['club_id']}/articles/{aid}"
    state['publications'].append({**pending,'article_id':aid,'url':url,'posted_at':None if recovered else stamp(),'confirmed_at':stamp(),'recovered':recovered,'visibility':'public'})
    for item in pending['items']:
        state['announcements'].append({'event_id':item['event_id'],'revision':item['revision'],'sources':item['sources'],'article_source_aliases':[canonical(s['url']) for s in item['sources'] if not s.get('entry')],'article_url':url})
    state['pending']=[]
    save(state)
    print(url,flush=True)

def validate(issue,config):
    checked=datetime.fromisoformat(issue['checked_at'])
    now=datetime.now(KST)
    if checked.tzinfo is None or not timedelta(0) <= now-checked <= timedelta(hours=24):
        raise ValueError('Issue must be verified within the past 24 hours')
    allowed=set(load('sources.json')['allowed_domains'])
    keys=set()
    for item in issue['items']:
        if item['category'] not in config['categories'] or not 3<=len(item['bullets'])<=5:
            raise ValueError('Invalid category or bullet count')
        key=(item['event_id'],item['revision'])
        if key in keys:
            raise ValueError('Duplicate event in issue')
        keys.add(key)
        announced=datetime.fromisoformat(item['announced_on']).date()
        if announced>now.date():
            raise ValueError('Future announcement date')
        if not item['sources'] or not item['conditions'] or not item['evidence']:
            raise ValueError('Missing source, conditions or reviewed evidence')
        for s in item['sources']:
            canonical(s['url'])
            if urlsplit(s['url']).hostname not in allowed:
                raise ValueError('Source domain not in official allowlist')

def main():
    config=load('config.json')
    issue=load('queue.json')
    state=load(HISTORY)
    validate(issue,config)
    diagnostic = config.get('diagnostic_event_id')
    if diagnostic:
        issue['items']=[x for x in issue['items'] if x['event_id']==diagnostic]
        if len(issue['items']) != 1:
            raise ValueError('Diagnostic mode requires exactly one selected announcement')
    if '--validate' in sys.argv:
        for cat in config['categories']:
            items=fresh_items([x for x in issue['items'] if x['category']==cat],state)
            if items:
                print(render(cat,items,datetime.now(KST))['subject'])
        return
    if not config['publishing_enabled'] or config['approval_status']!='approved_recurring_and_immediate':
        raise ValueError('Publication is disabled')
    rows=board(config)
    for pending in list(state['pending']):
        matches=[r for r in rows if r['title']==pending['title']]
        if len(matches)==1:
            record(state,pending,matches[0]['article_id'],config,recovered=True)
        else:
            raise ValueError('Uncertain delivery: board checked, manual reconciliation required; no retry sent')
    known={x['article_id'] for x in state['publications']} | set(state.get('externally_reviewed_article_ids',[]))
    if any(r['article_id'] not in known for r in rows):
        raise ValueError('Untracked board posts: read their contents and record dedup review before publishing')
    token=access_token()
    for cat in config['categories']:
        items=fresh_items([x for x in issue['items'] if x['category']==cat],state)
        if not items:
            continue
        draft=render(cat,items,datetime.now(KST))
        current=board(config)
        if any(r['article_id'] not in known for r in current):
            raise ValueError('Board changed during batch; review before continuing')
        if any(r['title']==draft['subject'] for r in current):
            raise ValueError('Duplicate title found; reconcile instead of resending')
        pending={'issue_id':issue['id'],'category':cat,'title':draft['subject'],'items':items,'started_at':stamp(),'body_sha256':hashlib.sha256(draft['content'].encode()).hexdigest()}
        state['pending']=[pending]
        save(state)  # If durable push fails, never transmit.
        try:
            article=publish(draft,None,token,config['cafe'])
        except Exception as error:
            if isinstance(error, CafeError):
                print('Naver sanitized error:', str(error), file=sys.stderr, flush=True)
            # Public list can lag; inspect once now and never blindly retry.
            matches=[r for r in board(config) if r['title']==draft['subject']]
            if len(matches)==1:
                record(state,pending,matches[0]['article_id'],config,recovered=True)
                known.add(matches[0]['article_id'])
                continue
            raise ValueError('Delivery uncertain; pending state retained for board reconciliation') from None
        record(state,pending,article['article_id'],config)
        known.add(article['article_id'])
        time.sleep(5)
        if not any(r['article_id']==article['article_id'] and r['title']==draft['subject'] for r in board(config)):
            raise ValueError('API success recorded, but public board visibility not yet confirmed')
        time.sleep(10)
    if diagnostic:
        return  # Never advance collection checkpoints for a partial diagnostic issue.
    for source in issue['source_checks']:
        if source['status']=='checked':
            state['source_checkpoints'][source['url']]=issue['checked_at']
    state['last_processed_issue']=issue['id']
    if all(s['status']=='checked' for s in issue['source_checks']):
        state['last_successful_collection_at']=issue['checked_at']
    save(state)

if __name__=='__main__':
    try:
        main()
    except Exception as error:
        # No raw transport exceptions or credentials in logs.
        print('Publication stopped:', str(error) if isinstance(error,ValueError) else type(error).__name__,file=sys.stderr)
        raise SystemExit(1)

