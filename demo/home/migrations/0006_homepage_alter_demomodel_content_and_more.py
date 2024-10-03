# Generated by Django 4.0 on 2024-10-03 13:25

from django.db import migrations, models
import django.db.models.deletion
import wagtail.blocks
import wagtail.contrib.table_block.blocks
import wagtail.fields
import wagtail.images.blocks


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0078_referenceindex'),
        ('home', '0005_auto_20210729_1649'),
    ]

    operations = [
        migrations.AlterField(
            model_name='demomodel',
            name='content',
            field=wagtail.fields.StreamField([('heading', wagtail.blocks.CharBlock(form_classname='full title')), ('text', wagtail.blocks.RichTextBlock())], blank=True, use_json_field=True),
        ),
        migrations.AlterField(
            model_name='htmlandpdfpage',
            name='content',
            field=wagtail.fields.StreamField([('heading', wagtail.blocks.CharBlock(form_classname='full title')), ('text', wagtail.blocks.RichTextBlock()), ('image', wagtail.images.blocks.ImageChooserBlock()), ('table', wagtail.contrib.table_block.blocks.TableBlock())], blank=True, use_json_field=True),
        ),
        migrations.AlterField(
            model_name='simplepdfpage',
            name='content',
            field=wagtail.fields.StreamField([('heading', wagtail.blocks.CharBlock(form_classname='full title')), ('text', wagtail.blocks.RichTextBlock())], blank=True, use_json_field=True),
        ),
    ]
