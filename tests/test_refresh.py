import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import refresh
import seed


class MonthTests(unittest.TestCase):
    def test_last_complete_month_january(self):
        s,e = refresh.month_window(datetime(2027,1,2,tzinfo=timezone.utc))
        self.assertEqual(s.isoformat(), '2026-12-01T00:00:00+00:00')
        self.assertEqual(e.isoformat(), '2027-01-01T00:00:00+00:00')

    def test_explicit_month(self):
        s,e=refresh.month_window(datetime(2026,11,9,tzinfo=timezone.utc), '2026-09')
        self.assertEqual(s.month, 9)
        self.assertEqual(e.month, 10)

    def test_future_month_rejected(self):
        with self.assertRaises(ValueError):
            refresh.month_window(datetime(2026,11,9,tzinfo=timezone.utc), '2026-11')

    def test_iso_duration(self):
        self.assertEqual(refresh.parse_duration('PT2M57S'), 177)
        self.assertEqual(refresh.parse_duration('PT1H3M'), 3780)
        self.assertEqual(refresh.parse_duration('invalid'), 0)


class DataTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy=seed.build_taxonomy()

    def test_exactly_fifty_distinct_playbooks(self):
        self.assertEqual(len(self.taxonomy),50)
        self.assertEqual(len({x['id'] for x in self.taxonomy}), 50)

    def test_keyword_classifier_does_not_guess(self):
        self.assertIsNone(refresh.classify_keyword({'title':'Look at this! #shorts', 'description':''}, self.taxonomy))
        guessed=refresh.classify_keyword({'title':'My three common mistakes', 'description':''}, self.taxonomy)
        self.assertEqual(guessed['format_id'], 'common_mistakes')

    def test_rankings_require_independent_creators(self):
        now = datetime(2026,11,9,tzinfo=timezone.utc)
        videos=[{
            'id':f'vid_{i}', 'title':'Before and after makeover',
            'description':'','channel_id':f'creator_{i%2}', 'channel':f'Creator {i%2}',
            'published_at':'2026-10-12T10:00:00Z', 'views':100000*(i+1),
            'likes':4000, 'comments':200, 'niches':['Beauty','Lifestyle'],
        }for i in range(4)]
        labels={v['id']:{'format_id':'before_after','confidence':.9} for v in videos}
        result=refresh.score_formats(videos,self.taxonomy,now,labels)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['rank'],1)
        self.assertEqual(result[0]['stats']['creators'],2)
        self.assertEqual(result[0]['stats']['videos'],4)
        self.assertEqual(len(result[0]['sample_videos']),2)
        labels={v['id']:{'format_id':'before_after','confidence':.9} for v in videos[:1]}
        self.assertEqual(refresh.score_formats(videos,self.taxonomy,now,labels),[])

    def test_older_report_does_not_overwrite_latest(self):
        from tempfile import TemporaryDirectory
        import json
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            newer={'month':'2026-10','period_label':'October 2026','generated_at':'2026-11-02T10:00:00Z','results':[{'id':'a'}]}
            older={'month':'2026-09','period_label':'September 2026','generated_at':'2026-11-02T10:00:00Z','results':[{'id':'b'}]}
            refresh.save_issue(newer,root)
            refresh.save_issue(older,root)
            self.assertEqual(json.loads((root/'latest.json').read_text())['month'],'2026-10')
            self.assertEqual(json.loads((root/'index.json').read_text())['latest'],'2026-10')
            self.assertTrue((root/'archive'/'2026-09.json').exists())

    def test_demo_has_no_false_rankings(self):
        import json
        data=json.loads((Path(__file__).resolve().parents[1]/'site/data/latest.json').read_text())
        if data['mode']=='demo':
            self.assertEqual(len(data['results']),50)
            self.assertTrue(all(x['rank'] is None and x['score'] is None for x in data['results']))


if __name__=='__main__':
    unittest.main()
