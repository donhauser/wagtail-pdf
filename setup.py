import setuptools

from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setuptools.setup(
    name='wagtail-pdf-view',
    version='1.0.0',
    description='PDF rendering views for the Wagtail CMS',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Jonas Donhauser',
    #author_email='',
    url='https://github.com/donhauser/wagtail-pdf',
    packages=['wagtail_pdf_view'],
    package_data={'': ['LICENSE', 'templates/*', 'static/*']},
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=["wagtail", "django-weasyprint"],
    extras_require = {
        'django-tex':["django-tex"],
    },
)
