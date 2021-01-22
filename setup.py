import setuptools

setuptools.setup(
    name='wagtail-pdf-view',
    version='0.1.0',
    description='PDF rendering views for the Wagtail CMS',
    author='Jonas Donhauser',
    #author_email='',
    url='https://github.com/donhauser/wagtail-pdf',
    packages=['wagtail_pdf_view'],
    package_data={'': ['LICENSE', 'templates/*']},
    include_package_data=True,
    python_requires=">=3.6",
    install_requires=["wagtail"],
    extras_require = {
        'weasyprint':["django-weasyprint"],
        'django-tex':["django-tex"],
    },
)
