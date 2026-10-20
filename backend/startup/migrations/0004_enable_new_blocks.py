from django.db import migrations


def enable_new_blocks(apps, schema_editor):
    Profile=apps.get_model('startup','StartupProfile')
    for p in Profile.objects.filter(onboarding_completed=True).iterator():
        blocks=p.blocks or {}
        enabled=blocks.get('enabled',[])
        p.blocks={**blocks,'enabled':list(dict.fromkeys(enabled+['demand','locations']))}
        p.save(update_fields=['blocks'])


class Migration(migrations.Migration):
    dependencies=[('startup','0003_cashflowentry_cost_type_employee_team_product_kind_and_more')]
    operations=[migrations.RunPython(enable_new_blocks,migrations.RunPython.noop)]
