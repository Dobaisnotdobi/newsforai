import copy
import unittest
from unittest.mock import patch
import publish as p

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.issue=p.load('queue.json')
        self.config=p.load('config.json')
        self.state={'announcements':[],'publications':[],'pending':[],'source_checkpoints':{}}

    def test_aliases_drop_tracking(self):
        self.assertEqual(p.canonical('https://openai.com/a/?utm_source=x'),p.canonical('https://openai.com/a'))

    def test_event_duplicate_filtered(self):
        x=self.issue['items'][0]
        self.state['announcements']=[{'event_id':x['event_id'],'revision':x['revision']}]
        self.assertEqual(p.fresh_items([x],self.state),[])

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

