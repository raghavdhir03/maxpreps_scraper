from setuptools import setup, find_packages

setup(
    name='maxpreps-scraper',                       # Package name (pip install maxpreps-scraper)
    version='0.1.0',                               # Initial version
    packages=find_packages(),                      # Automatically find all modules inside your package folder
    install_requires=[
        'requests',
        'beautifulsoup4',
        'tqdm',
        'pandas',
        'lxml',
        'html5lib',
    ],
    author='Raghav Dhir',
    author_email='dhir.raghav@gmail.com',         
    description='A Python scraper for MaxPreps high school sports data',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown', # So Markdown renders on PyPI
    url='https://github.com/raghavdhir03/maxpreps_scraper',  # Your GitHub repo
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)
