"""Populate the isolated local preview database only."""
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from accounts.models import User
from startup.models import StartupProfile,Employee,Product,CashFlowEntry,Assignment,StartupTodo,BusinessPost


class Command(BaseCommand):
    def handle(self,*args,**kwargs):
        if Path(settings.DATABASES['default']['NAME']).name!='preview.sqlite3':
            raise CommandError('This command only works with SQLITE_PATH pointing to preview.sqlite3.')
        user,created=User.objects.get_or_create(email='demo@zinvest.local',defaults={'first_name':'Demo','last_name':'Founder'})
        if created:
            user.set_password('Zinvest-Demo-2026!');user.save()
        p,_=StartupProfile.objects.get_or_create(user=user)
        p.name='Zinvest Demo';p.industry='Education';p.onboarding_completed=True
        p.onboarding={'problem':'Accessible learning','stage':'mvp','market':'b2c','revenue_model':'Subscription','description':'A demonstration of a learning business.'}
        p.blocks={'enabled':['employees','tasks','products','finance','advisor','todo','demand','locations'],'analysis':'Demo workspace','source':'demo'}
        p.public_summary='Demonstration company for exploring the Zinvest workspace.';p.public_visible=True
        p.demand={'level':'moderate','evidence':'Demo: 24 enquiries and 8 orders this month.','observed_on':timezone.localdate().isoformat(),'inquiries':24,'orders':8,'source':'founder'}
        p.locations=[{'country':'Uzbekistan','region':'','address':''}];p.save()
        if not Employee.objects.filter(user=user).exists():
            for name,position,role,team,salary in [('Demo Designer','Designer','Product design','Product',700),('Demo Engineer','Engineer','Platform development','Product',1200),('Demo Marketer','Marketer','Content and community','Growth',600)]:
                Employee.objects.create(user=user,full_name=name,position=position,role=role,team=team,salary=salary)
            Product.objects.create(user=user,name='Demo Pro plan',price=12,kind='subscription')
            CashFlowEntry.objects.create(user=user,entry_type='revenue',category='Demo subscriptions',amount=4800)
            CashFlowEntry.objects.create(user=user,entry_type='spending',category='Demo rent',amount=600,cost_type='fixed')
            CashFlowEntry.objects.create(user=user,entry_type='spending',category='Demo campaign',amount=240,cost_type='variable')
            Assignment.objects.create(employee=user.startup_employees.first(),title='Demo: review onboarding',start_date=timezone.localdate(),end_date=timezone.localdate())
            StartupTodo.objects.create(user=user,title='Demo: interview five customers')
        for i,(name,company,industry,summary) in enumerate([('Demo Partner','Demo Creative Studio','Design','A sample creative team for brand and product design.'),('Demo Founder','Demo Local Market','Retail','A sample marketplace connecting local makers with customers.')]):
            peer,_=User.objects.get_or_create(email=f'preview-{i}@zinvest.local',defaults={'first_name':name})
            StartupProfile.objects.update_or_create(user=peer,defaults={'name':company,'industry':industry,'public_summary':summary,'public_visible':True})
            BusinessPost.objects.get_or_create(user=peer,title=f'{company} — demo announcement',defaults={'text':summary+' This is demonstration content.'})
        self.stdout.write('Isolated preview data ready.')
