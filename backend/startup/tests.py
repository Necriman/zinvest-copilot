import json
import uuid
from unittest.mock import patch
from django.test import TestCase
from accounts.models import User
from accounts.jwt_utils import encode_access_token
from ai_engine.gemini import GeminiResult
from .models import StartupProfile, Employee, CashFlowEntry, FounderConnection, BusinessPost, FounderMessage


class StartupWorkspaceTests(TestCase):
    def setUp(self):
        self.owner=User.objects.create_user(email='owner@example.test',password='Str0ng-Passphrase!')
        self.peer=User.objects.create_user(email='peer@example.test',password='Str0ng-Passphrase!')
        self.other=User.objects.create_user(email='other@example.test',password='Str0ng-Passphrase!')
        self.p=StartupProfile.objects.create(user=self.owner,name='Owner company',public_visible=True)
        self.q=StartupProfile.objects.create(user=self.peer,name='Peer company',public_visible=True,public_summary='Public summary',onboarding={'secret':'private'},demand={'secret':'private'})
        StartupProfile.objects.create(user=self.other,name='Private company')

    def req(self,method,path,data=None,user=None):
        return getattr(self.client,method)('/api/startup/'+path,data=json.dumps({} if data is None else data),content_type='application/json',HTTP_AUTHORIZATION='Bearer '+encode_access_token(user or self.owner,uuid.uuid4()))

    def get(self,path,user=None):
        return self.client.get('/api/startup/'+path,HTTP_AUTHORIZATION='Bearer '+encode_access_token(user or self.owner,uuid.uuid4()))

    def test_workspace_fields_survive_readback(self):
        payload={'operating_mode':'offline','locations':[{'country':'Uzbekistan','region':'Tashkent','address':'Example street 1'}],'demand':{'level':'high','evidence':'20 enquiries this week','observed_on':'2026-08-19','inquiries':20,'orders':8}}
        self.assertEqual(self.req('put','profile',payload).status_code,200)
        result=self.get('profile').json()
        self.assertEqual(result['locations'],payload['locations'])
        self.assertEqual(result['demand']['source'],'founder')
        self.assertEqual(result['demand']['orders'],8)

    def test_invalid_workspace_is_atomic(self):
        r=self.req('put','profile',{'name':'bad','operating_mode':'offline','locations':[{'country':'UZ'}]})
        self.assertEqual(r.status_code,400)
        self.p.refresh_from_db();self.assertEqual(self.p.name,'Owner company');self.assertEqual(self.p.operating_mode,'online')

    def test_invalid_input_does_not_crash(self):
        self.assertEqual(self.req('put','profile',[]).status_code,400)
        for value in ['NaN','Infinity','-2','1000000000000']:
            self.assertEqual(self.req('post','cashflow',{'entry_type':'spending','amount':value}).status_code,400)
        self.assertEqual(self.req('post','cashflow',{'entry_type':'spending','amount':'5','occurred_on':'2026-02-31'}).status_code,400)

    def test_month_isolated_from_other_months_and_users(self):
        for user,month,kind,amount in [(self.owner,8,'revenue',100),(self.owner,8,'spending',25),(self.owner,9,'revenue',900),(self.peer,8,'revenue',500)]:
            CashFlowEntry.objects.create(user=user,occurred_on=f'2026-{month:02}-01',entry_type=kind,category='Test',amount=amount)
        data=self.get('cashflow?period=2026-08').json()
        self.assertEqual(len(data['entries']),2)
        self.assertEqual(data['totals'],{'revenue':'100.00','spending':'25.00','net':'75.00'})

    def test_employee_teams_and_ownership(self):
        r=self.req('post','employees',{'full_name':'Test Person','team':'Design','salary':'1200.25'})
        self.assertEqual(r.status_code,201);emp=r.json()['employee']
        self.assertEqual(emp['team'],'Design')
        self.assertEqual(r.json()['total_salary'],'1200.25')
        self.assertEqual(self.req('put','employees/'+emp['id'],{'team':'Other'},user=self.peer).status_code,404)
        self.assertEqual(self.req('put','employees/'+emp['id'],{'team':'Product'}).json()['employee']['team'],'Product')

    def test_product_kind(self):
        r=self.req('post','products',{'name':'Support','kind':'subscription','price':'9.99'})
        self.assertEqual(r.status_code,201);self.assertEqual(r.json()['product']['kind'],'subscription')
        self.assertEqual(self.req('post','products',{'name':'Invalid','kind':'nonsense'}).status_code,400)

    INTAKE={'name':'Qarz','location':'Tashkent, Uzbekistan','problem':'Friends forget who owes what','market':'b2c',
            'description':'A Telegram bot that tracks debts between friends','revenue_model':'Freemium, 15 000 UZS a month',
            'stage':'idea','team':'solo','alternatives':''}
    RESEARCH=('```json\n{"verdict":"promising","summary":"Room for it in Tashkent.","demand":"Young people lend often.",'
              '"competitors":[{"name":"Splitwise","what":"Splits bills","where":"online","url":"https://www.splitwise.com"},'
              '{"name":"Made up","what":"","where":"","url":"javascript:alert(1)"}],"gap":"Uzbek and Telegram first.",'
              '"risks":["Low willingness to pay"],"next_steps":["Interview 20 students","Ship a bot prototype","Test the price"],'
              '"enabled":["advisor","finance","demand","nonsense"],"enable_tasks":false}\n```')

    def test_onboarding_requires_the_intake_answers(self):
        self.assertEqual(self.req('post','onboarding',{'answers':{'description':'Hi'}}).status_code,400)
        self.assertEqual(self.req('post','onboarding',{'answers':{**self.INTAKE,'team':'huge'}}).status_code,400)

    def test_onboarding_checks_the_market_with_search(self):
        sources=[{'title':'spot.uz','url':'https://example.org/a'}]
        with patch('startup.research.gemini.generate',return_value=GeminiResult(self.RESEARCH,'test',10,10,sources=sources)) as gen:
            result=self.req('post','onboarding',{'answers':self.INTAKE,'language':'ru'})
        self.assertEqual(result.status_code,200)
        self.assertIsNotNone(gen.call_args.kwargs['config'].tools)  # Google Search was on
        research=result.json()['blocks']['research']
        self.assertEqual(research['verdict'],'promising')
        self.assertTrue(research['searched'])
        self.assertEqual(research['sources'],sources)
        self.assertEqual(research['competitors'][0]['url'],'https://www.splitwise.com')
        self.assertEqual(research['competitors'][1]['url'],'')  # only real web links survive
        self.assertEqual(result.json()['blocks']['analysis'],'Room for it in Tashkent.')
        self.assertEqual(result.json()['blocks']['enabled'],['advisor','finance','demand','roadmap'])
        self.p.refresh_from_db()
        self.assertEqual(self.p.name,'Qarz')
        self.assertNotIn('extra',self.p.onboarding)

    def test_onboarding_falls_back_to_no_search_then_to_a_default_workspace(self):
        from ai_engine.gemini import GeminiError
        plain=GeminiResult(self.RESEARCH,'test',10,10)
        with patch('startup.research.gemini.generate',side_effect=[GeminiError('timed out'),plain]):
            result=self.req('post','onboarding',{'answers':self.INTAKE})
        self.assertEqual(result.status_code,200)
        self.assertFalse(result.json()['blocks']['research']['searched'])
        self.assertEqual(result.json()['blocks']['research']['sources'],[])
        with patch('startup.research.gemini.generate',side_effect=GeminiError('down')):
            result=self.req('post','onboarding',{'answers':self.INTAKE})
        self.assertEqual(result.status_code,200)
        self.assertNotIn('research',result.json()['blocks'])
        self.assertIn('locations',result.json()['blocks']['enabled'])

    def test_employee_import_is_all_or_nothing(self):
        rows=[{'full_name':'A One','team':'Kitchen','salary':'800'},{'full_name':'','salary':'5'},{'full_name':'C Three','salary':'-1'}]
        r=self.req('post','employees/import',{'rows':rows})
        self.assertEqual(r.status_code,400)
        self.assertEqual([e['row'] for e in r.json()['errors']],[2,3])
        self.assertEqual(Employee.objects.count(),0)
        r=self.req('post','employees/import',{'rows':[rows[0],{'full_name':'B Two','role':'Chef'}]})
        self.assertEqual(r.status_code,201)
        self.assertEqual(r.json()['imported'],2);self.assertEqual(r.json()['total_salary'],'800.00')
        self.assertEqual(Employee.objects.filter(user=self.peer).count(),0)

    def test_product_import_validates_and_limits(self):
        self.assertEqual(self.req('post','products/import',{'rows':[]}).status_code,400)
        self.assertEqual(self.req('post','products/import',{'rows':[{'name':'x'}]*1001}).status_code,400)
        self.assertEqual(self.req('post','products/import',{'rows':[{'name':'Plov','kind':'dish'}]}).status_code,400)
        r=self.req('post','products/import',{'rows':[{'name':'Plov','price':'45000'},{'name':'Delivery','kind':'service'}]})
        self.assertEqual(r.status_code,201);self.assertEqual(len(r.json()['products']),2)

    def test_existing_workspace_gets_new_block_once(self):
        self.p.onboarding_completed=True;self.p.blocks={'enabled':['employees','advisor','finance']};self.p.save()
        self.assertEqual(self.get('profile').json()['blocks']['enabled'],['employees','advisor','roadmap','matches','finance'])
        self.assertEqual(self.req('put','profile',{'blocks':['finance','employees']}).json()['blocks']['enabled'],['finance','employees'])
        self.assertEqual(self.get('profile').json()['blocks']['enabled'],['finance','employees'])

    def test_directory_only_exposes_public_data(self):
        Employee.objects.create(user=self.peer,full_name='Secret staff',salary=999,team='Secret team')
        result=self.get('network').json()['founders']
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['name'],'Peer company')
        self.assertEqual(result[0]['team_size'],1)
        raw=json.dumps(result)
        for secret in ['private','Secret staff','salary','onboarding','demand','@example.test']:
            self.assertNotIn(secret,raw)

    def test_connection_requires_consent(self):
        r=self.req('post','network/connect/'+str(self.peer.id));cid=r.json()['id']
        self.assertFalse(r.json()['accepted'])
        self.assertEqual(self.req('patch','network/connections/'+cid).status_code,403)
        self.assertEqual(self.req('post','network/connections/'+cid+'/messages',{'text':'Hi'}).status_code,404)
        self.assertEqual(self.req('patch','network/connections/'+cid,user=self.peer).status_code,200)
        self.assertEqual(self.req('post','network/connections/'+cid+'/messages',{'text':'Hi'}).status_code,200)
        self.assertEqual(self.get('network/connections/'+cid+'/messages',user=self.peer).json()['messages'][0]['mine'],False)
        self.assertEqual(self.get('network/connections/'+cid+'/messages',user=self.other).status_code,404)

    def test_reverse_request_is_idempotent(self):
        a=self.req('post','network/connect/'+str(self.peer.id)).json()
        b=self.req('post','network/connect/'+str(self.owner.id),user=self.peer).json()
        self.assertEqual(a['id'],b['id']);self.assertFalse(b['accepted'])
        self.assertEqual(FounderConnection.objects.count(),1)

    def test_messages_latest_window_remains_chronological(self):
        c=FounderConnection.objects.create(sender=self.owner,recipient=self.peer,accepted=True)
        FounderMessage.objects.bulk_create([FounderMessage(connection=c,sender=self.owner,text=str(i)) for i in range(205)])
        rows=self.get('network/connections/'+str(c.id)+'/messages').json()['messages']
        self.assertEqual(len(rows),200);self.assertEqual(rows[-1]['text'],'204');self.assertEqual(rows[0]['text'],'5')

    def test_posts_ownership_and_visibility(self):
        p=self.req('post','network/posts',{'title':'Hello','text':'We launched'}).json()
        self.assertEqual(self.req('delete','network/posts/'+p['id'],user=self.peer).status_code,404)
        self.req('put','profile',{'public_visible':False})
        self.assertEqual(self.get('network/posts',user=self.peer).json()['posts'],[])
        self.assertEqual(self.req('post','network/posts',{'title':'Hidden'}).status_code,400)
        self.assertEqual(self.req('delete','network/posts/'+p['id']).status_code,200)

    def test_recommendations_cannot_invent_founders(self):
        with patch('startup.network.gemini.generate',return_value=GeminiResult(json.dumps({'matches':[{'id':str(self.peer.id),'reason':'Shared work'},{'id':'invented','reason':'Fake'}]}),'test',10,10)):
            result=self.req('post','network/recommendations').json()
        self.assertEqual(result['matches'],[{'id':str(self.peer.id),'reason':'Shared work'}])

    def test_missing_ai_does_not_fabricate_matches(self):
        with patch('startup.network.gemini.generate',return_value=GeminiResult('[STUB]','stub',10,10,is_stub=True)):
            result=self.req('post','network/recommendations').json()
        self.assertEqual(result['matches'],[]);self.assertTrue(result['is_stub'])

    def test_all_new_surfaces_require_auth(self):
        for path in ['network','network/posts','profile']:
            self.assertEqual(self.client.get('/api/startup/'+path).status_code,401)

    def test_invalid_month_is_rejected(self):
        self.assertEqual(self.get('cashflow?period=2026-13').status_code,400)
        self.assertEqual(self.get('summary?period=oops').status_code,400)

    def test_assignment_dates_are_validated_before_write(self):
        employee=Employee.objects.create(user=self.owner,full_name='Test')
        data={'employee':str(employee.id),'title':'Task','start_date':'2026-09-10','end_date':'2026-09-01'}
        self.assertEqual(self.req('post','assignments',data).status_code,400)
        data['end_date']='2026-09-12'
        r=self.req('post','assignments',data)
        self.assertEqual(r.status_code,201)
        self.assertEqual(self.req('patch','assignments/'+r.json()['assignment']['id'],{'end_date':'bad'}).status_code,400)

    def test_practice_grades_without_unlocking_or_awarding_coins(self):
        from learning.models import Unit,Lesson,LessonProgress,UserStats
        unit=Unit.objects.create(code='01',slug='practice',title='Unit',order=1,test_questions=[{'id':'q1','prompt':'2 + 2?','choices':['3','4'],'answer_index':1,'explanation':'Two pairs make four.'}])
        lesson=Lesson.objects.create(unit=unit,slug='one',title='Lesson',order=1)
        url=f'/api/learning/lessons/{lesson.id}/practice'
        auth={'HTTP_AUTHORIZATION':'Bearer '+encode_access_token(self.owner,uuid.uuid4())}
        r=self.client.get(url,**auth)
        self.assertNotIn('answer_index',r.json()['questions'][0])
        r=self.client.post(url,data=json.dumps({'question_id':'q1','choice_index':1}),content_type='application/json',**auth)
        self.assertTrue(r.json()['correct'])
        self.assertEqual(LessonProgress.objects.count(),0)
        self.assertEqual(UserStats.objects.count(),0)
        r=self.client.post(url,data=json.dumps({'question_id':'q1','choice_index':99}),content_type='application/json',**auth)
        self.assertEqual(r.status_code,400)

    def test_challenges_keep_answers_private_until_submission(self):
        from learning.models import Unit
        Unit.objects.create(code='01',slug='finance-fundamentals',title='Finance',order=1)
        auth={'HTTP_AUTHORIZATION':'Bearer '+encode_access_token(self.owner,uuid.uuid4())}
        url='/api/learning/challenges'
        data=self.client.get(url,**auth).json()
        self.assertNotIn('answer_index',data['challenges'][0])
        self.assertTrue(self.client.post(url,data=json.dumps({'id':'budget-buffer','choice_index':1}),content_type='application/json',**auth).json()['correct'])
