import copy
import json
import unittest
from unittest.mock import patch
import publish as p

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.issue=json.loads('''{"id":"test-grouped-issue","items":[{"event_id":"higgsfield-shorts-2026-11-03","revision":"launch","category":"영상","announced_on":"2026-11-03","headline":"Higgsfield Shorts, AI 진행자 쇼츠 제작","bullets":["AI 진행자가 등장하는 9:16 세로 영상을 제작합니다.","주제에서 대본을 생성하고, 캐릭터·제품·의류 자료를 활용할 수 있습니다.","선택적으로 10~120초 참고 영상의 움직임을 반영합니다.","최대 2분 길이와 Basic·High 품질 옵션을 제공합니다."],"conditions":"11월 3일 출시 기록, 11월 4일 상세 안내 기준입니다. 웹 또는 Claude의 Higgsfield MCP에서 이용하며 길이·품질에 따라 크레딧이 달라집니다. 구독 등급·제공 지역은 해당 안내에 명시되지 않았습니다.","evidence":"Official changelog Nov 3 Shorts and Nov 4 guide; minimum length differs so omitted.","sources":[{"url":"https://higgsfield.ai/creator-hub/changelog","label":"Higgsfield 출시 기록 — 11월 3일 Shorts","entry":"2026-11-03 Shorts"},{"url":"https://higgsfield.ai/blog/higgsfield-introduces-shorts-studio","label":"Higgsfield Shorts 상세 안내"}]},{"event_id":"higgsfield-intone-2026-10-30","revision":"launch","category":"영상","announced_on":"2026-10-30","headline":"Intone, 말하는 캐릭터 영상 생성","bullets":["캐릭터·장소·음성으로 대사와 입 모양이 맞는 영상을 만듭니다.","업로드 이미지 또는 AI Influencer 캐릭터와 녹음·생성 음성을 사용할 수 있습니다.","720p·1080p와 화면 비율 5종을 지원하며 움직임·카메라 지시를 추가할 수 있습니다."],"conditions":"공식 출시 기록 기준 생성당 음성은 최대 30초입니다. Video → Higgsfield Intone에서 사용합니다. 구독 등급·제공 지역·구체적인 요금은 해당 발표에 명시되지 않았습니다.","evidence":"Official Oct 30 Intone entry confirms launch, audio limit, resolutions and ratios.","sources":[{"url":"https://higgsfield.ai/creator-hub/changelog","label":"Higgsfield 출시 기록 — 10월 30일 Intone","entry":"2026-10-30 Intone"}]}]}''')
        self.config=p.load('config.json')
        self.config.pop('replace_articles', None)
        self.state={'announcements':[],'publications':[],'pending':[],'source_checkpoints':{}}

    def test_aliases_drop_tracking(self):
        self.assertEqual(p.canonical('https://openai.com/a/?utm_source=x'),p.canonical('https://openai.com/a'))

    def test_event_duplicate_filtered(self):
        x=self.issue['items'][0]
        self.state['announcements']=[{'event_id':x['event_id'],'revision':x['revision']}]
        self.assertEqual(p.fresh_items([x],self.state),[])

    def test_grouped_replacement_includes_old_and_new_items(self):
        videos=[x for x in self.issue['items'] if x['category']=='영상']
        url='https://cafe.naver.com/f-e/cafes/31813012/articles/11'
        self.state['publications']=[{'article_id':'11','url':url,'issue_id':self.issue['id'],'category':'영상'}]
        self.state['announcements']=[{'event_id':videos[0]['event_id'],'revision':videos[0]['revision'],'article_url':url}]
        with self.assertRaises(ValueError):p.category_items(self.issue,'영상',self.state,self.config)
        self.config['replace_articles']={'영상':'11'}
        items, old=p.category_items(self.issue,'영상',self.state,self.config)
        self.assertEqual(len(items),len(videos))
        self.assertEqual(old['article_id'],'11')
        draft=p.render('영상',items,p.datetime.now(p.KST))
        self.assertTrue(all(x['headline'] in draft['content'] for x in videos))
        self.assertNotIn('<a ',draft['content'])

    def test_followup_requires_change_and_previous_article(self):
        x=copy.deepcopy(self.issue['items'][0]);x['revision']='updated'
        self.state['announcements']=[{'event_id':x['event_id'],'revision':'launch','article_url':'https://cafe.naver.com/a'}]
        with self.assertRaises(ValueError):p.fresh_items([x],self.state)
        x.update(change='조건 변경',previous_url='https://cafe.naver.com/a')
        self.assertEqual(len(p.fresh_items([x],self.state)),1)

    def test_html_escape(self):
        x=copy.deepcopy(self.issue['items'][0]);x['bullets'][0]='<script>alert(1)</script>'
        result=p.render(x['category'],[x],p.datetime.now(p.KST))
        self.assertNotIn('<script>',result['content'])
        self.assertIn('&lt;script&gt;',result['content'])

    def test_pending_unconfirmed_never_retransmits(self):
        self.state['pending']=[{'title':'unconfirmed'}]
        def fake_load(path):
            return self.config if str(path)=='config.json' else self.issue if str(path)=='queue.json' else self.state
        with patch.object(p,'load',side_effect=fake_load),patch.object(p,'validate'),patch.object(p,'board',return_value=[]),patch.object(p,'publish') as send:
            with self.assertRaises(ValueError):p.main()
            send.assert_not_called()

    def test_failed_durable_save_never_sends(self):
        def fake_load(path):
            return self.config if str(path)=='config.json' else self.issue if str(path)=='queue.json' else self.state
        with patch.object(p,'load',side_effect=fake_load),patch.object(p,'validate'),patch.object(p,'board',return_value=[]),patch.object(p,'access_token',return_value='dummy'),patch.object(p,'save',side_effect=RuntimeError('disk')),patch.object(p,'publish') as send:
            with self.assertRaises(RuntimeError):p.main()
            send.assert_not_called()

    def test_unknown_board_post_blocks(self):
        def fake_load(path):
            return self.config if str(path)=='config.json' else self.issue if str(path)=='queue.json' else self.state
        with patch.object(p,'load',side_effect=fake_load),patch.object(p,'validate'),patch.object(p,'board',return_value=[{'article_id':'999','title':'unknown'}]),patch.object(p,'publish') as send:
            with self.assertRaises(ValueError):p.main()
            send.assert_not_called()

if __name__=='__main__':unittest.main()

