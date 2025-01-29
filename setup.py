import setuptools

import os


directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()
    
def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths


setuptools.setup(
    name='wagtail-pdf-view',
    version='2.0.0',
    description='PDF rendering views for the Wagtail CMS',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Jonas Donhauser',
    #author_email='',
    url='https://github.com/donhauser/wagtail-pdf',
    packages=[
        'wagtail_pdf_view',
        'wagtail_pdf_view_tex',
    ],
    package_data={
        '': ['LICENSE']
        + package_files('wagtail_pdf_view/static')
        + package_files('wagtail_pdf_view_tex/templates')
    },
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=["wagtail", "django-weasyprint"],
    extras_require = {
        'django-tex':["django-tex"],
    },
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: Django",
        "Framework :: Django :: 4",
        "Framework :: Django :: 5.0",
        "Framework :: Django :: 5.1",
        "Framework :: Wagtail",
        "Framework :: Wagtail :: 6",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP :: Site Management",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ]
)
